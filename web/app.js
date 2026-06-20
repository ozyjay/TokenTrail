const traceSelect = document.querySelector("#traceSelect");
const runtimeSelect = document.querySelector("#runtimeSelect");
const trailSpeedSelect = document.querySelector("#trailSpeedSelect");
const playButton = document.querySelector("#playButton");
const resetButton = document.querySelector("#resetButton");
const promptText = document.querySelector("#promptText");
const promptInput = document.querySelector("#promptInput");
const promptTokens = document.querySelector("#promptTokens");
const candidateList = document.querySelector("#candidateList");
const generatedText = document.querySelector("#generatedText");
const explanation = document.querySelector("#explanation");

let currentTrace = null;
let selectedTrace = null;
let currentRuntime = null;
let timer = null;
let generatedTokens = [];
let stepIndex = 0;
let runNotice = "";

const TRAIL_SPEED_DELAYS_MS = {
  slow: 2200,
  normal: 1500,
  fast: 700,
};

async function loadRuntimeOptions() {
  const response = await fetch("/api/runtime");
  const payload = await response.json();
  currentRuntime = payload.selected;

  runtimeSelect.replaceChildren(
    ...payload.options.map((option) => {
      const item = document.createElement("option");
      item.value = option.id;
      item.textContent = option.label;
      if (!option.available && option.backend !== "scripted") {
        item.textContent += " (unavailable)";
      }
      return item;
    }),
  );

  runtimeSelect.value = payload.selected_id;
  renderRuntimeStatus(payload.selected);
  renderPrompt();
}

async function selectRuntime() {
  const response = await fetch("/api/runtime/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runtime_id: runtimeSelect.value }),
  });
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "Runtime selection failed");
  }

  currentRuntime = payload.selected;
  resetDemo({ restoreSelectedTrace: true });
  renderRuntimeStatus(payload.selected);
}

function renderRuntimeStatus(runtime) {
  const suffix = runtime.available ? "ready" : "unavailable";
  runtimeSelect.title = `${runtime.backend}: ${runtime.model || "prepared traces"} · ${suffix}. ${runtime.notes}`;
  runtimeSelect.setAttribute("aria-label", `Runtime: ${runtime.label}, ${suffix}`);
  updatePlayButton();
}

function updatePlayButton() {
  playButton.textContent = buttonLabelForRuntime();
  playButton.disabled = false;
}

async function loadTraceList() {
  const response = await fetch("/api/traces");
  const payload = await response.json();

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
  selectedTrace = await response.json();
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

function simpleTokenise(text) {
  return text.replaceAll(".", " .").replaceAll(",", " ,").replaceAll(":", " :").split(/\s+/).filter(Boolean);
}

function canEditPrompt() {
  return currentRuntime && currentRuntime.backend === "hf-trace" && currentRuntime.available;
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
    const visibleTokens = promptInput.value === trace.prompt ? trace.prompt_tokens : simpleTokenise(promptInput.value);
    renderTokens(promptTokens, visibleTokens);
    return;
  }

  promptInput.hidden = true;
  promptText.hidden = false;
  promptText.textContent = trace.prompt;
  renderTokens(promptTokens, trace.prompt_tokens);
}

function renderCandidates(step) {
  candidateList.replaceChildren(
    ...step.candidates.map((candidate) => {
      const row = document.createElement("div");
      row.className = candidate.token === step.selected_token ? "candidate selected" : "candidate";

      const label = document.createElement("span");
      label.className = "candidate-token";
      label.textContent = candidate.token;

      const barWrap = document.createElement("span");
      barWrap.className = "bar-wrap";

      const bar = document.createElement("span");
      bar.className = "bar";
      bar.style.width = `${Math.round(candidate.probability * 100)}%`;
      barWrap.append(bar);

      const probability = document.createElement("span");
      probability.className = "probability";
      probability.textContent = `${Math.round(candidate.probability * 100)}%`;

      row.append(label, barWrap, probability);
      return row;
    }),
  );
}

function joinTokens(tokens) {
  return tokens.join(" ").replaceAll(" .", ".").replaceAll(" ,", ",").replaceAll(" :", ":");
}

function trailDelayMs() {
  return TRAIL_SPEED_DELAYS_MS[trailSpeedSelect.value] || TRAIL_SPEED_DELAYS_MS.normal;
}

function scheduleNextStep() {
  clearTimeout(timer);
  timer = setTimeout(runStep, trailDelayMs());
}

function runStep() {
  if (!currentTrace || stepIndex >= currentTrace.steps.length) {
    playButton.textContent = "Replay trail";
    clearTimeout(timer);
    timer = null;
    return;
  }

  const step = currentTrace.steps[stepIndex];
  renderCandidates(step);
  generatedTokens.push(step.selected_token);
  generatedText.textContent = joinTokens(generatedTokens);
  explanation.textContent = runNotice ? `${runNotice}. ${step.explanation}` : step.explanation;
  stepIndex += 1;
  scheduleNextStep();
}

async function generateTrace() {
  const body = { runtime_id: currentRuntime.id, trace_id: traceSelect.value };
  if (canEditPrompt()) {
    body.prompt = promptInput.value.trim();
  }

  const response = await fetch("/api/generate-trace", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "Generation failed");
  }

  return payload;
}

function showHfLiveTrace(payload) {
  if (payload.trace) {
    currentTrace = payload.trace;
  }
  resetDemo();
  resetPromptToTrace();
  runNotice = "HF live trace — top returned alternatives from the local model";
  explanation.textContent = runNotice;
  startPreparedTrail();
}

function loadFallbackTrace(payload) {
  currentTrace = payload.trace || selectedTrace || currentTrace;
  resetDemo();
  resetPromptToTrace();
  runNotice = "Live generation unavailable — showing prepared trace";
  explanation.textContent = runNotice;
  startPreparedTrail();
}

async function startDemo() {
  if (timer) {
    return;
  }

  if (currentRuntime && currentRuntime.backend !== "scripted") {
    playButton.textContent = currentRuntime.available ? "Generating..." : "Loading prepared trail...";
    try {
      const payload = await generateTrace();
      if (payload.mode === "hf-live-trace") {
        showHfLiveTrace(payload);
      } else {
        loadFallbackTrace(payload);
      }
    } catch (error) {
      resetDemo({ restoreSelectedTrace: true });
      runNotice = `Live generation unavailable — showing prepared trace (${error})`;
      explanation.textContent = runNotice;
      startPreparedTrail();
    }
    return;
  }

  startPreparedTrail();
}

function startPreparedTrail() {
  if (stepIndex >= currentTrace.steps.length) {
    resetDemo();
  }

  playButton.textContent = "Running...";
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
  runNotice = "";
  candidateList.replaceChildren();
  generatedText.textContent = "";
  explanation.textContent = "Press start to see candidate tokens appear step by step.";
  renderPrompt();
  updatePlayButton();
}

function buttonLabelForRuntime() {
  if (!currentRuntime || currentRuntime.backend === "scripted") {
    return "Start trail";
  }
  return currentRuntime.available ? "Generate live trail" : "Show prepared trail";
}

traceSelect.addEventListener("change", loadSelectedTrace);
runtimeSelect.addEventListener("change", () => {
  selectRuntime().catch((error) => {
    explanation.textContent = `Could not switch runtime: ${error}`;
  });
});
promptInput.addEventListener("input", () => {
  if (canEditPrompt()) {
    renderTokens(promptTokens, simpleTokenise(promptInput.value));
  }
});
trailSpeedSelect.addEventListener("change", () => {
  if (timer) {
    scheduleNextStep();
  }
});
playButton.addEventListener("click", startDemo);
resetButton.addEventListener("click", () => resetDemo({ restoreSelectedTrace: true }));

Promise.all([loadRuntimeOptions(), loadTraceList()]).catch((error) => {
  explanation.textContent = `Could not load demo data: ${error}`;
});
