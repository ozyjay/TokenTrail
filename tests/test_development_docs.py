from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_uses_powershell_automation_only() -> None:
    assert not any((PROJECT_ROOT / "scripts").glob("*.sh"))
    for path in (
        "scripts/setup.ps1",
        "scripts/clean.ps1",
        "scripts/test.ps1",
        "scripts/run.ps1",
        "scripts/stop.ps1",
    ):
        assert (PROJECT_ROOT / path).exists()


def test_primary_docs_describe_external_modeldeck_ownership() -> None:
    for path in ("README.md", "AGENTS.md", "docs/MODEL_BACKENDS.md", "docs/LOCAL_TEST_NOTES.md"):
        document = (PROJECT_ROOT / path).read_text(encoding="utf-8")
        assert "ModelDeck" in document
        assert "Token Trail" in document

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "never starts, warms, stops or downloads models" in readme
    assert "GET /v1/models" in readme
    assert "POST /native/autoregressive/trace" in readme


def test_modeldeck_public_route_and_config_are_documented() -> None:
    for path in ("README.md", ".env.example"):
        document = (PROJECT_ROOT / path).read_text(encoding="utf-8")
        assert "TOKEN_TRAIL_MODELDECK_URL=" in document
        assert "TOKEN_TRAILS_MODEL=qwen-1-5b" in document
        assert "qwen-0-5b,qwen-1-5b,qwen-3b" in document


def test_agents_doc_records_project_safety_boundaries() -> None:
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Use PowerShell scripts only" in agents
    assert "must not start, warm, stop, or download model workers" in agents
    assert "scripted" in agents
