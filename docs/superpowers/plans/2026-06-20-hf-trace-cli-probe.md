# HF Trace CLI Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable CLI probe that checks whether Hugging Face Transformers can produce Token Trail-shaped `hf-live-trace` JSON on the local machine.

**Architecture:** Add one developer-only script at `scripts/probe_hf_trace.py`. Keep pure trace conversion helpers importable and testable without importing `torch` or `transformers`; load the heavy ML libraries lazily only inside the real probe path. Reuse `token_trail.adapters.hf_trace.validate_trace_payload` as the final contract check.

**Tech Stack:** Python 3.12 from active `pyenv`, standard library, optional local `torch`, optional local `transformers`, existing `pytest` test suite.

---

## File Structure

- Create `scripts/probe_hf_trace.py`
  - Owns CLI argument parsing, lazy ML imports, model/tokenizer loading, generation, trace conversion helpers, output formatting, and exit codes.
  - Must be importable when `torch` and `transformers` are not installed.
- Create `tests/test_probe_hf_trace.py`
  - Tests pure helpers and CLI importability without loading real HF models.
  - Uses small fake tensor/tokenizer objects rather than importing `torch`.
- No changes to `pyproject.toml`
  - Do not add heavy runtime dependencies during this spike.
- No changes to Token Trail server, runtime config, or web UI
  - The CLI probe is intentionally separate from app runtime integration.

---

### Task 1: Add Importable Probe Skeleton And CLI Defaults

**Files:**
- Create: `scripts/probe_hf_trace.py`
- Create: `tests/test_probe_hf_trace.py`

- [ ] **Step 1: Write the failing import and argument-default tests**

Create `tests/test_probe_hf_trace.py` with:

```python
import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "probe_hf_trace.py"


def load_probe_module():
    spec = importlib.util.spec_from_file_location("probe_hf_trace", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_probe_module_imports_without_hf_dependencies() -> None:
    probe = load_probe_module()

    assert probe.DEFAULT_MODEL == "Qwen/Qwen2.5-0.5B-Instruct"
    assert probe.DEFAULT_PROMPT == "Write one sentence about a robot at university."


def test_parse_args_uses_fast_probe_defaults() -> None:
    probe = load_probe_module()

    args = probe.parse_args([])

    assert args.model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert args.prompt == "Write one sentence about a robot at university."
    assert args.max_new_tokens == 24
    assert args.top_k == 5
    assert args.temperature == 0.3
    assert args.json is False
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py -v
```

Expected: FAIL because `scripts/probe_hf_trace.py` does not exist.

- [ ] **Step 3: Add the minimal CLI skeleton**

Create `scripts/probe_hf_trace.py` with:

```python
"""Probe whether Hugging Face Transformers can return Token Trail trace JSON.

This is a developer-only spike script. It does not change Token Trail runtime
behaviour and does not require Hugging Face dependencies during automated tests.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from token_trail.adapters.base import AdapterError  # noqa: E402
from token_trail.adapters.hf_trace import validate_trace_payload  # noqa: E402


DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_PROMPT = "Write one sentence about a robot at university."
DEFAULT_MAX_NEW_TOKENS = 24
DEFAULT_TOP_K = 5
DEFAULT_TEMPERATURE = 0.3
TRACE_EXPLANATION = "Top returned alternatives from the local model for this token position."


class ProbeError(Exception):
    """Raised when the HF trace probe cannot produce a valid trace."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe HF Transformers trace generation.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face model id or local model path")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt to generate from")
    parser.add_argument("--max-new-tokens", default=DEFAULT_MAX_NEW_TOKENS, type=int, help="Generated token budget")
    parser.add_argument("--top-k", default=DEFAULT_TOP_K, type=int, help="Candidate alternatives per generated token")
    parser.add_argument("--temperature", default=DEFAULT_TEMPERATURE, type=float, help="Sampling temperature")
    parser.add_argument("--json", action="store_true", help="Print full trace JSON instead of the compact summary")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        trace, elapsed_seconds = run_probe(args)
    except ProbeError as error:
        print(f"HF trace probe failed: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(trace, ensure_ascii=False, indent=2))
    else:
        print_summary(trace=trace, elapsed_seconds=elapsed_seconds)
    return 0


def run_probe(args: argparse.Namespace) -> tuple[dict[str, Any], float]:
    raise ProbeError("HF probe implementation is incomplete")


def print_summary(*, trace: dict[str, Any], elapsed_seconds: float) -> None:
    print("HF Transformers trace probe")
    print(f"model tested: {trace.get('model', 'missing')}")
    print(f"generated text: {generated_text_from_trace(trace)}")
    print(f"prompt tokens: {len(trace.get('prompt_tokens', []))}")
    print(f"generation steps: {len(trace.get('steps', []))}")
    print(f"elapsed seconds: {elapsed_seconds:.2f}")


def generated_text_from_trace(trace: dict[str, Any]) -> str:
    return "".join(str(step.get("selected_token", "")) for step in trace.get("steps", []))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the skeleton tests**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the skeleton**

Run:

```bash
git add scripts/probe_hf_trace.py tests/test_probe_hf_trace.py
git commit -m "Add HF trace probe CLI skeleton"
```

---

### Task 2: Add Pure Candidate And Trace Conversion Helpers

**Files:**
- Modify: `scripts/probe_hf_trace.py`
- Modify: `tests/test_probe_hf_trace.py`

- [ ] **Step 1: Add failing tests for candidate conversion and trace validation**

Append to `tests/test_probe_hf_trace.py`:

```python
class FakeScalar:
    def __init__(self, value: float) -> None:
        self._value = value

    def item(self) -> float:
        return self._value


class FakeTokenizer:
    def __init__(self, values: dict[int, str]) -> None:
        self.values = values

    def decode(self, token_id: int, skip_special_tokens: bool = True) -> str:
        return self.values[token_id]


def test_build_candidates_deduplicates_empty_and_repeated_decoded_tokens() -> None:
    probe = load_probe_module()
    tokenizer = FakeTokenizer({1: "A", 2: "A", 3: "", 4: " robot", 5: "The"})
    top_indices = [1, 2, 3, 4, 5]
    top_probabilities = [FakeScalar(0.42), FakeScalar(0.21), FakeScalar(0.14), FakeScalar(0.13), FakeScalar(0.10)]

    candidates = probe.build_candidates(
        tokenizer=tokenizer,
        selected_token_id=4,
        selected_probability=0.13,
        top_indices=top_indices,
        top_probabilities=top_probabilities,
    )

    assert candidates == [
        {"token": "A", "probability": 0.42},
        {"token": " robot", "probability": 0.13},
        {"token": "The", "probability": 0.10},
    ]


def test_build_trace_payload_matches_token_trail_contract() -> None:
    probe = load_probe_module()
    tokenizer = FakeTokenizer({10: "Write", 11: " one", 12: " sentence", 21: "A", 22: " robot"})
    prompt_token_ids = [10, 11, 12]
    selected_token_ids = [21, 22]
    candidates_by_step = [
        [{"token": "A", "probability": 0.7}, {"token": "The", "probability": 0.2}],
        [{"token": " robot", "probability": 0.6}, {"token": " student", "probability": 0.3}],
    ]

    trace = probe.build_trace_payload(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        prompt="Write one sentence",
        tokenizer=tokenizer,
        prompt_token_ids=prompt_token_ids,
        selected_token_ids=selected_token_ids,
        candidates_by_step=candidates_by_step,
    )

    probe.validate_trace_payload(trace)
    assert trace["mode"] == "hf-live-trace"
    assert trace["prompt_tokens"] == ["Write", " one", " sentence"]
    assert [step["selected_token"] for step in trace["steps"]] == ["A", " robot"]
    assert trace["steps"][0]["explanation"] == probe.TRACE_EXPLANATION
```

- [ ] **Step 2: Run the failing helper tests**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py -v
```

Expected: FAIL because `build_candidates` and `build_trace_payload` are missing.

- [ ] **Step 3: Implement pure helper functions**

Add these functions to `scripts/probe_hf_trace.py` above `run_probe`:

```python
def decode_token(tokenizer: Any, token_id: int) -> str:
    return str(tokenizer.decode(int(token_id), skip_special_tokens=True))


def decode_token_ids(tokenizer: Any, token_ids: Sequence[int]) -> list[str]:
    return [decode_token(tokenizer, token_id) for token_id in token_ids if decode_token(tokenizer, token_id)]


def scalar_to_float(value: Any) -> float:
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def build_candidates(
    *,
    tokenizer: Any,
    selected_token_id: int,
    selected_probability: float,
    top_indices: Sequence[int],
    top_probabilities: Sequence[Any],
) -> list[dict[str, float | str]]:
    candidates_by_token: dict[str, float] = {}

    for token_id, probability_value in zip(top_indices, top_probabilities, strict=False):
        token = decode_token(tokenizer, int(token_id))
        if not token:
            continue
        probability = scalar_to_float(probability_value)
        if probability < 0 or probability > 1:
            continue
        if token not in candidates_by_token or probability > candidates_by_token[token]:
            candidates_by_token[token] = probability

    selected_token = decode_token(tokenizer, int(selected_token_id))
    if selected_token and selected_token not in candidates_by_token and 0 <= selected_probability <= 1:
        candidates_by_token[selected_token] = float(selected_probability)

    return [
        {"token": token, "probability": probability}
        for token, probability in sorted(candidates_by_token.items(), key=lambda item: item[1], reverse=True)
    ]


def build_trace_payload(
    *,
    model: str,
    prompt: str,
    tokenizer: Any,
    prompt_token_ids: Sequence[int],
    selected_token_ids: Sequence[int],
    candidates_by_step: Sequence[list[dict[str, float | str]]],
) -> dict[str, Any]:
    steps = []
    for selected_token_id, candidates in zip(selected_token_ids, candidates_by_step, strict=True):
        selected_token = decode_token(tokenizer, int(selected_token_id))
        if not selected_token:
            continue
        steps.append(
            {
                "selected_token": selected_token,
                "candidates": candidates,
                "explanation": TRACE_EXPLANATION,
            }
        )

    trace = {
        "mode": "hf-live-trace",
        "model": model,
        "prompt": prompt,
        "prompt_tokens": decode_token_ids(tokenizer, prompt_token_ids),
        "steps": steps,
    }
    validate_trace_payload(trace)
    return trace
```

- [ ] **Step 4: Run helper tests**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the helpers**

Run:

```bash
git add scripts/probe_hf_trace.py tests/test_probe_hf_trace.py
git commit -m "Add HF trace conversion helpers"
```

---

### Task 3: Add Lazy Transformers Generation Path

**Files:**
- Modify: `scripts/probe_hf_trace.py`
- Modify: `tests/test_probe_hf_trace.py`

- [ ] **Step 1: Add failing lazy-import error test**

Append to `tests/test_probe_hf_trace.py`:

```python
def test_load_hf_libraries_reports_missing_dependency(monkeypatch) -> None:
    probe = load_probe_module()
    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "torch":
            raise ImportError("torch missing in test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    try:
        probe.load_hf_libraries()
    except probe.ProbeError as error:
        assert "Missing optional dependency 'torch'" in str(error)
        assert "python3 -m pip install torch transformers" in str(error)
    else:
        raise AssertionError("expected ProbeError")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py::test_load_hf_libraries_reports_missing_dependency -v
```

Expected: FAIL because `load_hf_libraries` is missing.

- [ ] **Step 3: Implement lazy library loading and real probe path**

Replace the current `run_probe` stub in `scripts/probe_hf_trace.py` and add `load_hf_libraries`, `load_model_and_tokenizer`, `generate_with_scores`, `build_trace_from_generation`, and `normalise_token_id_list`:

```python
def load_hf_libraries() -> tuple[Any, Any, Any]:
    try:
        import torch
    except ImportError as error:
        raise ProbeError(
            "Missing optional dependency 'torch'. Install probe dependencies in the active pyenv Python with: "
            "python3 -m pip install torch transformers"
        ) from error

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise ProbeError(
            "Missing optional dependency 'transformers'. Install probe dependencies in the active pyenv Python with: "
            "python3 -m pip install torch transformers"
        ) from error

    return torch, AutoModelForCausalLM, AutoTokenizer


def run_probe(args: argparse.Namespace) -> tuple[dict[str, Any], float]:
    torch, model_class, tokenizer_class = load_hf_libraries()
    started_at = time.perf_counter()

    tokenizer, model = load_model_and_tokenizer(
        model_name=args.model,
        model_class=model_class,
        tokenizer_class=tokenizer_class,
        torch_module=torch,
    )
    generated = generate_with_scores(
        tokenizer=tokenizer,
        model=model,
        torch_module=torch,
        prompt=args.prompt,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )
    trace = build_trace_from_generation(
        model_name=args.model,
        prompt=args.prompt,
        tokenizer=tokenizer,
        torch_module=torch,
        generated=generated,
        top_k=args.top_k,
    )

    try:
        validate_trace_payload(trace)
    except AdapterError as error:
        raise ProbeError(f"Generated trace did not match Token Trail contract: {error}") from error

    return trace, time.perf_counter() - started_at


def load_model_and_tokenizer(*, model_name: str, model_class: Any, tokenizer_class: Any, torch_module: Any) -> tuple[Any, Any]:
    try:
        tokenizer = tokenizer_class.from_pretrained(model_name)
        model = model_class.from_pretrained(model_name, torch_dtype="auto", device_map="auto")
    except Exception as error:
        raise ProbeError(f"Failed to load model or tokenizer for {model_name!r}: {error}") from error

    if getattr(tokenizer, "pad_token_id", None) is None and getattr(tokenizer, "eos_token_id", None) is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model.eval()
    return tokenizer, model


def generate_with_scores(
    *,
    tokenizer: Any,
    model: Any,
    torch_module: Any,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
) -> Any:
    if max_new_tokens < 1:
        raise ProbeError("--max-new-tokens must be at least 1")
    if temperature < 0:
        raise ProbeError("--temperature must not be negative")

    try:
        encoded = tokenizer(prompt, return_tensors="pt")
        model_device = getattr(model, "device", None)
        if model_device is not None and hasattr(encoded, "to"):
            encoded = encoded.to(model_device)

        do_sample = temperature > 0
        generation_kwargs = {
            "return_dict_in_generate": True,
            "output_scores": True,
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
        }
        if do_sample:
            generation_kwargs["temperature"] = temperature
        if getattr(tokenizer, "eos_token_id", None) is not None:
            generation_kwargs["pad_token_id"] = tokenizer.eos_token_id

        with torch_module.no_grad():
            return model.generate(**encoded, **generation_kwargs)
    except Exception as error:
        raise ProbeError(f"Generation failed: {error}") from error


def build_trace_from_generation(
    *,
    model_name: str,
    prompt: str,
    tokenizer: Any,
    torch_module: Any,
    generated: Any,
    top_k: int,
) -> dict[str, Any]:
    if top_k < 1:
        raise ProbeError("--top-k must be at least 1")
    if not hasattr(generated, "sequences") or not hasattr(generated, "scores"):
        raise ProbeError("Generation output did not include sequences and scores")
    if not generated.scores:
        raise ProbeError("Generation returned no score tensors")

    sequence = generated.sequences[0]
    prompt_length = len(sequence) - len(generated.scores)
    if prompt_length < 1:
        raise ProbeError("Could not infer prompt token length from generation output")

    prompt_token_ids = normalise_token_id_list(sequence[:prompt_length])
    selected_token_ids = normalise_token_id_list(sequence[prompt_length:])
    if not selected_token_ids:
        raise ProbeError("Generation returned no selected token ids")

    candidates_by_step: list[list[dict[str, float | str]]] = []
    for selected_token_id, score_tensor in zip(selected_token_ids, generated.scores, strict=False):
        probabilities = torch_module.softmax(score_tensor[0], dim=-1)
        selected_probability = scalar_to_float(probabilities[int(selected_token_id)])
        effective_top_k = min(int(top_k), int(probabilities.numel()))
        top_probabilities, top_indices = torch_module.topk(probabilities, effective_top_k)
        candidates = build_candidates(
            tokenizer=tokenizer,
            selected_token_id=int(selected_token_id),
            selected_probability=selected_probability,
            top_indices=normalise_token_id_list(top_indices),
            top_probabilities=list(top_probabilities),
        )
        if not candidates:
            raise ProbeError("A generated step had no usable candidate alternatives")
        candidates_by_step.append(candidates)

    return build_trace_payload(
        model=model_name,
        prompt=prompt,
        tokenizer=tokenizer,
        prompt_token_ids=prompt_token_ids,
        selected_token_ids=selected_token_ids,
        candidates_by_step=candidates_by_step,
    )


def normalise_token_id_list(values: Any) -> list[int]:
    if hasattr(values, "tolist"):
        values = values.tolist()
    if isinstance(values, int):
        return [values]
    return [int(value) for value in values]
```

- [ ] **Step 4: Run the full probe tests**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit lazy generation path**

Run:

```bash
git add scripts/probe_hf_trace.py tests/test_probe_hf_trace.py
git commit -m "Add lazy HF trace generation path"
```

---

### Task 4: Polish Summary Output And JSON Mode

**Files:**
- Modify: `scripts/probe_hf_trace.py`
- Modify: `tests/test_probe_hf_trace.py`

- [ ] **Step 1: Add failing tests for generated text and preview output**

Append to `tests/test_probe_hf_trace.py`:

```python
def test_generated_text_from_trace_joins_selected_tokens() -> None:
    probe = load_probe_module()
    trace = {
        "steps": [
            {"selected_token": "A"},
            {"selected_token": " robot"},
            {"selected_token": " studied"},
            {"selected_token": "."},
        ]
    }

    assert probe.generated_text_from_trace(trace) == "A robot studied."


def test_format_step_preview_includes_candidates() -> None:
    probe = load_probe_module()
    trace = {
        "steps": [
            {
                "selected_token": "A",
                "candidates": [
                    {"token": "A", "probability": 0.42},
                    {"token": "The", "probability": 0.31},
                ],
            }
        ]
    }

    assert probe.format_step_preview(trace) == ["1. selected='A' candidates='A' 0.420, 'The' 0.310"]
```

- [ ] **Step 2: Run the failing output tests**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py::test_generated_text_from_trace_joins_selected_tokens tests/test_probe_hf_trace.py::test_format_step_preview_includes_candidates -v
```

Expected: FAIL because text joining is too naive and `format_step_preview` is missing.

- [ ] **Step 3: Implement summary helpers**

Replace `generated_text_from_trace` and `print_summary` in `scripts/probe_hf_trace.py`, and add `format_step_preview`:

```python
def print_summary(*, trace: dict[str, Any], elapsed_seconds: float) -> None:
    print("HF Transformers trace probe")
    print(f"model tested: {trace.get('model', 'missing')}")
    print(f"generated text: {generated_text_from_trace(trace)}")
    print(f"prompt tokens: {len(trace.get('prompt_tokens', []))}")
    print(f"generation steps: {len(trace.get('steps', []))}")
    print(f"elapsed seconds: {elapsed_seconds:.2f}")
    print()
    print("First generated steps:")
    previews = format_step_preview(trace)
    if previews:
        for line in previews:
            print(line)
    else:
        print("No generated steps returned.")


def generated_text_from_trace(trace: dict[str, Any]) -> str:
    text = "".join(str(step.get("selected_token", "")) for step in trace.get("steps", []))
    return text.replace(" .", ".").replace(" ,", ",").replace(" :", ":").strip()


def format_step_preview(trace: dict[str, Any], limit: int = 5) -> list[str]:
    previews: list[str] = []
    for index, step in enumerate(trace.get("steps", [])[:limit], start=1):
        candidates = []
        for candidate in step.get("candidates", [])[:5]:
            token = str(candidate.get("token", ""))
            probability = float(candidate.get("probability", 0))
            candidates.append(f"{token!r} {probability:.3f}")
        previews.append(f"{index}. selected={step.get('selected_token', '')!r} candidates={', '.join(candidates)}")
    return previews
```

- [ ] **Step 4: Run full probe tests**

Run:

```bash
python3 -m pytest tests/test_probe_hf_trace.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all automated tests**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS for the full suite.

- [ ] **Step 6: Commit output polish**

Run:

```bash
git add scripts/probe_hf_trace.py tests/test_probe_hf_trace.py
git commit -m "Polish HF trace probe output"
```

---

### Task 5: Manual Probe Documentation And Verification

**Files:**
- Modify: `docs/LOCAL_TEST_NOTES.md`

- [ ] **Step 1: Add a failing docs expectation**

Append to `tests/test_development_docs.py`:

```python
def test_local_test_notes_document_hf_trace_probe() -> None:
    notes = (PROJECT_ROOT / "docs/LOCAL_TEST_NOTES.md").read_text(encoding="utf-8")

    assert "HF trace CLI probe" in notes
    assert "python3 scripts/probe_hf_trace.py" in notes
```

- [ ] **Step 2: Run the failing docs test**

Run:

```bash
python3 -m pytest tests/test_development_docs.py::test_local_test_notes_document_hf_trace_probe -v
```

Expected: FAIL because `docs/LOCAL_TEST_NOTES.md` does not mention the HF trace probe yet.

- [ ] **Step 3: Document manual verification commands**

Append this section to `docs/LOCAL_TEST_NOTES.md`:

```markdown
## HF trace CLI probe

**Context:** The HF trace path is still a spike. The CLI probe checks whether the current machine can load a small Hugging Face Transformers causal language model and convert generated token scores into Token Trail-shaped `hf-live-trace` JSON.

**Install optional probe dependencies in the active pyenv Python if needed:**

```bash
python3 -m pip install torch transformers
```

**Run a compact human-readable probe:**

```bash
python3 scripts/probe_hf_trace.py --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5
```

**Run JSON mode for contract inspection:**

```bash
python3 scripts/probe_hf_trace.py --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5 --json
```

**Pass condition:** generated text appears, generation steps are non-empty, each step has candidate alternatives, elapsed time is acceptable for rehearsal, and the script exits with status `0`.

**Fail condition:** keep `TOKEN_TRAIL_HF_TRACE_ENABLED=false` if model load time, memory use, generation latency, or trace quality is not acceptable on the target machine.
```

- [ ] **Step 4: Run docs test**

Run:

```bash
python3 -m pytest tests/test_development_docs.py::test_local_test_notes_document_hf_trace_probe -v
```

Expected: PASS.

- [ ] **Step 5: Run all automated tests**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Optionally run the real HF probe**

Run this only if `torch` and `transformers` are installed or you are ready to install them in the active `pyenv` environment:

```bash
python3 scripts/probe_hf_trace.py --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5
```

Expected on success: output begins with `HF Transformers trace probe`, includes generated text, reports non-zero generation steps, and exits `0`.

If dependencies are missing, expected output includes:

```text
HF trace probe failed: Missing optional dependency
```

- [ ] **Step 7: Commit docs and verification updates**

Run:

```bash
git add docs/LOCAL_TEST_NOTES.md tests/test_development_docs.py
git commit -m "Document HF trace probe verification"
```

---

## Final Verification

- [ ] Run:

```bash
python3 -m pytest -q
```

Expected: PASS.

- [ ] Check that heavy dependencies were not added:

```bash
git diff HEAD~4..HEAD -- pyproject.toml poetry.lock
```

Expected: no dependency additions for `torch` or `transformers`.

- [ ] Check status:

```bash
git status --short
```

Expected: clean working tree, unless the optional real-model smoke run created an external model cache outside the repo.

---

## Self-Review Notes

- Spec coverage: the plan creates `scripts/probe_hf_trace.py`, validates the `hf-live-trace` contract, prints summary or JSON output, handles missing optional dependencies clearly, avoids `pyproject.toml` dependency changes, and leaves server/runtime/UI integration untouched.
- Placeholder scan: no implementation step relies on an unspecified helper; each introduced function has a concrete code block.
- Type consistency: helper names and signatures are consistent across tests and implementation steps.
