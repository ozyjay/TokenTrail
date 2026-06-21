from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cross_platform_scripts_exist() -> None:
    for relative_path in (
        "scripts/setup.ps1",
        "scripts/clean.ps1",
        "scripts/test.ps1",
        "scripts/run.ps1",
        "scripts/check_ports.ps1",
        "scripts/probe_hf_trace.ps1",
    ):
        assert (PROJECT_ROOT / relative_path).exists(), relative_path

    assert not any((PROJECT_ROOT / "scripts").glob("*.sh"))


def test_environment_docs_exist() -> None:
    for relative_path in (
        "AGENTS.md",
        ".env.example",
        "docs/DEVELOPMENT_ENVIRONMENTS.md",
        "docs/MODEL_BACKENDS.md",
    ):
        assert (PROJECT_ROOT / relative_path).exists(), relative_path


def test_local_test_notes_document_hf_trace_probe() -> None:
    notes = (PROJECT_ROOT / "docs/LOCAL_TEST_NOTES.md").read_text(encoding="utf-8")

    assert "HF trace CLI probe" in notes
    assert "pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1" in notes
    assert "pwsh -NoProfile -File ./scripts/serve_hf_trace.ps1" in notes
    assert "--candidate-source generation-scores" in notes


def test_main_docs_explain_hf_trace_is_core_dependency() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    environments = (PROJECT_ROOT / "docs/DEVELOPMENT_ENVIRONMENTS.md").read_text(encoding="utf-8")

    for document in (readme, environments):
        assert "poetry install --with hf-trace" not in document
        assert "HF trace dependencies are installed by the normal Poetry setup" in document
        assert "pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1" in document
        assert "--candidate-source forward-logits" in document


def test_docs_describe_hf_trace_as_primary_with_preload() -> None:
    for relative_path in (
        "README.md",
        "docs/DEVELOPMENT_ENVIRONMENTS.md",
        "docs/MODEL_BACKENDS.md",
        "docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md",
        "docs/LOCAL_TEST_NOTES.md",
    ):
        document = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

        assert "optional HF trace" not in document
        assert "loads on the first HF generation request" not in document
        assert "first HF generation request pays" not in document
        assert "preload" in document.lower() or "preloads" in document.lower()


def test_local_test_notes_include_hf_model_benchmark_table() -> None:
    notes = (PROJECT_ROOT / "docs/LOCAL_TEST_NOTES.md").read_text(encoding="utf-8")

    for heading in (
        "Model",
        "Machine",
        "Candidate source",
        "Cold load time",
        "Warm trace time",
        "Repeat trace time",
        "Peak RAM/VRAM if known",
        "Complete-sentence success",
        "Candidate quality notes",
        "Decision",
    ):
        assert heading in notes

    for model in (
        "Qwen/Qwen2.5-0.5B-Instruct",
        "Qwen/Qwen2.5-1.5B-Instruct",
        "Qwen/Qwen2.5-3B-Instruct",
    ):
        assert model in notes

    assert "HuggingFaceTB/SmolLM2-1.7B-Instruct" not in notes
    assert "Choose the final booth default from measured local performance, not assumptions" in notes


def test_main_docs_do_not_reference_shell_scripts() -> None:
    for relative_path in (
        "README.md",
        "docs/DEVELOPMENT_ENVIRONMENTS.md",
        "docs/LOCAL_TEST_NOTES.md",
        "docs/TOKEN_TRAIL_ROADMAP.md",
    ):
        document = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

        assert ".sh" not in document


def test_agents_doc_records_powershell_only_script_policy() -> None:
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "Use PowerShell scripts only" in agents
    assert "Do not add shell scripts" in agents
    assert "pwsh -NoProfile -File ./scripts/clean.ps1" in agents
    assert "pwsh -NoProfile -File ./scripts/test.ps1" in agents
    assert "--candidate-source forward-logits" in agents


def test_hf_trace_plan_records_cli_probe_result() -> None:
    plan = (PROJECT_ROOT / "docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md").read_text(encoding="utf-8")

    assert "CLI probe implemented" in plan
    assert "--candidate-source forward-logits" in plan
    assert "generation-scores" in plan


def test_hf_trace_model_list_is_documented() -> None:
    for relative_path in (
        ".env.example",
        "README.md",
        "docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md",
    ):
        document = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

        assert "TOKEN_TRAIL_HF_TRACE_MODEL=" in document
        assert "TOKEN_TRAIL_HF_TRACE_MODELS=" in document


def test_model_config_json_is_documented() -> None:
    for relative_path in (
        ".env.example",
        "README.md",
        "docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md",
    ):
        document = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

        assert "TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json" in document
        assert "config/models.json" in document
