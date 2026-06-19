import sys

from token_trail import server
from token_trail.config import RuntimeConfig


def test_server_main_uses_loaded_config(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(sys, "argv", ["token-trail"])
    monkeypatch.setattr(
        server,
        "load_config",
        lambda: RuntimeConfig(
            backend="scripted",
            host="127.0.0.2",
            port=8123,
            ollama_base_url="http://127.0.0.1:11434",
            ollama_model="qwen3:4b",
            vllm_base_url="http://127.0.0.1:8001/v1",
            vllm_model="Qwen/Qwen3-4B",
        ),
    )
    monkeypatch.setattr(server, "run_server", lambda host, port: calls.append((host, port)))

    server.main()

    assert calls == [("127.0.0.2", 8123)]


def test_server_cli_args_override_loaded_config(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(sys, "argv", ["token-trail", "--host", "0.0.0.0", "--port", "9000"])
    monkeypatch.setattr(
        server,
        "load_config",
        lambda: RuntimeConfig(
            backend="scripted",
            host="127.0.0.2",
            port=8123,
            ollama_base_url="http://127.0.0.1:11434",
            ollama_model="qwen3:4b",
            vllm_base_url="http://127.0.0.1:8001/v1",
            vllm_model="Qwen/Qwen3-4B",
        ),
    )
    monkeypatch.setattr(server, "run_server", lambda host, port: calls.append((host, port)))

    server.main()

    assert calls == [("0.0.0.0", 9000)]
