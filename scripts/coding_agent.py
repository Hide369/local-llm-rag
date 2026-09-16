"""OllamaのモデルをVS Codeのコーディングエージェントに使うための診断・セットアップ・起動。

接続先は .env の OLLAMA_HOST、モデルは --model、コンテキスト長は --context-size で
決める。ColabのL4（HTTPS＋APIキー）でも、社内LANのGB10（HTTP・認証なし）でも
同じ補助を使う。手順は docs/vscode-colab-agent.md と docs/gb10-coding-agent.md。
"""

import argparse
import json
from pathlib import Path
import sys
import tomllib

from coding_agent.connection import (
    DEFAULT_MODEL,
    DEFAULT_WIRE_API,
    SUPPORTED_CONTEXT_SIZES,
    SUPPORTED_WIRE_APIS,
    AgentError,
    OllamaClient,
    load_settings,
    smaller_context_size,
)
from coding_agent.environment import (
    find_codex_executable, find_superpowers, launch_vscode,
    prepare_environment, runtime_directory,
)


def project_directory(value: str | None) -> Path:
    """対象ワークスペースを解決し、実在するフォルダだけを受け入れる。"""

    candidate = Path(value) if value else Path.cwd()
    try:
        project = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise AgentError("--project にはアクセス可能なフォルダを指定してください。") from None
    if not project.is_dir():
        raise AgentError("--project にはフォルダを指定してください。")
    return project


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="接続・モデルを診断する（推論なし）")
    mode.add_argument("--setup", action="store_true", help="設定とスキルを準備する（起動なし）")
    mode.add_argument("--configure-context", action="store_true", help="元モデルを保存してColabのコンテキストを設定する")
    mode.add_argument("--restore-context", action="store_true", help="保存した元モデルの設定へ戻す")
    mode.add_argument("--probe", action="store_true", help="GPU配置とResponses APIのツール往復を検証する")
    parser.add_argument("--project", metavar="PATH", help="VS Codeで開く対象プロジェクト（省略時は現在のフォルダ）")
    parser.add_argument(
        "--context-size",
        type=int,
        choices=SUPPORTED_CONTEXT_SIZES,
        help="省略時は保存済み設定、初回は65536。131072は128GB級のメモリが要る",
    )
    parser.add_argument(
        "--model",
        metavar="NAME",
        help=f"Ollamaのモデル名。省略時は保存済み設定、初回は{DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--wire-api",
        choices=SUPPORTED_WIRE_APIS,
        help=f"Codexが叩くエンドポイント。省略時は保存済み設定、初回は{DEFAULT_WIRE_API}",
    )
    args = parser.parse_args(argv)
    try:
        project = project_directory(args.project)
        runtime = runtime_directory(project)
        # 保存済みのCodex設定を「前回の選択」として引き継ぐ。コンテキスト長と
        # モデルは別々に指定できるので、片方だけ渡した回でももう片方は保たれる。
        saved = runtime / "codex/config.toml"
        config = tomllib.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {}
        context_size = args.context_size
        if context_size is None:
            context_size = config.get("model_context_window", 65536)
        model = args.model
        if model is None:
            model = config.get("model", DEFAULT_MODEL)
        wire_api = args.wire_api
        if wire_api is None:
            # プロバイダ名は設定側が決めるので、model_provider から引く。
            provider = config.get("model_providers", {}).get(
                config.get("model_provider", ""), {}
            )
            wire_api = provider.get("wire_api", DEFAULT_WIRE_API)
        settings = load_settings(project, context_size, model, wire_api)
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
                # 次に試す値は並びから引く。具体値を書くと、選べる値を増やした
                # ときに案内がずれる（131072 を足すまで、ここは 32768 固定だった）。
                smaller = smaller_context_size(settings.context_size)
                hint = (
                    f"--context-size {smaller}で再設定・検証してください。"
                    if smaller
                    else "これ以上小さい対応値がありません。モデルを小さくするか、"
                    "同じGPUを使う他の処理を止めてください。"
                )
                raise AgentError(f"モデルの一部がCPUへ配置されています。{hint}")
            result = {"gpu": gpu, "tools": client.probe_tools()}
        else:
            find_codex_executable()
            if not args.setup:
                client.inspect()
            result = prepare_environment(project, runtime, settings, find_superpowers())
            if not args.setup:
                launch_vscode(project, runtime, settings)
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
