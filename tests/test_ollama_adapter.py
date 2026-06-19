from urllib.error import URLError
import json

from token_trail.adapters.base import AdapterError
from token_trail.adapters.ollama import OllamaAdapter


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_ollama_adapter_lists_models() -> None:
    def opener(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/tags"
        assert timeout == 1.0
        return FakeResponse(b'{"models": [{"name": "qwen3:4b"}, {"name": "qwen3:1.7b"}]}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.list_models() == ("qwen3:4b", "qwen3:1.7b")
    assert adapter.is_available()


def test_ollama_adapter_returns_empty_models_on_connection_failure() -> None:
    def opener(request, timeout):
        raise URLError("connection refused")

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.list_models() == ()
    assert not adapter.is_available()
    assert "unreachable" in (adapter.status().error or "")


def test_ollama_adapter_returns_empty_models_on_timeout() -> None:
    def opener(request, timeout):
        raise TimeoutError

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.list_models() == ()
    assert not adapter.is_available()
    assert "timed out" in (adapter.status().error or "")


def test_ollama_adapter_ignores_malformed_model_entries() -> None:
    def opener(request, timeout):
        return FakeResponse(
            b'{"models": [{"name": "qwen3:4b"}, {"name": ""}, {"model": "missing-name"}, null, {"name": "qwen3:4b"}]}'
        )

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.list_models() == ("qwen3:4b",)


def test_ollama_adapter_detects_exact_model_availability() -> None:
    def opener(request, timeout):
        return FakeResponse(b'{"models": [{"name": "qwen3:4b"}]}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.has_model("qwen3:4b")
    assert not adapter.has_model("qwen3")


def test_ollama_generate_posts_expected_payload() -> None:
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        seen["content_type"] = request.headers["Content-type"]
        return FakeResponse(b'{"response": "A live response."}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.generate("qwen3:4b", "Write a short story.", timeout_seconds=3.0, max_tokens=12) == "A live response."
    assert seen == {
        "url": "http://127.0.0.1:11434/api/generate",
        "timeout": 3.0,
        "payload": {
            "model": "qwen3:4b",
            "prompt": "/no_think\n\nWrite a short, direct answer.\nDo not show reasoning.\n\nPrompt:\nWrite a short story.",
            "stream": False,
            "think": False,
            "options": {
                "num_predict": 12,
                "temperature": 0.4,
            },
        },
        "content_type": "application/json",
    }


def test_ollama_generate_supports_custom_temperature_and_no_thinking_toggle() -> None:
    seen = {}

    def opener(request, timeout):
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(b'{"response": "A live response."}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    adapter.generate(
        "qwen3:4b",
        "Prompt",
        temperature=0.2,
        max_tokens=44,
        disable_thinking=False,
    )

    assert seen["payload"]["prompt"] == "Write a short, direct answer.\nDo not show reasoning.\n\nPrompt:\nPrompt"
    assert "think" not in seen["payload"]
    assert seen["payload"]["options"] == {"num_predict": 44, "temperature": 0.2}


def test_ollama_generate_returns_response_text() -> None:
    def opener(request, timeout):
        return FakeResponse(b'{"response": "  A small robot waved.  "}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.generate("qwen3:4b", "Prompt") == "A small robot waved."


def test_ollama_generate_strips_closed_thinking_preamble() -> None:
    def opener(request, timeout):
        return FakeResponse(
            b'{"response": "Hmm, the user wants a story. I need to plan it. </think>\\n\\nA robot joined class."}'
        )

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.generate("qwen3:4b", "Prompt") == "A robot joined class."


def test_ollama_generate_retries_reasoning_only_response_with_larger_budget() -> None:
    calls = []

    def opener(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        calls.append(payload["options"]["num_predict"])
        if len(calls) == 1:
            return FakeResponse(b'{"response": "Hmm, the user wants a short story. I need to keep it concise."}')
        return FakeResponse(b'{"response": "Thinking through the request. </think>\\n\\nA robot helped students debug code."}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert (
        adapter.generate("qwen3:4b", "Prompt", max_tokens=96, reasoning_retry_tokens=512)
        == "A robot helped students debug code."
    )
    assert calls == [96, 512]


def test_ollama_generate_does_not_retry_unprofiled_model() -> None:
    calls = []

    def opener(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        calls.append(payload["options"]["num_predict"])
        return FakeResponse(b'{"response": "Hmm, the user wants a short story. I need to keep it concise."}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    try:
        adapter.generate("qwen3:1.7b", "Prompt", max_tokens=96, reasoning_retry_tokens=None)
    except AdapterError as error:
        assert "empty response" in str(error)
    else:
        raise AssertionError("Expected AdapterError")

    assert calls == [96]


def test_ollama_generate_keeps_public_response_short() -> None:
    def opener(request, timeout):
        return FakeResponse(
            b'{"response": "One. Two. Three. Four. Five. Six."}'
        )

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    assert adapter.generate("qwen3:4b", "Prompt") == "One. Two. Three."


def test_ollama_generate_handles_timeout() -> None:
    def opener(request, timeout):
        raise TimeoutError

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    try:
        adapter.generate("qwen3:4b", "Prompt")
    except AdapterError as error:
        assert "timed out" in str(error)
    else:
        raise AssertionError("Expected AdapterError")


def test_ollama_generate_handles_connection_error() -> None:
    def opener(request, timeout):
        raise URLError("connection refused")

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    try:
        adapter.generate("qwen3:4b", "Prompt")
    except AdapterError as error:
        assert "failed" in str(error)
    else:
        raise AssertionError("Expected AdapterError")


def test_ollama_generate_handles_bad_json() -> None:
    def opener(request, timeout):
        return FakeResponse(b"not-json")

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    try:
        adapter.generate("qwen3:4b", "Prompt")
    except AdapterError as error:
        assert "invalid JSON" in str(error)
    else:
        raise AssertionError("Expected AdapterError")


def test_ollama_generate_handles_empty_response() -> None:
    def opener(request, timeout):
        return FakeResponse(b'{"response": "   "}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    try:
        adapter.generate("qwen3:4b", "Prompt")
    except AdapterError as error:
        assert "empty response" in str(error)
    else:
        raise AssertionError("Expected AdapterError")


def test_ollama_warmup_posts_expected_payload() -> None:
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        seen["content_type"] = request.headers["Content-type"]
        return FakeResponse(b'{"response": "ready"}')

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    adapter.warmup("qwen3:4b")

    assert seen == {
        "url": "http://127.0.0.1:11434/api/generate",
        "timeout": 45.0,
        "payload": {
            "model": "qwen3:4b",
            "prompt": "/no_think\n\nReply with: ready",
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "num_predict": 2,
                "temperature": 0,
            },
        },
        "content_type": "application/json",
    }


def test_ollama_warmup_handles_timeout() -> None:
    def opener(request, timeout):
        raise TimeoutError

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    try:
        adapter.warmup("qwen3:4b")
    except AdapterError as error:
        assert "timed out" in str(error)
    else:
        raise AssertionError("Expected AdapterError")


def test_ollama_warmup_handles_invalid_json() -> None:
    def opener(request, timeout):
        return FakeResponse(b"not-json")

    adapter = OllamaAdapter("http://127.0.0.1:11434", opener=opener)

    try:
        adapter.warmup("qwen3:4b")
    except AdapterError as error:
        assert "invalid JSON" in str(error)
    else:
        raise AssertionError("Expected AdapterError")
