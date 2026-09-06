---
name: finishing-a-development-branch
description: 実装が完了し、すべてのテストに合格し、作業を統合する方法を決定する必要がある場合に使用します。
---

# 開発ブランチの終了

## 概要

**中心原則:** テストを検証する → 環境を検出する → オプションを提示する → 選択を実行する → クリーンアップする。

**開始時にアナウンスします:** 「この作業を完了するために、開発ブランチの終了スキルを使用しています。」

## ステップ 1: テストの検証

プロジェクトの完全なテスト スイートを実行します (`npm test` / `cargo test` / `pytest` / `go test ./...`）。

**テストが失敗した場合**、失敗を報告して停止します。メニューは緑色のスイートの後に表示されます。

```
Tests failing (<N> failures). Must fix before completing:

[Show failures]
```

**テストに合格した場合:** ステップ 2 に進みます。

## ステップ 2: 環境の検出

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
# Capture now, while still inside the workspace — Step 5 changes directory
# before cleanup (Step 6) needs this value
WORKTREE_PATH=$(git rev-parse --show-toplevel)
```

これにより、表示するメニューとクリーンアップの仕組みが決まります。

|状態 |メニュー |クリーンアップ |
|------|------|-----------|
| `GIT_DIR == GIT_COMMON` (通常のリポジトリ) |標準 3 オプション |クリーンアップするワークツリーがありません |
| `GIT_DIR != GIT_COMMON`、名前付きブランチ |標準 3 オプション |出所ベース (ステップ 6 を参照) |
| `GIT_DIR != GIT_COMMON`、分離された HEAD | 2 つのオプションを削減 (マージなし) |外部管理 - そのままにする |

## ステップ 3: ベース ブランチを決定する

基本ブランチは、この作業が分岐したものです。通常は、
計画、会話、またはブランチの上流。まだそうなっていない場合
わかっている場合は、「このブランチは <あなたの最善の推測> から分岐しました - それは正しいですか?」と尋ねます。
マージする前に確認してください: 間違ったベースにマージすると、元に戻すのにコストがかかります。

## ステップ 4: オプションを提示する

**通常のリポジトリと名前付きブランチ ワークツリー — まさに次の 3 つのオプションが表示されます。**

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)

Which option?
```

**分離された HEAD — まさに次の 2 つのオプションを示します:**

```
Implementation complete. You're on a detached HEAD (externally managed workspace).

1. Push as new branch and create a Pull Request
2. Keep as-is (I'll handle it later)

Which option?
```

メニューを書かれたとおりに正確に提示します — 簡潔で、すべてのオプションが表示されます
上のリストから。作業の破棄は、あなたの要求に応じた場合にのみ行われます。
人間のパートナーが明示的にそれを要求している場合 (「人間のパートナーが要求した場合」を参照)
作品を破棄する」（以下）。彼らの答えを待ちます。統合の決定
彼らのものです。

## ステップ 5: 選択の実行

### オプション 1: ローカルでマージする

```bash
# Get main repo root for CWD safety
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"

# Merge first — verify success before removing anything
git checkout <base-branch>
git pull
git merge <feature-branch>

# Verify tests on merged result
<test command>
```

マージされた結果でテストが失敗した場合: 停止し、ワークツリーを離れて分岐します。
配置して調査します。何もプッシュされていないため、マージはローカルで行われます。
そして回復可能です。

マージ結果が緑色になったら、ワークツリーをクリーンアップし (ステップ 6)、
ブランチを削除します。

```bash
git branch -d <feature-branch>
```

### オプション 2: PR のプッシュと作成

```bash
git push -u origin <feature-branch>
# From a detached HEAD, name the new branch on the remote:
# git push origin HEAD:refs/heads/<new-branch>
```

次に、フォージの <base-branch> に対するプル/マージ リクエストを作成します。
ツール — CLI が利用可能な場合、またはほとんどが偽造する作成 URL
プッシュ時に印刷します。リポジトリの PR テンプレートと規則に従います。
を提示し、その URL を人間のパートナーに報告します。

ワークツリーを維持します。そこで人間のパートナーが PR フィードバックを繰り返します。

### オプション 3: 現状維持

レポート: 「ブランチ <名前> を維持します。ワークツリーは <パス> に保存されます。」

### 人間のパートナーが仕事を破棄するように要求した場合

このパスは、
離れて働く。最初に確認してください:

```
This will permanently delete:
- Branch <name>
- All commits: <commit-list>
- Worktree at <path>

Type 'discard' to confirm.
```

正確な確認をお待ちください。到着したら:

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
```

次に、ワークツリーをクリーンアップし (ステップ 6)、ブランチを強制削除します。

```bash
git branch -D <feature-branch>
```

## ステップ 6: ワークスペースをクリーンアップする

**オプション 1 で実行され、破棄が確認されました。** オプション 2 と 3 は常に
ワークツリーを保存します。両方の呼び出し元がすでにディレクトリを次の場所に変更しています。
メイン リポジトリ ルート — ワークツリーの削除はワークツリーの外部から実行する必要があります —
そして使用してください `GIT_DIR`/`GIT_COMMON`/`WORKTREE_PATH` で捕捉された値
ステップ 2、ディレクトリを変更する前から。

**もし `GIT_DIR == GIT_COMMON`:** 通常のリポジトリ。クリーンアップするワークツリーはありません。終わり。

**もし `WORKTREE_PATH` 下にあります `.worktrees/` または `worktrees/`:** 超大国
このワークツリーを作成しました — 私たちはクリーンアップを独自に行いました:

```bash
git worktree remove "$WORKTREE_PATH"
git worktree prune  # Self-healing: clean up any stale registrations
```

**削除が拒否された場合** (`contains modified or untracked files`):
ワークツリーには、他には存在しないファイル (コミットされていない計画、メモ、
またはスクラッチ作業。一度もない `--force` あなた自身のイニシアチブで。自分の人間性を見せてください
何が問題になっているのかをパートナーに伝え、次のように尋ねます。

```bash
git -C "$WORKTREE_PATH" status --porcelain -uall
```

```
Worktree removal refused — these files were never committed:

<file list>

1. Commit them to <branch> before cleanup
2. Move them into <main repo root>
3. Delete them (unrecoverable)

Which?
```

選択を実行してから、ワークツリーを削除します。

**それ以外の場合:** ホスト環境がこのワークスペースを所有します。そのままにしておきます。
場所。プラットフォームにワークスペース終了ツールが提供されている場合は、それを使用してください。

## クイックリファレンス

|オプション |マージ |プッシュ |ワークツリーを保持する |クリーンナップブランチ |
|------|------|------|---------------|--------------|
| 1. ローカルでマージ |はい | - | - |はい |
| 2. PR を作成 | - |はい |はい | - |
| 3. そのままにしておく | - | - |はい | - |
|破棄 (明示的なリクエストのみ) | - | - | - |はい (強制) |

## 一般的な合理化

|言い訳 |現実 |
|--------|--------|
| 「このセッション以前にテストに合格しました」 |統合しようとしているツリー上でスイートを実行します。緑の走りは、それが走った木を証明するだけです。 |
| 「彼らは明らかにそれを統合したいと考えています」 |統合はあなたの人間のパートナーの決定です。メニューを提示して待ちます。 |
| 「彼らはこの機能を使い終わったようです — 私はそれを破棄することを申し出ます。」メニューは書いてある通りに完成しました。人間のパートナーが非常に多くの言葉でそれを要求した場合にのみ、廃棄が発生します。 |
| 「『はい、処分してください』は確認としてカウントされます」 |入力した単語のみ `discard` 削除を許可します。 |
| 「PR が起動したため、ワークツリーが乱雑になりました」 | PR フィードバックはそのワークツリーで修正されます。作業が完了するまでそのままです。 |
| 「この他のワークツリーは古くなっているように見えます。これもクリーンアップします。」 |以下のワークツリーのみをクリーンアップします `.worktrees/` または `worktrees/`。それ以外はすべてホストに属します。 |
| 「削除は拒否されました — `--force` クリーンアップを終了したところです」 | 拒否は、ファイルがそのワークツリーにのみ存在することを意味します。 `--force` それらを永久に破壊します。人間のパートナーを見せて尋ねてください。 |
| "マージ結果の失敗はおそらく不安定です" |マージ結果が失敗すると、すべてが停止します。調査中、ブランチとワークツリーはそのまま残ります。 |
| "ベース ブランチは明らかに main です" |分岐点を確認するか、尋ねてください。間違ったベースにマージすると、元に戻すにはコストがかかります。 |
| 「プッシュは拒否されました - 強制プッシュで解決します」 |プッシュが拒否された場合は、リモコンが移動したことを意味します。調査する;人間のパートナーの明示的な要求にのみ強制プッシュします。 |
