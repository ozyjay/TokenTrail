import csv
import importlib.util
import json
import sys
from pathlib import Path
from urllib.error import HTTPError


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_hf_trace.py"


def load_benchmark_module():
    spec = importlib.util.spec_from_file_location("benchmark_hf_trace", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status: int = 200, body: dict | None = None) -> None:
        self.status = status
        self._body = json.dumps(body or {}).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def read(self) -> bytes:
        return self._body


class FakeClock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        current = self.value
        self.value += 0.25
        return current


def test_benchmark_discovers_configured_models_warms_then_times_trace() -> None:
    benchmark = load_benchmark_module()
    calls = []
    request_bodies = []

    def opener(request, timeout):
        url = request.full_url
        method = request.get_method()
        calls.append((method, url, timeout))
        if request.data:
            request_bodies.append(json.loads(request.data.decode("utf-8")))

        if url.endswith("/api/models"):
            return FakeResponse(
                body={
                    "models": [
                        {
                            "model": "Qwen/Qwen2.5-0.5B-Instruct",
                            "configured": True,
                            "available": True,
                        },
                        {
                            "model": "not/configured",
                            "configured": False,
                            "available": True,
                        },
                        {
                            "model": "Qwen/Qwen2.5-3B-Instruct",
                            "configured": True,
                            "available": False,
                            "reason": "not cached",
                        },
                    ]
                }
            )
        if url.endswith("/api/warmup"):
            return FakeResponse(body={"status": "ready", "model": "Qwen/Qwen2.5-0.5B-Instruct"})
        if url.endswith("/api/trace"):
            return FakeResponse(
                body={
                    "mode": "hf-live-trace",
                    "model": "Qwen/Qwen2.5-0.5B-Instruct",
                    "steps": [
                        {
                            "selected_token": "A",
                            "candidates": [
                                {"token": "A", "probability": 0.7},
                                {"token": "The", "probability": 0.2},
                            ],
                        },
                        {
                            "selected_token": " robot",
                            "candidates": [{"token": " robot", "probability": 0.6}],
                        },
                    ],
                }
            )
        raise AssertionError(f"unexpected URL {url}")

    results = benchmark.run_benchmark(
        trace_url="http://127.0.0.1:8600/api/trace",
        prompts=["Open Day prompt"],
        timeout_seconds=5,
        max_new_tokens=24,
        top_k=5,
        temperature=0.3,
        candidate_source="forward-logits",
        opener=opener,
        clock=FakeClock(),
    )

    assert [call[0] for call in calls] == ["GET", "POST", "POST"]
    assert calls[1][1].endswith("/api/warmup")
    assert calls[2][1].endswith("/api/trace")
    assert request_bodies[0] == {"model": "Qwen/Qwen2.5-0.5B-Instruct"}
    assert request_bodies[1]["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert request_bodies[1]["prompt"] == "Open Day prompt"
    assert "candidate_source" not in request_bodies[1]
    assert results[0] == {
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "prompt": "Open Day prompt",
        "candidate_source": "forward-logits",
        "success": True,
        "warmup_seconds": 0.25,
        "trace_seconds": 0.25,
        "error": "",
        "fallback": "",
        "step_count": 2,
        "generated_text": "A robot",
        "candidate_count": 3,
    }
    assert results[1]["model"] == "Qwen/Qwen2.5-3B-Instruct"
    assert results[1]["success"] is False
    assert results[1]["error"] == "not cached"


def test_benchmark_records_unavailable_configured_model_without_warmup() -> None:
    benchmark = load_benchmark_module()
    calls = []

    def opener(request, timeout):
        calls.append((request.get_method(), request.full_url))
        return FakeResponse(
            body={
                "models": [
                    {
                        "model": "Qwen/Qwen2.5-3B-Instruct",
                        "configured": True,
                        "available": False,
                        "reason": "metadata not loadable",
                    }
                ]
            }
        )

    results = benchmark.run_benchmark(
        trace_url="http://127.0.0.1:8600/api/trace",
        prompts=["Prompt"],
        timeout_seconds=5,
        max_new_tokens=24,
        top_k=5,
        temperature=0.3,
        candidate_source="forward-logits",
        opener=opener,
        clock=FakeClock(),
    )

    assert calls == [("GET", "http://127.0.0.1:8600/api/models")]
    assert results[0]["success"] is False
    assert results[0]["model"] == "Qwen/Qwen2.5-3B-Instruct"
    assert results[0]["error"] == "metadata not loadable"
    assert results[0]["warmup_seconds"] == 0.0
    assert results[0]["trace_seconds"] == 0.0


def test_benchmark_records_trace_failure() -> None:
    benchmark = load_benchmark_module()

    def opener(request, timeout):
        if request.full_url.endswith("/api/models"):
            return FakeResponse(
                body={"models": [{"model": "Qwen/Qwen2.5-0.5B-Instruct", "configured": True, "available": True}]}
            )
        if request.full_url.endswith("/api/warmup"):
            return FakeResponse(body={"status": "ready"})
        raise HTTPError(request.full_url, 503, "trace unavailable", hdrs=None, fp=None)

    results = benchmark.run_benchmark(
        trace_url="http://127.0.0.1:8600/api/trace",
        prompts=["Prompt"],
        timeout_seconds=5,
        max_new_tokens=24,
        top_k=5,
        temperature=0.3,
        candidate_source="forward-logits",
        opener=opener,
        clock=FakeClock(),
    )

    assert results[0]["success"] is False
    assert results[0]["warmup_seconds"] == 0.25
    assert results[0]["trace_seconds"] == 0.25
    assert "HTTP 503" in results[0]["error"]


def test_write_results_creates_json_and_csv(tmp_path: Path) -> None:
    benchmark = load_benchmark_module()
    rows = [
        {
            "model": "Qwen/Qwen2.5-0.5B-Instruct",
            "prompt": "Prompt",
            "candidate_source": "forward-logits",
            "success": True,
            "warmup_seconds": 1.0,
            "trace_seconds": 2.0,
            "error": "",
            "fallback": "",
            "step_count": 1,
            "generated_text": "A robot.",
            "candidate_count": 5,
        }
    ]

    json_path, csv_path = benchmark.write_results(
        output_dir=tmp_path,
        trace_url="http://127.0.0.1:8600/api/trace",
        candidate_source="forward-logits",
        prompts=["Prompt"],
        results=rows,
        timestamp="20260621T120000Z",
    )

    assert json_path.exists()
    assert csv_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["results"] == rows

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))

    assert csv_rows[0]["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert csv_rows[0]["generated_text"] == "A robot."
