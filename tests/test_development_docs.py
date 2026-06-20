from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cross_platform_scripts_exist() -> None:
    for relative_path in (
        "scripts/setup.ps1",
        "scripts/test.ps1",
        "scripts/run.ps1",
        "scripts/check_ports.ps1",
        "scripts/setup.sh",
        "scripts/test.sh",
        "scripts/run.sh",
        "scripts/check_ports.sh",
    ):
        assert (PROJECT_ROOT / relative_path).exists(), relative_path


def test_environment_docs_exist() -> None:
    for relative_path in (
        ".env.example",
        "docs/DEVELOPMENT_ENVIRONMENTS.md",
        "docs/MODEL_BACKENDS.md",
    ):
        assert (PROJECT_ROOT / relative_path).exists(), relative_path


def test_local_test_notes_document_hf_trace_probe() -> None:
    notes = (PROJECT_ROOT / "docs/LOCAL_TEST_NOTES.md").read_text(encoding="utf-8")

    assert "HF trace CLI probe" in notes
    assert "python3 scripts/probe_hf_trace.py" in notes
