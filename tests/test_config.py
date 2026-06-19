from token_trail.config import load_config


def test_default_config_uses_scripted_local_mode(monkeypatch) -> None:
    for name in (
        "TOKEN_TRAIL_BACKEND",
        "TOKEN_TRAIL_HOST",
        "TOKEN_TRAIL_PORT",
        "TOKEN_TRAIL_OLLAMA_BASE_URL",
        "TOKEN_TRAIL_OLLAMA_MODEL",
        "TOKEN_TRAIL_VLLM_BASE_URL",
        "TOKEN_TRAIL_VLLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    config = load_config()

    assert config.backend == "scripted"
    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.ollama_model == "qwen3:4b"
    assert config.vllm_model == "Qwen/Qwen3-4B"


def test_config_reads_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND", "ollama")
    monkeypatch.setenv("TOKEN_TRAIL_PORT", "8123")

    config = load_config()

    assert config.backend == "ollama"
    assert config.port == 8123
