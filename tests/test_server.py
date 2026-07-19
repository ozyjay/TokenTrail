import json
import threading
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from token_trail.adapters.modeldeck import ModelDeckError
from token_trail.config import RuntimeConfig
from token_trail.server import TokenTrailServer, build_server_state


def make_config(backend: str = "modeldeck", *, enabled: bool = True) -> RuntimeConfig:
    return RuntimeConfig(
        backend=backend,
        host="127.0.0.1",
        port=3100,
        backend_port=8100,
        modeldeck_enabled=enabled,
        modeldeck_url="http://127.0.0.1:8600",
        modeldeck_model="qwen-1-5b",
        modeldeck_models=("qwen-0-5b", "qwen-1-5b", "qwen-3b"),
        modeldeck_top_k=5,
        modeldeck_max_new_tokens=64,
        modeldeck_temperature=0.3,
        modeldeck_timeout_seconds=7.5,
        modeldeck_instructions="Use one short sentence.",
    )


class FakeModelDeckAdapter:
    def __init__(
        self,
        *,
        gateway_order: tuple[str, ...] = ("qwen-3b", "qwen-0-5b", "qwen-1-5b"),
        ready: set[str] | None = None,
        error_code: str | None = None,
    ) -> None:
        self.gateway_order = gateway_order
        self.ready = ready if ready is not None else set(gateway_order)
        self.error_code = error_code
        self.generate_calls = []
        self.cancel_calls = []

    def models(self, *, timeout_seconds: float) -> dict:
        return {
            "object": "list",
            "data": [
                {"id": model, "object": "model", "owned_by": "modeldeck-local", "ready": model in self.ready}
                for model in self.gateway_order
            ],
        }

    def generate_trace(self, **kwargs) -> dict:
        self.generate_calls.append(kwargs)
        if self.error_code:
            raise ModelDeckError(
                "ModelDeck request failed",
                code=self.error_code,
                http_status=503 if self.error_code == "local_provider_unavailable" else 502,
            )
        return {
            "mode": "modeldeck-live-trace",
            "model": kwargs["model"],
            "prompt": kwargs["prompt"],
            "prompt_token_ids": [10, 20],
            "prompt_tokens": ["hidden", " context"],
            "user_prompt_token_ids": [20],
            "user_prompt_tokens": [kwargs["prompt"]],
            "metrics": {"generated_tokens": 1, "total_seconds": 0.2},
            "steps": [
                {
                    "step": 0,
                    "selected_token_id": 30,
                    "selected_token": "Tokens.",
                    "candidates": [{"token_id": 30, "token": "Tokens.", "probability": 0.8}],
                    "elapsed_seconds": 0.2,
                    "explanation": "This was selected from returned probabilities.",
                }
            ],
        }

    def cancel(self, request_id: str, *, timeout_seconds: float) -> dict:
        self.cancel_calls.append((request_id, timeout_seconds))
        return {"ok": True, "request_id": request_id}


@contextmanager
def running_server(config: RuntimeConfig, adapter: FakeModelDeckAdapter):
    state = build_server_state(config, modeldeck_adapter=adapter)
    httpd = TokenTrailServer(("127.0.0.1", 0), state)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_runtime_endpoint_lists_all_aliases_in_gateway_order() -> None:
    with running_server(make_config(), FakeModelDeckAdapter()) as base_url:
        payload = _get_json(f"{base_url}/api/runtime")

    assert payload["selected_id"] == "modeldeck:qwen-1-5b"
    assert [option["model"] for option in payload["options"][1:]] == [
        "qwen-3b",
        "qwen-0-5b",
        "qwen-1-5b",
    ]
    assert all(option["status"] == "ready" for option in payload["options"][1:])


def test_provider_not_ready_is_visible_without_lifecycle_actions() -> None:
    with running_server(make_config(), FakeModelDeckAdapter(ready={"qwen-0-5b", "qwen-3b"})) as base_url:
        payload = _get_json(f"{base_url}/api/runtime")

    route = next(option for option in payload["options"] if option["model"] == "qwen-1-5b")
    assert route["status"] == "provider_not_ready"
    assert "ModelDeck Workers view" in route["notes"]


def test_provider_not_ready_returns_live_error_without_prepared_trace() -> None:
    adapter = FakeModelDeckAdapter(ready={"qwen-0-5b", "qwen-3b"})
    with running_server(make_config(), adapter) as base_url:
        payload, status = _post_json_with_status(
            f"{base_url}/api/generate-trace",
            {
                "runtime_id": "modeldeck:qwen-1-5b",
                "trace_id": "robot-university",
                "request_id": "browser-not-ready",
            },
        )

    assert status == 503
    assert payload["state"] == "provider_not_ready"
    assert payload["fallback_used"] is False
    assert "trace" not in payload
    assert adapter.generate_calls == []


@pytest.mark.parametrize("model", ["qwen-0-5b", "qwen-1-5b", "qwen-3b"])
def test_generate_trace_calls_each_selected_public_alias(model: str) -> None:
    adapter = FakeModelDeckAdapter()
    with running_server(make_config(), adapter) as base_url:
        payload = _post_json(
            f"{base_url}/api/generate-trace",
            {
                "runtime_id": f"modeldeck:{model}",
                "trace_id": "robot-university",
                "prompt": "  Explain token prediction simply.  ",
                "request_id": "browser-request-1",
            },
        )

    assert payload["mode"] == "modeldeck-live-trace"
    assert payload["runtime_id"] == f"modeldeck:{model}"
    assert payload["fallback_used"] is False
    assert adapter.generate_calls == [
        {
            "prompt": "Explain token prediction simply.",
            "instructions": "Use one short sentence.",
            "model": model,
            "max_new_tokens": 64,
            "top_k": 5,
            "temperature": 0.3,
            "timeout_seconds": 7.5,
            "request_id": "browser-request-1",
        }
    ]


def test_structured_unavailable_error_returns_live_503_without_fallback() -> None:
    adapter = FakeModelDeckAdapter(error_code="local_provider_unavailable")
    with running_server(make_config(), adapter) as base_url:
        payload, status = _post_json_with_status(
            f"{base_url}/api/generate-trace",
            {
                "runtime_id": "modeldeck:qwen-1-5b",
                "trace_id": "robot-university",
                "request_id": "browser-request-2",
            },
        )

    assert status == 503
    assert payload["mode"] == "modeldeck-unavailable"
    assert payload["fallback_used"] is False
    assert "trace" not in payload
    assert payload["state"] == "provider_not_ready"
    assert payload["code"] == "local_provider_unavailable"
    assert "ModelDeck Workers view" in payload["message"]


def test_invalid_worker_metadata_has_distinct_fallback_state() -> None:
    adapter = FakeModelDeckAdapter(error_code="invalid_worker_trace_metadata")
    with running_server(make_config(), adapter) as base_url:
        payload, status = _post_json_with_status(
            f"{base_url}/api/generate-trace",
            {
                "runtime_id": "modeldeck:qwen-1-5b",
                "trace_id": "robot-university",
                "request_id": "browser-request-3",
            },
        )

    assert status == 502
    assert payload["state"] == "invalid_worker_trace_metadata"
    assert "invalid trace metadata" in payload["message"]


def test_cancellation_is_forwarded_through_modeldeck_gateway_contract() -> None:
    adapter = FakeModelDeckAdapter()
    with running_server(make_config(), adapter) as base_url:
        payload = _post_json(
            f"{base_url}/api/generate-trace/cancel",
            {"request_id": "browser-request-4"},
        )

    assert payload["state"] == "request_cancelled"
    assert adapter.cancel_calls == [("browser-request-4", 2.0)]


def test_scripted_runtime_ignores_custom_prompt() -> None:
    with running_server(make_config(backend="scripted", enabled=False), FakeModelDeckAdapter()) as base_url:
        payload = _post_json(
            f"{base_url}/api/generate-trace",
            {
                "runtime_id": "scripted:prepared-traces",
                "trace_id": "robot-university",
                "prompt": "Ignore this prompt.",
            },
        )

    assert payload["mode"] == "scripted"
    assert payload["trace"]["prompt"] == "Write a short story about a robot at university."


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json_with_status(url: str, payload: dict) -> tuple[dict, int]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except HTTPError as error:
        return json.loads(error.read().decode("utf-8")), error.code
