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
        "TOKEN_TRAIL_OLLAMA_NUM_PREDICT",
        "TOKEN_TRAIL_OLLAMA_TEMPERATURE",
        "TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS",
        "TOKEN_TRAIL_OLLAMA_DISABLE_THINKING",
        "TOKEN_TRAIL_OLLAMA_WARMUP_ENABLED",
        "TOKEN_TRAIL_OLLAMA_WARMUP_TIMEOUT_SECONDS",
        "TOKEN_TRAIL_OLLAMA_KEEP_ALIVE",
        "TOKEN_TRAIL_OLLAMA_REASONING_RETRY_TOKENS",
        "TOKEN_TRAIL_VLLM_BASE_URL",
        "TOKEN_TRAIL_VLLM_MODEL",
        "TOKEN_TRAIL_VLLM_MODELS",
        "TOKEN_TRAIL_HF_TRACE_ENABLED",
        "TOKEN_TRAIL_HF_TRACE_URL",
        "TOKEN_TRAIL_HF_TRACE_MODEL",
        "TOKEN_TRAIL_HF_TRACE_MODELS",
        "TOKEN_TRAIL_HF_TRACE_TOP_K",
        "TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS",
        "TOKEN_TRAIL_HF_TRACE_TEMPERATURE",
        "TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS",
        "TOKEN_TRAIL_MODEL_CONFIG_PATH",
    ):
        monkeypatch.delenv(name, raising=False)

    config = load_config(env_file=None)

    assert config.backend == "scripted"
    assert config.host == "127.0.0.1"
    assert config.port == 3100
    assert config.backend_port == 8100
    assert config.ollama_model == "qwen3:4b"
    assert config.ollama_models == ("qwen3:4b",)
    assert config.ollama_num_predict == 256
    assert config.ollama_temperature == 0.4
    assert config.ollama_timeout_seconds == 20.0
    assert config.ollama_disable_thinking is True
    assert config.ollama_warmup_enabled is True
    assert config.ollama_warmup_timeout_seconds == 45.0
    assert config.ollama_keep_alive == "30m"
    assert config.ollama_reasoning_retry_tokens == {"qwen3:4b": 512}
    assert config.vllm_base_url == "http://127.0.0.1:8000/v1"
    assert config.vllm_model == "Qwen/Qwen3-4B"
    assert config.vllm_models == ("Qwen/Qwen3-4B",)
    assert config.hf_trace_enabled is False
    assert config.hf_trace_url == "http://127.0.0.1:8600/api/trace"
    assert config.hf_trace_model == "Qwen/Qwen2.5-1.5B-Instruct"
    assert config.hf_trace_models == ("Qwen/Qwen2.5-1.5B-Instruct",)
    assert config.hf_trace_top_k == 5
    assert config.hf_trace_max_new_tokens == 48
    assert config.hf_trace_temperature == 0.3
    assert config.hf_trace_timeout_seconds == 20.0


def test_config_reads_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND", "ollama")
    monkeypatch.setenv("TOKEN_TRAIL_PORT", "8123")
    monkeypatch.setenv("TOKEN_TRAIL_BACKEND_PORT", "9123")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_MODELS", "qwen3:4b, qwen3:1.7b, qwen3:4b")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_NUM_PREDICT", "128")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_TEMPERATURE", "0.2")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_DISABLE_THINKING", "false")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_WARMUP_ENABLED", "false")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_WARMUP_TIMEOUT_SECONDS", "30.5")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_KEEP_ALIVE", "10m")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_REASONING_RETRY_TOKENS", "qwen3:4b=384, qwen3:1.7b=0, bad, nope=x")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_ENABLED", "true")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_URL", "http://127.0.0.1:8700/api/trace")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    monkeypatch.setenv(
        "TOKEN_TRAIL_HF_TRACE_MODELS",
        "Qwen/Qwen2.5-0.5B-Instruct, Qwen/Qwen2.5-1.5B-Instruct, Qwen/Qwen2.5-0.5B-Instruct",
    )
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_TOP_K", "3")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS", "24")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_TEMPERATURE", "0.1")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS", "6.5")

    config = load_config(env_file=None)

    assert config.backend == "ollama"
    assert config.port == 8123
    assert config.backend_port == 9123
    assert config.ollama_models == ("qwen3:4b", "qwen3:1.7b")
    assert config.ollama_num_predict == 128
    assert config.ollama_temperature == 0.2
    assert config.ollama_timeout_seconds == 12.5
    assert config.ollama_disable_thinking is False
    assert config.ollama_warmup_enabled is False
    assert config.ollama_warmup_timeout_seconds == 30.5
    assert config.ollama_keep_alive == "10m"
    assert config.ollama_reasoning_retry_tokens == {"qwen3:4b": 384}
    assert config.hf_trace_enabled is True
    assert config.hf_trace_url == "http://127.0.0.1:8700/api/trace"
    assert config.hf_trace_model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert config.hf_trace_models == ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")
    assert config.hf_trace_top_k == 3
    assert config.hf_trace_max_new_tokens == 24
    assert config.hf_trace_temperature == 0.1
    assert config.hf_trace_timeout_seconds == 6.5


def test_config_reads_env_file(monkeypatch) -> None:
    for name in (
        "TOKEN_TRAIL_BACKEND",
        "TOKEN_TRAIL_HOST",
        "TOKEN_TRAIL_PORT",
        "TOKEN_TRAIL_BACKEND_PORT",
        "TOKEN_TRAIL_OLLAMA_MODEL",
        "TOKEN_TRAIL_OLLAMA_MODELS",
        "TOKEN_TRAIL_OLLAMA_NUM_PREDICT",
        "TOKEN_TRAIL_OLLAMA_TEMPERATURE",
        "TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS",
        "TOKEN_TRAIL_OLLAMA_DISABLE_THINKING",
        "TOKEN_TRAIL_OLLAMA_WARMUP_ENABLED",
        "TOKEN_TRAIL_OLLAMA_WARMUP_TIMEOUT_SECONDS",
        "TOKEN_TRAIL_OLLAMA_KEEP_ALIVE",
        "TOKEN_TRAIL_OLLAMA_REASONING_RETRY_TOKENS",
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
                "TOKEN_TRAIL_OLLAMA_NUM_PREDICT=160",
                "TOKEN_TRAIL_OLLAMA_TEMPERATURE=0.3",
                "TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS=15",
                "TOKEN_TRAIL_OLLAMA_DISABLE_THINKING=no",
                "TOKEN_TRAIL_OLLAMA_WARMUP_ENABLED=off",
                "TOKEN_TRAIL_OLLAMA_WARMUP_TIMEOUT_SECONDS=22.5",
                "TOKEN_TRAIL_OLLAMA_KEEP_ALIVE=5m",
                "TOKEN_TRAIL_OLLAMA_REASONING_RETRY_TOKENS=qwen3:4b=256",
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
    assert config.ollama_num_predict == 160
    assert config.ollama_temperature == 0.3
    assert config.ollama_timeout_seconds == 15.0
    assert config.ollama_disable_thinking is False
    assert config.ollama_warmup_enabled is False
    assert config.ollama_warmup_timeout_seconds == 22.5
    assert config.ollama_keep_alive == "5m"
    assert config.ollama_reasoning_retry_tokens == {"qwen3:4b": 256}


def test_process_environment_overrides_env_file(monkeypatch) -> None:
    env_file = FakeEnvFile("TOKEN_TRAIL_PORT=8123\nTOKEN_TRAIL_OLLAMA_KEEP_ALIVE=5m\n")
    monkeypatch.setenv("TOKEN_TRAIL_PORT", "9000")
    monkeypatch.setenv("TOKEN_TRAIL_OLLAMA_KEEP_ALIVE", "20m")

    config = load_config(env_file=env_file)

    assert config.port == 9000
    assert config.ollama_keep_alive == "20m"


def test_hf_trace_default_model_is_included_in_model_options(monkeypatch) -> None:
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    monkeypatch.setenv("TOKEN_TRAIL_HF_TRACE_MODELS", "Qwen/Qwen2.5-1.5B-Instruct")

    config = load_config(env_file=None)

    assert config.hf_trace_models == ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")


def test_config_reads_json_model_config(tmp_path, monkeypatch) -> None:
    for name in (
        "TOKEN_TRAIL_BACKEND",
        "TOKEN_TRAIL_OLLAMA_MODEL",
        "TOKEN_TRAIL_OLLAMA_MODELS",
        "TOKEN_TRAIL_VLLM_MODEL",
        "TOKEN_TRAIL_VLLM_MODELS",
        "TOKEN_TRAIL_HF_TRACE_MODEL",
        "TOKEN_TRAIL_HF_TRACE_MODELS",
        "TOKEN_TRAIL_MODEL_CONFIG_PATH",
    ):
        monkeypatch.delenv(name, raising=False)

    model_config = tmp_path / "models.json"
    model_config.write_text(
        """
        {
          "defaults": {
            "backend": "hf-trace",
            "ollama_model": "qwen3:1.7b",
            "vllm_model": "Qwen/Qwen3-4B",
            "hf_trace_model": "Qwen/Qwen2.5-0.5B-Instruct"
          },
          "ollama": [
            {"model": "qwen3:1.7b"},
            {"model": "qwen3:4b"},
            {"model": "qwen3:1.7b"}
          ],
          "vllm": [
            {"model": "Qwen/Qwen3-4B"}
          ],
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
    assert config.ollama_model == "qwen3:1.7b"
    assert config.ollama_models == ("qwen3:1.7b", "qwen3:4b")
    assert config.vllm_model == "Qwen/Qwen3-4B"
    assert config.vllm_models == ("Qwen/Qwen3-4B",)
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
