from token_trail.config import RuntimeConfig
from token_trail.local_runner import (
    hf_trace_health_url,
    hf_trace_server_address,
    should_manage_hf_trace,
    warm_hf_trace_server,
)
from urllib.error import HTTPError
import io
import json


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


def test_warm_hf_trace_server_accepts_incomplete_readiness_trace(monkeypatch, capsys) -> None:
    def fake_urlopen(request, timeout):
        raise HTTPError(
            url="http://127.0.0.1:8600/api/trace",
            code=500,
            msg="error",
            hdrs={},
            fp=io.BytesIO(json.dumps({"error": "Generated trace did not reach a complete sentence"}).encode("utf-8")),
        )

    monkeypatch.setattr("token_trail.local_runner.urlopen", fake_urlopen)

    warm_hf_trace_server(make_config())

    assert "HF trace model warmed" in capsys.readouterr().out
