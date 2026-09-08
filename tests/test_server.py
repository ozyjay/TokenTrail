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
        generated_token: str = "Tokens.",
    ) -> None:
        self.gateway_order = gateway_order
        self.ready = ready if ready is not None else set(gateway_order)
        self.error_code = error_code
        self.generated_token = generated_token
        self.generate_calls = []
        self.cancel_calls = []

    def capabilities(self, *, timeout_seconds: float) -> dict:
        return {
            "resolution": {},
            "capabilities": [
                {"id": f"uuid-{model}", "display_name": model, "public_name": model,
                 "protocol_contract": "native-ar-trace-v1",
                 "surfaces": ["POST /native/v1/autoregressive/traces"],
                 "metadata": {}, "ready": model in self.ready}
                for model in self.gateway_order
            ],
        }

    def generate_trace(self, **kwargs) -> dict:
        self.generate_calls.append(kwargs)
        if self.error_code:
            raise ModelDeckError(
                "ModelDeck request failed",
                code=self.error_code,
                http_status=503 if self.error_code in {"local_provider_unavailable", "local_route_unavailable"} else 502,
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
                    "selected_token": self.generated_token,
                    "candidates": [
                        {"token_id": 30, "token": self.generated_token, "probability": 0.8}
                    ],
                    "elapsed_seconds": 0.2,
                    "explanation": "This was selected from returned probabilities.",
                }
            ],
        }

    def cancel(self, request_id: str, *, timeout_seconds: float) -> dict:
        self.cancel_calls.append((request_id, timeout_seconds))
        return {"ok": True, "request_id": request_id, "state": "cancelled", "worker_id": "worker-uuid"}


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


def test_runtime_endpoint_lists_all_aliases_in_configuration_order() -> None:
    with running_server(make_config(), FakeModelDeckAdapter()) as base_url:
        payload = _get_json(f"{base_url}/api/runtime")

    assert payload["selected_id"] == "modeldeck:qwen-1-5b"
    assert [option["model"] for option in payload["options"][1:]] == [
        "qwen-0-5b",
        "qwen-1-5b",
        "qwen-3b",
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


def test_generated_control_token_is_rejected_at_server_boundary() -> None:
    adapter = FakeModelDeckAdapter(generated_token="<|im_end|>")
    with running_server(make_config(), adapter) as base_url:
        payload, status = _post_json_with_status(
            f"{base_url}/api/generate-trace",
            {
                "runtime_id": "modeldeck:qwen-1-5b",
                "trace_id": "robot-university",
                "request_id": "browser-control-token",
            },
        )

    assert status == 502
    assert payload["mode"] == "modeldeck-unavailable"
    assert payload["state"] == "invalid_worker_trace_metadata"
    assert payload["fallback_used"] is False
    assert "trace" not in payload


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


def test_discovery_filters_extra_aliases_and_retains_missing_configured_alias():
    adapter = FakeModelDeckAdapter(gateway_order=("unconfigured", "qwen-3b", "qwen-0-5b"))
    state = build_server_state(make_config(), modeldeck_adapter=adapter)
    assert [option.model for option in state.runtime_options[1:]] == ["qwen-0-5b", "qwen-1-5b", "qwen-3b"]
    assert state.runtime_options[2].status == "route_not_advertised"
    assert state.runtime_state.selected_id == "modeldeck:qwen-1-5b"


def test_gateway_failure_keeps_explicit_selection_and_prepared_option():
    class UnavailableAdapter(FakeModelDeckAdapter):
        def capabilities(self, **kwargs):
            raise ModelDeckError("connection refused", code="gateway_unavailable")
    state = build_server_state(make_config(), modeldeck_adapter=UnavailableAdapter())
    assert state.runtime_options[0].available
    assert all(option.status == "gateway_unavailable" for option in state.runtime_options[1:])


@pytest.mark.parametrize("gateway_state", ["not-found", "worker-unavailable"])
def test_cancellation_preserves_unsuccessful_gateway_acknowledgement(gateway_state):
    class CancelAdapter(FakeModelDeckAdapter):
        def cancel(self, request_id, **kwargs):
            return {"ok": False, "request_id": request_id, "state": gateway_state, "worker_id": "worker-uuid"}
    with running_server(make_config(), CancelAdapter()) as base_url:
        payload = _post_json(f"{base_url}/api/generate-trace/cancel", {"request_id": "cancel-1"})
    assert payload["cancelled"] is False
    assert payload["gateway_state"] == gateway_state
    assert payload["worker_id"] == "worker-uuid"


def test_current_local_route_error_does_not_claim_worker_is_stopped():
    with running_server(make_config(), FakeModelDeckAdapter(error_code="local_route_unavailable")) as base_url:
        payload, status = _post_json_with_status(f"{base_url}/api/generate-trace", {
            "runtime_id": "modeldeck:qwen-1-5b", "trace_id": "robot-university", "request_id": "route-1"})
    assert status == 503
    assert payload["state"] == "route_unavailable"
    assert payload["fallback_used"] is False
    assert "trace" not in payload


def test_incompatible_capability_cannot_generate():
    class IncompatibleAdapter(FakeModelDeckAdapter):
        def capabilities(self, **kwargs):
            payload = super().capabilities(**kwargs)
            for entry in payload["capabilities"]:
                entry.pop("protocol_contract")
            return payload
    adapter = IncompatibleAdapter()
    with running_server(make_config(), adapter) as base_url:
        payload, status = _post_json_with_status(f"{base_url}/api/generate-trace", {
            "runtime_id": "modeldeck:qwen-1-5b", "trace_id": "robot-university", "request_id": "incompatible-1"})
    assert status == 503
    assert payload["state"] == "incompatible_contract"
    assert "trace" not in payload
    assert adapter.generate_calls == []
