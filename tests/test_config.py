from token_trail.config import load_config


class FakeEnvFile:
    def __init__(self, content: str) -> None:
        self.content = content

    def exists(self) -> bool:
        return True

    def read_text(self, encoding: str) -> str:
        return self.content


def test_default_config_uses_scripted_local_mode(monkeypatch) -> None:
    for name in (
        "TOKEN_TRAIL_BACKEND",
        "TOKEN_TRAIL_HOST",
        "TOKEN_TRAIL_PORT",
        "TOKEN_TRAIL_BACKEND_PORT",
        "TOKEN_TRAIL_OLLAMA_BASE_URL",
        "TOKEN_TRAIL_OLLAMA_MODEL",
        "TOKEN_TRAIL_OLLAMA_MODELS",
        "TOKEN_TRAIL_VLLM_BASE_URL",
        "TOKEN_TRAIL_VLLM_MODEL",
        "TOKEN_TRAIL_VLLM_MODELS",
    ):
        monkeypatch.delenv(name, raising=False)

    config = load_config(env_file=None)

    assert config.backend == "scripted"
    assert config.host == "127.0.0.1"
    assert config.port == 3100
    assert config.backend_port == 8100
    assert config.ollama_model == "qwen3:4b"
    assert config.ollama_models == ("qwen3:4b",)
    assert config.vllm_base_url == "http://127.0.0.1:8000/v1"
    assert config.vllm_model == "Qwen/Qwen3-4B"
    assert config.vllm_models == ("Qwen/Qwen3-4B",)


def test_config_reads_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND", "ollama")
    monkeypatch.setenv("TOKEN_TRAIL_PORT", "8123")
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND_PORT", "9123")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_MODELS", "qwen3:4b, qwen3:1.7b, qwen3:4b")

    config = load_config(env_file=None)

    assert config.backend == "ollama"
    assert config.port == 8123
    assert config.backend_port == 9123
    assert config.ollama_models == ("qwen3:4b", "qwen3:1.7b")


def test_config_reads_env_file(monkeypatch) -> None:
    for name in (
        "TOKEN_TRAIL_BACKEND",
        "TOKEN_TRAIL_HOST",
        "TOKEN_TRAIL_PORT",
        "TOKEN_TRAIL_BACKEND_PORT",
        "TOKEN_TRAIL_OLLAMA_MODEL",
        "TOKEN_TRAIL_OLLAMA_MODELS",
    ):
        monkeypatch.delenv(name, raising=False)

    env_file = FakeEnvFile(
        "\n".join(
            [
                "# Local Token Trail settings",
                "TOKEN_TRAIL_BACKEND=ollama",
                "TOKEN_TRAIL_HOST='0.0.0.0'",
                'TOKEN_TRAIL_PORT="8123"',
                "TOKEN_TRAIL_BACKEND_PORT=9123",
                "TOKEN_TRAIL_OLLAMA_MODEL=qwen3:1.7b",
                "TOKEN_TRAIL_OLLAMA_MODELS=qwen3:1.7b,qwen3:4b",
            ]
        )
    )

    config = load_config(env_file=env_file)

    assert config.backend == "ollama"
    assert config.host == "0.0.0.0"
    assert config.port == 8123
    assert config.backend_port == 9123
    assert config.ollama_model == "qwen3:1.7b"
    assert config.ollama_models == ("qwen3:1.7b", "qwen3:4b")


def test_process_environment_overrides_env_file(monkeypatch) -> None:
    env_file = FakeEnvFile("TOKEN_TRAIL_PORT=8123\n")
    monkeypatch.setenv("TOKEN_TRAIL_PORT", "9000")

    config = load_config(env_file=env_file)

    assert config.port == 9000
