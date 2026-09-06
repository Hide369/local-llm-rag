# 反重力 CLI (`agy`) ツールマッピング

スキルはアクションで話します (「サブエージェントを派遣する」、「ToDo を作成する」、「ファイルを読み取る」)。 Antigravity CLI (`agy`) これらは以下のツールで解決されます。

|アクションスキルリクエスト |反重力 CLI と同等 |
|---------------------|---------------------|
|代理人を派遣する（`Subagent (general-purpose):` テンプレート) | `invoke_subagent` 内蔵の `TypeName` — `self` 全力で仕事をするために、 `research` 読み取り専用 |
|タスク追跡 (「ToDo を作成」、「完了としてマーク」) | **タスク成果物** — `write_to_file` と `IsArtifact: true` そして `ArtifactType: "task"` ([タスク追跡](#task-tracking)を参照)。 **ない** `manage_task`、バックグラウンドプロセスを管理します。 |

## タスクの追跡

Antigravity には **ToDo ツールがありません** (`manage_task` 背景を管理する
プロセス — `list`/`kill`/`status`/`send_input` — これはチェックリストではありません)。とき
スキルは、ToDo リストを作成するかタスクを追跡し、**タスク アーティファクト**を維持するように指示します。
で保存されたマークダウン チェックリスト `write_to_file` (`IsArtifact: true`、
`ArtifactMetadata.ArtifactType: "task"`)、編集済み `replace_file_content` /
`multi_replace_file_content` 進むにつれて。

複数ステップのタスクの開始時に、タスクの各ステップをリストするタスク成果物を作成します。
あなたの計画。各ステップを完了したら、アーティファクトを編集して完了のマークを付けます(`- [x]`）。
計画が変更された場合は、チェックリストを更新します。最新の情報を維持してください — それはあなたの情報源です
残るものの真実。会話が長くなったら、始める前にもう一度読んでください
それぞれのステップ。
