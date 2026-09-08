const traceSelect = document.querySelector("#traceSelect");
const runtimeSelect = document.querySelector("#runtimeSelect");
const trailSpeedSelect = document.querySelector("#trailSpeedSelect");
const playButton = document.querySelector("#playButton");
const cancelButton = document.querySelector("#cancelButton");
const retryRuntimeButton = document.querySelector("#retryRuntimeButton");
const resetButton = document.querySelector("#resetButton");
const generationElapsed = document.querySelector("#generationElapsed");
const promptText = document.querySelector("#promptText");
const promptInput = document.querySelector("#promptInput");
const promptTokens = document.querySelector("#promptTokens");
const candidateList = document.querySelector("#candidateList");
const generatedText = document.querySelector("#generatedText");
const traceMeta = document.querySelector("#traceMeta");
const generationPosition = document.querySelector("#generationPosition");
const generationPositionOutput = document.querySelector("#generationPositionOutput");
const explanation = document.querySelector("#explanation");

let currentTrace = null;
let selectedTrace = null;
let currentRuntime = null;
let timer = null;
let generatedTokens = [];
let stepIndex = 0;
let trailStarted = false;
let runNotice = "";
let runtimeRequestId = 0;
let runtimePollTimer = null;
let activeGenerationController = null;
let activeGenerationRequestId = null;
let generationInProgress = false;
let generationStartedAt = null;
let generationElapsedTimer = null;

const TRAIL_SPEED_DELAYS_MS = {
  slow: 2200,
  normal: 1500,
  fast: 700,
};

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    throw new Error(`The demo server returned an invalid response (${response.status || "unknown status"})`);
  }
}

function responseError(payload, fallback) {
  return new Error(payload?.message || payload?.error || fallback);
}

async function loadRuntimeOptions({ requestId = runtimeRequestId } = {}) {
  const response = await fetch("/api/runtime");
  const payload = await readJsonResponse(response);
  if (!response.ok) {
    throw responseError(payload, "Could not load runtime status");
  }
  if (requestId !== runtimeRequestId) {
    return null;
  }
  currentRuntime = payload.selected;

  runtimeSelect.replaceChildren(
    ...payload.options.map((option) => {
      const item = document.createElement("option");
      item.value = option.id;
      item.textContent = option.label;
      if (option.backend !== "scripted") {
        item.textContent += ` (${runtimeStatusLabel(option)})`;
      }
      return item;
    }),
  );

  runtimeSelect.value = payload.selected_id;
  renderRuntimeStatus(payload.selected);
  renderPrompt();
  if (isSelectedRuntimeLoading()) {
    explanation.textContent = `Loading ${currentRuntime.model}...`;
    pollSelectedRuntimeUntilSettled(requestId);
  } else {
    clearTimeout(runtimePollTimer);
  }
  return payload;
}

async function selectRuntime() {
  const requestId = ++runtimeRequestId;
  clearTimeout(runtimePollTimer);
  const response = await fetch("/api/runtime/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runtime_id: runtimeSelect.value }),
  });
  const payload = await readJsonResponse(response);

  if (!response.ok) {
    throw responseError(payload, "Runtime selection failed");
  }

  if (requestId !== runtimeRequestId) {
    return;
  }
  currentRuntime = payload.selected;
  resetDemo({ restoreSelectedTrace: true });
  renderRuntimeStatus(payload.selected);
  if (isSelectedRuntimeLoading()) {
    explanation.textContent = `Loading ${currentRuntime.model}...`;
    pollSelectedRuntimeUntilSettled(requestId);
  } else if (!currentRuntime.available) {
    explanation.textContent = currentRuntime.notes;
  }
}

function renderRuntimeStatus(runtime) {
  const suffix = runtimeStatusLabel(runtime);
  runtimeSelect.title = `${runtime.backend}: ${runtime.model || "prepared traces"} · ${suffix}. ${runtime.notes}`;
  runtimeSelect.setAttribute("aria-label", `Runtime: ${runtime.label}, ${suffix}`);
  retryRuntimeButton.hidden = runtime.backend !== "modeldeck" || runtime.available || isSelectedRuntimeLoading();
  updatePlayButton();
}

function runtimeStatusLabel(option) {
  switch (option.status) {
    case "ready":
      return "ready";
    case "loading":
      return "loading";
    case "idle":
      return "select to load";
    case "unavailable":
      return "unavailable";
    case "gateway_unavailable":
      return "gateway unavailable";
    case "route_not_advertised":
      return "route not advertised";
    case "incompatible_contract":
      return "incompatible trace contract";
    case "provider_not_ready":
      return "local provider not ready";
    default:
      return option.available ? "ready" : "unavailable";
  }
}

function updatePlayButton() {
  runtimeSelect.disabled = Boolean(timer) || generationInProgress;
  playButton.disabled = isSelectedRuntimeLoading() || generationInProgress || isLiveRuntimeUnavailable();
  cancelButton.hidden = !generationInProgress;
  cancelButton.disabled = false;
  retryRuntimeButton.disabled = Boolean(timer) || generationInProgress || isSelectedRuntimeLoading();
  if (generationInProgress) {
    playButton.textContent = "Generating...";
    return;
  }
  if (timer) {
    playButton.textContent = "Pause trail";
    return;
  }
  playButton.textContent = buttonLabelForRuntime();
}

function isLiveRuntimeUnavailable() {
  return currentRuntime?.backend === "modeldeck" && !currentRuntime.available;
}

function isSelectedRuntimeLoading() {
  return currentRuntime?.backend === "modeldeck" && currentRuntime.status === "loading";
}

async function retryRuntimeStatus() {
  const requestId = ++runtimeRequestId;
  clearTimeout(runtimePollTimer);
  retryRuntimeButton.disabled = true;
  explanation.textContent = "Refreshing ModelDeck runtime status...";
  try {
    const payload = await loadRuntimeOptions({ requestId });
    if (!payload || requestId !== runtimeRequestId || isSelectedRuntimeLoading()) {
      return;
    }
    explanation.textContent = currentRuntime.available
      ? `${currentRuntime.model} is ready.`
      : currentRuntime.notes;
  } catch (error) {
    retryRuntimeButton.hidden = false;
    explanation.textContent = `Could not refresh runtime status: ${error.message || error}`;
  } finally {
    retryRuntimeButton.disabled = false;
  }
}

function pollSelectedRuntimeUntilSettled(requestId) {
  clearTimeout(runtimePollTimer);
  runtimePollTimer = setTimeout(async () => {
    if (requestId !== runtimeRequestId) {
      return;
    }

    try {
      const payload = await loadRuntimeOptions({ requestId });
      if (!payload || requestId !== runtimeRequestId) {
        return;
      }
      if (isSelectedRuntimeLoading()) {
        explanation.textContent = `Loading ${currentRuntime.model}...`;
        pollSelectedRuntimeUntilSettled(requestId);
        return;
      }
      explanation.textContent = currentRuntime.status === "ready" ? `${currentRuntime.model} is ready.` : currentRuntime.notes;
    } catch (error) {
      if (requestId === runtimeRequestId) {
        explanation.textContent = `Could not refresh runtime status: ${error}`;
      }
    }
  }, 900);
}

async function loadTraceList() {
  const response = await fetch("/api/traces");
  const payload = await readJsonResponse(response);
  if (!response.ok) {
    throw responseError(payload, "Could not load example prompts");
  }

  traceSelect.replaceChildren(
    ...payload.traces.map((trace) => {
      const option = document.createElement("option");
      option.value = trace.id;
      option.textContent = trace.title;
      return option;
    }),
  );

  await loadSelectedTrace();
}

async function loadSelectedTrace() {
  const response = await fetch(`/api/traces/${traceSelect.value}`);
  const payload = await readJsonResponse(response);
  if (!response.ok) {
    throw responseError(payload, "Could not load the selected example prompt");
  }
  selectedTrace = payload;
  currentTrace = selectedTrace;
  resetDemo();
  resetPromptToTrace();
}

function renderTokens(container, tokens) {
  container.replaceChildren(
    ...tokens.map((token) => {
      const span = document.createElement("span");
      span.className = "token";
      span.textContent = token;
      return span;
    }),
  );
}

function promptTokensForDisplay(trace) {
  const tokens = trace.mode === "modeldeck-live-trace" ? trace.user_prompt_tokens || [] : trace.prompt_tokens || [];
  return tokens.filter((token) => token.trim() !== "");
}

function simpleTokenise(text) {
  return text.replaceAll(".", " .").replaceAll(",", " ,").replaceAll(":", " :").split(/\s+/).filter(Boolean);
}

function canEditPrompt() {
  return currentRuntime && currentRuntime.backend === "modeldeck" && currentRuntime.available;
}

function resetPromptToTrace() {
  const trace = currentTrace || selectedTrace;
  if (!trace) {
    return;
  }

  promptInput.value = trace.prompt;
  renderPrompt();
}

function renderPrompt() {
  const trace = currentTrace || selectedTrace;
  if (!trace) {
    return;
  }

  if (canEditPrompt()) {
    promptText.hidden = true;
    promptInput.hidden = false;
    const visibleTokens = promptInput.value === trace.prompt ? promptTokensForDisplay(trace) : simpleTokenise(promptInput.value);
    renderTokens(promptTokens, visibleTokens);
    return;
  }

  promptInput.hidden = true;
  promptText.hidden = false;
  promptText.textContent = trace.prompt;
  renderTokens(promptTokens, promptTokensForDisplay(trace));
}

function renderCandidates(step) {
  candidateList.replaceChildren(
    ...step.candidates.map((candidate) => {
      const row = document.createElement("div");
      row.className = candidate.token === step.selected_token ? "candidate selected" : "candidate";
      row.setAttribute("role", "listitem");

      const percentageValue = Math.round(candidate.probability * 100);
      const tokenLabel = candidate.token.trim() || "whitespace token";
      const selectedLabel = candidate.token === step.selected_token ? ", selected" : "";
      row.setAttribute("aria-label", `${tokenLabel}, ${percentageValue} percent${selectedLabel}`);
      if (candidate.token === step.selected_token) {
        row.setAttribute("aria-current", "true");
      }

      const label = document.createElement("span");
      label.className = "candidate-token";
      label.textContent = candidate.token;

      const barWrap = document.createElement("span");
      barWrap.className = "bar-wrap";

      const bar = document.createElement("span");
      bar.className = "bar";
      bar.style.width = `${percentageValue}%`;
      bar.setAttribute("aria-hidden", "true");
      barWrap.append(bar);

      const probability = document.createElement("span");
      probability.className = "probability";
      probability.textContent = `${percentageValue}%`;

      row.append(label, barWrap, probability);
      return row;
    }),
  );
}

function hasDecodedSpacing(tokens) {
  return tokens.some((token) => /^\s|\s$/.test(token));
}

function joinDisplayTokens(tokens, preserveDecodedSpacing = true) {
  const text = preserveDecodedSpacing || hasDecodedSpacing(tokens) ? tokens.join("") : tokens.join(" ");
  return text.replaceAll(" .", ".").replaceAll(" ,", ",").replaceAll(" :", ":");
}

function trailDelayMs() {
  return TRAIL_SPEED_DELAYS_MS[trailSpeedSelect.value] || TRAIL_SPEED_DELAYS_MS.normal;
}

function scheduleNextStep() {
  clearTimeout(timer);
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    timer = null;
    updatePlayButton();
    return;
  }
  timer = setTimeout(runStep, trailDelayMs());
  updatePlayButton();
}

function renderGenerationPosition(position) {
  if (!currentTrace) {
    return;
  }

  const boundedPosition = Math.max(0, Math.min(Number(position), currentTrace.steps.length));
  stepIndex = boundedPosition;
  generatedTokens = currentTrace.steps.slice(0, stepIndex).map((step) => step.selected_token);
  generatedText.textContent = joinDisplayTokens(generatedTokens, currentTrace.mode === "modeldeck-live-trace");

  if (stepIndex === 0) {
    candidateList.replaceChildren();
    explanation.textContent = runNotice || "At the start of the trail.";
    updateReplayNavigator();
    return;
  }

  const step = currentTrace.steps[stepIndex - 1];
  renderCandidates(step);
  explanation.textContent = runNotice ? `${runNotice}. ${step.explanation}` : step.explanation;
  updateReplayNavigator();
}

function updateReplayNavigator() {
  const totalSteps = currentTrace ? currentTrace.steps.length : 0;
  generationPosition.max = String(totalSteps);
  generationPosition.value = String(Math.min(stepIndex, totalSteps));
  generationPosition.disabled = !trailStarted || totalSteps === 0;
  generationPositionOutput.value = `${Math.min(stepIndex, totalSteps)} / ${totalSteps} tokens`;
}

function renderTraceMeta() {
  if (!trailStarted || !currentTrace) {
    traceMeta.hidden = true;
    traceMeta.textContent = "";
    return;
  }

  const tokens = currentTrace.steps.length;
  if (currentTrace.mode === "modeldeck-live-trace") {
    const parts = ["Live trace", currentTrace.model, `${tokens} tokens`].filter(Boolean);
    const totalSeconds = currentTrace.metrics?.total_seconds;
    if (Number.isFinite(totalSeconds)) {
      parts.push(`${Number(totalSeconds).toFixed(1)} s generation time`);
    }
    traceMeta.textContent = parts.join(" · ");
  } else {
    traceMeta.textContent = `Prepared replay · ${tokens} tokens`;
  }
  traceMeta.hidden = false;
}

function stopPlayback() {
  clearTimeout(timer);
  timer = null;
  updatePlayButton();
}

function runStep() {
  if (!currentTrace || stepIndex >= currentTrace.steps.length) {
    stopPlayback();
    return;
  }

  renderGenerationPosition(stepIndex + 1);
  if (stepIndex >= currentTrace.steps.length) {
    stopPlayback();
    return;
  }
  scheduleNextStep();
}

async function generateTrace() {
  const requestId = crypto.randomUUID();
  const controller = new AbortController();
  activeGenerationRequestId = requestId;
  activeGenerationController = controller;
  generationInProgress = true;
  startGenerationElapsed();
  updatePlayButton();
  const body = { runtime_id: currentRuntime.id, trace_id: traceSelect.value, request_id: requestId };
  if (canEditPrompt()) {
    body.prompt = promptInput.value.trim();
  }

  try {
    const response = await fetch("/api/generate-trace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const payload = await readJsonResponse(response);
    controller.signal.throwIfAborted();

    if (!response.ok && payload.mode !== "modeldeck-unavailable") {
      throw responseError(payload, `Live trace request failed (${response.status})`);
    }

    return payload;
  } finally {
    if (activeGenerationRequestId === requestId) {
      activeGenerationRequestId = null;
      activeGenerationController = null;
      generationInProgress = false;
      stopGenerationElapsed();
      updatePlayButton();
    }
  }
}

function updateGenerationElapsed() {
  if (generationStartedAt === null) {
    return;
  }
  const elapsedSeconds = Math.max(0, Math.floor((performance.now() - generationStartedAt) / 1000));
  generationElapsed.textContent = `Generating live trace… ${elapsedSeconds} s`;
}

function startGenerationElapsed() {
  clearInterval(generationElapsedTimer);
  generationStartedAt = performance.now();
  generationElapsed.hidden = false;
  updateGenerationElapsed();
  generationElapsedTimer = setInterval(updateGenerationElapsed, 1000);
}

function stopGenerationElapsed() {
  clearInterval(generationElapsedTimer);
  generationElapsedTimer = null;
  generationStartedAt = null;
  generationElapsed.hidden = true;
}

function cancelActiveGeneration() {
  if (!activeGenerationRequestId) {
    return false;
  }
  const requestId = activeGenerationRequestId;
  activeGenerationController?.abort();
  fetch("/api/generate-trace/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_id: requestId }),
  }).catch(() => {});
  return true;
}

function showModelDeckLiveTrace(payload) {
  if (payload.trace) {
    currentTrace = payload.trace;
  }
  resetDemo();
  resetPromptToTrace();
  runNotice = "ModelDeck live trace";
  explanation.textContent = runNotice;
  loadRuntimeOptions().catch((error) => {
    explanation.textContent = `Could not refresh runtime status: ${error}`;
  });
  startPreparedTrail();
}

function showLiveUnavailable(payload) {
  resetDemo({ restoreSelectedTrace: true });
  runNotice = payload.message || "Live ModelDeck trace unavailable";
  explanation.textContent = runNotice;
  loadRuntimeOptions().catch((error) => {
    explanation.textContent = `Could not refresh runtime status: ${error}`;
  });
}

async function startDemo() {
  if (timer) {
    stopPlayback();
    explanation.textContent = "Trail paused. Use Continue trail or the generation position control.";
    return;
  }
  if (isSelectedRuntimeLoading()) {
    updatePlayButton();
    explanation.textContent = `Loading ${currentRuntime.model}...`;
    return;
  }
  if (trailStarted && currentTrace) {
    startPreparedTrail();
    return;
  }

  if (currentRuntime && currentRuntime.backend !== "scripted") {
    playButton.textContent = "Generating...";
    try {
      const payload = await generateTrace();
      if (payload.mode === "modeldeck-live-trace") {
        showModelDeckLiveTrace(payload);
      } else if (payload.mode === "modeldeck-unavailable") {
        showLiveUnavailable(payload);
      } else {
        throw new Error("Unexpected live trace response");
      }
    } catch (error) {
      if (error.name === "AbortError") {
        resetDemo({ restoreSelectedTrace: true });
        runNotice = "Trace request cancelled";
        explanation.textContent = runNotice;
        return;
      }
      resetDemo({ restoreSelectedTrace: true });
      runNotice = `Live ModelDeck request failed; no prepared output was substituted (${error})`;
      explanation.textContent = runNotice;
    }
    return;
  }

  runNotice = "Prepared replay mode";
  explanation.textContent = runNotice;
  startPreparedTrail();
}

function startPreparedTrail() {
  if (stepIndex >= currentTrace.steps.length) {
    renderGenerationPosition(0);
  }

  trailStarted = true;
  renderTraceMeta();
  updateReplayNavigator();
  runStep();
}

function resetDemo({ restoreSelectedTrace = false } = {}) {
  clearTimeout(timer);
  timer = null;
  if (restoreSelectedTrace && selectedTrace) {
    currentTrace = selectedTrace;
  }
  generatedTokens = [];
  stepIndex = 0;
  trailStarted = false;
  runNotice = "";
  candidateList.replaceChildren();
  generatedText.textContent = "";
  renderTraceMeta();
  explanation.textContent = isLiveRuntimeUnavailable()
    ? currentRuntime.notes
    : "Press start to see candidate tokens appear step by step.";
  updateReplayNavigator();
  renderPrompt();
  updatePlayButton();
}

function buttonLabelForRuntime() {
  if (trailStarted && currentTrace) {
    return stepIndex >= currentTrace.steps.length ? "Replay trail" : "Continue trail";
  }
  if (!currentRuntime || currentRuntime.backend === "scripted") {
    return "Start trail";
  }
  if (isSelectedRuntimeLoading()) {
    return "Loading model...";
  }
  return currentRuntime.available ? "Generate live trail" : "Live model unavailable";
}

traceSelect.addEventListener("change", loadSelectedTrace);
runtimeSelect.addEventListener("change", () => {
  selectRuntime().catch((error) => {
    explanation.textContent = `Could not switch runtime: ${error}`;
  });
});
retryRuntimeButton.addEventListener("click", retryRuntimeStatus);
cancelButton.addEventListener("click", () => {
  if (cancelActiveGeneration()) {
    cancelButton.disabled = true;
    explanation.textContent = "Cancelling the live trace request...";
  }
});
promptInput.addEventListener("input", () => {
  if (canEditPrompt()) {
    if (trailStarted) {
      resetDemo({ restoreSelectedTrace: true });
    }
    renderTokens(promptTokens, simpleTokenise(promptInput.value));
  }
});
generationPosition.addEventListener("input", () => {
  if (!trailStarted) {
    return;
  }
  clearTimeout(timer);
  timer = null;
  renderGenerationPosition(Number(generationPosition.value));
  updatePlayButton();
});
trailSpeedSelect.addEventListener("change", () => {
  if (timer) {
    scheduleNextStep();
  }
});
playButton.addEventListener("click", startDemo);
resetButton.addEventListener("click", () => {
  const cancelled = cancelActiveGeneration();
  resetDemo({ restoreSelectedTrace: true });
  resetPromptToTrace();
  if (cancelled) {
    runNotice = "Trace request cancelled";
    explanation.textContent = runNotice;
  }
});

Promise.all([loadRuntimeOptions(), loadTraceList()]).catch((error) => {
  retryRuntimeButton.hidden = false;
  explanation.textContent = `Could not load demo data: ${error.message || error}. Refresh the runtime or reload the page.`;
});
