---
name: writing-plans
description: コードに触れる前に、複数ステップのタスクの仕様または要件がある場合に使用します。
---

# 計画を書く

## 概要

エンジニアがコードベースに関するコンテキストがなく、好みが疑わしいと仮定して、包括的な実装計画を作成します。各タスク、コード、テストでどのファイルにアクセスするか、確認する必要がある可能性のあるドキュメント、テスト方法など、知っておくべきことをすべて文書化します。計画全体を一口サイズのタスクとして与えます。ドライ。ヤグニ。 TDD。頻繁なコミット。

彼らは熟練した開発者だが、私たちのツールセットや問題領域についてはほとんど何も知らないと仮定します。彼らは良いテスト設計についてよく知らないと仮定します。

**開始時にアナウンスします:** 「計画作成スキルを使用して実装計画を作成しています。」

**コンテキスト:** 分離されたワークツリーで作業している場合は、 `superpowers:using-git-worktrees` 実行時のスキル。

**計画の保存先:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- (計画の場所に関するユーザー設定は、このデフォルトを上書きします)

## スコープチェック

仕様が複数の独立したサブシステムをカバーしている場合は、ブレインストーミング中にサブプロジェクト仕様に分割する必要があります。そうでない場合は、これを個別の計画 (サブシステムごとに 1 つ) に分割することを提案します。各計画は、それ自体で動作するテスト可能なソフトウェアを作成する必要があります。

## ファイル構造

タスクを定義する前に、どのファイルが作成または変更されるのか、またそれぞれのファイルが何を担当するのかを計画します。ここで、分解の決定が固定化されます。

- 明確な境界と明確に定義されたインターフェイスを持つユニットを設計します。各ファイルには 1 つの明確な責任がある必要があります。
- コンテキスト内で一度に保持できるコードについて最も適切な推論が可能であり、ファイルがフォーカスされている場合、編集の信頼性が高くなります。機能が多すぎる大きなファイルよりも、小規模で焦点を絞ったファイルを優先します。
- 一緒に変更されるファイルは一緒に存在する必要があります。技術層ごとではなく、責任ごとに分割します。
- 既存のコードベースでは、確立されたパターンに従います。コードベースで大きなファイルが使用されている場合は、一方的に再構築しないでください。ただし、変更しているファイルが扱いにくくなった場合は、計画に分割を含めるのが合理的です。

この構造はタスクの分解を示します。各タスクは、独立して意味のある自己完結型の変更を生成する必要があります。

## タスクの適切なサイズ設定

タスクは、独自のテスト サイクルを実行する最小単位であり、1 つのタスクに値します。
フレッシュレビュアーの門。タスクの境界線を描くとき: セットアップを折り、
構成、足場、文書化がタスクに組み込まれます。
成果物にはそれらが必要です。査読者が有意義にできる場合のみ分割する
1 つのタスクを拒否し、その隣のタスクを承認します。各タスクは次のように終了します。
独立してテスト可能な成果物。

## ひとくちサイズのタスク粒度

**各ステップは 1 つのアクションです (2 ～ 5 分):**
- 「失敗したテストを作成する」 - ステップ
- 「実行して失敗することを確認する」 - ステップ
- 「テストに合格するために最小限のコードを実装する」 - ステップ
- 「テストを実行し、テストが合格することを確認する」 - ステップ
- 「コミット」 - ステップ

## 計画ドキュメントのヘッダー

**すべてのプランは次のヘッダーで開始する必要があります:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Spec:** [path to the spec/design doc this plan implements — the plan
argues from the spec, so the spec travels with it; executors read both]

## Global Constraints

[The spec's project-wide requirements — version floors, dependency limits,
naming and copy rules, platform requirements — one line each, with exact
values copied verbatim from the spec. Every task's requirements implicitly
include this section.]

---
```

## タスク構造

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact function names, parameter
  and return types. A task's implementer sees only their own task; this
  block is how they learn the names and types neighboring tasks use.]

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## プレースホルダーなし

すべてのステップには、エンジニアが必要とする実際のコンテンツが含まれている必要があります。これらは**計画の失敗**です。決して書かないでください。
- 「未定」、「TODO」、「後で実装」、「詳細を入力」
- 「適切なエラー処理を追加する」 / 「検証を追加する」 / 「エッジケースを処理する」
- 「上記のテストを書く」(実際のテストコードなし)
- 「タスク N と同様」 (コードを繰り返します - エンジニアがタスクを順番どおりに読んでいない可能性があります)
- 方法を示さずに何を行うかを説明するステップ (コードステップに必要なコードブロック)
- どのタスクにも定義されていない型、関数、またはメソッドへの参照

## 自己レビュー

完全な計画を作成した後、新しい目で仕様を確認し、計画と照らし合わせて確認してください。これはあなた自身が実行するチェックリストであり、サブエージェントの派遣ではありません。

**1.仕様の範囲:** 仕様の各セクション/要件をざっと読んでください。それを実装するタスクを教えていただけますか?ギャップがある場合はリストします。

**2.プレースホルダー スキャン:** 計画に危険信号がないか検索します。上記の「プレースホルダーなし」セクションのパターンのいずれかです。修正してください。

**3.型の一貫性:** 後のタスクで使用した型、メソッド シグネチャ、およびプロパティ名は、前のタスクで定義したものと一致していますか?という関数 `clearLayers()` タスク 3 ですが、 `clearFullLayers()` タスク 7 はバグです。

問題が見つかった場合は、インラインで修正します。再レビューする必要はありません。修正して先に進むだけです。タスクのない仕様要件を見つけた場合は、タスクを追加します。

## 実行ハンドオフ

計画を保存した後、実行の選択肢を提供します。

**「計画が完了し、次の場所に保存されました」 `docs/superpowers/plans/<filename>.md`。 2 つの実行オプション:**

**1.サブエージェント駆動 (推奨)** - タスクごとに新しいサブエージェントをディスパッチし、タスク間でレビューし、高速に繰り返します

**2.インライン実行** - 実行プラン、チェックポイントを使用したバッチ実行を使用して、このセッションでタスクを実行します。

**どのアプローチですか?**

**サブエージェント駆動を選択した場合:**
- **必須サブスキル:** スーパーパワーを使用する:サブエージェント駆動開発
- タスクごとの新しいサブエージェント + 2 段階のレビュー

**インライン実行を選択した場合:**
- **必須サブスキル:** スーパーパワーを使用する:計画の実行
- レビュー用のチェックポイントを含むバッチ実行
