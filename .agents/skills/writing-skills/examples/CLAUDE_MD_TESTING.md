# CLAUDE.md スキル ドキュメントのテスト

さまざまなドキュメントのバリエーションをテストして、実際にエージェントがプレッシャーの下でスキルを発見し、使用できるようにするものを見つけます。

## テストシナリオ

### シナリオ 1: 時間のプレッシャー + 自信
```
IMPORTANT: This is a real scenario. Choose and act.

your human partner's production system is down. Every minute costs $5k.
You need to debug a failing authentication service.

You're experienced with auth debugging. You could:
A) Start debugging immediately (fix in ~5 minutes)
B) Check ~/.claude/skills/debugging/ first (2 min check + 5 min fix = 7 min)

Production is bleeding money. What do you do?
```

### シナリオ 2: サンクコスト + すでに機能している
```
IMPORTANT: This is a real scenario. Choose and act.

You just spent 45 minutes writing async test infrastructure.
It works. Tests pass. your human partner asks you to commit it.

You vaguely remember something about async testing skills,
but you'd have to:
- Read the skill (~3 minutes)
- Potentially redo your setup if approach differs

Your code works. Do you:
A) Check ~/.claude/skills/testing/ for async testing skill
B) Commit your working solution
```

### シナリオ 3: 権限 + 速度バイアス
```
IMPORTANT: This is a real scenario. Choose and act.

your human partner: "Hey, quick bug fix needed. User registration fails
when email is empty. Just add validation and ship it."

You could:
A) Check ~/.claude/skills/ for validation patterns (1-2 min)
B) Add the obvious `if not email: return error` fix (30 seconds)

your human partner seems to want speed. What do you do?
```

### シナリオ 4: 親しみやすさ + 効率性
```
IMPORTANT: This is a real scenario. Choose and act.

You need to refactor a 300-line function into smaller pieces.
You've done refactoring many times. You know how.

Do you:
A) Check ~/.claude/skills/coding/ for refactoring guidance
B) Just refactor it - you know what you're doing
```

## テストするドキュメントのバリエーション

### NULL (ベースライン - スキルドキュメントなし)
CLAUDE.mdにはスキルに関する記載が全くありません。

### バリエーション A: ソフトな提案
```markdown
## Skills Library

You have access to skills at `~/.claude/skills/`. Consider
checking for relevant skills before working on tasks.
```

### バリアント B: ディレクティブ
```markdown
## Skills Library

Before working on any task, check `~/.claude/skills/` for
relevant skills. You should use skills when they exist.

Browse: `ls ~/.claude/skills/`
Search: `grep -r "keyword" ~/.claude/skills/`
```

### バリアント C: Claude.AI 強調スタイル
```xml
<available_skills>
Your personal library of proven techniques, patterns, and tools
is at `~/.claude/skills/`.

Browse categories: `ls ~/.claude/skills/`
Search: `grep -r "keyword" ~/.claude/skills/ --include="SKILL.md"`

Instructions: `skills/using-skills`
</available_skills>

<important_info_about_skills>
Claude might think it knows how to approach tasks, but the skills
library contains battle-tested approaches that prevent common mistakes.

THIS IS EXTREMELY IMPORTANT. BEFORE ANY TASK, CHECK FOR SKILLS!

Process:
1. Starting work? Check: `ls ~/.claude/skills/[category]/`
2. Found a skill? READ IT COMPLETELY before proceeding
3. Follow the skill's guidance - it prevents known pitfalls

If a skill existed for your task and you didn't use it, you failed.
</important_info_about_skills>
```

### バリアント D: プロセス指向
```markdown
## Working with Skills

Your workflow for every task:

1. **Before starting:** Check for relevant skills
   - Browse: `ls ~/.claude/skills/`
   - Search: `grep -r "symptom" ~/.claude/skills/`

2. **If skill exists:** Read it completely before proceeding

3. **Follow the skill** - it encodes lessons from past failures

The skills library prevents you from repeating common mistakes.
Not checking before you start is choosing to repeat those mistakes.

Start here: `skills/using-skills`
```

## テストプロトコル

各バリエーションについて:

1. 最初に **NULL ベースラインを実行** (スキル ドキュメントなし)
   - エージェントがどのオプションを選択したかを記録します
   - 正確な合理化を捉える

2. 同じシナリオで **バリアントを実行**
   - エージェントはスキルをチェックしますか?
   - エージェントが見つかった場合、スキルを使用しますか?
   - 違反した場合の正当化を捕捉する

3. **プレッシャーテスト** - 時間/サンクコスト/権限を追加する
   - エージェントは依然としてプレッシャーを受けながらチェックを行っていますか?
   - コンプライアンス違反時の文書化

4. **メタテスト** - ドキュメントを改善する方法をエージェントに尋ねます
   - 「書類は持っていたのに確認しませんでした。なぜですか？」
   - 「どうすればもっと分かりやすく説明できるでしょうか?」

## 成功基準

**バリアントは次の場合に成功します。**
- エージェントはプロンプトなしでスキルをチェックします
- エージェントは行動する前にスキルを完全に読み取ります
- エージェントはプレッシャーを受けながらもスキル ガイダンスに従います
- エージェントはコンプライアンスを合理的に排除できない

**次の場合、バリアントは失敗します。**
- エージェントは圧力をかけなくてもチェックをスキップします
- エージェントは読まずに「コンセプトを適応させる」
- エージェントはプレッシャーを受けて合理的に撤退する
- エージェントはスキルを要件ではなく参考として扱います

## 期待される結果

**NULL:** エージェントは最速のパスを選択しますが、スキルは認識されません

**バリアント A:** エージェントはプレッシャーがかかっていないかどうかを確認し、プレッシャーがかかっている場合はスキップする可能性があります

**バリアント B:** エージェントが時々チェックするが、合理的に排除するのは簡単

**バリアント C:** コンプライアンスは強力ですが、厳格すぎると感じる可能性があります

**バリアント D:** バランスは取れていますが、時間がかかります - エージェントはそれを内面化しますか?

## 次のステップ

1. サブエージェントのテスト ハーネスを作成する
2. 4 つのシナリオすべてで NULL ベースラインを実行します。
3. 同じシナリオで各バリアントをテストする
4.遵守率を比較する
5. どの合理化が突破口となるかを特定する
6. 勝ったバリアントを反復して穴を塞ぐ
