import json
from pathlib import Path
import subprocess
import tomllib

import pytest

from coding_agent.connection import AgentError, AgentSettings
from coding_agent import environment


@pytest.fixture
def inputs(tmp_path):
    project = tmp_path / "日本語 project"
    project.mkdir()
    runtime = tmp_path / "runtime data"
    plugin = tmp_path / "plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin/plugin.json").write_text(
        json.dumps({"name": "superpowers", "version": "6.3.0"}), encoding="utf-8"
    )
    (plugin / "LICENSE").write_text("MIT test license", encoding="utf-8")
    for name in (
        "using-superpowers", "brainstorming", "writing-plans",
        "test-driven-development", "systematic-debugging", "verification-before-completion",
    ):
        folder = plugin / "skills" / name
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Test\n---\n", encoding="utf-8")
    return project, runtime, plugin


def settings(host="https://first.ngrok-free.app", key="secret-test-only"):
    return AgentSettings(host, key)


def test_rendered_config_routes_to_colab_without_embedding_the_key():
    text = environment.render_config(settings())
    config = tomllib.loads(text)
    assert config["model"] == "gpt-oss:20b"
    catalog_path = Path(config["model_catalog_json"])
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    model = catalog["models"][0]
    assert model["slug"] == "gpt-oss:20b"
    assert "apply_patch_tool_type" not in model
    assert model["include_skills_usage_instructions"] is True
    assert "available tools" in model["base_instructions"]
    provider = config["model_providers"][config["model_provider"]]
    assert provider["base_url"] == "https://first.ngrok-free.app/v1"
    assert provider["wire_api"] == "responses"
    assert provider["env_http_headers"] == {"X-API-Key": "OLLAMA_API_KEY"}
    assert provider["requires_openai_auth"] is False
    assert config["model_auto_compact_token_limit"] < config["model_context_window"] == 65536
    assert config["sandbox_mode"] == "workspace-write"
    assert config["approval_policy"] == "on-request"
    assert config["model_reasoning_effort"] == "medium"
    assert "SKILL.md" in config["developer_instructions"]
    assert "actual command output" in config["developer_instructions"]
    assert "PowerShell" in config["developer_instructions"]
    assert config["features"]["plugins"] is False
    assert "OLLAMA_API_KEY" in config["shell_environment_policy"]["exclude"]
    assert "secret-test-only" not in text


def test_lower_context_also_lowers_compaction():
    config = tomllib.loads(environment.render_config(AgentSettings("https://example.com", "key", context_size=32768)))
    assert 0 < config["model_auto_compact_token_limit"] < config["model_context_window"] == 32768


def test_runtime_directory_is_isolated_per_external_project(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    first_runtime = environment.runtime_directory(first)
    second_runtime = environment.runtime_directory(second)

    assert first_runtime != second_runtime
    assert first_runtime.parent == second_runtime.parent
    assert first_runtime.parent.name == "projects"
    assert first_runtime.name != second_runtime.name


def test_tool_project_keeps_the_existing_runtime_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    runtime = environment.runtime_directory(environment.tool_root())

    assert runtime == tmp_path / "local/local-llm/coding-agent"


def test_setup_installs_readable_skills_and_can_be_repeated(inputs):
    project, runtime, plugin = inputs
    first = environment.prepare_environment(project, runtime, settings(), plugin)
    second = environment.prepare_environment(project, runtime, settings(), plugin)
    assert first == second
    assert first["skills"] == 6
    skills_root = project / ".agents/skills"
    assert (skills_root / "brainstorming").resolve() == (
        runtime / "superpowers/6.3.0/skills/brainstorming"
    ).resolve()
    assert (skills_root / "using-superpowers/SKILL.md").is_file()
    assert not (skills_root / "superpowers").exists()
    assert (runtime / "superpowers/6.3.0/LICENSE").read_text() == "MIT test license"
    config = tomllib.loads((runtime / "codex/config.toml").read_text(encoding="utf-8"))
    assert config["model"] == "gpt-oss:20b"
    assert Path(config["model_catalog_json"]) == runtime.resolve() / "codex/models.json"
    catalog = json.loads(
        (runtime / "codex/models.json").read_text(encoding="utf-8")
    )
    assert catalog["models"][0]["slug"] == "gpt-oss:20b"


def test_reconnect_updates_managed_config_and_preserves_user_sections(inputs):
    project, runtime, plugin = inputs
    environment.prepare_environment(project, runtime, settings(), plugin)
    path = runtime / "codex/config.toml"
    with path.open("a", encoding="utf-8") as handle:
        handle.write('\n[custom_section]\nvalue = "keep"\n')
    environment.prepare_environment(project, runtime, settings("https://second.ngrok-free.app", "new-secret"), plugin)
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    assert config["model_providers"]["colab-oss"]["base_url"] == "https://second.ngrok-free.app/v1"
    assert config["custom_section"]["value"] == "keep"
    assert "new-secret" not in path.read_text(encoding="utf-8")


def test_unmanaged_runtime_is_not_adopted(inputs):
    project, runtime, plugin = inputs
    runtime.mkdir()
    original = runtime / "valuable.txt"
    original.write_text("keep")
    with pytest.raises(AgentError, match="管理|既存"):
        environment.prepare_environment(project, runtime, settings(), plugin)
    assert original.read_text() == "keep"
    assert not (project / ".agents").exists()


def test_existing_skill_folder_is_not_replaced(inputs):
    project, runtime, plugin = inputs
    link = project / ".agents/skills/superpowers"
    link.mkdir(parents=True)
    (link / "original.txt").write_text("keep")
    with pytest.raises(AgentError, match="既存|競合"):
        environment.prepare_environment(project, runtime, settings(), plugin)
    assert (link / "original.txt").read_text() == "keep"
    assert not runtime.exists()


def test_existing_direct_skill_folder_is_not_replaced(inputs):
    project, runtime, plugin = inputs
    skill = project / ".agents/skills/brainstorming"
    skill.mkdir(parents=True)
    (skill / "original.txt").write_text("keep")

    with pytest.raises(AgentError, match="既存|競合"):
        environment.prepare_environment(project, runtime, settings(), plugin)

    assert (skill / "original.txt").read_text() == "keep"
    assert not runtime.exists()


def test_runtime_cannot_be_reused_for_a_different_project(inputs, tmp_path):
    project, runtime, plugin = inputs
    environment.prepare_environment(project, runtime, settings(), plugin)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(AgentError, match="プロジェクト"):
        environment.prepare_environment(other, runtime, settings(), plugin)
    assert not (other / ".agents").exists()


def test_user_replaced_config_is_not_overwritten(inputs):
    project, runtime, plugin = inputs
    environment.prepare_environment(project, runtime, settings(), plugin)
    path = runtime / "codex/config.toml"
    path.write_text('model = "user-choice"\n', encoding="utf-8")
    with pytest.raises(AgentError, match="設定|管理"):
        environment.prepare_environment(project, runtime, settings(), plugin)
    assert path.read_text() == 'model = "user-choice"\n'


def test_launch_uses_an_isolated_process_environment(inputs, monkeypatch):
    project, runtime, _ = inputs
    monkeypatch.setenv("OLLAMA_API_KEY", "parent-value")
    monkeypatch.setattr(environment, "find_vscode", lambda: Path("C:/VS Code/Code.exe"))
    monkeypatch.setattr(environment, "dedicated_vscode_running", lambda path: False)
    captured = []
    monkeypatch.setattr(environment.subprocess, "Popen", lambda args, **kwargs: captured.append((args, kwargs)))
    environment.launch_vscode(project, runtime, settings())
    import os
    assert os.environ["OLLAMA_API_KEY"] == "parent-value"
    args, kwargs = captured[0]
    assert str(runtime / "vscode-user-data") == args[args.index("--user-data-dir") + 1]
    assert str(project) in args
    assert kwargs["env"]["CODEX_HOME"] == str(runtime / "codex")
    assert kwargs["env"]["OLLAMA_API_KEY"] == "secret-test-only"
    assert all("secret-test-only" not in str(arg) for arg in args)


def test_running_vscode_is_not_reused_with_stale_environment(inputs, monkeypatch):
    project, runtime, _ = inputs
    monkeypatch.setattr(environment, "dedicated_vscode_running", lambda path: True)
    with pytest.raises(AgentError, match="閉じ"):
        environment.launch_vscode(project, runtime, settings())


def test_launch_failure_is_an_actionable_error(inputs, monkeypatch):
    project, runtime, _ = inputs
    monkeypatch.setattr(environment, "find_vscode", lambda: Path("C:/VS Code/Code.exe"))
    monkeypatch.setattr(environment, "dedicated_vscode_running", lambda path: False)
    def fail(*args, **kwargs):
        raise OSError("private process details")
    monkeypatch.setattr(environment.subprocess, "Popen", fail)
    with pytest.raises(AgentError, match="VS Code") as error:
        environment.launch_vscode(project, runtime, settings())
    assert "private process details" not in str(error.value)
