import json

from scripts import coding_agent as cli


def test_missing_env_is_reported_without_a_traceback(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert cli.main(["--check", "--project", str(tmp_path)]) == 1
    out = capsys.readouterr()
    assert ".env" in out.err
    assert "Traceback" not in out.err


def test_check_does_not_install_or_launch(tmp_path, capsys, monkeypatch):
    (tmp_path / ".env").write_text("OLLAMA_HOST=https://example.ngrok-free.app\nOLLAMA_API_KEY=secret-test-only\n")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    class Client:
        def __init__(self, settings):
            self.settings = settings
        def inspect(self):
            return {"model": self.settings.model, "tools": True, "loaded": False}
    monkeypatch.setattr(cli, "OllamaClient", Client)
    assert cli.main(["--check", "--project", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["model"] == "gpt-oss:20b"
    assert "secret-test-only" not in output
    assert not (tmp_path / "local").exists()


def test_saved_context_is_used_on_next_launch(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("OLLAMA_HOST=https://example.ngrok-free.app\nOLLAMA_API_KEY=key\n")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    runtime = cli.runtime_directory(tmp_path)
    (runtime / "codex").mkdir(parents=True)
    (runtime / "codex/config.toml").write_text("model_context_window = 32768\n")
    received = []
    class Client:
        def __init__(self, settings):
            received.append(settings.context_size)
        def inspect(self):
            return {"tools": True}
    monkeypatch.setattr(cli, "OllamaClient", Client)
    assert cli.main(["--check", "--project", str(tmp_path)]) == 0
    assert cli.main(["--check", "--project", str(tmp_path), "--context-size", "65536"]) == 0
    assert received == [32768, 65536]


def test_restore_context_uses_project_env(tmp_path, capsys, monkeypatch):
    (tmp_path / ".env").write_text(
        "OLLAMA_HOST=https://example.ngrok-free.app\nOLLAMA_API_KEY=key\n"
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    class Client:
        def __init__(self, settings):
            self.settings = settings

        def restore_context(self):
            return {"model": self.settings.model, "restored": True}

    monkeypatch.setattr(cli, "OllamaClient", Client)

    assert cli.main(["--restore-context", "--project", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["restored"] is True


def test_current_directory_is_the_default_project(tmp_path, capsys, monkeypatch):
    (tmp_path / ".env").write_text(
        "OLLAMA_HOST=https://example.ngrok-free.app\nOLLAMA_API_KEY=key\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    class Client:
        def __init__(self, settings):
            self.settings = settings

        def inspect(self):
            return {"model": self.settings.model}

    monkeypatch.setattr(cli, "OllamaClient", Client)

    assert cli.main(["--check"]) == 0
    assert json.loads(capsys.readouterr().out)["model"] == "gpt-oss:20b"


def test_file_is_rejected_as_a_project(tmp_path, capsys, monkeypatch):
    project_file = tmp_path / "not-a-project.txt"
    project_file.write_text("not a directory")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    assert cli.main(["--check", "--project", str(project_file)]) == 1
    assert "フォルダ" in capsys.readouterr().err


def _probe_client(monkeypatch, *, fully_on_gpu, context_length):
    """--probe の判定だけを見るための差し替え。推論も接続もしない。"""

    class Client:
        def __init__(self, settings):
            self.settings = settings

        def warmup(self):
            return {"fully_on_gpu": fully_on_gpu, "context_length": context_length}

        def probe_tools(self):
            return {"called": True}

    monkeypatch.setattr(cli, "OllamaClient", Client)


def test_probe_accepts_the_largest_context_size(tmp_path, capsys, monkeypatch):
    """131072 が CLI の選択肢を通り、そのまま検証まで届くこと。"""
    (tmp_path / ".env").write_text("OLLAMA_HOST=https://example.ngrok-free.app\nOLLAMA_API_KEY=key\n")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    _probe_client(monkeypatch, fully_on_gpu=True, context_length=131072)

    assert cli.main(["--probe", "--project", str(tmp_path), "--context-size", "131072"]) == 0
    assert json.loads(capsys.readouterr().out)["gpu"]["context_length"] == 131072


def test_cpu_placement_points_at_the_next_smaller_size(tmp_path, capsys, monkeypatch):
    """案内する値は並びから引く。131072 で溢れたなら次は 65536 である。"""
    (tmp_path / ".env").write_text("OLLAMA_HOST=https://example.ngrok-free.app\nOLLAMA_API_KEY=key\n")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    _probe_client(monkeypatch, fully_on_gpu=False, context_length=131072)

    assert cli.main(["--probe", "--project", str(tmp_path), "--context-size", "131072"]) == 1
    message = capsys.readouterr().err
    assert "65536" in message
    assert "32768" not in message


def test_cpu_placement_at_the_smallest_size_says_there_is_no_next_step(
    tmp_path, capsys, monkeypatch
):
    """一番小さい値でも溢れたら、下げる案内をしても意味がない。"""
    (tmp_path / ".env").write_text("OLLAMA_HOST=https://example.ngrok-free.app\nOLLAMA_API_KEY=key\n")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    _probe_client(monkeypatch, fully_on_gpu=False, context_length=32768)

    assert cli.main(["--probe", "--project", str(tmp_path), "--context-size", "32768"]) == 1
    message = capsys.readouterr().err
    assert "--context-size" not in message
    assert "モデルを小さくする" in message
