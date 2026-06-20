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
