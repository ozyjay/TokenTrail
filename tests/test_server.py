import importlib
import json
import sys
import threading
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError
from token_trail.adapters.ollama import OllamaStatus
from token_trail.config import RuntimeConfig


def make_config(
    backend: str = "scripted",
    *,
    ollama_warmup_enabled: bool = True,
    ollama_warmup_timeout_seconds: float = 45.0,
    ollama_keep_alive: str = "30m",
    ollama_reasoning_retry_tokens: dict[str, int] | None = None,
    hf_trace_enabled: bool = False,
    hf_trace_timeout_seconds: float = 20.0,
) -> RuntimeConfig:
    return RuntimeConfig(
        backend=backend,
        host="127.0.0.1",
        port=3100,
        backend_port=8100,
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen3:4b",
        ollama_models=("qwen3:4b", "qwen3:1.7b"),
        ollama_num_predict=256,
        ollama_temperature=0.4,
        ollama_timeout_seconds=20.0,
        ollama_disable_thinking=True,
        ollama_warmup_enabled=ollama_warmup_enabled,
        ollama_warmup_timeout_seconds=ollama_warmup_timeout_seconds,
        ollama_keep_alive=ollama_keep_alive,
        ollama_reasoning_retry_tokens=ollama_reasoning_retry_tokens,
        vllm_base_url="http://127.0.0.1:8000/v1",
        vllm_model="Qwen/Qwen3-4B",
        vllm_models=("Qwen/Qwen3-4B",),
        hf_trace_enabled=hf_trace_enabled,
        hf_trace_url="http://127.0.0.1:8600/api/trace",
        hf_trace_model="Qwen/Qwen2.5-1.5B-Instruct",
        hf_trace_top_k=5,
        hf_trace_max_new_tokens=48,
        hf_trace_temperature=0.3,
        hf_trace_timeout_seconds=hf_trace_timeout_seconds,
    )


class FakeOllamaAdapter:
    def __init__(
        self,
        status: OllamaStatus,
        generated_text: str = "A live robot story.",
        warmup_error: bool = False,
    ) -> None:
        self._status = status
        self.generated_text = generated_text
        self.generate_calls = []
        self.warmup_error = warmup_error
        self.warmup_calls = []

    def status(self) -> OllamaStatus:
        return self._status

    def generate(self, model: str, prompt: str, **kwargs) -> str:
        self.generate_calls.append((model, prompt, kwargs))
        if self.generated_text == "RAISE":
            raise AdapterError("boom")
        return self.generated_text

    def warmup(self, model: str, **kwargs) -> None:
        self.warmup_calls.append((model, kwargs))
        if self.warmup_error:
            raise AdapterError("boom")


class FakeHfTraceAdapter:
    def __init__(self, available: bool = True, trace: dict | None = None, error: bool = False) -> None:
        self.available = available
        self.trace = trace or {
            "mode": "hf-live-trace",
            "model": "Qwen/Qwen2.5-1.5B-Instruct",
            "prompt": "Write a short story about a robot at university.",
            "prompt_tokens": ["Write", " a", " short"],
            "steps": [
                {
                    "selected_token": "A",
                    "candidates": [
                        {"token": "A", "probability": 0.62},
                        {"token": "The", "probability": 0.21},
                    ],
                    "explanation": "Top returned alternatives from the local model for this token position.",
                }
            ],
        }
        self.error = error
        self.generate_calls = []

    def status(self, **kwargs):
        import token_trail.adapters.hf_trace as hf_trace

        return hf_trace.HfTraceStatus(available=self.available)

    def generate_trace(self, **kwargs) -> dict:
        self.generate_calls.append(kwargs)
        if self.error:
            raise AdapterError("boom")
        return self.trace


def import_server_module():
    sys.modules.pop("token_trail.server", None)
    return importlib.import_module("token_trail.server")


def test_importing_server_does_not_load_config_or_contact_ollama(monkeypatch) -> None:
    import token_trail.config

    monkeypatch.setattr(token_trail.config, "load_config", lambda: (_ for _ in ()).throw(AssertionError("loaded")))

    import_server_module()


def test_server_main_uses_loaded_config(monkeypatch) -> None:
    server = import_server_module()
    calls = []

    monkeypatch.setattr(sys, "argv", ["token-trail"])
    monkeypatch.setattr(server, "load_config", lambda: make_config())
    monkeypatch.setattr(server, "run_server", lambda host, port, config: calls.append((host, port, config.port)))

    server.main()

    assert calls == [("127.0.0.1", 3100, 3100)]


def test_server_cli_args_override_loaded_config(monkeypatch) -> None:
    server = import_server_module()
    calls = []

    monkeypatch.setattr(sys, "argv", ["token-trail", "--host", "0.0.0.0", "--port", "9000"])
    monkeypatch.setattr(server, "load_config", lambda: make_config())
    monkeypatch.setattr(server, "run_server", lambda host, port, config: calls.append((host, port, config.port)))

    server.main()

    assert calls == [("0.0.0.0", 9000, 3100)]


def test_build_server_state_marks_ollama_models_available() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",))),
    )

    options = {option.id: option for option in state.runtime_options}

    assert options["ollama:qwen3:4b"].available
    assert not options["ollama:qwen3:1.7b"].available
    assert state.ollama_status.available


def test_build_server_state_marks_hf_trace_available_when_enabled_and_probe_succeeds() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(hf_trace_enabled=True),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=False, models=())),
        hf_trace_adapter=FakeHfTraceAdapter(available=True),
    )

    options = {option.id: option for option in state.runtime_options}

    assert options["hf-trace:Qwen/Qwen2.5-1.5B-Instruct"].available


def test_runtime_and_health_endpoints_report_ollama_availability() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",))),
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        base_url = f"http://127.0.0.1:{httpd.server_port}"
        runtime_payload = _get_json(f"{base_url}/api/runtime")
        health_payload = _get_json(f"{base_url}/health")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    options = {option["id"]: option for option in runtime_payload["options"]}
    assert options["ollama:qwen3:4b"]["available"]
    assert not options["ollama:qwen3:1.7b"]["available"]
    assert health_payload["status"] == "ok"
    assert health_payload["runtime"] == "scripted:prepared-traces"
    assert health_payload["ollama_available"]
    assert health_payload["ollama_models"] == ["qwen3:4b"]


def test_generate_trace_returns_live_response() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(
        OllamaStatus(available=True, models=("qwen3:4b",)),
        generated_text="A robot joined orientation and waved.",
    )
    state = server.build_server_state(
        make_config(backend="ollama", ollama_reasoning_retry_tokens={"qwen3:4b": 384}),
        ollama_adapter=adapter,
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {"runtime_id": "ollama:qwen3:4b", "trace_id": "robot-university"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload == {
        "mode": "live",
        "runtime_id": "ollama:qwen3:4b",
        "fallback_used": False,
        "generated_text": "A robot joined orientation and waved.",
    }
    assert adapter.generate_calls == [
        (
            "qwen3:4b",
            "Write a short story about a robot at university.",
            {
                "timeout_seconds": 20.0,
                "max_tokens": 256,
                "temperature": 0.4,
                "disable_thinking": True,
                "reasoning_retry_tokens": 384,
            },
        )
    ]


def test_generate_trace_returns_hf_live_trace_response_using_curated_prompt() -> None:
    server = import_server_module()
    hf_adapter = FakeHfTraceAdapter()
    state = server.build_server_state(
        make_config(backend="hf-trace", hf_trace_enabled=True, hf_trace_timeout_seconds=7.5),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=False, models=())),
        hf_trace_adapter=hf_adapter,
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {
                "runtime_id": "hf-trace:Qwen/Qwen2.5-1.5B-Instruct",
                "trace_id": "robot-university",
                "prompt": "This visitor prompt must not be used.",
            },
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "hf-live-trace"
    assert payload["runtime_id"] == "hf-trace:Qwen/Qwen2.5-1.5B-Instruct"
    assert payload["fallback_used"] is False
    assert payload["trace"]["mode"] == "hf-live-trace"
    assert payload["trace"]["steps"][0]["selected_token"] == "A"
    assert hf_adapter.generate_calls == [
        {
            "prompt": "Write a short story about a robot at university.",
            "model": "Qwen/Qwen2.5-1.5B-Instruct",
            "max_new_tokens": 48,
            "top_k": 5,
            "temperature": 0.3,
            "timeout_seconds": 7.5,
        }
    ]


def test_hf_trace_error_uses_scripted_fallback() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(backend="hf-trace", hf_trace_enabled=True),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=False, models=())),
        hf_trace_adapter=FakeHfTraceAdapter(available=True, error=True),
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {"runtime_id": "hf-trace:Qwen/Qwen2.5-1.5B-Instruct", "trace_id": "robot-university"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "scripted-fallback"
    assert payload["runtime_id"] == "hf-trace:Qwen/Qwen2.5-1.5B-Instruct"
    assert payload["fallback_used"]
    assert payload["trace"]["id"] == "robot-university"


def test_malformed_hf_trace_uses_scripted_fallback() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(backend="hf-trace", hf_trace_enabled=True),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=False, models=())),
        hf_trace_adapter=FakeHfTraceAdapter(available=True, trace={"mode": "hf-live-trace", "steps": []}),
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {"runtime_id": "hf-trace:Qwen/Qwen2.5-1.5B-Instruct", "trace_id": "robot-university"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "scripted-fallback"
    assert payload["trace"]["id"] == "robot-university"


def test_generate_trace_uses_custom_prompt_for_available_ollama() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(
        OllamaStatus(available=True, models=("qwen3:4b",)),
        generated_text="A custom live answer.",
    )
    state = server.build_server_state(
        make_config(backend="ollama"),
        ollama_adapter=adapter,
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {
                "runtime_id": "ollama:qwen3:4b",
                "trace_id": "robot-university",
                "prompt": "  Write a tiny poem about a campus robot.  ",
            },
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "live"
    assert payload["generated_text"] == "A custom live answer."
    assert adapter.generate_calls[0][1] == "Write a tiny poem about a campus robot."


def test_generate_trace_ignores_custom_prompt_for_scripted_runtime() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",)))
    state = server.build_server_state(make_config(), ollama_adapter=adapter)
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {
                "runtime_id": "scripted:prepared-traces",
                "trace_id": "robot-university",
                "prompt": "Use this only if the scripted path is broken.",
            },
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "scripted"
    assert payload["trace"]["prompt"] == "Write a short story about a robot at university."
    assert adapter.generate_calls == []


def test_generation_failure_uses_scripted_fallback() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",)), generated_text="RAISE")
    state = server.build_server_state(make_config(backend="ollama"), ollama_adapter=adapter)
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {"runtime_id": "ollama:qwen3:4b", "trace_id": "robot-university"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "scripted-fallback"
    assert payload["runtime_id"] == "ollama:qwen3:4b"
    assert payload["fallback_used"]
    assert payload["message"] == "Live generation unavailable"
    assert payload["trace"]["id"] == "robot-university"


def test_unavailable_ollama_runtime_uses_scripted_fallback_without_generation() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",)))
    state = server.build_server_state(make_config(backend="ollama"), ollama_adapter=adapter)
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {"runtime_id": "ollama:qwen3:1.7b", "trace_id": "robot-university"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "scripted-fallback"
    assert payload["trace"]["id"] == "robot-university"
    assert adapter.generate_calls == []


def test_unknown_runtime_returns_400() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",))),
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {"runtime_id": "ollama:nope", "trace_id": "robot-university"},
            expected_status=400,
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert "Unknown runtime option" in payload["error"]


def test_runtime_warmup_returns_ready_for_available_ollama() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",)))
    config = make_config(backend="ollama", ollama_warmup_timeout_seconds=33.5, ollama_keep_alive="12m")
    state = server.build_server_state(config, ollama_adapter=adapter)
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/runtime/warmup",
            {"runtime_id": "ollama:qwen3:4b"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload == {
        "status": "ready",
        "runtime_id": "ollama:qwen3:4b",
        "message": "Local model warmed",
    }
    assert adapter.warmup_calls == [("qwen3:4b", {"timeout_seconds": 33.5, "keep_alive": "12m"})]


def test_runtime_warmup_skips_scripted_runtime() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",)))
    state = server.build_server_state(make_config(), ollama_adapter=adapter)
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/runtime/warmup",
            {"runtime_id": "scripted:prepared-traces"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload == {
        "status": "skipped",
        "runtime_id": "scripted:prepared-traces",
        "message": "Scripted runtime does not need warm-up",
    }
    assert adapter.warmup_calls == []


def test_runtime_warmup_returns_fallback_on_adapter_error() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",)), warmup_error=True)
    config = make_config(backend="ollama", ollama_warmup_timeout_seconds=21.0, ollama_keep_alive="8m")
    state = server.build_server_state(config, ollama_adapter=adapter)
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/runtime/warmup",
            {"runtime_id": "ollama:qwen3:4b"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload == {
        "status": "fallback",
        "runtime_id": "ollama:qwen3:4b",
        "message": "Could not warm local model; scripted fallback remains available",
    }
    assert adapter.warmup_calls == [("qwen3:4b", {"timeout_seconds": 21.0, "keep_alive": "8m"})]


def test_runtime_warmup_skips_when_disabled() -> None:
    server = import_server_module()
    adapter = FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",)))
    state = server.build_server_state(
        make_config(backend="ollama", ollama_warmup_enabled=False),
        ollama_adapter=adapter,
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/runtime/warmup",
            {"runtime_id": "ollama:qwen3:4b"},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload == {
        "status": "skipped",
        "runtime_id": "ollama:qwen3:4b",
        "message": "Ollama warm-up disabled",
    }
    assert adapter.warmup_calls == []


def test_runtime_warmup_returns_400_for_unknown_runtime() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(),
        ollama_adapter=FakeOllamaAdapter(OllamaStatus(available=True, models=("qwen3:4b",))),
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/runtime/warmup",
            {"runtime_id": "ollama:nope"},
            expected_status=400,
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert "Unknown runtime option" in payload["error"]


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict, expected_status: int = 200) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2) as response:
            assert response.status == expected_status
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        if not hasattr(error, "code") or error.code != expected_status:
            raise
        return json.loads(error.read().decode("utf-8"))
