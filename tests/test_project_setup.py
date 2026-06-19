from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_project_files_exist() -> None:
    required_paths = [
        "pyproject.toml",
        "poetry.lock",
        ".python-version",
        "README.md",
        "scripts/setup.ps1",
        "scripts/test.ps1",
        "scripts/run.ps1",
        "web/index.html",
    ]

    for relative_path in required_paths:
        assert (PROJECT_ROOT / relative_path).exists(), relative_path


def test_python_version_matches_voicechanger_baseline() -> None:
    assert (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12.13"


def test_run_scripts_support_configurable_host_and_port() -> None:
    powershell_script = (PROJECT_ROOT / "scripts/run.ps1").read_text(encoding="utf-8")
    bash_script = (PROJECT_ROOT / "scripts/run.sh").read_text(encoding="utf-8")

    for script in (powershell_script, bash_script):
        assert "TOKEN_TRAIL_HOST" in script
        assert "TOKEN_TRAIL_PORT" in script
        assert "--host" in script
        assert "--port" in script
