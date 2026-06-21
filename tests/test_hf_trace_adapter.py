import io
import json
from urllib.error import HTTPError, URLError

from token_trail.adapters.base import AdapterError
from token_trail.adapters.hf_trace import HfTraceAdapter, _warmup_url_for_trace_url


def http_error(status: int, payload: dict) -> HTTPError:
    return HTTPError(
        url="http://127.0.0.1:8600/api/trace",
        code=status,
        msg="error",
        hdrs={},
        fp=io.BytesIO(json.dumps(payload).encode("utf-8")),
    )


class FakeResponse:
    def __init__(self, status: int = 200, body: dict | None = None) -> None:
        self.status = status
        self._body = json.dumps(body or {}).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_status_uses_health_endpoint_without_generating_trace() -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        return FakeResponse(status=200, body={"status": "ok", "model_loaded": True})

    status = HfTraceAdapter("http://127.0.0.1:8600/api/trace", opener=opener).status(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        max_new_tokens=1,
        top_k=1,
        temperature=0,
        timeout_seconds=2,
    )

    assert status.available
    assert status.model_loaded
    assert calls == [("http://127.0.0.1:8600/health?model=Qwen%2FQwen2.5-0.5B-Instruct", "GET", 2.0)]


def test_status_reports_unavailable_when_health_endpoint_fails() -> None:
    def opener(request, timeout):
        raise URLError("connection refused")

    status = HfTraceAdapter("http://127.0.0.1:8600/api/trace", opener=opener).status()

    assert not status.available
    assert "connection refused" in status.error


def test_warmup_posts_model_to_warmup_endpoint() -> None:
    calls = []

    def opener(request, timeout):
        calls.append(
            (
                request.full_url,
                request.get_method(),
                json.loads(request.data.decode("utf-8")),
                timeout,
            )
        )
        return FakeResponse(status=200, body={"status": "ready", "model": "Qwen/Qwen2.5-0.5B-Instruct"})

    payload = HfTraceAdapter("http://127.0.0.1:8600/api/trace", opener=opener).warmup(
        "Qwen/Qwen2.5-0.5B-Instruct",
        timeout_seconds=12,
    )

    assert payload == {"status": "ready", "model": "Qwen/Qwen2.5-0.5B-Instruct"}
    assert calls == [
        (
            "http://127.0.0.1:8600/api/warmup",
            "POST",
            {"model": "Qwen/Qwen2.5-0.5B-Instruct"},
            12.0,
        )
    ]


def test_warmup_reports_http_error() -> None:
    def opener(request, timeout):
        raise http_error(400, {"error": "Request body is missing required string: model"})

    adapter = HfTraceAdapter("http://127.0.0.1:8600/api/trace", opener=opener)

    try:
        adapter.warmup("", timeout_seconds=2)
    except AdapterError as error:
        assert "model" in str(error)
    else:
        raise AssertionError("expected AdapterError")


def test_warmup_url_uses_trace_server_origin() -> None:
    assert _warmup_url_for_trace_url("http://127.0.0.1:8600/api/trace") == "http://127.0.0.1:8600/api/warmup"


def test_generate_trace_still_reports_incomplete_generation_as_error() -> None:
    def opener(request, timeout):
        raise http_error(400, {"error": "Generated trace did not reach a complete sentence"})

    adapter = HfTraceAdapter("http://127.0.0.1:8600/api/trace", opener=opener)

    try:
        adapter.generate_trace(
            prompt="Write one sentence.",
            model="Qwen/Qwen2.5-0.5B-Instruct",
            max_new_tokens=1,
            top_k=1,
            temperature=0,
            timeout_seconds=2,
        )
    except AdapterError as error:
        assert "complete sentence" in str(error)
    else:
        raise AssertionError("expected AdapterError")
