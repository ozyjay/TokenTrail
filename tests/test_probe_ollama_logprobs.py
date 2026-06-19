import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "probe_ollama_logprobs.py"


def load_probe_module():
    spec = importlib.util.spec_from_file_location("probe_ollama_logprobs", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_token_logprob_entries_from_list_shape() -> None:
    probe = load_probe_module()
    payload = {
        "response": "A robot studied.",
        "logprobs": [
            {
                "token": "A",
                "logprob": -0.2,
                "top_logprobs": [
                    {"token": "A", "logprob": -0.2},
                    {"token": "The", "logprob": -1.1},
                ],
            },
            {
                "token": " robot",
                "logprob": -0.4,
                "top_logprobs": {" robot": -0.4, " student": -1.7},
            },
        ],
    }

    entries = probe.extract_token_logprob_entries(payload)

    assert [entry.token for entry in entries] == ["A", " robot"]
    assert entries[0].logprob == -0.2
    assert [alternative.token for alternative in entries[0].top_alternatives] == ["A", "The"]
    assert [alternative.token for alternative in entries[1].top_alternatives] == [" robot", " student"]


def test_extract_token_logprob_entries_from_content_shape() -> None:
    probe = load_probe_module()
    payload = {
        "response": "The robot enrolled.",
        "logprobs": {
            "content": [
                {
                    "text": "The",
                    "logprob": -0.3,
                    "top_logprobs": [
                        {"text": "The", "logprob": -0.3},
                        {"text": "A", "logprob": -0.9},
                    ],
                }
            ]
        },
    }

    entries = probe.extract_token_logprob_entries(payload)

    assert len(entries) == 1
    assert entries[0].token == "The"
    assert entries[0].top_alternatives[1].token == "A"


def test_extract_token_logprob_entries_returns_empty_for_missing_logprobs() -> None:
    probe = load_probe_module()

    assert probe.extract_token_logprob_entries({"response": "No metadata."}) == []


def test_build_payload_uses_non_streaming_generate_options() -> None:
    probe = load_probe_module()

    payload = probe.build_payload(
        model="qwen3:1.7b",
        prompt="Write one sentence.",
        top_logprobs=7,
        max_tokens=12,
    )

    assert payload == {
        "model": "qwen3:1.7b",
        "prompt": "Write one sentence.",
        "stream": False,
        "options": {
            "num_predict": 12,
            "temperature": 0.3,
            "logprobs": True,
            "top_logprobs": 7,
        },
    }
