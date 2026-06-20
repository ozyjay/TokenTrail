from token_trail.config import RuntimeConfig
from token_trail.runtime import build_runtime_options, default_runtime_id, select_runtime


def make_config(backend: str = "scripted", *, hf_trace_enabled: bool = False) -> RuntimeConfig:
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
    )


def test_build_runtime_options_includes_only_scripted_by_default() -> None:
    options = build_runtime_options(make_config())

    assert [option.id for option in options] == ["scripted:prepared-traces"]
    assert options[0].available


def test_build_runtime_options_includes_hf_trace_when_enabled() -> None:
    options = build_runtime_options(
        make_config(hf_trace_enabled=True),
        hf_trace_statuses={
            "Qwen/Qwen2.5-1.5B-Instruct": {"available": True, "model_loaded": True},
            "Qwen/Qwen2.5-0.5B-Instruct": {"available": True, "model_loaded": False},
        },
    )

    assert [option.id for option in options] == [
        "scripted:prepared-traces",
        "hf-trace:Qwen/Qwen2.5-1.5B-Instruct",
        "hf-trace:Qwen/Qwen2.5-0.5B-Instruct",
    ]
    assert [option.backend for option in options] == ["scripted", "hf-trace", "hf-trace"]
    assert [option.available for option in options] == [True, True, True]
    assert [option.status for option in options] == ["ready", "ready", "running"]
    assert options[1].notes == "HF trace server is running and this model is ready."
    assert options[2].notes == "HF trace server is running; this model loads on first use."


def test_hf_trace_options_show_unavailable_when_probe_fails() -> None:
    options = build_runtime_options(make_config(hf_trace_enabled=True), hf_trace_available=False)
    hf_option = next(option for option in options if option.backend == "hf-trace")

    assert not hf_option.available
    assert hf_option.status == "unavailable"
    assert hf_option.notes == "Configured HF trace server is unavailable; scripted fallback remains available."


def test_default_runtime_uses_configured_hf_trace_when_available() -> None:
    config = make_config(backend="hf-trace", hf_trace_enabled=True)
    options = build_runtime_options(config, hf_trace_available=True)

    assert default_runtime_id(config, options) == "hf-trace:Qwen/Qwen2.5-1.5B-Instruct"


def test_default_runtime_falls_back_to_scripted_for_unknown_backend() -> None:
    config = make_config(backend="unknown")
    options = build_runtime_options(config)

    assert default_runtime_id(config, options) == "scripted:prepared-traces"


def test_select_runtime_validates_known_ids() -> None:
    options = build_runtime_options(make_config(hf_trace_enabled=True), hf_trace_available=True)

    assert select_runtime("hf-trace:Qwen/Qwen2.5-0.5B-Instruct", options) == "hf-trace:Qwen/Qwen2.5-0.5B-Instruct"
