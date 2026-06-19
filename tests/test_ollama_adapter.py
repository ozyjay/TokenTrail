from urllib.error import URLError

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
