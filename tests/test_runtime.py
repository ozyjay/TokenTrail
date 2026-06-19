from token_trail.config import RuntimeConfig
from token_trail.runtime import build_runtime_options, default_runtime_id, select_runtime


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


def test_build_runtime_options_includes_scripted_and_configured_models() -> None:
    options = build_runtime_options(make_config())

    assert [option.id for option in options] == [
        "scripted:prepared-traces",
        "ollama:qwen3:4b",
        "ollama:qwen3:1.7b",
        "vllm:Qwen/Qwen3-4B",
    ]


def test_default_runtime_uses_configured_backend_and_model() -> None:
    config = make_config(backend="ollama")
    options = build_runtime_options(config)

    assert default_runtime_id(config, options) == "ollama:qwen3:4b"


def test_default_runtime_falls_back_to_scripted_for_unknown_backend() -> None:
    config = make_config(backend="unknown")
    options = build_runtime_options(config)

    assert default_runtime_id(config, options) == "scripted:prepared-traces"


def test_select_runtime_validates_known_ids() -> None:
    options = build_runtime_options(make_config())

    assert select_runtime("ollama:qwen3:1.7b", options) == "ollama:qwen3:1.7b"
