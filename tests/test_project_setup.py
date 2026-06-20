import json
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_project_files_exist() -> None:
    required_paths = [
        "pyproject.toml",
        "poetry.lock",
        ".python-version",
        "README.md",
        "config/models.json",
        "scripts/setup.ps1",
        "scripts/test.ps1",
        "scripts/run.ps1",
        "scripts/serve_hf_trace.ps1",
        "web/index.html",
    ]

    for relative_path in required_paths:
        assert (PROJECT_ROOT / relative_path).exists(), relative_path


def test_python_version_matches_voicechanger_baseline() -> None:
    assert (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12.13"


def test_run_scripts_delegate_host_and_port_config_to_python() -> None:
    powershell_script = (PROJECT_ROOT / "scripts/run.ps1").read_text(encoding="utf-8")

    assert "token_trail.ports" in powershell_script
    assert "token_trail.server" in powershell_script
    assert "--host" not in powershell_script
    assert "--port" not in powershell_script
    assert "TOKEN_TRAIL_HOST" not in powershell_script
    assert "TOKEN_TRAIL_PORT" not in powershell_script


def test_hf_trace_probe_dependencies_are_optional_poetry_group() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    hf_trace_group = pyproject["tool"]["poetry"]["group"]["hf-trace"]

    assert hf_trace_group["optional"] is True
    assert set(hf_trace_group["dependencies"]) == {"torch", "transformers", "accelerate"}


def test_hf_trace_probe_powershell_script_installs_optional_group_and_forwards_args() -> None:
    script = (PROJECT_ROOT / "scripts/probe_hf_trace.ps1").read_text(encoding="utf-8")

    assert "poetry install --with hf-trace" in script
    assert "$env:PYTHONPATH = \"src\"" in script
    assert "poetry run python scripts/probe_hf_trace.py @args" in script


def test_hf_trace_server_powershell_script_installs_optional_group_and_forwards_args() -> None:
    script = (PROJECT_ROOT / "scripts/serve_hf_trace.ps1").read_text(encoding="utf-8")

    assert "poetry install --with hf-trace" in script
    assert "$env:PYTHONPATH = \"src\"" in script
    assert "poetry run python scripts/serve_hf_trace.py @args" in script


def test_model_config_file_lists_runtime_models() -> None:
    model_config = json.loads((PROJECT_ROOT / "config" / "models.json").read_text(encoding="utf-8"))

    assert model_config["defaults"]["hf_trace_model"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert [entry["model"] for entry in model_config["ollama"]] == ["qwen3:1.7b", "qwen3:4b"]
    assert [entry["model"] for entry in model_config["hf_trace"]] == [
        "Qwen/Qwen2.5-1.5B-Instruct",
        "Qwen/Qwen2.5-0.5B-Instruct",
    ]
