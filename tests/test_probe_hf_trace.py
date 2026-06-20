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
    assert args.candidate_source == "forward-logits"
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


class FakeVector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def __getitem__(self, index: int) -> FakeScalar:
        return FakeScalar(self.values[index])

    def numel(self) -> int:
        return len(self.values)


class FakeTorch:
    @staticmethod
    def softmax(score_vector: FakeVector, dim: int = -1) -> FakeVector:
        total = sum(score_vector.values)
        return FakeVector([value / total for value in score_vector.values])

    @staticmethod
    def topk(probabilities: FakeVector, top_k: int) -> tuple[list[FakeScalar], list[int]]:
        ranked = sorted(enumerate(probabilities.values), key=lambda item: item[1], reverse=True)[:top_k]
        return [FakeScalar(value) for _, value in ranked], [index for index, _ in ranked]


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


def test_build_candidates_from_score_vector_uses_raw_logits_for_richer_alternatives() -> None:
    probe = load_probe_module()
    tokenizer = FakeTokenizer({1: "A", 2: "The", 3: "One", 4: " robot"})

    candidates = probe.build_candidates_from_score_vector(
        tokenizer=tokenizer,
        torch_module=FakeTorch,
        selected_token_id=4,
        score_vector=FakeVector([0.0, 5.0, 3.0, 2.0, 4.0]),
        top_k=3,
    )

    assert candidates == [
        {"token": "A", "probability": 5 / 14},
        {"token": " robot", "probability": 4 / 14},
        {"token": "The", "probability": 3 / 14},
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


def test_trim_trace_keeps_first_complete_sentence_after_minimum_steps() -> None:
    probe = load_probe_module()
    trace = make_trace(["A", " robot", " studied", " tokens", " in", " the", " lab", ".", " Extra", "."])

    trimmed = probe.trim_trace_to_complete_sentence(trace)

    assert [step["selected_token"] for step in trimmed["steps"]] == [
        "A",
        " robot",
        " studied",
        " tokens",
        " in",
        " the",
        " lab",
        ".",
    ]
    assert trimmed["steps"][-1]["candidates"] == [{"token": ".", "probability": 1.0}]


def test_trim_trace_ignores_sentence_boundary_before_minimum_steps() -> None:
    probe = load_probe_module()
    trace = make_trace(["A", " robot", ".", " It", " later", " studied", " tokens", " carefully", "."])

    trimmed = probe.trim_trace_to_complete_sentence(trace)

    assert len(trimmed["steps"]) == 9
    assert probe.generated_text_from_trace(trimmed) == "A robot. It later studied tokens carefully."


def test_trim_trace_accepts_sentence_boundary_before_closing_quote() -> None:
    probe = load_probe_module()
    trace = make_trace(["The", " robot", " said", " hello", " to", " the", " room", "!\""])

    trimmed = probe.trim_trace_to_complete_sentence(trace)

    assert len(trimmed["steps"]) == 8
    assert probe.generated_text_from_trace(trimmed) == 'The robot said hello to the room!"'


def test_trim_trace_rejects_incomplete_generation() -> None:
    probe = load_probe_module()
    trace = make_trace(["A", " robot", " studied", " tokens", " in", " the", " lab", " with", " care"])

    try:
        probe.trim_trace_to_complete_sentence(trace)
    except probe.ProbeError as error:
        assert "complete sentence" in str(error)
    else:
        raise AssertionError("expected ProbeError")


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
        assert "Missing required dependency 'torch'" in str(error)
        assert "poetry install" in str(error)
        assert "--with hf-trace" not in str(error)
    else:
        raise AssertionError("expected ProbeError")


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


def test_summary_includes_candidate_source(capsys) -> None:
    probe = load_probe_module()
    trace = {
        "candidate_source": "forward-logits",
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "prompt_tokens": ["Write"],
        "steps": [
            {
                "selected_token": "A",
                "candidates": [{"token": "A", "probability": 0.42}],
            }
        ],
    }

    probe.print_summary(trace=trace, elapsed_seconds=1.25)

    assert "candidate source: forward-logits" in capsys.readouterr().out


def make_trace(tokens: list[str]) -> dict:
    return {
        "mode": "hf-live-trace",
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "prompt": "Write one sentence",
        "prompt_tokens": ["Write", " one", " sentence"],
        "steps": [
            {
                "selected_token": token,
                "candidates": [{"token": token, "probability": 1.0}],
                "explanation": "Top returned alternatives from the local model for this token position.",
            }
            for token in tokens
        ],
    }
