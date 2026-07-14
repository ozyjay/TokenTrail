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
        "config/instructions/modeldeck_default.txt",
        "scripts/setup.ps1",
        "scripts/clean.ps1",
        "scripts/test.ps1",
        "scripts/run.ps1",
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


def test_setup_script_explains_how_to_install_missing_poetry() -> None:
    setup_script = (PROJECT_ROOT / "scripts/setup.ps1").read_text(encoding="utf-8")

    assert "Get-Command poetry" in setup_script
    assert "pipx install poetry" in setup_script


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


def test_run_script_starts_only_token_trail() -> None:
    powershell_script = (PROJECT_ROOT / "scripts/run.ps1").read_text(encoding="utf-8")

    assert "poetry install --with hf-trace" not in powershell_script
    assert "Installing optional HF trace" not in powershell_script
    assert "poetry run python -m token_trail.local_runner" in powershell_script


def test_legacy_hf_diagnostics_remain_available_without_driving_startup() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert {"torch", "transformers", "accelerate"}.issubset(pyproject["project"]["dependencies"])
    runner = (PROJECT_ROOT / "src/token_trail/local_runner.py").read_text(encoding="utf-8")
    assert "serve_hf_trace" not in runner
    assert ".warmup(" not in runner


def test_model_config_file_lists_runtime_models() -> None:
    model_config = json.loads((PROJECT_ROOT / "config" / "models.json").read_text(encoding="utf-8"))

    assert "ollama" not in model_config
    assert "vllm" not in model_config
    assert "ollama_model" not in model_config["defaults"]
    assert "vllm_model" not in model_config["defaults"]
    assert model_config["defaults"]["backend"] == "modeldeck"
    assert model_config["defaults"]["modeldeck_model"] == "qwen-1-5b"
    assert [entry["model"] for entry in model_config["modeldeck"]] == [
        "qwen-0-5b",
        "qwen-1-5b",
        "qwen-3b",
    ]


def test_removed_backend_support_files_are_absent() -> None:
    removed_paths = (
        "src/token_trail/adapters/ollama.py",
        "scripts/check_ollama_update.ps1",
        "scripts/probe_ollama_logprobs.py",
        "scripts/probe_ollama_logprobs.ps1",
        "tests/test_ollama_adapter.py",
        "tests/test_probe_ollama_logprobs.py",
        "docs/OLLAMA_ADAPTER_PLAN.md",
        "docs/OLLAMA_PHASE_2_GENERATION_PLAN.md",
        "docs/OLLAMA_WARMUP_PLAN.md",
    )

    for relative_path in removed_paths:
        assert not (PROJECT_ROOT / relative_path).exists(), relative_path
