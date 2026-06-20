import importlib
import json
import sys
import threading
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError
from token_trail.config import RuntimeConfig


def make_config(
    backend: str = "scripted",
    *,
    hf_trace_enabled: bool = False,
    hf_trace_timeout_seconds: float = 20.0,
) -> RuntimeConfig:
    return RuntimeConfig(
        backend=backend,
        host="127.0.0.1",
        port=3100,
        backend_port=8100,
        hf_trace_enabled=hf_trace_enabled,
        hf_trace_url="http://127.0.0.1:8600/api/trace",
        hf_trace_model="Qwen/Qwen2.5-1.5B-Instruct",
        hf_trace_models=("Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-0.5B-Instruct"),
        hf_trace_top_k=5,
        hf_trace_max_new_tokens=96,
        hf_trace_temperature=0.3,
        hf_trace_timeout_seconds=hf_trace_timeout_seconds,
    )


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


def test_importing_server_does_not_load_config(monkeypatch) -> None:
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


def test_run_server_handles_ctrl_c_without_reraising(monkeypatch, capsys) -> None:
    server = import_server_module()

    class InterruptingServer:
        def __init__(self, server_address, state) -> None:
            self.server_address = server_address
            self.state = state
            self.closed = False

        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            self.closed = True

    instances = []

    def fake_server(server_address, state):
        instance = InterruptingServer(server_address, state)
        instances.append(instance)
        return instance

    monkeypatch.setattr(server, "TokenTrailServer", fake_server)

    server.run_server(host="127.0.0.1", port=0, config=make_config())

    output = capsys.readouterr().out
    assert "Stopping Token Trail." in output
    assert instances[0].closed


def test_build_server_state_marks_hf_trace_available_when_enabled_and_probe_succeeds() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(hf_trace_enabled=True),
        hf_trace_adapter=FakeHfTraceAdapter(available=True),
    )

    options = {option.id: option for option in state.runtime_options}

    assert options["hf-trace:Qwen/Qwen2.5-1.5B-Instruct"].available


def test_runtime_and_health_endpoints_report_only_scripted_and_hf_trace() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(hf_trace_enabled=True),
        hf_trace_adapter=FakeHfTraceAdapter(available=True),
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

    assert [option["backend"] for option in runtime_payload["options"]] == ["scripted", "hf-trace", "hf-trace"]
    assert health_payload == {
        "status": "ok",
        "service": "token-trail",
        "runtime": "scripted:prepared-traces",
    }


def test_warmup_route_is_removed() -> None:
    server = import_server_module()
    state = server.build_server_state(make_config())
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/runtime/warmup",
            {"runtime_id": "scripted:prepared-traces"},
            expected_status=404,
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert "Route not found" in payload["message"]


def test_generate_trace_returns_hf_live_trace_response_using_custom_prompt() -> None:
    server = import_server_module()
    hf_adapter = FakeHfTraceAdapter()
    state = server.build_server_state(
        make_config(backend="hf-trace", hf_trace_enabled=True, hf_trace_timeout_seconds=7.5),
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
                "prompt": "  Explain tokenisation with a tiny campus story.  ",
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
    assert hf_adapter.generate_calls == [
        {
            "prompt": "Explain tokenisation with a tiny campus story.",
            "model": "Qwen/Qwen2.5-1.5B-Instruct",
            "max_new_tokens": 96,
            "top_k": 5,
            "temperature": 0.3,
            "timeout_seconds": 7.5,
        }
    ]


def test_generate_trace_uses_selected_hf_trace_model() -> None:
    server = import_server_module()
    hf_adapter = FakeHfTraceAdapter()
    state = server.build_server_state(
        make_config(backend="hf-trace", hf_trace_enabled=True),
        hf_trace_adapter=hf_adapter,
    )
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {
                "runtime_id": "hf-trace:Qwen/Qwen2.5-0.5B-Instruct",
                "trace_id": "robot-university",
            },
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "hf-live-trace"
    assert payload["runtime_id"] == "hf-trace:Qwen/Qwen2.5-0.5B-Instruct"
    assert hf_adapter.generate_calls[-1]["model"] == "Qwen/Qwen2.5-0.5B-Instruct"


def test_hf_trace_error_uses_scripted_fallback() -> None:
    server = import_server_module()
    state = server.build_server_state(
        make_config(backend="hf-trace", hf_trace_enabled=True),
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


def test_generate_trace_ignores_custom_prompt_for_scripted_runtime() -> None:
    server = import_server_module()
    state = server.build_server_state(make_config())
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


def test_unknown_runtime_returns_400() -> None:
    server = import_server_module()
    state = server.build_server_state(make_config())
    httpd = server.TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/generate-trace",
            {"runtime_id": "hf-trace:nope", "trace_id": "robot-university"},
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
