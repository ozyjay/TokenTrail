from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_web_app_branches_modeldeck_live_trace_to_replay_ui() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'payload.mode === "modeldeck-live-trace"' in app_js
    assert "showModelDeckLiveTrace(payload)" in app_js
    assert "currentTrace = payload.trace" in app_js
    assert "startPreparedTrail()" in app_js


def test_web_app_keeps_selected_trace_separate_from_live_replay_trace() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "let selectedTrace = null;" in app_js
    assert "selectedTrace = await response.json();" in app_js
    assert "currentTrace = selectedTrace;" in app_js
    assert "resetDemo({ restoreSelectedTrace: true })" in app_js
    assert "currentTrace = payload.trace || selectedTrace || currentTrace;" in app_js
    reset_handler = app_js.split('resetButton.addEventListener("click"', 1)[1].split("Promise.all", 1)[0]
    assert "resetDemo({ restoreSelectedTrace: true });" in reset_handler
    assert "resetPromptToTrace();" in reset_handler


def test_reset_demo_rerenders_prompt_for_current_runtime() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    reset_demo_body = app_js.split("function resetDemo", 1)[1].split("function buttonLabelForRuntime", 1)[0]

    assert "renderPrompt();" in reset_demo_body


def test_web_app_prefers_active_trace_tokens_for_prompt_display() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "const trace = currentTrace || selectedTrace;" in app_js
    assert "promptInput.value === trace.prompt ? promptTokensForDisplay(trace) : simpleTokenise(promptInput.value)" in app_js
    assert "renderTokens(promptTokens, promptTokensForDisplay(trace));" in app_js


def test_web_app_prefers_user_prompt_tokens_and_hides_whitespace_only_chips() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    helper_body = app_js.split("function promptTokensForDisplay", 1)[1].split("function simpleTokenise", 1)[0]

    assert "trace.user_prompt_tokens || trace.prompt_tokens || []" in helper_body
    assert 'tokens.filter((token) => token.trim() !== "")' in helper_body


def test_web_app_preserves_modeldeck_decoded_token_spacing() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "function hasDecodedSpacing(tokens)" in app_js
    assert "function joinDisplayTokens(tokens, preserveDecodedSpacing = true)" in app_js
    assert 'tokens.join("")' in app_js
    assert 'tokens.join(" ")' in app_js
    assert 'currentTrace.mode === "modeldeck-live-trace"' in app_js


def test_web_app_does_not_replace_custom_prompt_on_live_fallback() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")
    fallback_body = app_js.split("function loadFallbackTrace", 1)[1].split("async function startDemo", 1)[0]

    assert "resetPromptToTrace();" not in fallback_body
    assert "renderPrompt();" in fallback_body
    assert 'payload.message || "Live generation unavailable — showing prepared trace"' in fallback_body


def test_web_app_allows_prompt_editing_for_available_modeldeck_runtimes() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'currentRuntime.backend === "modeldeck"' in app_js
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


def test_runtime_selector_labels_runtime_status() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'runtimeStatusLabel(option)' in app_js
    assert 'case "ready":' in app_js
    assert 'return "ready";' in app_js
    assert 'case "loading":' in app_js
    assert 'return "loading";' in app_js
    assert 'case "idle":' in app_js
    assert 'return "select to load";' in app_js
    assert 'case "unavailable":' in app_js
    assert 'return "unavailable";' in app_js


def test_web_app_prevents_runtime_selection_races() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "let runtimeRequestId = 0;" in app_js
    assert "const requestId = ++runtimeRequestId;" in app_js
    assert "if (requestId !== runtimeRequestId)" in app_js
    assert "pollSelectedRuntimeUntilSettled(requestId)" in app_js


def test_web_app_disables_generation_while_selected_model_loads() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "isSelectedRuntimeLoading()" in app_js
    assert 'return "Loading model...";' in app_js
    assert "playButton.disabled = isSelectedRuntimeLoading();" in app_js
    assert "runtimeSelect.disabled = Boolean(timer);" in app_js


def test_web_app_has_trail_speed_control() -> None:
    index_html = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert 'for="trailSpeedSelect"' in index_html
    assert 'id="trailSpeedSelect"' in index_html
    assert '<option value="slow">Slow</option>' in index_html
    assert '<option value="normal" selected>Normal</option>' in index_html
    assert '<option value="fast">Fast</option>' in index_html


def test_web_app_has_accessible_generation_position_slider() -> None:
    index_html = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert 'for="generationPosition"' in index_html
    assert 'id="generationPosition"' in index_html
    assert 'type="range"' in index_html
    assert 'min="0" max="0" value="0" step="1" disabled' in index_html
    assert 'id="generationPositionOutput"' in index_html
    assert 'aria-live="polite"' in index_html
    assert "0 / 0 tokens" in index_html


def test_web_app_centralises_autoplay_and_scrub_position_rendering() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    render_body = app_js.split("function renderGenerationPosition", 1)[1].split("function updateReplayNavigator", 1)[0]
    run_step_body = app_js.split("function runStep", 1)[1].split("async function generateTrace", 1)[0]
    scrub_body = app_js.split('generationPosition.addEventListener("input"', 1)[1].split(
        'trailSpeedSelect.addEventListener', 1
    )[0]

    assert "currentTrace.steps.slice(0, stepIndex)" in render_body
    assert "currentTrace.steps[stepIndex - 1]" in render_body
    assert "candidateList.replaceChildren();" in render_body
    assert "renderGenerationPosition(stepIndex + 1);" in run_step_body
    assert "timer = null;" in scrub_body
    assert "renderGenerationPosition(Number(generationPosition.value));" in scrub_body


def test_web_app_enables_slider_only_after_start_and_resumes_existing_trace() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    navigator_body = app_js.split("function updateReplayNavigator", 1)[1].split("function stopPlayback", 1)[0]
    start_demo_body = app_js.split("async function startDemo", 1)[1].split("function startPreparedTrail", 1)[0]

    assert "generationPosition.disabled = !trailStarted || totalSteps === 0;" in navigator_body
    assert "generationPositionOutput.value" in navigator_body
    assert "if (trailStarted && currentTrace)" in start_demo_body
    assert start_demo_body.index("if (trailStarted && currentTrace)") < start_demo_body.index("await generateTrace()")
    assert 'return stepIndex >= currentTrace.steps.length ? "Replay trail" : "Continue trail";' in app_js


def test_web_app_invalidates_replay_on_reset_and_prompt_edit() -> None:
    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    reset_body = app_js.split("function resetDemo", 1)[1].split("function buttonLabelForRuntime", 1)[0]
    prompt_input_body = app_js.split('promptInput.addEventListener("input"', 1)[1].split('generationPosition.addEventListener', 1)[0]

    assert "trailStarted = false;" in reset_body
    assert "updateReplayNavigator();" in reset_body
    assert "resetDemo({ restoreSelectedTrace: true });" in prompt_input_body


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
