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
