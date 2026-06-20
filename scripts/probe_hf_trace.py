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
