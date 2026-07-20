import io
import json
from urllib.error import HTTPError, URLError

from token_trail.adapters.base import AdapterError
from token_trail.adapters.modeldeck import ModelDeckAdapter, ModelDeckError, validate_trace_payload


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


def model_list(*, ready: bool = True, include_requested: bool = True) -> dict:
    data = [
        {"id": "qwen-0-5b", "object": "model", "owned_by": "modeldeck-local", "ready": True},
        {"id": "qwen-1-5b", "object": "model", "owned_by": "modeldeck-local", "ready": False},
        {"id": "qwen-3b", "object": "model", "owned_by": "modeldeck-local", "ready": True},
    ]
    if include_requested:
        data.append(
            {
                "id": "token-explainer",
                "object": "model",
                "owned_by": "modeldeck-local",
                "ready": ready,
            }
        )
    return {
        "object": "list",
        "data": data,
    }


def native_trace(*, complete: bool = True, include_user_prompt_tokens: bool = True) -> dict:
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
                "generated_token_ids": list(range(index + 1)),
                "timestamp": 1_700_000_000 + index,
                "elapsed_seconds": 0.1 * (index + 1),
                "complete": index == 7 and complete,
            }
        )
    payload = {
        "request_id": "request-1",
        "model": "token-explainer",
        "prompt_token_ids": [10, 20],
        "prompt_tokens": ["system", "\n"],
        "events": events,
        "metrics": {"first_token_seconds": 0.1, "total_seconds": 0.8, "generated_tokens": 8},
    }
    if include_user_prompt_tokens:
        payload["user_prompt_token_ids"] = [30, 31, 32, 33, 34]
        payload["user_prompt_tokens"] = ["Explain", " ", "token", " prediction", "."]
    return payload


def test_models_uses_modeldeck_gateway_contract() -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        return FakeResponse(model_list())

    payload = ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).models(timeout_seconds=3)

    assert [entry["id"] for entry in payload["data"][:3]] == [
        "qwen-0-5b",
        "qwen-1-5b",
        "qwen-3b",
    ]
    assert calls == [("http://127.0.0.1:8600/v1/models", "GET", 3.0)]


def test_status_reports_alias_readiness_without_warming_worker() -> None:
    def opener(request, timeout):
        return FakeResponse(model_list())

    adapter = ModelDeckAdapter("http://127.0.0.1:8600", opener=opener)

    status = adapter.status(model="token-explainer")

    assert status.available is True
    assert status.state == "ready"
    assert status.error == "ModelDeck trace route is ready."


def test_status_distinguishes_route_not_advertised_from_provider_not_ready() -> None:
    adapter = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: FakeResponse(model_list(ready=False)),
    )
    status = adapter.status(
        model="token-explainer"
    )

    assert status.available is False
    assert status.state == "provider_not_ready"
    assert "ModelDeck Workers view" in str(status.error)

    missing = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: FakeResponse(model_list(include_requested=False)),
    ).status(model="token-explainer")
    assert missing.state == "route_not_advertised"


def test_generate_trace_sends_messages_and_converts_native_events() -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, json.loads(request.data), timeout))
        return FakeResponse(native_trace())

    trace = ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).generate_trace(
        prompt="Explain token prediction.",
        instructions="Use one sentence.",
        model="token-explainer",
        max_new_tokens=96,
        top_k=5,
        temperature=0.3,
        timeout_seconds=20,
        request_id="trace-123",
    )

    url, body, timeout = calls[0]
    assert url == "http://127.0.0.1:8600/native/autoregressive/trace"
    assert body["request_id"] == "trace-123"
    assert body["model"] == "token-explainer"
    assert body["messages"] == [
        {"role": "system", "content": "Use one sentence."},
        {"role": "user", "content": "Explain token prediction."},
    ]
    assert body["min_tokens"] == 8
    assert timeout == 20.0
    assert trace["mode"] == "modeldeck-live-trace"
    assert trace["prompt"] == "Explain token prediction."
    assert trace["prompt_tokens"] == ["system", "\n"]
    assert trace["prompt_token_ids"] == [10, 20]
    assert trace["user_prompt_tokens"] == ["Explain", " ", "token", " prediction", "."]
    assert trace["user_prompt_token_ids"] == [30, 31, 32, 33, 34]
    assert trace["steps"][-1]["selected_token"] == " words."
    assert trace["steps"][0]["candidates"] == [
        {"token_id": 0, "token": "Token", "probability": 0.7},
        {"token_id": 100, "token": " other", "probability": 0.2},
    ]
    assert trace["steps"][0]["elapsed_seconds"] == 0.1
    assert trace["metrics"]["total_seconds"] == 0.8


def test_generate_trace_bounds_modeldeck_generation_controls() -> None:
    calls = []

    def opener(request, timeout):
        calls.append(json.loads(request.data))
        return FakeResponse(native_trace())

    ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).generate_trace(
        prompt="Explain token prediction.",
        instructions=None,
        model="token-explainer",
        max_new_tokens=10_000,
        top_k=1_000,
        temperature=99,
        timeout_seconds=20,
        request_id="trace-bounded",
    )

    assert calls[0]["max_tokens"] == 128
    assert calls[0]["top_k"] == 20
    assert calls[0]["temperature"] == 2.0


def test_generate_trace_rejects_missing_user_prompt_metadata() -> None:
    adapter = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: FakeResponse(native_trace(include_user_prompt_tokens=False)),
    )

    try:
        adapter.generate_trace(
            prompt="Explain token prediction.",
            instructions="Use one sentence.",
            model="token-explainer",
            max_new_tokens=96,
            top_k=5,
            temperature=0.3,
            timeout_seconds=20,
            request_id="trace-123",
        )
    except ModelDeckError as error:
        assert error.code == "invalid_worker_trace_metadata"
    else:
        raise AssertionError("expected ModelDeckError")


def test_generate_trace_rejects_incomplete_sentence() -> None:
    adapter = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: FakeResponse(native_trace(complete=False)),
    )

    try:
        adapter.generate_trace(
            prompt="Explain token prediction.",
            instructions=None,
            model="token-explainer",
            max_new_tokens=96,
            top_k=5,
            temperature=0.3,
            timeout_seconds=20,
            request_id="trace-123",
        )
    except AdapterError as error:
        assert "complete sentence" in str(error)
    else:
        raise AssertionError("expected AdapterError")


def test_generate_trace_rejects_generated_model_control_tokens() -> None:
    for control_token in ("<|im_end|>", "<|endoftext|>", "<eos>"):
        payload = native_trace()
        payload["events"][4]["selected"]["token"] = control_token
        payload["events"][4]["text_so_far"] += control_token
        adapter = ModelDeckAdapter(
            "http://127.0.0.1:8600",
            opener=lambda request, timeout, payload=payload: FakeResponse(payload),
        )

        try:
            adapter.generate_trace(
                prompt="Explain token prediction.",
                instructions="Use one sentence.",
                model="token-explainer",
                max_new_tokens=96,
                top_k=5,
                temperature=0.3,
                timeout_seconds=20,
                request_id="trace-control-token",
            )
        except ModelDeckError as error:
            assert error.code == "invalid_worker_trace_metadata"
        else:
            raise AssertionError("expected ModelDeckError")


def test_generate_trace_rejects_control_tokens_in_returned_alternatives() -> None:
    payload = native_trace()
    payload["events"][4]["alternatives"][1]["token"] = "<|im_end|>"
    adapter = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: FakeResponse(payload),
    )

    try:
        adapter.generate_trace(
            prompt="Explain token prediction.",
            instructions="Use one sentence.",
            model="token-explainer",
            max_new_tokens=96,
            top_k=5,
            temperature=0.3,
            timeout_seconds=20,
            request_id="trace-control-token-alternative",
        )
    except ModelDeckError as error:
        assert error.code == "invalid_worker_trace_metadata"
    else:
        raise AssertionError("expected ModelDeckError")


def test_trace_validation_rejects_control_tokens_from_custom_adapters() -> None:
    trace = {
        "mode": "modeldeck-live-trace",
        "prompt": "Explain token prediction.",
        "prompt_token_ids": [10],
        "prompt_tokens": ["hidden"],
        "user_prompt_token_ids": [20],
        "user_prompt_tokens": ["Explain token prediction."],
        "steps": [
            {
                "selected_token": "Safe.",
                "text_so_far": "Safe.<|endoftext|>",
                "candidates": [{"token": "Safe.", "probability": 1.0}],
                "explanation": "Returned by the model.",
            }
        ],
    }

    try:
        validate_trace_payload(trace)
    except AdapterError as error:
        assert "generated control token" in str(error)
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
                    {
                        "error": {
                            "code": "local_provider_unavailable",
                            "message": "No ready local provider supplies the requested alias.",
                            "cloud_fallback_attempted": False,
                        }
                    }
                ).encode("utf-8")
            ),
        )

    try:
        ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).models()
    except ModelDeckError as error:
        assert "No ready local provider" in str(error)
        assert error.code == "local_provider_unavailable"
    else:
        raise AssertionError("expected AdapterError")


def test_status_reports_unreachable_gateway() -> None:
    adapter = ModelDeckAdapter(
        "http://127.0.0.1:8600",
        opener=lambda request, timeout: (_ for _ in ()).throw(URLError("connection refused")),
    )

    status = adapter.status(model="token-explainer")

    assert status.available is False
    assert status.state == "gateway_unavailable"
    assert "connection refused" in str(status.error)


def test_cancel_uses_stable_gateway_request_route() -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        return FakeResponse({"ok": True, "request_id": "trace-123"})

    result = ModelDeckAdapter("http://127.0.0.1:8600", opener=opener).cancel(
        "trace-123", timeout_seconds=4
    )

    assert result["ok"] is True
    assert calls == [
        ("http://127.0.0.1:8600/v1/requests/trace-123/cancel", "POST", 4.0)
    ]
