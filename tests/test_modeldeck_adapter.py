import io
import json
from urllib.error import HTTPError, URLError

from token_trail.adapters.base import AdapterError
from token_trail.adapters.modeldeck import ModelDeckAdapter


class FakeResponse:
    def __init__(self, body: dict) -> None:
        self.status = 200
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def model_list(*, ready: bool = True) -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen-1-5b",
                "object": "model",
                "owned_by": "modeldeck-local",
                "ready": ready,
                "effective_provider": "qwen-1-5b-rocm" if ready else None,
            }
        ],
    }


def native_trace(*, complete: bool = True) -> dict:
    events = []
    text = ""
    for index, token in enumerate(("Token", " Trail", " shows", " how", " local", " models", " choose", " words.")):
        text += token
        events.append(
            {
                "step": index,
                "selected": {"token_id": index, "token": token, "probability": 0.7},
                "alternatives": [
                    {"token_id": index, "token": token, "probability": 0.7},
                    {"token_id": index + 100, "token": " other", "probability": 0.2},
                ],
                "text_so_far": text.rstrip(".") if index == 7 and not complete else text,
            }
        )
    return {"request_id": "request-1", "model": "qwen-1-5b", "prompt_token_ids": [10, 20], "events": events}


def test_models_uses_modeldeck_gateway_contract() -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        return FakeResponse(model_list())

    payload = ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).models(timeout_seconds=3)

    assert payload["data"][0]["id"] == "qwen-1-5b"
    assert calls == [("http://127.0.0.1:8600/v1/models", "GET", 3.0)]


def test_status_reports_alias_readiness_without_warming_worker() -> None:
    adapter = ModelDeckAdapter("http://127.0.0.1:8600", opener=lambda request, timeout: FakeResponse(model_list()))

    status = adapter.status(model="qwen-1-5b")

    assert status.available is True
    assert status.model_loaded is True
    assert status.error == "Ready through qwen-1-5b-rocm"


def test_generate_trace_sends_messages_and_converts_native_events() -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, json.loads(request.data), timeout))
        return FakeResponse(native_trace())

    trace = ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).generate_trace(
        prompt="Explain token prediction.",
        instructions="Use one sentence.",
        model="qwen-1-5b",
        max_new_tokens=96,
        top_k=5,
        temperature=0.3,
        timeout_seconds=20,
    )

    url, body, timeout = calls[0]
    assert url == "http://127.0.0.1:8600/native/autoregressive/trace"
    assert body["model"] == "qwen-1-5b"
    assert body["messages"] == [
        {"role": "system", "content": "Use one sentence."},
        {"role": "user", "content": "Explain token prediction."},
    ]
    assert body["min_tokens"] == 8
    assert timeout == 20.0
    assert trace["mode"] == "modeldeck-live-trace"
    assert trace["prompt"] == "Explain token prediction."
    assert trace["prompt_tokens"] == ["<10>", "<20>"]
    assert trace["steps"][-1]["selected_token"] == " words."
    assert trace["steps"][0]["candidates"] == [
        {"token": "Token", "probability": 0.7},
        {"token": " other", "probability": 0.2},
    ]


def test_generate_trace_rejects_incomplete_sentence() -> None:
    adapter = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: FakeResponse(native_trace(complete=False)),
    )

    try:
        adapter.generate_trace(
            prompt="Explain token prediction.",
            instructions=None,
            model="qwen-1-5b",
            max_new_tokens=96,
            top_k=5,
            temperature=0.3,
            timeout_seconds=20,
        )
    except AdapterError as error:
        assert "complete sentence" in str(error)
    else:
        raise AssertionError("expected AdapterError")


def test_modeldeck_errors_remain_local_and_actionable() -> None:
    def opener(request, timeout):
        raise HTTPError(
            request.full_url,
            503,
            "unavailable",
            {},
            io.BytesIO(
                json.dumps(
                    {"error": {"message": "No ready local provider supplies alias 'qwen-1-5b'."}}
                ).encode("utf-8")
            ),
        )

    try:
        ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).models()
    except AdapterError as error:
        assert "No ready local provider" in str(error)
    else:
        raise AssertionError("expected AdapterError")


def test_status_reports_unreachable_gateway() -> None:
    adapter = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: (_ for _ in ()).throw(URLError("connection refused")),
    )

    status = adapter.status(model="qwen-1-5b")

    assert status.available is False
    assert "connection refused" in str(status.error)
