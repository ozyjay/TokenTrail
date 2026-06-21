"""Benchmark configured HF trace models through the local server API."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


DEFAULT_TRACE_URL = "http://127.0.0.1:8600/api/trace"
DEFAULT_OUTPUT_DIR = Path("artifacts/hf_trace_benchmarks")
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_NEW_TOKENS = 96
DEFAULT_TOP_K = 5
DEFAULT_TEMPERATURE = 0.3
CANDIDATE_SOURCE = "forward-logits"
BENCHMARK_PROMPTS = [
    "Write one friendly sentence about a robot helping at university open day.",
    "Explain tokenisation to a curious high school student in one short sentence.",
    "Describe how a small language model predicts the next word in one sentence.",
]
CSV_FIELDS = [
    "model",
    "prompt",
    "candidate_source",
    "success",
    "warmup_seconds",
    "trace_seconds",
    "error",
    "fallback",
    "step_count",
    "generated_text",
    "candidate_count",
]


class BenchmarkError(Exception):
    """Raised when the benchmark cannot run."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark configured HF trace models through the local API.")
    parser.add_argument("--trace-url", default=DEFAULT_TRACE_URL, help="HF trace endpoint URL")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for JSON and CSV results")
    parser.add_argument("--timeout-seconds", default=DEFAULT_TIMEOUT_SECONDS, type=float, help="HTTP timeout")
    parser.add_argument("--max-new-tokens", default=DEFAULT_MAX_NEW_TOKENS, type=int, help="Trace token budget")
    parser.add_argument("--top-k", default=DEFAULT_TOP_K, type=int, help="Candidate alternatives per step")
    parser.add_argument("--temperature", default=DEFAULT_TEMPERATURE, type=float, help="Generation temperature")
    parser.add_argument(
        "--candidate-source",
        default=CANDIDATE_SOURCE,
        choices=(CANDIDATE_SOURCE,),
        help="Candidate source expected from the running HF trace server",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        results = run_benchmark(
            trace_url=args.trace_url,
            prompts=BENCHMARK_PROMPTS,
            timeout_seconds=args.timeout_seconds,
            max_new_tokens=args.max_new_tokens,
            top_k=args.top_k,
            temperature=args.temperature,
            candidate_source=args.candidate_source,
        )
        json_path, csv_path = write_results(
            output_dir=Path(args.output_dir),
            trace_url=args.trace_url,
            candidate_source=args.candidate_source,
            prompts=BENCHMARK_PROMPTS,
            results=results,
        )
    except BenchmarkError as error:
        print(f"HF trace benchmark failed: {error}", file=sys.stderr)
        return 2

    successes = sum(1 for row in results if row["success"])
    print(f"Wrote HF trace benchmark JSON: {json_path}")
    print(f"Wrote HF trace benchmark CSV: {csv_path}")
    print(f"Successful traces: {successes}/{len(results)}")
    return 0 if successes else 1


def run_benchmark(
    *,
    trace_url: str,
    prompts: Sequence[str],
    timeout_seconds: float,
    max_new_tokens: int,
    top_k: int,
    temperature: float,
    candidate_source: str,
    opener: Callable[..., Any] = urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> list[dict[str, Any]]:
    discovery = request_json(_models_url_for_trace_url(trace_url), timeout_seconds=timeout_seconds, opener=opener)
    model_entries = discovery.get("models")
    if not isinstance(model_entries, list):
        raise BenchmarkError("GET /api/models returned no models list")

    results: list[dict[str, Any]] = []
    for entry in model_entries:
        if not isinstance(entry, dict) or not entry.get("configured", False):
            continue
        model = str(entry.get("model") or "")
        if not model:
            continue
        if not entry.get("available", False):
            results.append(_failure_row(model=model, prompt="", candidate_source=candidate_source, error=_entry_reason(entry)))
            continue

        warmup_seconds, warmup_result = _time_request(
            clock,
            lambda: request_json(
                _warmup_url_for_trace_url(trace_url),
                method="POST",
                payload={"model": model},
                timeout_seconds=timeout_seconds,
                opener=opener,
            ),
        )
        if isinstance(warmup_result, str):
            for prompt in prompts:
                results.append(
                    _failure_row(
                        model=model,
                        prompt=prompt,
                        candidate_source=candidate_source,
                        warmup_seconds=warmup_seconds,
                        error=warmup_result,
                    )
                )
            continue

        for prompt in prompts:
            trace_seconds, trace_result = _time_trace(
                trace_url=trace_url,
                model=model,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
                max_new_tokens=max_new_tokens,
                top_k=top_k,
                temperature=temperature,
                opener=opener,
                clock=clock,
            )
            if isinstance(trace_result, str):
                results.append(
                    _failure_row(
                        model=model,
                        prompt=prompt,
                        candidate_source=candidate_source,
                        warmup_seconds=warmup_seconds,
                        trace_seconds=trace_seconds,
                        error=trace_result,
                    )
                )
            else:
                results.append(
                    _success_row(
                        model=model,
                        prompt=prompt,
                        candidate_source=candidate_source,
                        warmup_seconds=warmup_seconds,
                        trace_seconds=trace_seconds,
                        trace=trace_result,
                    )
                )

    return results


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: float,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with opener(request, timeout=float(timeout_seconds)) as response:
            body = response.read().decode("utf-8")
            status = getattr(response, "status", 200)
    except HTTPError as error:
        raise BenchmarkError(f"HTTP {error.code} from {url}: {error.reason}") from error
    except (TimeoutError, URLError, OSError) as error:
        raise BenchmarkError(f"{url} failed: {error}") from error

    if status >= 400:
        raise BenchmarkError(f"HTTP {status} from {url}: {body}")
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as error:
        raise BenchmarkError(f"{url} returned invalid JSON") from error
    if not isinstance(decoded, dict):
        raise BenchmarkError(f"{url} returned a non-object JSON payload")
    return decoded


def write_results(
    *,
    output_dir: Path,
    trace_url: str,
    candidate_source: str,
    prompts: Sequence[str],
    results: Sequence[dict[str, Any]],
    timestamp: str | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base_path = output_dir / f"hf_trace_benchmark_{created_at}"
    json_path = base_path.with_suffix(".json")
    csv_path = base_path.with_suffix(".csv")

    payload = {
        "created_at": created_at,
        "trace_url": trace_url,
        "candidate_source": candidate_source,
        "prompts": list(prompts),
        "results": list(results),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in results:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})

    return json_path, csv_path


def _time_trace(
    *,
    trace_url: str,
    model: str,
    prompt: str,
    timeout_seconds: float,
    max_new_tokens: int,
    top_k: int,
    temperature: float,
    opener: Callable[..., Any],
    clock: Callable[[], float],
) -> tuple[float, dict[str, Any] | str]:
    payload = {
        "model": model,
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
        "top_k": top_k,
        "temperature": temperature,
    }
    elapsed_seconds, result = _time_request(
        clock,
        lambda: request_json(trace_url, method="POST", payload=payload, timeout_seconds=timeout_seconds, opener=opener),
    )
    return elapsed_seconds, result


def _time_request(clock: Callable[[], float], operation: Callable[[], dict[str, Any]]) -> tuple[float, dict[str, Any] | str]:
    start = clock()
    try:
        result = operation()
    except BenchmarkError as error:
        return round(clock() - start, 6), str(error)
    return round(clock() - start, 6), result


def _success_row(
    *,
    model: str,
    prompt: str,
    candidate_source: str,
    warmup_seconds: float,
    trace_seconds: float,
    trace: dict[str, Any],
) -> dict[str, Any]:
    steps = trace.get("steps")
    if not isinstance(steps, list):
        steps = []
    return {
        "model": model,
        "prompt": prompt,
        "candidate_source": candidate_source,
        "success": True,
        "warmup_seconds": warmup_seconds,
        "trace_seconds": trace_seconds,
        "error": "",
        "fallback": _fallback_text(trace),
        "step_count": len(steps),
        "generated_text": _generated_text_from_steps(steps),
        "candidate_count": _candidate_count(steps),
    }


def _failure_row(
    *,
    model: str,
    prompt: str,
    candidate_source: str,
    error: str,
    warmup_seconds: float = 0.0,
    trace_seconds: float = 0.0,
) -> dict[str, Any]:
    return {
        "model": model,
        "prompt": prompt,
        "candidate_source": candidate_source,
        "success": False,
        "warmup_seconds": warmup_seconds,
        "trace_seconds": trace_seconds,
        "error": error,
        "fallback": "",
        "step_count": 0,
        "generated_text": "",
        "candidate_count": 0,
    }


def _entry_reason(entry: dict[str, Any]) -> str:
    reason = entry.get("reason") or entry.get("error")
    return str(reason or "model is not locally available")


def _fallback_text(trace: dict[str, Any]) -> str:
    fallback = trace.get("fallback") or trace.get("error")
    return "" if fallback is None else str(fallback)


def _generated_text_from_steps(steps: Iterable[Any]) -> str:
    tokens = []
    for step in steps:
        if isinstance(step, dict):
            token = step.get("selected_token")
            if isinstance(token, str):
                tokens.append(token)
    return "".join(tokens).strip()


def _candidate_count(steps: Iterable[Any]) -> int:
    total = 0
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("candidates"), list):
            total += len(step["candidates"])
    return total


def _warmup_url_for_trace_url(trace_url: str) -> str:
    parsed = urlparse(trace_url)
    return urlunparse((parsed.scheme or "http", parsed.netloc, "/api/warmup", "", "", ""))


def _models_url_for_trace_url(trace_url: str) -> str:
    parsed = urlparse(trace_url)
    return urlunparse((parsed.scheme or "http", parsed.netloc, "/api/models", "", "", ""))


if __name__ == "__main__":
    raise SystemExit(main())
