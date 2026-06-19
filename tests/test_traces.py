from token_trail.traces import TRACE_LIBRARY, get_trace, join_tokens, simple_tokenise


def test_trace_library_has_open_day_prompt() -> None:
    trace = get_trace("robot-university")

    assert trace.title == "Robot at university"
    assert trace.prompt.startswith("Write a short story")
    assert len(trace.steps) >= 3


def test_trace_probabilities_are_display_ready() -> None:
    for trace in TRACE_LIBRARY:
        for step in trace.steps:
            assert step.selected_token in {candidate.token for candidate in step.candidates}
            for candidate in step.candidates:
                assert 0 <= candidate.probability <= 1


def test_simple_tokeniser_splits_basic_punctuation() -> None:
    assert simple_tokenise("Hello, robot.") == ("Hello", ",", "robot", ".")


def test_join_tokens_removes_spaces_before_punctuation() -> None:
    assert join_tokens(["Hello", ",", "robot", "."]) == "Hello, robot."
