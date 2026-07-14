import json
import threading
from contextlib import contextmanager
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError
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
        modeldeck_max_new_tokens=96,
        modeldeck_temperature=0.3,
        modeldeck_timeout_seconds=7.5,
        modeldeck_instructions="Use one short sentence.",
    )


class FakeModelDeckAdapter:
    def __init__(self, *, ready: set[str] | None = None, error: bool = False) -> None:
        self.ready = ready if ready is not None else {"qwen-0-5b", "qwen-1-5b", "qwen-3b"}
        self.error = error
        self.generate_calls = []

    def models(self, *, timeout_seconds: float) -> dict:
        return {
            "object": "list",
            "data": [
                {
                    "id": alias,
                    "ready": alias in self.ready,
                    "effective_provider": f"{alias}-rocm" if alias in self.ready else None,
                }
                for alias in ("qwen-0-5b", "qwen-1-5b", "qwen-3b")
            ],
        }

    def generate_trace(self, **kwargs) -> dict:
        self.generate_calls.append(kwargs)
        if self.error:
            raise AdapterError("ModelDeck request failed")
        return {
            "mode": "modeldeck-live-trace",
            "model": kwargs["model"],
            "prompt": kwargs["prompt"],
            "prompt_tokens": ["<10>", "<20>"],
            "steps": [
                {
                    "selected_token": "Tokens.",
                    "candidates": [{"token": "Tokens.", "probability": 0.8}],
                    "explanation": "This was selected from returned probabilities.",
                }
            ],
        }


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


def test_runtime_endpoint_lists_scripted_and_modeldeck_aliases() -> None:
    with running_server(make_config(), FakeModelDeckAdapter()) as base_url:
        payload = _get_json(f"{base_url}/api/runtime")

    assert payload["selected_id"] == "modeldeck:qwen-1-5b"
    assert [option["backend"] for option in payload["options"]] == [
        "scripted",
        "modeldeck",
        "modeldeck",
        "modeldeck",
    ]
    assert all(option["status"] == "ready" for option in payload["options"][1:])


def test_unready_modeldeck_alias_is_visible_without_start_or_warmup() -> None:
    with running_server(make_config(), FakeModelDeckAdapter(ready={"qwen-0-5b"})) as base_url:
        payload = _get_json(f"{base_url}/api/runtime")

    aliases = {option["model"]: option for option in payload["options"] if option["backend"] == "modeldeck"}
    assert aliases["qwen-0-5b"]["status"] == "ready"
    assert aliases["qwen-1-5b"]["status"] == "unavailable"
    assert "no ready worker" in aliases["qwen-1-5b"]["notes"]


def test_generate_trace_calls_selected_modeldeck_alias() -> None:
    adapter = FakeModelDeckAdapter()
    with running_server(make_config(), adapter) as base_url:
        payload = _post_json(
            f"{base_url}/api/generate-trace",
            {
                "runtime_id": "modeldeck:qwen-3b",
                "trace_id": "robot-university",
                "prompt": "  Explain token prediction simply.  ",
            },
        )

    assert payload["mode"] == "modeldeck-live-trace"
    assert payload["runtime_id"] == "modeldeck:qwen-3b"
    assert payload["fallback_used"] is False
    assert adapter.generate_calls == [
        {
            "prompt": "Explain token prediction simply.",
            "instructions": "Use one short sentence.",
            "model": "qwen-3b",
            "max_new_tokens": 96,
            "top_k": 5,
            "temperature": 0.3,
            "timeout_seconds": 7.5,
        }
    ]


def test_modeldeck_failure_uses_scripted_fallback() -> None:
    with running_server(make_config(), FakeModelDeckAdapter(error=True)) as base_url:
        payload = _post_json(
            f"{base_url}/api/generate-trace",
            {"runtime_id": "modeldeck:qwen-1-5b", "trace_id": "robot-university"},
        )

    assert payload["mode"] == "scripted-fallback"
    assert payload["fallback_used"] is True
    assert payload["trace"]["id"] == "robot-university"
    assert "ModelDeck request failed" in payload["message"]


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
