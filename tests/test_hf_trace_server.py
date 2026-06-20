import importlib.util
import json
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "serve_hf_trace.py"


def load_server_module():
    spec = importlib.util.spec_from_file_location("serve_hf_trace", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeTraceRunner:
    def __init__(self) -> None:
        self.calls = []

    def generate_trace(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "mode": "hf-live-trace",
            "model": kwargs["model"],
            "prompt": kwargs["prompt"],
            "prompt_tokens": ["Write"],
            "steps": [
                {
                    "selected_token": " A",
                    "candidates": [{"token": " A", "probability": 0.8}],
                    "explanation": "Top returned alternatives from the local model for this token position.",
                }
            ],
        }


def post_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_hf_trace_server_returns_trace_payload() -> None:
    server = load_server_module()
    runner = FakeTraceRunner()
    httpd = server.create_server(("127.0.0.1", 0), trace_runner=runner)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    status = 0

    try:
        payload = post_json(
            f"http://127.0.0.1:{httpd.server_port}/api/trace",
            {
                "prompt": "Write one sentence.",
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "max_new_tokens": 8,
                "top_k": 3,
                "temperature": 0.2,
            },
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert payload["mode"] == "hf-live-trace"
    assert payload["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert runner.calls == [
        {
            "prompt": "Write one sentence.",
            "model": "Qwen/Qwen2.5-0.5B-Instruct",
            "max_new_tokens": 8,
            "top_k": 3,
            "temperature": 0.2,
        }
    ]


def test_hf_trace_server_rejects_bad_requests() -> None:
    server = load_server_module()
    httpd = server.create_server(("127.0.0.1", 0), trace_runner=FakeTraceRunner())
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        request = Request(
            f"http://127.0.0.1:{httpd.server_port}/api/trace",
            data=json.dumps({"model": "Qwen/Qwen2.5-0.5B-Instruct"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(request, timeout=5)
        except HTTPError as error:
            status = error.code
            body = json.loads(error.read().decode("utf-8"))
        else:
            raise AssertionError("Expected HTTPError")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert status == 400
    assert "prompt" in body["error"]
