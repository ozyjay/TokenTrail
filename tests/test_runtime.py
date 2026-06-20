from token_trail.config import RuntimeConfig
from token_trail.adapters.ollama import OllamaStatus
from token_trail.runtime import build_runtime_options, default_runtime_id, select_runtime


def make_config(backend: str = "scripted", *, hf_trace_enabled: bool = False) -> RuntimeConfig:
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
        hf_trace_enabled=hf_trace_enabled,
        hf_trace_url="http://127.0.0.1:8600/api/trace",
        hf_trace_model="Qwen/Qwen2.5-1.5B-Instruct",
        hf_trace_top_k=5,
        hf_trace_max_new_tokens=48,
        hf_trace_temperature=0.3,
    )


def test_build_runtime_options_includes_scripted_and_configured_models() -> None:
    options = build_runtime_options(make_config(), ollama_status=OllamaStatus(available=True, models=("qwen3:4b",)))

    assert [option.id for option in options] == [
        "scripted:prepared-traces",
        "ollama:qwen3:4b",
        "ollama:qwen3:1.7b",
        "vllm:Qwen/Qwen3-4B",
    ]
    assert [option.available for option in options] == [True, True, False, False]


def test_build_runtime_options_includes_available_hf_trace_when_enabled_and_probed() -> None:
    options = build_runtime_options(
        make_config(hf_trace_enabled=True),
        ollama_status=OllamaStatus(available=False, models=()),
        hf_trace_available=True,
    )

    hf_option = next(option for option in options if option.id == "hf-trace:Qwen/Qwen2.5-1.5B-Instruct")
    assert hf_option.backend == "hf-trace"
    assert hf_option.model == "Qwen/Qwen2.5-1.5B-Instruct"
    assert hf_option.available
    assert hf_option.notes == "Configured HF trace server is reachable."


def test_build_runtime_options_omits_hf_trace_when_disabled() -> None:
    options = build_runtime_options(make_config(hf_trace_enabled=False), hf_trace_available=True)

    assert all(option.backend != "hf-trace" for option in options)


def test_default_runtime_uses_configured_hf_trace_when_available() -> None:
    config = make_config(backend="hf-trace", hf_trace_enabled=True)
    options = build_runtime_options(config, hf_trace_available=True)

    assert default_runtime_id(config, options) == "hf-trace:Qwen/Qwen2.5-1.5B-Instruct"


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


def test_ollama_options_show_missing_model_when_ollama_is_reachable() -> None:
    options = build_runtime_options(make_config(), ollama_status=OllamaStatus(available=True, models=("qwen3:4b",)))
    missing_option = next(option for option in options if option.id == "ollama:qwen3:1.7b")

    assert not missing_option.available
    assert missing_option.notes == "Configured, but not found in local Ollama."


def test_ollama_options_show_unavailable_when_ollama_is_unreachable() -> None:
    options = build_runtime_options(make_config(), ollama_status=OllamaStatus(available=False, models=(), error="nope"))
    ollama_option = next(option for option in options if option.id == "ollama:qwen3:4b")

    assert not ollama_option.available
    assert ollama_option.notes == "Configured local Ollama model, but Ollama is unavailable."
