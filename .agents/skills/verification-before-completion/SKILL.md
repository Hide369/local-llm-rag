---
name: verification-before-completion
description: PR をコミットまたは作成する前に、作業が完了、修正、または合格したと主張しようとしているときに使用します。成功したと主張する前に、検証コマンドを実行して出力を確認する必要があります。主張の前に常に証拠
---

# 完了前の検証

## 概要

**基本原則:** 主張の前に必ず証拠を。

**このルールの条文に違反することは、このルールの精神に違反することになります。**

## 鉄の法則

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

このメッセージにある検証コマンドを実行していない場合、コマンドが成功したとは言えません。

## ゲート機能

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## よくある失敗

|クレーム |必要なもの |不十分 |
|------|----------|-----|
|テストに合格しました |テスト コマンド出力: 0 失敗 |前回の実行、「合格するはず」 |
|リンタークリーン |リンター出力: エラー 0 |部分チェック、外挿 |
|ビルドは成功しました |ビルドコマンド: exit 0 |リンターの通過、ログは良好です |
|バグ修正 |元の症状をテスト: 合格 |コードが変更されました。修正されたと想定されます |
|回帰テストは機能します |赤と緑のサイクルが検証されました |テストは 1 回合格します |
|エージェントが完了しました | VCS diff は変更を示します |エージェントは「成功」を報告します。
|要件を満たしました |行ごとのチェックリスト |テストに合格 |

## 赤旗 - 停止

- 「すべき」、「おそらく」、「ようだ」の使用
- 検証前の満足感の表現 (「素晴らしい!」、「完璧!」、「完了!」など)
- 検証せずにコミット/プッシュ/PR しようとしています
- 信頼できるエージェントの成功レポート
- 部分的な検証に依存する
・「一度だけ」と思って
- 疲れていて仕事を終えたい
- **検証を実行せずに成功を示唆する文言**

## 合理化の防止

|言い訳 |現実 |
|--------|--------|
| 「今すぐ動作するはずです」 |検証を実行する |
| 「自信があります」 |自信≠証拠 |
| 「一度だけ」 |例外はありません |
| "リンターが合格しました" |リンター ≠ コンパイラー |
| 「エージェントは成功と言った」 |個別に検証する |
| 「疲れた」 |疲れ≠言い訳 |
| 「部分的なチェックで十分です」 |部分的では何も証明されない |
| 「単語が異なるためルールは適用されません」 |文字よりも精神 |

## キーパターン

**テスト:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**回帰テスト (TDD Red-Green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**建てる：**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**要件：**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**エージェントの委任:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## いつ適用するか

**常に前に:**
- 成功/完了のクレームのあらゆるバリエーション
- あらゆる満足の表現
- 仕事の状態についての肯定的な発言
- コミット、PR 作成、タスクの完了
- 次のタスクに進む
- エージェントに委任する

**ルールは以下に適用されます:**
- 正確なフレーズ
- 言い換えと類義語
- 成功の意味
- 完了/正確性を示唆するあらゆるコミュニケーション
