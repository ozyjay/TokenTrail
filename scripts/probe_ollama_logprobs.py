"""Probe whether local Ollama generate responses include usable logprobs.

This is a developer-only spike script. It does not change Token Trail runtime
behaviour or require Ollama during automated tests.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from token_trail.config import load_config  # noqa: E402


DEFAULT_PROMPT = "Write one sentence about a robot at university."
DEFAULT_MAX_TOKENS = 96
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TOP_LOGPROBS = 5
NO_THINK_PREFIX = "/no_think"


@dataclass(frozen=True)
class TopAlternative:
    token: str
    logprob: float | None


@dataclass(frozen=True)
class TokenLogprobEntry:
    token: str
    logprob: float | None
    top_alternatives: tuple[TopAlternative, ...]


def extract_token_logprob_entries(payload: dict[str, Any]) -> list[TokenLogprobEntry]:
    """Extract token logprob entries from known non-streaming response shapes."""

    raw_logprobs = payload.get("logprobs")
    if isinstance(raw_logprobs, dict):
        raw_entries = raw_logprobs.get("content") or raw_logprobs.get("tokens") or raw_logprobs.get("items")
    else:
        raw_entries = raw_logprobs

    if not isinstance(raw_entries, list):
        return []

    entries: list[TokenLogprobEntry] = []
    for raw_entry in raw_entries:
        entry = _parse_token_entry(raw_entry)
        if entry is not None:
            entries.append(entry)
    return entries


def has_response_text(payload: dict[str, Any]) -> bool:
    return bool(str(payload.get("response", "")).strip())


def has_thinking_text(payload: dict[str, Any]) -> bool:
    return bool(str(payload.get("thinking", "")).strip())


def entry_has_top_alternatives(entry: TokenLogprobEntry) -> bool:
    return bool(entry.top_alternatives)


def _parse_token_entry(raw_entry: Any) -> TokenLogprobEntry | None:
    if isinstance(raw_entry, str):
        return TokenLogprobEntry(token=raw_entry, logprob=None, top_alternatives=())

    if not isinstance(raw_entry, dict):
        return None

    token = _first_string(raw_entry, ("token", "text", "selected_token", "bytes"))
    if token is None:
        return None

    return TokenLogprobEntry(
        token=token,
        logprob=_as_float(raw_entry.get("logprob")),
        top_alternatives=tuple(_parse_top_alternatives(raw_entry.get("top_logprobs"))),
    )


def _parse_top_alternatives(raw_top_logprobs: Any) -> list[TopAlternative]:
    if isinstance(raw_top_logprobs, dict):
        return [
            TopAlternative(token=str(token), logprob=_as_float(logprob))
            for token, logprob in raw_top_logprobs.items()
            if str(token)
        ]

    if not isinstance(raw_top_logprobs, list):
        return []

    alternatives: list[TopAlternative] = []
    for raw_alternative in raw_top_logprobs:
        if isinstance(raw_alternative, dict):
            token = _first_string(raw_alternative, ("token", "text", "bytes"))
            if token is None:
                continue
            alternatives.append(TopAlternative(token=token, logprob=_as_float(raw_alternative.get("logprob"))))
        elif isinstance(raw_alternative, str):
            alternatives.append(TopAlternative(token=raw_alternative, logprob=None))
    return alternatives


def _first_string(values: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float) and math.isfinite(value):
        return float(value)
    return None


def build_payload(
    *,
    model: str,
    prompt: str,
    top_logprobs: int,
    max_tokens: int,
    disable_thinking: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": DEFAULT_TEMPERATURE,
            "logprobs": True,
            "top_logprobs": top_logprobs,
        },
    }

    if disable_thinking:
        payload["prompt"] = _with_no_think_prefix(prompt)
        payload["think"] = False

    return payload


def _with_no_think_prefix(prompt: str) -> str:
    stripped_prompt = prompt.lstrip()
    if stripped_prompt.startswith(NO_THINK_PREFIX):
        return prompt
    return f"{NO_THINK_PREFIX}\n\n{prompt}"


def post_generate(base_url: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/generate"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def print_summary(*, model: str, payload: dict[str, Any], entries: list[TokenLogprobEntry]) -> None:
    response_returned = has_response_text(payload)
    thinking_returned = has_thinking_text(payload)
    entries_with_logprobs = [entry for entry in entries if entry.logprob is not None]
    top_alternatives_present = any(entry_has_top_alternatives(entry) for entry in entries)
    usable = response_returned and bool(entries_with_logprobs) and top_alternatives_present

    print("Ollama logprobs probe")
    print(f"model tested: {model}")
    print(f"response text returned: {_yes_no(response_returned)}")
    print(f"thinking text returned: {_yes_no(thinking_returned)}")
    print(f"done_reason: {payload.get('done_reason', 'missing')}")
    print(f"eval_count: {payload.get('eval_count', 'missing')}")
    print(f"logprobs present: {_yes_no(bool(entries_with_logprobs))}")
    print(f"generated token entries with logprobs: {len(entries_with_logprobs)}")
    print(f"top alternatives present: {_yes_no(top_alternatives_present)}")
    print()
    print("First generated token entries:")

    if entries:
        for index, entry in enumerate(entries[:3], start=1):
            alternatives = _format_alternatives(entry.top_alternatives)
            print(f"{index}. selected={entry.token!r} top_alternatives={alternatives}")
    else:
        print("No token logprob entries returned.")

    print()
    print("Model output handling: response text, if present, is model output and should not be treated as public reasoning.")
    print()
    if not response_returned and thinking_returned:
        print("FAIL: model produced thinking output but no visible response text.")
    elif response_returned and not entries_with_logprobs:
        print("FAIL: visible response returned, but logprobs were not returned by this Ollama/model combination.")
    elif usable:
        print("PASS: usable for SLM live trace.")
    elif response_returned:
        print("FAIL: visible response and logprobs returned, but top_logprobs alternatives were not returned.")
    else:
        print("FAIL: no visible response text was returned.")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _format_alternatives(alternatives: tuple[TopAlternative, ...]) -> str:
    if not alternatives:
        return "none"

    formatted = []
    for alternative in alternatives[:DEFAULT_TOP_LOGPROBS]:
        if alternative.logprob is None:
            formatted.append(repr(alternative.token))
        else:
            formatted.append(f"{alternative.token!r} ({alternative.logprob:.3f})")
    return ", ".join(formatted)


def parse_args() -> argparse.Namespace:
    config = load_config()
    parser = argparse.ArgumentParser(description="Probe Ollama /api/generate logprobs support.")
    parser.add_argument("--model", default=config.ollama_model, help="Ollama model to test")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt to send to Ollama")
    parser.add_argument("--top-logprobs", default=DEFAULT_TOP_LOGPROBS, type=int, help="Requested top alternatives per token")
    parser.add_argument("--max-tokens", default=DEFAULT_MAX_TOKENS, type=int, help="Requested generated token count")
    parser.add_argument("--dump-json", action="store_true", help="Print the full raw JSON response from Ollama")
    return parser.parse_args()


def main() -> int:
    config = load_config()
    args = parse_args()
    payload = build_payload(
        model=args.model,
        prompt=args.prompt,
        top_logprobs=args.top_logprobs,
        max_tokens=args.max_tokens,
        disable_thinking=True,
    )

    try:
        response_payload = post_generate(config.ollama_base_url, payload, config.ollama_timeout_seconds)
    except HTTPError as error:
        print(f"Ollama request failed: HTTP {error.code} {error.reason}")
        return 2
    except (URLError, TimeoutError) as error:
        print(f"Ollama request failed: {error}")
        return 2
    except json.JSONDecodeError as error:
        print(f"Ollama returned invalid JSON: {error}")
        return 2

    entries = extract_token_logprob_entries(response_payload)
    if args.dump_json:
        print(json.dumps(response_payload, ensure_ascii=False, indent=2))
        print()
    print_summary(model=args.model, payload=response_payload, entries=entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
