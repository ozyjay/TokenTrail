from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_web_app_branches_hf_live_trace_to_replay_ui() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'payload.mode === "hf-live-trace"' in app_js
    assert "showHfLiveTrace(payload)" in app_js
    assert "currentTrace = payload.trace" in app_js
    assert "startPreparedTrail()" in app_js
