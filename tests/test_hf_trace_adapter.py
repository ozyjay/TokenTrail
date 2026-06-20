import io
import json
from urllib.error import HTTPError

from token_trail.adapters.base import AdapterError
from token_trail.adapters.hf_trace import HfTraceAdapter


def http_error(status: int, payload: dict) -> HTTPError:
    return HTTPError(
        url="http://127.0.0.1:8600/api/trace",
        code=status,
        msg="error",
        hdrs={},
        fp=io.BytesIO(json.dumps(payload).encode("utf-8")),
    )


def test_status_treats_incomplete_readiness_trace_as_available() -> None:
    def opener(request, timeout):
        raise http_error(400, {"error": "Generated trace did not reach a complete sentence"})

    status = HfTraceAdapter("http://127.0.0.1:8600/api/trace", opener=opener).status(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        max_new_tokens=1,
        top_k=1,
        temperature=0,
        timeout_seconds=2,
    )

    assert status.available


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
