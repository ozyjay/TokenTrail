# HF Trace CLI Probe Design

## Purpose

Build a small, repeatable CLI spike that checks whether a local Hugging Face Transformers model can produce Token Trail-shaped live trace JSON with generated tokens and candidate alternatives.

The spike answers one question: can this machine generate a short, non-empty `hf-live-trace` payload quickly and reliably enough to justify a later local HTTP trace server?

## Scope

In scope:

- Add a standalone probe script at `scripts/probe_hf_trace.py`.
- Load a causal language model and tokenizer through Hugging Face Transformers.
- Generate a short response with `return_dict_in_generate=True` and `output_scores=True`.
- Convert generated token IDs and per-step score tensors into Token Trail trace steps.
- Validate the output with `token_trail.adapters.hf_trace.validate_trace_payload`.
- Print a compact human-readable summary by default.
- Optionally print the full trace JSON with `--json`.

Out of scope:

- Running an HTTP server on port `8600`.
- Adding new Token Trail runtime integration.
- Changing the web UI.
- Enabling `TOKEN_TRAIL_HF_TRACE_ENABLED` by default.
- Sending visitor-edited free text through the HF path.

## CLI Behaviour

The probe defaults to a small model:

```text
Qwen/Qwen2.5-0.5B-Instruct
```

The script accepts:

- `--model`
- `--prompt`
- `--max-new-tokens`
- `--top-k`
- `--temperature`
- `--json`

The default prompt should be short and public-demo-safe. Defaults should favour a fast probe over model quality.

On success, the probe prints:

- model name;
- generated text;
- prompt token count;
- generation step count;
- elapsed time;
- a short preview of selected tokens and candidate alternatives.

With `--json`, it prints the full trace-shaped payload instead of the preview.

## Trace Construction

The generated payload uses the existing planned contract:

```json
{
  "mode": "hf-live-trace",
  "model": "Qwen/Qwen2.5-0.5B-Instruct",
  "prompt": "Write one sentence about a robot at university.",
  "prompt_tokens": ["Write", " one", " sentence"],
  "steps": [
    {
      "selected_token": "A",
      "candidates": [
        {"token": "A", "probability": 0.31},
        {"token": "The", "probability": 0.22}
      ],
      "explanation": "Top returned alternatives from the local model for this token position."
    }
  ]
}
```

For each generated token:

1. Decode the selected token ID.
2. Convert the matching score vector to probabilities with softmax.
3. Select the top candidate token IDs.
4. Decode candidate token text.
5. Deduplicate empty or repeated display tokens.
6. Ensure the selected token appears in the candidate list when practical.
7. Sort candidates by probability.
8. Add the standard public-safe explanation.

The probe should reject traces with empty steps, empty selected tokens, empty candidate lists, or probabilities outside `0..1`.

## Error Handling

Failures should exit non-zero with a clear message for:

- missing `transformers`;
- missing `torch`;
- model or tokenizer load failure;
- generation failure;
- unsupported generation output;
- invalid trace payload;
- no usable generated steps.

The error messages should name the missing package or failing stage so setup problems are easy to fix.

## Dependencies

The project currently has no runtime dependencies beyond the standard library. This spike should avoid adding heavy dependencies to `pyproject.toml` until the probe proves worthwhile.

The script may import `torch` and `transformers` lazily and explain that they must be installed in the active `pyenv` Python environment.

## Testing

Add focused unit tests for pure conversion helpers if the script contains enough logic to make that practical without importing heavy ML packages at test time.

At minimum, verify:

- score-to-candidate conversion handles duplicate decoded text;
- trace validation catches malformed payloads through the existing validator;
- the script remains importable when `torch` and `transformers` are not installed.

Manual verification for the actual spike is running the script against a small model and checking that:

- generated text appears;
- steps are non-empty;
- candidate alternatives are present;
- elapsed time is recorded;
- JSON mode validates against Token Trail's existing contract.

## Go/No-Go

Proceed to the HTTP trace server only if the CLI probe can return a short trace with non-empty steps and candidate alternatives in acceptable time on the target machine.

Keep HF live trace disabled if model load time, memory pressure, generation latency, or trace quality is not acceptable for rehearsal.
