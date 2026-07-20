from token_trail.config import RuntimeConfig
from token_trail.local_runner import run_local_stack


def test_local_runner_starts_only_token_trail(monkeypatch, tmp_path) -> None:
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
    pid_file = tmp_path / "token-trail.pid"
    monkeypatch.setattr("token_trail.local_runner.PID_FILE", pid_file)

    run_local_stack(config)

    assert [call[0] for call in calls] == ["port", "server"]
    assert calls[1][1] == {"host": "127.0.0.1", "port": 3100, "config": config}
    assert not pid_file.exists()


def test_local_runner_records_pid_while_server_is_running(monkeypatch, tmp_path) -> None:
    config = RuntimeConfig(
        backend="scripted",
        host="127.0.0.1",
        port=3100,
        backend_port=8100,
    )
    pid_file = tmp_path / "token-trail.pid"
    recorded_pid = []
    monkeypatch.setattr("token_trail.local_runner.PID_FILE", pid_file)
    monkeypatch.setattr("token_trail.local_runner.check_port_or_exit", lambda **kwargs: None)
    monkeypatch.setattr(
        "token_trail.local_runner.run_server",
        lambda **kwargs: recorded_pid.append(pid_file.read_text(encoding="utf-8").strip()),
    )

    run_local_stack(config)

    assert len(recorded_pid) == 1
    assert recorded_pid[0].isdigit()
    assert not pid_file.exists()
