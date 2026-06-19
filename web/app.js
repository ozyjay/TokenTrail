const traceSelect = document.querySelector("#traceSelect");
const playButton = document.querySelector("#playButton");
const resetButton = document.querySelector("#resetButton");
const promptText = document.querySelector("#promptText");
const promptTokens = document.querySelector("#promptTokens");
const candidateList = document.querySelector("#candidateList");
const generatedText = document.querySelector("#generatedText");
const explanation = document.querySelector("#explanation");

let currentTrace = null;
let timer = null;
let generatedTokens = [];
let stepIndex = 0;

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
  currentTrace = await response.json();
  resetDemo();
  promptText.textContent = currentTrace.prompt;
  renderTokens(promptTokens, currentTrace.prompt_tokens);
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

function renderCandidates(step) {
  candidateList.replaceChildren(
    ...step.candidates.map((candidate) => {
      const row = document.createElement("div");
      row.className = candidate.token === step.selected_token ? "candidate selected" : "candidate";

      const label = document.createElement("span");
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

function runStep() {
  if (!currentTrace || stepIndex >= currentTrace.steps.length) {
    playButton.textContent = "Replay trail";
    clearInterval(timer);
    timer = null;
    return;
  }

  const step = currentTrace.steps[stepIndex];
  renderCandidates(step);
  generatedTokens.push(step.selected_token);
  generatedText.textContent = joinTokens(generatedTokens);
  explanation.textContent = step.explanation;
  stepIndex += 1;
}

function startDemo() {
  if (timer) {
    return;
  }

  if (stepIndex >= currentTrace.steps.length) {
    resetDemo();
  }

  playButton.textContent = "Running...";
  runStep();
  timer = setInterval(runStep, 1500);
}

function resetDemo() {
  clearInterval(timer);
  timer = null;
  generatedTokens = [];
  stepIndex = 0;
  candidateList.replaceChildren();
  generatedText.textContent = "";
  explanation.textContent = "Press start to see candidate tokens appear step by step.";
  playButton.textContent = "Start trail";
}

traceSelect.addEventListener("change", loadSelectedTrace);
playButton.addEventListener("click", startDemo);
resetButton.addEventListener("click", resetDemo);

loadTraceList().catch((error) => {
  explanation.textContent = `Could not load scripted traces: ${error}`;
});
