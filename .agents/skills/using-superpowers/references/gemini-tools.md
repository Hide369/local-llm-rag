# Gemini CLI ツールのマッピング

スキルはアクションで話します (「サブエージェントを派遣する」、「ToDo を作成する」、「ファイルを読み取る」)。 Gemini CLI では、これらは以下のツールに解決されます。

|アクションスキルリクエスト | Gemini CLI と同等 |
|---------------------|---------------------|
|ファイルを読む | `read_file` |
|複数のファイルを一度に読み取る | `read_many_files` |
|新しいファイルを作成する | `write_file` |
|ファイルを編集する | `replace` |
|シェルコマンドを実行する | `run_shell_command` |
|ファイルの内容を検索 | `grep_search` |
|ファイルを名前で検索 | `glob` |
|ファイルとサブディレクトリをリストする | `list_directory` |
| URL を取得する | `web_fetch` |
|ウェブを検索 | `google_web_search` |
|スキルを発動する | `activate_skill` |
|代理人を派遣する（`Subagent (general-purpose):` テンプレート) | `invoke_agent` と `agent_name: "generalist"` (経由で呼び出し可能 `@generalist` チャット構文 — [Subagent support](#subagent-support)) を参照してください。
|複数の並列ディスパッチ |複数 `invoke_agent` 同じ応答内の呼び出し |
|タスク追跡 (「ToDo を作成」、「完了としてマーク」) | `write_todos` (ステータス: 保留中、進行中、完了、キャンセル、ブロック) |

## 指示ファイル

スキルで「指示ファイル」が言及されている場合、Gemini CLI ではこれは **`GEMINI.md`**。 Gemini CLI のロード `GEMINI.md` 階層的に: グローバルで `~/.gemini/GEMINI.md`、ワークスペース ディレクトリとその先祖、およびサブディレクトリ内のプロジェクト レベルのファイル `GEMINI.md` ツールがそれらのディレクトリ内のファイルにアクセスするときに、ファイルが削除されます。

## 個人スキル ディレクトリ

ユーザーレベルのスキルは ** にあります`~/.gemini/skills/`**、 と **`~/.agents/skills/`** クロスランタイムエイリアスとして (Codex および Copilot CLI と共有)。両方のディレクトリが同じスコープに存在する場合、 `.agents/skills/` が優先されます。各スキルは、 `SKILL.md` （と `name` そして `description` 前題）。

## サブエージェントのサポート

Gemini CLI は、 `invoke_agent` ツール、これには `agent_name` そして `prompt` パラメータ。同じディスパッチは、チャット構文のショートカットとしても表示されます。 `@generalist <prompt>` を呼び出すのと同じです `invoke_agent` と `agent_name: "generalist"`。組み込みエージェント名には次のものがあります。 `generalist`、 `cli_help`、 `codebase_investigator`、および (ブラウザツールが有効な場合) `browser_agent`。

スキル派遣 `Subagent (general-purpose):` プロンプト テンプレート ファイルを参照するか (例: `superpowers:subagent-driven-development`さんの `./implementer-prompt.md`) またはインライン プロンプトを提供します。 Gemini CLI の場合:

|スキル派遣フォーム | Gemini CLI と同等 |
|---------------------|---------------------|
|参考文献 `*-prompt.md` テンプレート (実装者、タスクレビュー者、コードレビュー者など) |テンプレートに記入してから、 `invoke_agent` と `agent_name: "generalist"` そして入力されたプロンプト |
|参考文献 `superpowers:requesting-code-review`さんの `./code-reviewer.md` | `invoke_agent` と `agent_name: "generalist"` および記入されたレビュー テンプレート |
|インライン プロンプト (テンプレートは参照されません) | `invoke_agent` と `agent_name: "generalist"` とインラインプロンプト |

### 迅速な記入

スキルは、次のようなプレースホルダーを含むプロンプト テンプレートを提供します。 `{WHAT_WAS_IMPLEMENTED}` または `[FULL TEXT of task]`。完全なプロンプトを渡す前に、すべてのプレースホルダーを入力してください。 `invoke_agent`。プロンプト テンプレート自体には、エージェントの役割、レビュー基準、および予期される出力形式が含まれており、サブエージェントはこれに従います。

### 並行ディスパッチ

Gemini CLI は、並列サブエージェント ディスパッチをサポートしています。複数発行 `invoke_agent` 同じ応答内での呼び出し (または複数の呼び出し) `@generalist` 1 つのプロンプトで呼び出し)、独立したサブエージェントの作業を並行して実行します。依存タスクは連続的に保ちますが、単純な履歴を保存するためだけに独立したサブエージェント タスクを連続化しないでください。

## 追加の Gemini CLI ツール

これらのツールは Gemini CLI に固有です。

|ツール |目的 |
|-----|----------|
| `save_memory` (レガシー) |次の場合にセッション間でファクトを保持する `experimental.memoryV2 = false` |
| `get_internal_docs` | Gemini CLI のバンドルされたドキュメントを参照してください。
| `ask_user` |ユーザーに構造化された質問を投げかける (テキスト / 単一選択 / 複数選択) |
| `enter_plan_mode` / `exit_plan_mode` |読み取り専用プラン モードへの切り替え | 読み取り専用プラン モードの切り替え |
| `update_topic` |現在の会話のトピック/戦略的意図のメタデータを更新します。
| `complete_task` | Gemini サブエージェントが完了したことを通知し、その結果を親エージェントに返します。
| `tracker_create_task`、 `tracker_update_task`、 `tracker_get_task`、 `tracker_list_tasks`、 `tracker_add_dependency`、 `tracker_visualize` |依存関係と視覚化をサポートする豊富なタスク トラッカー |
| `read_mcp_resource`、 `list_mcp_resources` | MCP リソース アクセス |
