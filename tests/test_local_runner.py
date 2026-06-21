from token_trail.config import RuntimeConfig
from token_trail.local_runner import (
    ensure_hf_trace_server,
    hf_trace_health_url,
    hf_trace_server_address,
    preload_hf_trace_model,
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
        hf_trace_models=("Qwen/Qwen2.5-0.5B-Instruct",),
        hf_trace_top_k=5,
        hf_trace_max_new_tokens=96,
        hf_trace_temperature=0.3,
        hf_trace_timeout_seconds=20,
    )


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


def test_ensure_hf_trace_server_preloads_model_when_already_healthy(monkeypatch) -> None:
    warmups = []
    monkeypatch.setattr("token_trail.local_runner.is_hf_trace_server_healthy", lambda config: True)
    monkeypatch.setattr("token_trail.local_runner.preload_hf_trace_model", lambda config: warmups.append(config))

    process = ensure_hf_trace_server(make_config())

    assert process is None
    assert warmups == [make_config()]


def test_ensure_hf_trace_server_preloads_model_after_start(monkeypatch) -> None:
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
    assert warmups == [make_config()]


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
        ("warmup", "Qwen/Qwen2.5-0.5B-Instruct", 20),
    ]
