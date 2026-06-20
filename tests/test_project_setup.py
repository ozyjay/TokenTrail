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
        "scripts/clean.ps1",
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

    assert "token_trail.local_runner" in powershell_script
    assert "--host" not in powershell_script
    assert "--port" not in powershell_script
    assert "TOKEN_TRAIL_HOST" not in powershell_script
    assert "TOKEN_TRAIL_PORT" not in powershell_script


def test_clean_script_removes_local_python_and_test_artifacts_only() -> None:
    script = (PROJECT_ROOT / "scripts" / "clean.ps1").read_text(encoding="utf-8")

    assert "Remove-Item" in script
    assert "__pycache__" in script
    assert ".pytest_cache" in script
    assert ".ruff_cache" in script
    assert "build" in script
    assert "dist" in script
    assert "$DryRun" in script
    assert "Get-ChildItem -Path $ProjectRoot" in script


def test_run_script_manages_hf_trace_stack_when_configured() -> None:
    powershell_script = (PROJECT_ROOT / "scripts/run.ps1").read_text(encoding="utf-8")

    assert "poetry install --with hf-trace" not in powershell_script
    assert "Installing optional HF trace" not in powershell_script
    assert "poetry run python -m token_trail.local_runner" in powershell_script


def test_hf_trace_probe_dependencies_are_core_poetry_dependencies() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "hf-trace" not in pyproject["tool"]["poetry"].get("group", {})
    assert {"torch", "transformers", "accelerate"}.issubset(set(pyproject["project"]["dependencies"]))


def test_hf_trace_probe_powershell_script_uses_core_install_and_forwards_args() -> None:
    script = (PROJECT_ROOT / "scripts/probe_hf_trace.ps1").read_text(encoding="utf-8")

    assert "poetry install --with hf-trace" not in script
    assert "poetry install" not in script
    assert "$env:PYTHONPATH = \"src\"" in script
    assert "poetry run python scripts/probe_hf_trace.py @args" in script


def test_hf_trace_server_powershell_script_uses_core_install_and_forwards_args() -> None:
    script = (PROJECT_ROOT / "scripts/serve_hf_trace.ps1").read_text(encoding="utf-8")

    assert "poetry install --with hf-trace" not in script
    assert "poetry install" not in script
    assert "$env:PYTHONPATH = \"src\"" in script
    assert "poetry run python scripts/serve_hf_trace.py @args" in script


def test_model_config_file_lists_runtime_models() -> None:
    model_config = json.loads((PROJECT_ROOT / "config" / "models.json").read_text(encoding="utf-8"))

    assert model_config["defaults"]["hf_trace_model"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert [entry["model"] for entry in model_config["ollama"]] == ["qwen3:1.7b", "qwen3:4b"]
    hf_trace_models = [entry["model"] for entry in model_config["hf_trace"]]
    assert "Qwen/Qwen2.5-1.5B-Instruct" in hf_trace_models
    assert "Qwen/Qwen2.5-0.5B-Instruct" in hf_trace_models
