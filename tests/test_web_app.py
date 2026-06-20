from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_web_app_branches_hf_live_trace_to_replay_ui() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'payload.mode === "hf-live-trace"' in app_js
    assert "showHfLiveTrace(payload)" in app_js
    assert "currentTrace = payload.trace" in app_js
    assert "startPreparedTrail()" in app_js


def test_web_app_keeps_selected_trace_separate_from_hf_replay_trace() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "let selectedTrace = null;" in app_js
    assert "selectedTrace = await response.json();" in app_js
    assert "currentTrace = selectedTrace;" in app_js
    assert "resetDemo({ restoreSelectedTrace: true })" in app_js
    assert "currentTrace = payload.trace || selectedTrace || currentTrace;" in app_js
    assert "resetButton.addEventListener(\"click\", () => resetDemo({ restoreSelectedTrace: true }));" in app_js


def test_web_app_prefers_active_trace_tokens_for_prompt_display() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "const trace = currentTrace || selectedTrace;" in app_js
    assert "promptInput.value === trace.prompt ? trace.prompt_tokens : simpleTokenise(promptInput.value)" in app_js
    assert "renderTokens(promptTokens, trace.prompt_tokens);" in app_js


def test_web_app_allows_prompt_editing_for_available_live_runtimes() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'currentRuntime.backend !== "scripted"' in app_js
    assert "currentRuntime.available" in app_js


def test_web_layout_prioritises_generated_text_width() -> None:
    index_html = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    styles_css = (PROJECT_ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    assert 'class="panel generated-panel"' in index_html
    assert ".generated-panel {" in styles_css
    assert "grid-column: span 2;" in styles_css
    assert "max-width: none;" in styles_css
