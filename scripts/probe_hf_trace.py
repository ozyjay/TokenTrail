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
