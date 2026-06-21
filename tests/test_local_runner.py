from token_trail.adapters.base import AdapterError
from token_trail.config import RuntimeConfig
from token_trail.local_runner import (
    ensure_hf_trace_server,
    hf_trace_health_url,
    hf_trace_server_address,
    preload_hf_trace_model,
    run_local_stack,
    resolve_hf_trace_models,
    should_manage_hf_trace,
)


def make_config(
    *,
    backend: str = "hf-trace",
    hf_trace_enabled: bool = True,
    hf_trace_url: str = "http://127.0.0.1:8600/api/trace",
) -> RuntimeConfig:
    return RuntimeConfig(
        backend=backend,
        host="127.0.0.1",
        port=3100,
        backend_port=8100,
        hf_trace_enabled=hf_trace_enabled,
        hf_trace_url=hf_trace_url,
        hf_trace_model="Qwen/Qwen2.5-0.5B-Instruct",
        hf_trace_models=("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct"),
        hf_trace_top_k=5,
        hf_trace_max_new_tokens=96,
        hf_trace_temperature=0.3,
        hf_trace_timeout_seconds=20,
        hf_trace_warmup_timeout_seconds=180,
    )


def discovery_payload(*, default_available: bool = True, fallback_available: bool = True) -> dict:
    return {
        "default_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "selected_model": "Qwen/Qwen2.5-0.5B-Instruct" if default_available else "Qwen/Qwen2.5-1.5B-Instruct",
        "models": [
            {
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "configured": True,
                "cached": default_available,
                "metadata_loadable": default_available,
                "loaded": False,
                "available": default_available,
                "reason": "Available locally; not loaded" if default_available else "Not found locally",
            },
            {
                "model": "Qwen/Qwen2.5-1.5B-Instruct",
                "configured": True,
                "cached": fallback_available,
                "metadata_loadable": fallback_available,
                "loaded": False,
                "available": fallback_available,
                "reason": "Available locally; not loaded" if fallback_available else "Not found locally",
            },
        ],
    }


def test_should_manage_hf_trace_only_for_enabled_hf_backend() -> None:
    assert should_manage_hf_trace(make_config())
    assert not should_manage_hf_trace(make_config(backend="scripted"))
    assert not should_manage_hf_trace(make_config(hf_trace_enabled=False))


def test_hf_trace_server_address_comes_from_trace_url() -> None:
    assert hf_trace_server_address(make_config()) == ("127.0.0.1", 8600)
    assert hf_trace_server_address(make_config(hf_trace_url="http://localhost/api/trace")) == ("localhost", 80)


def test_hf_trace_health_url_uses_trace_server_origin() -> None:
    assert hf_trace_health_url(make_config(hf_trace_url="http://127.0.0.1:8600/api/trace")) == (
        "http://127.0.0.1:8600/health"
    )


def test_ensure_hf_trace_server_does_not_preload_before_model_discovery_when_already_healthy(monkeypatch) -> None:
    warmups = []
    monkeypatch.setattr("token_trail.local_runner.is_hf_trace_server_healthy", lambda config: True)
    monkeypatch.setattr("token_trail.local_runner.preload_hf_trace_model", lambda config: warmups.append(config))

    process = ensure_hf_trace_server(make_config())

    assert process is None
    assert warmups == []


def test_ensure_hf_trace_server_does_not_preload_before_model_discovery_after_start(monkeypatch) -> None:
    health_calls = []
    warmups = []

    class FakeProcess:
        returncode = None

        def poll(self):
            return None

    def fake_is_healthy(config):
        health_calls.append(config)
        return len(health_calls) > 1

    monkeypatch.setattr("token_trail.local_runner.is_hf_trace_server_healthy", fake_is_healthy)
    monkeypatch.setattr("token_trail.local_runner.preload_hf_trace_model", lambda config: warmups.append(config))
    monkeypatch.setattr("token_trail.local_runner.subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr("token_trail.local_runner.time.sleep", lambda seconds: None)

    process = ensure_hf_trace_server(make_config())

    assert isinstance(process, FakeProcess)
    assert warmups == []


def test_preload_hf_trace_model_calls_adapter_warmup(monkeypatch) -> None:
    calls = []

    class FakeAdapter:
        def __init__(self, trace_url):
            calls.append(("init", trace_url))

        def warmup(self, model, *, timeout_seconds):
            calls.append(("warmup", model, timeout_seconds))
            return {"status": "ready", "model": model}

    monkeypatch.setattr("token_trail.local_runner.HfTraceAdapter", FakeAdapter)

    preload_hf_trace_model(make_config())

    assert calls == [
        ("init", "http://127.0.0.1:8600/api/trace"),
        ("warmup", "Qwen/Qwen2.5-0.5B-Instruct", 180),
    ]


def test_preload_hf_trace_model_wraps_timeout_with_operator_guidance(monkeypatch) -> None:
    class FakeAdapter:
        def __init__(self, trace_url):
            pass

        def warmup(self, model, *, timeout_seconds):
            raise AdapterError("HF trace warm-up timed out")

    monkeypatch.setattr("token_trail.local_runner.HfTraceAdapter", FakeAdapter)

    try:
        preload_hf_trace_model(make_config())
    except RuntimeError as error:
        message = str(error)
    else:
        raise AssertionError("expected RuntimeError")

    assert "Qwen/Qwen2.5-0.5B-Instruct" in message
    assert "180 seconds" in message
    assert "TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS" in message


def test_run_local_stack_warms_default_model_before_starting_app(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr("token_trail.local_runner.check_port_or_exit", lambda **kwargs: calls.append(("port", kwargs)))
    monkeypatch.setattr("token_trail.local_runner.ensure_hf_trace_server", lambda config: None)

    class FakeAdapter:
        def __init__(self, trace_url):
            calls.append(("init", trace_url))

        def models(self, *, timeout_seconds):
            calls.append(("models", timeout_seconds))
            return discovery_payload(default_available=True)

        def warmup(self, model, *, timeout_seconds):
            calls.append(("warmup", model, timeout_seconds))
            return {"status": "ready", "model": model}

    monkeypatch.setattr("token_trail.local_runner.HfTraceAdapter", FakeAdapter)
    monkeypatch.setattr(
        "token_trail.local_runner.run_server",
        lambda host, port, config: calls.append(("run_server", host, port, config.hf_trace_model)),
    )

    run_local_stack(make_config())

    assert ("warmup", "Qwen/Qwen2.5-0.5B-Instruct", 180) in calls
    assert calls[-1] == ("run_server", "127.0.0.1", 3100, "Qwen/Qwen2.5-0.5B-Instruct")


def test_run_local_stack_warms_first_available_when_default_missing(monkeypatch) -> None:
    calls = []

    class FakeAdapter:
        def __init__(self, trace_url):
            pass

        def models(self, *, timeout_seconds):
            return discovery_payload(default_available=False, fallback_available=True)

        def warmup(self, model, *, timeout_seconds):
            calls.append(("warmup", model, timeout_seconds))
            return {"status": "ready", "model": model}

    monkeypatch.setattr("token_trail.local_runner.check_port_or_exit", lambda **kwargs: None)
    monkeypatch.setattr("token_trail.local_runner.ensure_hf_trace_server", lambda config: None)
    monkeypatch.setattr("token_trail.local_runner.HfTraceAdapter", FakeAdapter)
    monkeypatch.setattr(
        "token_trail.local_runner.run_server",
        lambda host, port, config: calls.append(("run_server", config.hf_trace_model, config.hf_trace_models)),
    )

    run_local_stack(make_config())

    assert calls == [
        ("warmup", "Qwen/Qwen2.5-1.5B-Instruct", 180),
        (
            "run_server",
            "Qwen/Qwen2.5-1.5B-Instruct",
            ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct"),
        ),
    ]


def test_run_local_stack_fails_when_no_configured_hf_model_is_available(monkeypatch) -> None:
    class FakeAdapter:
        def __init__(self, trace_url):
            pass

        def models(self, *, timeout_seconds):
            return discovery_payload(default_available=False, fallback_available=False)

    monkeypatch.setattr("token_trail.local_runner.check_port_or_exit", lambda **kwargs: None)
    monkeypatch.setattr("token_trail.local_runner.ensure_hf_trace_server", lambda config: None)
    monkeypatch.setattr("token_trail.local_runner.HfTraceAdapter", FakeAdapter)
    monkeypatch.setattr(
        "token_trail.local_runner.run_server",
        lambda host, port, config: (_ for _ in ()).throw(AssertionError("app should not start")),
    )

    try:
        run_local_stack(make_config())
    except RuntimeError as error:
        message = str(error)
    else:
        raise AssertionError("expected RuntimeError")

    assert "No configured HF trace models are locally available" in message
    assert "Qwen/Qwen2.5-0.5B-Instruct: Not found locally" in message
