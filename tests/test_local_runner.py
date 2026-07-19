from token_trail.config import RuntimeConfig
from token_trail.local_runner import run_local_stack


def test_local_runner_starts_only_token_trail(monkeypatch) -> None:
    calls = []
    config = RuntimeConfig(
        backend="modeldeck",
        host="127.0.0.1",
        port=3100,
        backend_port=8100,
        modeldeck_enabled=True,
        modeldeck_url="http://127.0.0.1:8600",
        modeldeck_model="qwen-1-5b",
    )
    monkeypatch.setattr("token_trail.local_runner.check_port_or_exit", lambda **kwargs: calls.append(("port", kwargs)))
    monkeypatch.setattr(
        "token_trail.local_runner.run_server",
        lambda **kwargs: calls.append(("server", kwargs)),
    )

    run_local_stack(config)

    assert [call[0] for call in calls] == ["port", "server"]
    assert calls[1][1] == {"host": "127.0.0.1", "port": 3100, "config": config}
