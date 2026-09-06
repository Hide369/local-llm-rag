"""Colabのgpt-oss:20bを使うVS Code環境の診断・セットアップ・起動。"""

import argparse
import json
from pathlib import Path
import sys
import tomllib

from coding_agent.connection import AgentError, OllamaClient, load_settings
from coding_agent.environment import (
    find_codex_executable, find_superpowers, launch_vscode,
    prepare_environment, runtime_directory,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="接続・モデルを診断する（推論なし）")
    mode.add_argument("--setup", action="store_true", help="設定とスキルを準備する（起動なし）")
    mode.add_argument("--configure-context", action="store_true", help="元モデルを保存してColabのコンテキストを設定する")
    mode.add_argument("--restore-context", action="store_true", help="保存した元モデルの設定へ戻す")
    mode.add_argument("--probe", action="store_true", help="GPU配置とResponses APIのツール往復を検証する")
    parser.add_argument("--context-size", type=int, choices=(32768, 65536), help="省略時は保存済み設定、初回は65536")
    args = parser.parse_args(argv)
    try:
        runtime = runtime_directory()
        context_size = args.context_size
        if context_size is None:
            saved = runtime / "codex/config.toml"
            config = tomllib.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {}
            context_size = config.get("model_context_window", 65536)
        settings = load_settings(PROJECT_ROOT, context_size)
        client = OllamaClient(settings)
        if args.check:
            result = client.inspect()
        elif args.configure_context:
            result = client.configure_context()
        elif args.restore_context:
            result = client.restore_context()
        elif args.probe:
            gpu = client.warmup()
            if gpu.get("context_length") != settings.context_size:
                raise AgentError("Colabのコンテキスト長が設定と一致しません。--configure-contextを実行してください。")
            if not gpu.get("fully_on_gpu"):
                raise AgentError("モデルの一部がCPUへ配置されています。--context-size 32768で再設定・検証してください。")
            result = {"gpu": gpu, "tools": client.probe_tools()}
        else:
            find_codex_executable()
            if not args.setup:
                client.inspect()
            result = prepare_environment(PROJECT_ROOT, runtime, settings, find_superpowers())
            if not args.setup:
                launch_vscode(PROJECT_ROOT, runtime, settings)
                result["launched"] = True
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except AgentError as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        # 外部例外にはURLやプロセス環境が含まれ得るため、型だけを表示する。
        print(f"エラー: 設定の読み書きに失敗しました（{type(error).__name__}）。設定形式と権限を確認してください。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
