from token_trail.config import RuntimeConfig
from token_trail.runtime import build_runtime_options, default_runtime_id, select_runtime


def make_config(backend: str = "scripted") -> RuntimeConfig:
    return RuntimeConfig(
        backend=backend,
        host="127.0.0.1",
        port=3100,
        backend_port=8100,
    )


def test_build_runtime_options_includes_only_scripted_by_default() -> None:
    options = build_runtime_options(make_config())

    assert [option.id for option in options] == ["scripted:prepared-traces"]


def test_build_runtime_options_includes_ready_modeldeck_aliases() -> None:
    config = make_config()
    config = RuntimeConfig(
        **{
            **config.__dict__,
            "backend": "modeldeck",
            "modeldeck_enabled": True,
            "modeldeck_model": "qwen-1-5b",
            "modeldeck_models": ("qwen-0-5b", "qwen-1-5b", "qwen-3b"),
        }
    )

    options = build_runtime_options(
        config,
        modeldeck_statuses={
            "qwen-0-5b": {"available": True, "model_loaded": True, "reason": "Ready through qwen-small-rocm"},
            "qwen-1-5b": {"available": True, "model_loaded": True, "reason": "Ready through qwen-1-5b-rocm"},
            "qwen-3b": {"available": False, "model_loaded": False, "reason": "No ready worker"},
        },
    )

    assert [option.id for option in options[:4]] == [
        "scripted:prepared-traces",
        "modeldeck:qwen-0-5b",
        "modeldeck:qwen-1-5b",
        "modeldeck:qwen-3b",
    ]
    assert default_runtime_id(config, options) == "modeldeck:qwen-1-5b"
    assert options[3].status == "unavailable"
    assert options[0].available


def test_default_runtime_falls_back_to_scripted_for_unknown_backend() -> None:
    config = make_config(backend="unknown")
    options = build_runtime_options(config)

    assert default_runtime_id(config, options) == "scripted:prepared-traces"


def test_default_runtime_falls_back_to_scripted_when_modeldeck_alias_is_unready() -> None:
    config = RuntimeConfig(
        **{
            **make_config().__dict__,
            "backend": "modeldeck",
            "modeldeck_enabled": True,
            "modeldeck_model": "qwen-1-5b",
            "modeldeck_models": ("qwen-1-5b",),
        }
    )
    options = build_runtime_options(config, modeldeck_statuses={"qwen-1-5b": {"available": False}})

    assert default_runtime_id(config, options) == "scripted:prepared-traces"


def test_select_runtime_validates_known_ids() -> None:
    config = RuntimeConfig(
        **{
            **make_config().__dict__,
            "modeldeck_enabled": True,
            "modeldeck_model": "qwen-1-5b",
            "modeldeck_models": ("qwen-1-5b",),
        }
    )
    options = build_runtime_options(config, modeldeck_statuses={"qwen-1-5b": {"available": True}})

    assert select_runtime("modeldeck:qwen-1-5b", options) == "modeldeck:qwen-1-5b"
