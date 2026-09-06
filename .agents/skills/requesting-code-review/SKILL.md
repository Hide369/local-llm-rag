---
name: requesting-code-review
description: タスクを完了するとき、主要な機能を実装するとき、または作業が要件を満たしていることを確認するためにマージする前に使用します。
---

# コードレビューのリクエスト

コードレビュー担当者のサブエージェントを派遣して、問題が連鎖する前に問題を発見します。レビュー担当者は、セッションの履歴ではなく、評価用に正確に作成されたコンテキストを取得します。

**基本原則:** 早めに見直し、頻繁に見直してください。

## レビューをリクエストする場合

**必須:**
- サブエージェント駆動開発の各タスクの後
- 主要な機能を完了した後
- メインにマージする前

**オプションですが価値があります:**
- 行き詰まったとき（新鮮な視点）
- リファクタリング前（ベースラインチェック）
- 複雑なバグを修正した後

## リクエスト方法

**1. git SHA を取得します:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2.コードレビュー担当者のサブエージェントを派遣します:**

を派遣する `general-purpose` サブエージェント、[code-reviewer.md](code-reviewer.md) のテンプレートに記入します

**プレースホルダー:**
- `{DESCRIPTION}` - 構築したものの簡単な概要
- `{PLAN_OR_REQUIREMENTS}` - 何をすべきか
- `{BASE_SHA}` - コミットの開始
- `{HEAD_SHA}` - コミットの終了

**3.フィードバックに基づいて行動する:**
- 重大な問題をすぐに修正する
- 続行する前に重要な問題を修正してください
- 細かい問題については後でメモします
- 査読者が間違っている場合は反論します（理由を添えて）

## 例

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code reviewer subagent]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from docs/superpowers/plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## 一般的な合理化

|言い訳 |現実 |
|--------|--------|
| 「レビュアーを派遣するのではなく、自分で差分をレビューします。」 |あなたはコーディネーターです。インラインで diff を確認すると、作業を進めるために必要なコンテキスト ウィンドウが消費されます。レビュー担当者サブエージェントを派遣します。差分と評価はそのコンテキスト内に存在し、結果だけが戻ってきます。 |
| 「レビュー担当者が変更を理解するには、私のセッション履歴全体が必要です。」 |セッションの履歴ではなく、正確に作成されたコンテキストを渡します。これにより、レビュー担当者はあなたの思考プロセスではなく成果物に集中することができます。 |

## 赤旗

**決してしないでください:**
- 「簡単だから」レビューはスキップ
- 重大な問題を無視する
- 未修正の重要な問題を続行します
- 有効な技術的フィードバックで議論する

**査読者が間違っている場合:**
- 技術的な推論で押し返す
- 機能することを証明するコード/テストを表示する
- 説明の要求

テンプレートは [code-reviewer.md](code-reviewer.md) を参照してください。
