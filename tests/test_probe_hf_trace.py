import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "probe_hf_trace.py"


def load_probe_module():
    spec = importlib.util.spec_from_file_location("probe_hf_trace", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_probe_module_imports_without_hf_dependencies() -> None:
    probe = load_probe_module()

    assert probe.DEFAULT_MODEL == "Qwen/Qwen2.5-0.5B-Instruct"
    assert probe.DEFAULT_PROMPT == "Write one sentence about a robot at university."


def test_parse_args_uses_fast_probe_defaults() -> None:
    probe = load_probe_module()

    args = probe.parse_args([])

    assert args.model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert args.prompt == "Write one sentence about a robot at university."
    assert args.max_new_tokens == 24
    assert args.top_k == 5
    assert args.temperature == 0.3
    assert args.json is False
