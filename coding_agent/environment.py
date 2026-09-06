"""Colab専用のCodex設定とVS Codeインスタンスを準備する。"""

import json
import os
from pathlib import Path
import shutil
from string import Template
import subprocess
import tempfile
import tomllib

from coding_agent.connection import AgentError, AgentSettings


_BEGIN = "# BEGIN LOCAL_LLM_MANAGED_CONFIG"
_END = "# END LOCAL_LLM_MANAGED_CONFIG"
_MARKER = ".local-llm-agent.json"
_VERSION = "6.3.0"
_REQUIRED_SKILLS = (
    "using-superpowers", "brainstorming", "writing-plans",
    "test-driven-development", "systematic-debugging", "verification-before-completion",
)


def runtime_directory() -> Path:
    value = os.environ.get("LOCALAPPDATA")
    if not value or not Path(value).is_absolute():
        raise AgentError("WindowsのLOCALAPPDATAが設定されていません。")
    return Path(value) / "local-llm" / "coding-agent"


def render_config(settings: AgentSettings, model_catalog_path: Path | None = None) -> str:
    path = Path(__file__).resolve().parent.parent / "infra/codex-colab/config.toml.template"
    if model_catalog_path is None:
        model_catalog_path = path.with_name("models.json")
    text = Template(path.read_text(encoding="utf-8")).substitute(
        base_url=json.dumps(settings.host.rstrip("/") + "/v1", ensure_ascii=False),
        model_catalog_path=json.dumps(str(model_catalog_path.resolve()), ensure_ascii=False),
        context_size=settings.context_size,
        compact_limit=settings.context_size * 3 // 4,
    )
    tomllib.loads(text)
    return text


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise AgentError(f"設定ファイルを読み取れません: {path.name}") from error
    if not isinstance(data, dict):
        raise AgentError(f"設定ファイルの形式が不正です: {path.name}")
    return data


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # 同じディレクトリ内で置換し、途中終了による半端な設定を避ける。
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _merged_config(path: Path, generated: str) -> str:
    if not path.exists():
        return generated
    original = path.read_text(encoding="utf-8")
    if not original.startswith(_BEGIN + "\n") or original.count(_END) != 1:
        raise AgentError("既存のCodex設定が管理形式ではありません。上書きを中止しました。")
    tail = original.split(_END, 1)[1]
    result = generated.rstrip() + tail
    try:
        tomllib.loads(result)
    except tomllib.TOMLDecodeError as error:
        raise AgentError("追加されたCodex設定が生成設定と競合しています。") from error
    return result


def _validate_plugin(source: Path) -> None:
    manifest = _read_json(source / ".codex-plugin/plugin.json")
    if manifest.get("name") != "superpowers" or manifest.get("version") != _VERSION:
        raise AgentError("Superpowers 6.3.0のインストール先を確認してください。")
    if not (source / "LICENSE").is_file():
        raise AgentError("SuperpowersのLICENSEが見つかりません。")
    for name in _REQUIRED_SKILLS:
        if not (source / "skills" / name / "SKILL.md").is_file():
            raise AgentError(f"Superpowersの必須スキルが見つかりません: {name}")


def find_superpowers() -> Path:
    cache = Path.home() / ".codex/plugins/cache"
    for manifest in sorted(cache.glob("*/superpowers/*/.codex-plugin/plugin.json")):
        data = _read_json(manifest)
        if data.get("version") == _VERSION:
            source = manifest.parent.parent
            _validate_plugin(source)
            return source
    raise AgentError("Superpowers 6.3.0をCodexのプラグイン画面からインストールしてください。")


def _is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _powershell(command: str, extra_env: dict) -> str:
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            env={**os.environ, **extra_env}, capture_output=True, text=True,
            timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AgentError("Windowsの環境準備コマンドを実行できませんでした。") from error
    if result.returncode:
        raise AgentError("Windowsの環境準備に失敗しました。フォルダの権限を確認してください。")
    return result.stdout.strip()


def _create_directory_link(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        _powershell(
            "$ErrorActionPreference='Stop'; "
            "New-Item -ItemType Junction -Path $env:LOCAL_LLM_LINK "
            "-Target $env:LOCAL_LLM_TARGET | Out-Null",
            {"LOCAL_LLM_LINK": str(link), "LOCAL_LLM_TARGET": str(target)},
        )
    else:
        link.symlink_to(target, target_is_directory=True)


def _remove_directory_link(link: Path) -> None:
    if link.is_symlink():
        link.unlink()
    else:
        link.rmdir()


def prepare_environment(project: Path, runtime: Path, settings: AgentSettings,
                        superpowers_source: Path) -> dict:
    project = project.resolve(strict=True)
    if _is_link(runtime):
        raise AgentError("実行時フォルダが既存のリンクです。管理先を確認してください。")
    runtime = runtime.resolve()
    _validate_plugin(superpowers_source)
    installed = runtime / "superpowers" / _VERSION
    target = installed / "skills"
    source_skills = sorted(
        skill.parent for skill in (superpowers_source / "skills").glob("*/SKILL.md")
    )
    skills_root = project / ".agents/skills"
    if _is_link(skills_root):
        raise AgentError("既存のスキル配置と競合しています。上書きしません。")
    links = [(skills_root / skill.name, target / skill.name) for skill in source_skills]
    legacy_link = skills_root / "superpowers"
    legacy_managed = False
    # 既存ユーザーデータの競合は、書き込みを始める前に判定する。
    if legacy_link.exists() or _is_link(legacy_link):
        if not _is_link(legacy_link) or legacy_link.resolve() != target.resolve():
            raise AgentError("既存のSuperpowersスキル配置と競合しています。上書きしません。")
        legacy_managed = True
    for link, skill_target in links:
        if link.exists() or _is_link(link):
            if not _is_link(link) or link.resolve() != skill_target.resolve():
                raise AgentError(f"既存のスキル配置と競合しています: {link.name}")
    marker = runtime / _MARKER
    identity = {"manager": "local-llm-coding-agent", "schema": 1, "project": str(project)}
    if marker.exists():
        if _read_json(marker) != identity:
            raise AgentError("実行時フォルダは別のプロジェクトまたは別形式で管理されています。")
    elif runtime.exists() and any(runtime.iterdir()):
        raise AgentError("実行時フォルダに既存の未管理ファイルがあります。上書きしません。")
    config_path = runtime / "codex/config.toml"
    model_catalog_path = runtime / "codex/models.json"
    config = _merged_config(
        config_path, render_config(settings, model_catalog_path=model_catalog_path)
    )
    vscode_settings_path = runtime / "vscode-user-data/User/settings.json"
    vscode_settings = _read_json(vscode_settings_path) if vscode_settings_path.exists() else {}
    if installed.exists():
        _validate_plugin(installed)
    else:
        installed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(superpowers_source, installed)
    _atomic_write(marker, json.dumps(identity, ensure_ascii=False, indent=2) + "\n")
    catalog_source = Path(__file__).resolve().parent.parent / "infra/codex-colab/models.json"
    _atomic_write(model_catalog_path, catalog_source.read_text(encoding="utf-8"))
    _atomic_write(config_path, config)
    vscode_settings.setdefault("chatgpt.openOnStartup", True)
    vscode_settings["chatgpt.runCodexInWindowsSubsystemForLinux"] = False
    vscode_settings.setdefault("window.title", "local_llm · Colab gpt-oss:20b · ${activeEditorShort}")
    _atomic_write(vscode_settings_path, json.dumps(vscode_settings, ensure_ascii=False, indent=2) + "\n")
    if legacy_managed:
        _remove_directory_link(legacy_link)
    for link, skill_target in links:
        if not link.exists():
            _create_directory_link(link, skill_target)
        if link.resolve() != skill_target.resolve() or not (link / "SKILL.md").is_file():
            raise AgentError(f"Superpowersスキルへのリンクを確認できませんでした: {link.name}")
    return {
        "codex_home": str(runtime / "codex"),
        "user_data": str(runtime / "vscode-user-data"),
        "skills": len(links),
        "context_size": settings.context_size,
    }


def find_vscode() -> Path:
    command = shutil.which("code.cmd")
    candidates = [Path(command).parent.parent / "Code.exe"] if command else []
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "Programs/Microsoft VS Code/Code.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise AgentError("VS CodeのCode.exeが見つかりません。VS Codeをインストールしてください。")


def find_codex_executable() -> Path:
    found = []
    for manifest in (Path.home() / ".vscode/extensions").glob("openai.chatgpt-*/package.json"):
        data = _read_json(manifest)
        executable = manifest.parent / "bin/windows-x86_64/codex.exe"
        if executable.is_file():
            try:
                version = tuple(int(part) for part in data["version"].split("."))
            except (KeyError, ValueError):
                continue
            found.append((version, executable))
    if not found:
        raise AgentError("VS CodeのCodex拡張機能（openai.chatgpt）をインストールしてください。")
    return max(found)[1]


def dedicated_vscode_running(user_data: Path) -> bool:
    if os.name != "nt":
        raise AgentError("この起動補助はWindows用です。")
    result = _powershell(
        "$ErrorActionPreference='Stop'; "
        "$matchesForAgent = @(Get-CimInstance Win32_Process -Filter \"Name = 'Code.exe'\" | "
        "Where-Object { $_.CommandLine -and "
        "$_.CommandLine.IndexOf($env:LOCAL_LLM_VSCODE_DATA, [StringComparison]::OrdinalIgnoreCase) -ge 0 }); "
        "[Console]::Write($matchesForAgent.Count)",
        {"LOCAL_LLM_VSCODE_DATA": str(user_data)},
    )
    if not result.isdigit():
        raise AgentError("専用VS Codeの起動状態を確認できませんでした。")
    return int(result) > 0


def launch_vscode(project: Path, runtime: Path, settings: AgentSettings) -> None:
    user_data = runtime / "vscode-user-data"
    if dedicated_vscode_running(user_data):
        raise AgentError("Colab用のVS Codeウィンドウを閉じてから再実行してください。接続設定を再読み込みします。")
    executable = find_vscode()
    child_env = dict(os.environ)
    child_env.update({"CODEX_HOME": str(runtime / "codex"), "OLLAMA_API_KEY": settings.api_key})
    # Codexのシェル経由で起動する場合もElectronをNodeモードで動かさない。
    child_env.pop("ELECTRON_RUN_AS_NODE", None)
    try:
        subprocess.Popen(
            [str(executable), "--user-data-dir", str(user_data),
             "--extensions-dir", str(Path.home() / ".vscode/extensions"),
             "--new-window", str(project)],
            env=child_env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise AgentError("VS Codeを起動できませんでした。インストール先と権限を確認してください。") from error
