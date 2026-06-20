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


def test_reset_demo_rerenders_prompt_for_current_runtime() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    reset_demo_body = app_js.split("function resetDemo", 1)[1].split("function buttonLabelForRuntime", 1)[0]

    assert "renderPrompt();" in reset_demo_body


def test_web_app_prefers_active_trace_tokens_for_prompt_display() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "const trace = currentTrace || selectedTrace;" in app_js
    assert "promptInput.value === trace.prompt ? trace.prompt_tokens : simpleTokenise(promptInput.value)" in app_js
    assert "renderTokens(promptTokens, trace.prompt_tokens);" in app_js


def test_web_app_preserves_hf_decoded_token_spacing() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "function hasDecodedSpacing(tokens)" in app_js
    assert "function joinDisplayTokens(tokens, preserveDecodedSpacing = true)" in app_js
    assert 'tokens.join("")' in app_js
    assert 'tokens.join(" ")' in app_js
    assert 'currentTrace.mode === "hf-live-trace"' in app_js


def test_web_app_does_not_replace_custom_prompt_on_hf_fallback() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")
    fallback_body = app_js.split("function loadFallbackTrace", 1)[1].split("async function startDemo", 1)[0]

    assert "resetPromptToTrace();" not in fallback_body
    assert "renderPrompt();" in fallback_body
    assert 'payload.message || "Live generation unavailable — showing prepared trace"' in fallback_body


def test_web_app_allows_prompt_editing_for_available_hf_trace_runtimes() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'currentRuntime.backend === "hf-trace"' in app_js
    assert "currentRuntime.available" in app_js


def test_runtime_status_is_not_repeated_as_a_visible_pill() -> None:
    index_html = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")
    styles_css = (PROJECT_ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    assert 'id="runtimeStatus"' not in index_html
    assert "status-pill" not in index_html
    assert "const runtimeStatus" not in app_js
    assert ".status-pill" not in styles_css
    assert "runtimeSelect.title =" in app_js
    assert "runtimeSelect.setAttribute(\"aria-label\"" in app_js


def test_runtime_selector_labels_hf_warm_status() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'runtimeStatusLabel(option)' in app_js
    assert 'case "ready":' in app_js
    assert 'return "ready";' in app_js
    assert 'case "running":' in app_js
    assert 'return "loads on first use";' in app_js
    assert 'case "unavailable":' in app_js
    assert 'return "unavailable";' in app_js


def test_web_app_has_trail_speed_control() -> None:
    index_html = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert 'for="trailSpeedSelect"' in index_html
    assert 'id="trailSpeedSelect"' in index_html
    assert '<option value="slow">Slow</option>' in index_html
    assert '<option value="normal" selected>Normal</option>' in index_html
    assert '<option value="fast">Fast</option>' in index_html


def test_web_app_uses_speed_presets_and_timeout_replay_loop() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "const TRAIL_SPEED_DELAYS_MS = {" in app_js
    assert "slow: 2200" in app_js
    assert "normal: 1500" in app_js
    assert "fast: 700" in app_js
    assert "setTimeout(runStep, trailDelayMs())" in app_js
    assert "setInterval(" not in app_js
    assert "payload.mode === \"live\"" not in app_js
    assert "showLiveGeneration" not in app_js


def test_web_layout_prioritises_generated_text_width() -> None:
    index_html = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    styles_css = (PROJECT_ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    assert 'class="panel generated-panel"' in index_html
    assert ".generated-panel {" in styles_css
    assert "grid-column: span 2;" in styles_css
    assert "max-width: none;" in styles_css


def test_candidate_labels_do_not_overlap_probability_bars() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")
    styles_css = (PROJECT_ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    assert 'label.className = "candidate-token";' in app_js
    assert "grid-template-columns: minmax(0, 1.1fr) minmax(7rem, 1fr) 4rem;" in styles_css
    assert ".candidate-token {" in styles_css
    assert "overflow-wrap: anywhere;" in styles_css
    assert ".bar-wrap {" in styles_css
