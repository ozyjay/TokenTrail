import importlib
import json
import sys
import threading
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError
from token_trail.adapters.ollama import OllamaStatus
from token_trail.config import RuntimeConfig


def make_config(backend: str = "scripted") -> RuntimeConfig:
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
        vllm_base_url="http://127.0.0.1:8000/v1",
        vllm_model="Qwen/Qwen3-4B",
        vllm_models=("Qwen/Qwen3-4B",),
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
            },
        )
    ]


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
    state = server.build_server_state(make_config(backend="ollama"), ollama_adapter=adapter)
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
    assert adapter.warmup_calls == [("qwen3:4b", {"timeout_seconds": 45.0, "keep_alive": "30m"})]


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
    state = server.build_server_state(make_config(backend="ollama"), ollama_adapter=adapter)
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
    assert adapter.warmup_calls == [("qwen3:4b", {"timeout_seconds": 45.0, "keep_alive": "30m"})]


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
