from token_trail.config import load_config


class FakeEnvFile:
    def __init__(self, content: str) -> None:
        self.content = content

    def exists(self) -> bool:
        return True

    def read_text(self, encoding: str) -> str:
        return self.content


def clear_token_trail_env(monkeypatch) -> None:
    for name in (
        "TOKEN_TRAIL_BACKEND",
        "TOKEN_TRAIL_HOST",
        "TOKEN_TRAIL_PORT",
        "TOKEN_TRAIL_BACKEND_PORT",
        "TOKEN_TRAIL_HF_TRACE_ENABLED",
        "TOKEN_TRAIL_HF_TRACE_URL",
        "TOKEN_TRAIL_HF_TRACE_MODEL",
        "TOKEN_TRAIL_HF_TRACE_MODELS",
        "TOKEN_TRAIL_HF_TRACE_TOP_K",
        "TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS",
        "TOKEN_TRAIL_HF_TRACE_TEMPERATURE",
        "TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS",
        "TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS",
        "TOKEN_TRAIL_MODEL_CONFIG_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


def test_default_config_uses_scripted_local_mode(monkeypatch) -> None:
    clear_token_trail_env(monkeypatch)

    config = load_config(env_file=None)

    assert config.backend == "scripted"
    assert config.host == "127.0.0.1"
    assert config.port == 3100
    assert config.backend_port == 8100
    assert config.hf_trace_enabled is False
    assert config.hf_trace_url == "http://127.0.0.1:8600/api/trace"
    assert config.hf_trace_model == "Qwen/Qwen2.5-1.5B-Instruct"
    assert config.hf_trace_models == ("Qwen/Qwen2.5-1.5B-Instruct",)
    assert config.hf_trace_top_k == 5
    assert config.hf_trace_max_new_tokens == 96
    assert config.hf_trace_temperature == 0.3
    assert config.hf_trace_timeout_seconds == 20.0
    assert config.hf_trace_warmup_timeout_seconds == 180.0


def test_config_reads_environment_overrides(monkeypatch) -> None:
    clear_token_trail_env(monkeypatch)
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND", "hf-trace")
    monkeypatch.setenv("TOKEN_TRAIL_PORT", "8123")
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND_PORT", "9123")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_ENABLED", "true")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_URL", "http://127.0.0.1:8700/api/trace")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    monkeypatch.setenv(
        "TOKEN_TRAIL_HF_TRACE_MODELS",
        "Qwen/Qwen2.5-0.5B-Instruct, Qwen/Qwen2.5-1.5B-Instruct, Qwen/Qwen2.5-0.5B-Instruct",
    )
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_TOP_K", "3")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS", "48")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_TEMPERATURE", "0.1")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS", "6.5")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS", "90")

    config = load_config(env_file=None)

    assert config.backend == "hf-trace"
    assert config.port == 8123
    assert config.backend_port == 9123
    assert config.hf_trace_enabled is True
    assert config.hf_trace_url == "http://127.0.0.1:8700/api/trace"
    assert config.hf_trace_model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert config.hf_trace_models == ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")
    assert config.hf_trace_top_k == 3
    assert config.hf_trace_max_new_tokens == 48
    assert config.hf_trace_temperature == 0.1
    assert config.hf_trace_timeout_seconds == 6.5
    assert config.hf_trace_warmup_timeout_seconds == 90.0


def test_config_reads_env_file(monkeypatch) -> None:
    clear_token_trail_env(monkeypatch)
    env_file = FakeEnvFile(
        "\n".join(
            [
                "# Local Token Trail settings",
                "TOKEN_TRAIL_BACKEND=hf-trace",
                "TOKEN_TRAIL_HOST='0.0.0.0'",
                'TOKEN_TRAIL_PORT="8123"',
                "TOKEN_TRAIL_BACKEND_PORT=9123",
                "TOKEN_TRAIL_HF_TRACE_ENABLED=true",
                "TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-0.5B-Instruct",
                "TOKEN_TRAIL_HF_TRACE_MODELS=Qwen/Qwen2.5-0.5B-Instruct,Qwen/Qwen2.5-1.5B-Instruct",
                "TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS=64",
            ]
        )
    )

    config = load_config(env_file=env_file)

    assert config.backend == "hf-trace"
    assert config.host == "0.0.0.0"
    assert config.port == 8123
    assert config.backend_port == 9123
    assert config.hf_trace_enabled is True
    assert config.hf_trace_model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert config.hf_trace_models == ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")
    assert config.hf_trace_max_new_tokens == 64


def test_process_environment_overrides_env_file(monkeypatch) -> None:
    clear_token_trail_env(monkeypatch)
    env_file = FakeEnvFile("TOKEN_TRAIL_PORT=8123\nTOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS=64\n")
    monkeypatch.setenv("TOKEN_TRAIL_PORT", "9000")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS", "72")

    config = load_config(env_file=env_file)

    assert config.port == 9000
    assert config.hf_trace_max_new_tokens == 72


def test_hf_trace_default_model_is_included_in_model_options(monkeypatch) -> None:
    clear_token_trail_env(monkeypatch)
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MODELS", "Qwen/Qwen2.5-1.5B-Instruct")

    config = load_config(env_file=None)

    assert config.hf_trace_models == ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")


def test_config_reads_json_model_config(tmp_path, monkeypatch) -> None:
    clear_token_trail_env(monkeypatch)
    model_config = tmp_path / "models.json"
    model_config.write_text(
        """
        {
          "defaults": {
            "backend": "hf-trace",
            "hf_trace_model": "Qwen/Qwen2.5-0.5B-Instruct"
          },
          "hf_trace": [
            {"model": "Qwen/Qwen2.5-0.5B-Instruct"},
            {"model": "Qwen/Qwen2.5-1.5B-Instruct"}
          ]
        }
        """,
        encoding="utf-8",
    )
    env_file = FakeEnvFile(f"TOKEN_TRAIL_MODEL_CONFIG_PATH={model_config}\n")

    config = load_config(env_file=env_file)

    assert config.backend == "hf-trace"
    assert config.hf_trace_model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert config.hf_trace_models == ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")


def test_environment_overrides_json_model_config(tmp_path, monkeypatch) -> None:
    model_config = tmp_path / "models.json"
    model_config.write_text(
        """
        {
          "defaults": {
            "backend": "hf-trace",
            "hf_trace_model": "Qwen/Qwen2.5-1.5B-Instruct"
          },
          "hf_trace": [
            {"model": "Qwen/Qwen2.5-1.5B-Instruct"}
          ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("TOKEN_TRAIL_MODEL_CONFIG_PATH", str(model_config))
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND", "scripted")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")

    config = load_config(env_file=None)

    assert config.backend == "scripted"
    assert config.hf_trace_model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert config.hf_trace_models == ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")
