import importlib
import json
import sys
import threading
from urllib.request import urlopen

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
        vllm_base_url="http://127.0.0.1:8000/v1",
        vllm_model="Qwen/Qwen3-4B",
        vllm_models=("Qwen/Qwen3-4B",),
    )


class FakeOllamaAdapter:
    def __init__(self, status: OllamaStatus) -> None:
        self._status = status

    def status(self) -> OllamaStatus:
        return self._status


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


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))
