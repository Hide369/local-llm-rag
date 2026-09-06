# Hermes エージェント ツールのマッピング

スキルはアクションで話します (「サブエージェントを派遣する」、「ToDo を作成する」、「ファイルを読み取る」)。 Hermes Agent では、これらは以下のツールに解決されます。

## ツール

|アクションスキルリクエスト |エルメスのツール |
|---|---|
|ファイルを読む | `read_file` |
|新しいファイルを作成する | `write_file` |
|ファイルを編集する (対象パッチ) | `patch` |
|シェルコマンドを実行する | `terminal` |
|ファイルの内容を検索 | `search_files` |
|ファイルを名前で検索 | `terminal` と `find` |
| URL を取得する / Web ページを読み取る | `web_extract(urls=[...])` |
|ウェブを検索 | `web_search(query=...)` |
|代理人を派遣する | `delegate_task(goal=..., context=..., toolsets=[...], role="leaf")` |
|タスクの追跡 | `todo` ツール |
|スキルを発動する | `skill_view("skill-name")` |

## 指示ファイル

スキルが「指示ファイル」に言及する場合、Hermes Agent ではこれは **`AGENTS.md`** プロジェクト ディレクトリ内、または **`SOUL.md`** 世界中で `~/.hermes/SOUL.md`。

## スキルの発動

ヘルメスエージェントには、 `skills` ツールセット付き `skill_view` そして `skills_list` ツール。
スーパーパワーのスキルを呼び出すには、次を使用します。

```
skill_view("brainstorming")
skill_view("test-driven-development")
```

もし `skill_view` 超能力スキルが見つかりません (カタログに載っていない可能性があります)
プラグインが完全に登録するまで)、SKILL.md を直接読み取るようにフォールバックします。

```
read_file(path="~/.hermes/plugins/superpowers/skills/<skill-name>/SKILL.md")
```

このフォールバックは、ネイティブ スキルの読み込みを行わない他のハーネスで使用されるのと同じメカニズムです。

## サブエージェントのディスパッチ

使用する `delegate_task` 並列または順次のワークストリーム用に分離されたサブエージェントを生成するには、次のようにします。

```
delegate_task(goal="...", context="...", toolsets=[...], role="leaf")
```

もし `delegate_task` が使用できない場合は、ツール呼び出しを作成するのではなく、作業をインラインで実行します。

## タスクの追跡

を使用します。 `todo` セッション内のタスクを追跡するためのツール。マルチエージェントタスクボードの場合は、次を使用します。 `hermes kanban` 利用可能な場合は CLI。高齢者を治療する `TodoWrite` タスク追跡アクションとして参照します。
