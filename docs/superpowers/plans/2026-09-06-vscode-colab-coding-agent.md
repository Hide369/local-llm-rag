# VS Code Colab Coding Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** VS CodeのCodexサイドバーで、Colab L4のgpt-oss:20bとSuperpowersを使ってWindowsのコードを編集・検証できるようにする。

**Architecture:** Pythonの起動補助が既存.envを読み、Colab専用Codex設定とVS Codeユーザーデータを準備する。Ollamaへの接続診断と長文コンテキスト設定は独立モジュールにし、推論は既存の認証プロキシへ直接送る。Superpowersはローカルの単体スキルとして配置する。

**Tech Stack:** Python 3.13、既存requests/python-dotenv/pytest、Windows、VS Code Codex拡張、Ollama Responses API。

**Spec:** `docs/superpowers/specs/2026-09-06-vscode-colab-coding-agent-design.md`（ユーザーが2026-09-06に実行を承認）

## Global Constraints

- モデルは `gpt-oss:20b`。推論はColab L4、ツール実行はWindows。
- 作業ブランチは `feat/vscode-colab-agent`。既存venvと.envを使うため現在のチェックアウトで作業する。
- 実行時保存先は `%LOCALAPPDATA%/local-llm/coding-agent/`。
- APIキーを設定テンプレート、コマンド引数、診断ログへ出さない。
- 設定の適用先は専用Codex環境。同名の未管理ファイル・ジャンクションは上書きしない。
- 新しいPython依存は追加しない。通常テストはColab接続不要。
- 64k候補でGPU使用量を測定する。GPUに収まらなければ32kを実測し、採用理由を記録する。
- VS Code同梱Codex `0.153.0` とPATH上の `0.139.0` を区別する。
- 実装前の基準テストは391 passed、3 deselected。サンドボックス内のWinError 5を避け、通常ユーザー権限で実行して確認済み。

## Task 1: 接続設定・診断・コンテキストの設定

**Files:** Create `coding_agent/__init__.py`, `coding_agent/connection.py`, `tests/test_agent_connection.py`.

**Interfaces:**

```python
# connection.pyの公開インターフェース
class AgentError(RuntimeError): ...
@dataclass(frozen=True)
class AgentSettings:
    host: str
    api_key: str = field(repr=False)
    model: str = "gpt-oss:20b"
    context_size: int = 65536
def load_settings(project: Path, context_size: int = 65536) -> AgentSettings: ...
class OllamaClient:
    def __init__(self, settings: AgentSettings, session=None): ...
    def request(self, method: str, path: str, payload=None, timeout=(5, 60)) -> dict: ...
    def inspect(self) -> dict: ...
    def configure_context(self) -> dict: ...
    def restore_context(self) -> dict: ...
    def warmup(self) -> dict: ...
    def probe_tools(self) -> dict: ...
```

- [x] 先に設定と通信のテストを書く。未設定、不正URL、APIキーの改行、401、404、接続断、タイムアウト、JSON不正、想定外スキーマで秘密情報を含まないAgentErrorとなることを検証する。

```python
def test_missing_env_is_actionable(tmp_path):
    with pytest.raises(AgentError, match=".env"):
        load_settings(tmp_path)

def test_settings_hide_api_key():
    settings = AgentSettings("https://example.ngrok-free.app", "private-test-key")
    assert "private-test-key" not in repr(settings)
```

- [x] `python.exe -m pytest tests/test_agent_connection.py -q` を実行して未実装による失敗を確認。
- [x] `.env` を唯一の接続情報源とする。HTTPS、ホストあり、ユーザー情報・クエリ・フラグメントなし、パスは空か `/`、キーは空白・改行なしを検証。context_sizeは32768/65536のみ許可。
- [x] requestは認証ヘッダーを付け、リダイレクトを禁止し、タイムアウトを設ける。例外にはレスポンス本文やURLを埋め込まない。
- [x] inspectは `/api/version`、`/api/show`、`/api/ps` を確認し、モデル・tools対応・GPU配置を返す。
- [x] configure_contextは変更前モデルを `/api/copy` で `gpt-oss:20b-before-coding-agent` に初回だけ保存し、`/api/create` で同じgpt-oss:20bのnum_ctxを設定する。バックアップタグは上書きしない。元モデル名を維持する。
- [x] warmupは `/api/generate` に空プロンプト、num_ctx、keep_aliveを送り、`/api/ps` の実際のcontext_lengthとsize_vramを返す。
- [x] probe_toolsはResponsesのSSEを読み、テスト用関数 `get_probe_value` の呼び出しを受け、固定のテスト結果を返す次の推論まで確認する。外部コマンドは実行しない。失敗した場合はHTTP応答成功とツール成功を混同しない。
- [x] 応答の制御可能なテストダブルで各処理と通信契約を検証し、上記テストを再実行する。

## Task 2: 専用設定の生成とVS Code起動

**Files:** Create `coding_agent/environment.py`, `scripts/coding_agent.py`, `infra/codex-colab/config.toml.template`, `tests/test_agent_environment.py`; Modify `.gitignore`.

**Interfaces:** Task 1のAgentSettings/AgentError/OllamaClientを消費。

```python
def render_config(settings: AgentSettings) -> str: ...
def prepare_environment(project: Path, runtime: Path, settings: AgentSettings,
                        superpowers_source: Path) -> dict: ...
def launch_vscode(project: Path, runtime: Path, settings: AgentSettings) -> None: ...
```

- [x] 生成したTOMLをtomllibで読み、モデル・provider・/v1 URL・環境変数ヘッダー参照・contextが一致し、キーが含まれないテストを書く。
- [x] 一時フォルダ上で新規セットアップ、同設定の再実行、.env変更、未管理ファイルとの競合、既存スキルとの競合をテストする。
- [x] `python.exe -m pytest tests/test_agent_environment.py -q` で未実装の失敗を確認する。
- [x] templateは `wire_api = "responses"`、認証不要のカスタムprovider、`web_search = "disabled"`、workspace-write、on-request、contextと圧縮しきい値、shellへのキー継承除外を設定する。
- [x] runtimeに管理マーカーを置き、設定ファイルは一時ファイルから置換する。作業フォルダをマーカーへ記録して、別プロジェクトによる混用を拒否する。
- [x] Superpowers本体を版ごとコピーし、各スキルを`.agents/skills`直下へ個別のWindowsジャンクションとして配置する。既存の同一参照は再利用し、異なる参照は明示的に拒否する。
- [x] VS Codeは `--user-data-dir` と既存 `--extensions-dir` を明示する。子プロセス用envへCODEX_HOMEとOLLAMA_API_KEYを設定し、親プロセスの環境を書き換えない。実行中の専用ウィンドウへのキー更新は再起動が必要と案内する。
- [x] CLIは `--check`（診断のみ）、`--setup`（設定のみ）、`--configure-context`（Colabモデル設定）、`--restore-context`（元モデル設定へ復元）、`--probe`（推論検証）、既定（診断・設定・VS Code起動）を提供。contextは `--context-size 32768` で切り替え可能とする。
- [x] テストを再実行し、正常な起動要求の引数・envと秘密を含まないエラー出力を確認する。

## Task 3: Colabノートブックの再現性

**Files:** Modify `colab/run_ollama_server.ipynb`; Create `tests/test_colab_agent_notebook.py`.

**Interfaces:** 既存のOllama起動セルと認証プロキシを維持。Task 1とは独立した、Colabの新規起動時の設定。

- [x] ノートブックのコードセルを取り出し、外部プロセス起動と通信だけを置換して、ollama serveへコンテキスト65536と並列数1が渡ることをテストする。
- [x] テストを実行して現在セルの不足を確認する。
- [x] Ollama起動セルにコピーした環境を渡し、`OLLAMA_CONTEXT_LENGTH=65536`、`OLLAMA_NUM_PARALLEL=1` を設定する。ユーザーが32768へ変更できる定数を置く。
- [x] プロキシのキーをソースへ埋め込まず環境変数で渡す。HTTPクライアントにタイムアウトを設定し、切断・例外時もupstreamを閉じるようにする。許可ヘッダーの仕組みは維持する。
- [x] GPU確認セルに `ollama ps` と `nvidia-smi` の確認方法を追加し、先にモデルをロードしないと測定できないことを記す。
- [x] RAG説明内の古いモデル名と起動コマンドを現在の構成へ更新する。保存済みoutputs/execution_countを消して認証情報の再保存を避ける。
- [x] テストを再実行し、ノートブック形式とコードセル構文を検証する。

## Task 4: 実環境セットアップ・受け入れ・ドキュメント

**Files:** Modify `README.md`, spec, this plan; Create `AGENTS.md`, `docs/vscode-colab-agent.md`.

- [x] Task 1/2/3をレビューし、通常テスト一式を実行する。
- [x] 現在の.envで診断、Colabのコンテキスト設定、ウォームアップ、SSEツール往復を実行し、GPU使用量と所要時間を記録する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --check
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup
```

- [x] 同梱Codexのバックエンドで実効設定・スキル検出を確認し、検証フォルダで小さなPythonコードの読取→編集→テスト実行を確認する。実行履歴にツール呼び出しとテスト結果があることを確認する。
- [x] 専用VS Codeを開き、確認できる範囲でサイドバーを検証する。画面操作が未確認の場合はCLI/backend検証と区別して明記する。
- [x] 起動・再接続・停止・コンテキストを戻す方法・既知の制限をドキュメントへ記録する。
- [x] 新たな修正の影響範囲だけ再検証し、ブランチ全体をレビューする。承認済み範囲の変更をConventional Commit形式で保存する。共有ブランチへはpush/mergeしない。

## 実行記録

- 初期レビュー: Task 1の設定型をTask 2が消費。Task 3のサーバー起動設定とTask 1のモデル設定は同じcontext値を使用。Task 4が双方を実機検証する。
- Ruling: 現在のチェックアウトに作業ブランチを作成して進める。venv/.env/VS Codeで開く実パスを維持するため。
- Ruling: ユーザーの「計画通り進めてほしい」を実装と検証までの実行承認として扱い、途中で実行方式の再確認は求めない。
- 実機: Ollama 0.33.3、gpt-oss:20bのcompletion/tools/thinkingを確認。64k設定後は `context_length=65536`、`size=size_vram=12,971,640,094` バイトでL4へ全量配置。ロード済み状態の成功プローブは約9.7秒。
- 実機: Responses APIの関数呼び出しと結果返却を完了。同梱Codex 0.153.0のstrict configで専用モデルカタログを読み、`using-superpowers`読取、Python編集、指定pytestの `1 passed` をイベント履歴で確認。
- 互換性: Ollama 0.33.3はCodexのfreeform `apply_patch`呼び出しを互換形式で返さないため、専用カタログから同ツールを外し、PowerShell編集を明示した。不要なリモートプラグイン同期も無効化した。
- 検証: 対象テスト65件、通常スイート456件（integration 3件は選択外）が成功。VS Code画面上のサイドバー確認だけは起動後に人が確認する。
- UI: 専用ユーザーデータとCODEX_HOMEを渡したVS Codeウィンドウを機能ブランチのworktreeで起動。GUI内のサイドバー表示と対話操作は自動検証対象外のため、ユーザーの目視確認を残す。
