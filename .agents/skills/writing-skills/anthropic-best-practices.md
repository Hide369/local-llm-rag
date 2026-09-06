# スキルオーサリングのベストプラクティス

> エージェントが見つけてうまく使用できる効果的なスキルを作成する方法を学びます。

優れたスキルは簡潔で、よく構造化されており、実際の使用法でテストされています。このガイドでは、エージェントが発見して効果的に使用できるスキルを作成するのに役立つ、実際的な作成上の決定事項を提供します。

スキルの仕組みに関する概念的な背景については、[スキルの概要](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) を参照してください。

## 基本原則

### 簡潔さが重要です

[コンテキスト ウィンドウ](https://platform.claude.com/docs/en/build-with-claude/context-windows) は公共財です。スキルは、エージェントが知る必要があるその他すべてのものとコンテキスト ウィンドウを共有します。これには次のものが含まれます。

* システムプロンプト
*会話履歴
* その他のスキルのメタデータ
*実際のリクエスト

スキル内のすべてのトークンに即時コストがあるわけではありません。起動時に、すべてのスキルのメタデータ (名前と説明) のみがプリロードされます。エージェントは、スキルが関連する場合にのみ SKILL.md を読み取り、必要に応じてのみ追加ファイルを読み取ります。ただし、SKILL.md で簡潔であることは依然として重要です。エージェントが SKILL.md を読み込むと、すべてのトークンが会話履歴やその他のコンテキストと競合します。

**デフォルトの仮定**: エージェントはすでに非常に賢いです

エージェントがまだ持っていないコンテキストのみを追加します。それぞれの情報に挑戦してください。

* 「エージェントは本当にこの説明が必要ですか?」
* 「エージェントはこのことを知っていると考えてよいでしょうか?」
* 「この段落はトークンコストを正当化しますか?」

**良い例: 簡潔** (約 50 トークン):

````markdown  theme={null}
## Extract PDF text

Use pdfplumber for text extraction:

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
````

**悪い例: 冗長すぎる** (約 150 トークン):

```markdown  theme={null}
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. There are many libraries available for PDF processing, but we
recommend pdfplumber because it's easy to use and handles most cases well.
First, you'll need to install it using pip. Then you can use the code below...
```

簡易バージョンでは、エージェントが PDF とは何か、ライブラリがどのように機能するかを知っていることを前提としています。

### 適切な自由度を設定する

タスクの脆弱性と変動性に合わせて具体性のレベルを調整します。

**高い自由度** (テキストベースの指示):

次の場合に使用します。

* 複数のアプローチが有効です
* 決定は状況に応じて異なります
* ヒューリスティックがアプローチをガイドします

例:

```markdown  theme={null}
## Code review process

1. Analyze the code structure and organization
2. Check for potential bugs or edge cases
3. Suggest improvements for readability and maintainability
4. Verify adherence to project conventions
```

**中程度の自由度** (疑似コードまたはパラメーター付きスクリプト):

次の場合に使用します。

※優先パターンあり
* 多少の変動は許容されます
* 設定は動作に影響します

例:

````markdown  theme={null}
## Generate report

Use this template and customize as needed:

```python
def generate_report(data, format="markdown", include_charts=True):
    # Process data
    # Generate output in specified format
    # Optionally include visualizations
```
````

**自由度が低い** (特定のスクリプト、パラメータがほとんどまたはまったくない):

次の場合に使用します。

* 操作は脆弱でエラーが発生しやすい
* 一貫性が重要です
* 特定の順序に従う必要があります

例:

````markdown  theme={null}
## Database migration

Run exactly this script:

```bash
python scripts/migrate.py --verify --backup
```

Do not modify the command or add additional flags.
````

**類推**: エージェントを、パスを探索するロボットとして考えてみましょう。

* **両側が崖になっている狭い橋**: 安全な道は 1 つだけです。特定のガードレールと正確な指示を提供します (自由度が低い)。例: 正確な順序で実行する必要があるデータベースの移行。
* **危険のないオープンフィールド**: 成功につながる多くの道。一般的な指示を与え、エージェントが最適なルート (高い自由度) を見つけてくれることを信頼します。例: コンテキストによって最適なアプローチが決定されるコード レビュー。

### 使用する予定のすべてのモデルでテストします。

スキルはモデルへの追加として機能するため、有効性は基礎となるモデルに依存します。スキルを使用する予定のすべてのモデルでスキルをテストします。

**モデル別のテストに関する考慮事項**:

* **Claude Haiku** (高速、経済的): スキルは十分な指導を提供しますか?
* **Claude Sonnet** (バランス): スキルは明確で効率的ですか?
* **Claude Opus** (強力な推論): スキルは過剰な説明を避けていますか?

Opus では完璧に機能するものでも、Haiku ではさらに詳細な情報が必要になる場合があります。スキルを複数のモデルで使用する予定がある場合は、すべてのモデルで適切に機能する命令を目指してください。

## スキル構造

<注意>
  **YAML フロントマッター**: SKILL.md フロントマッターには 2 つのフィールドが必要です。

  * `name` - 人間が読めるスキル名 (最大 64 文字)
  * `description` - スキルの内容といつ使用するかの 1 行の説明 (最大 1024 文字)

  スキル構造の詳細については、[スキルの概要](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#skill- Structure)を参照してください。
</注>

### 命名規則

一貫した命名パターンを使用して、スキルを参照したり議論したりしやすくします。スキル名には **動名詞形式** (動詞 + -ing) を使用することをお勧めします。これは、スキルが提供するアクティビティや機能を明確に説明するためです。

**適切な命名例 (動名詞形式)**:

* 「PDF の処理」
* 「スプレッドシートの分析」
* 「データベースの管理」
* 「テストコード」
*「ドキュメントを書く」

**許容可能な代替案**:

* 名詞句: 「PDF 処理」、「スプレッドシート分析」
* アクション指向: 「PDF の処理」、「スプレッドシートの分析」

**避けてください**:

* 曖昧な名前: 「ヘルパー」、「ユーティリティ」、「ツール」
* 過度に一般的: 「ドキュメント」、「データ」、「ファイル」
* スキルコレクション内の一貫性のないパターン

一貫した名前を付けることで、次のことが容易になります。

* 文書化と会話における参考スキル
* スキルの内容が一目でわかる
* 複数のスキルを整理および検索
* 専門的で一貫したスキル ライブラリを維持する

### 効果的な説明を書く

の `description` フィールドはスキルの検出を有効にし、スキルの機能とそれをいつ使用するかの両方を含める必要があります。

<警告>
  **常に三人称で書きます**。説明はシステム プロンプトに挿入され、一貫性のない視点により検出の問題が発生する可能性があります。

  * **良い:** 「Excel ファイルを処理し、レポートを生成します」
  * **避けてください:** 「Excel ファイルの処理をお手伝いします」
  * **回避:** 「これを使用して Excel ファイルを処理できます」
</警告>

**具体的にし、重要な用語を含めてください**。スキルの機能と、それを使用する特定のトリガー/コンテキストの両方を含めます。

各スキルには説明フィールドが 1 つだけあります。説明はスキルの選択にとって重要です。エージェントはこの説明を使用して、100 以上の利用可能なスキルから適切なスキルを選択します。説明では、エージェントがこのスキルを選択するタイミングを知るのに十分な詳細を提供する必要がありますが、SKILL.md の残りの部分では実装の詳細が提供されます。

効果的な例:

**PDF 処理スキル:**

```yaml  theme={null}
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

**Excel 分析スキル:**

```yaml  theme={null}
description: Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.
```

**Git コミット ヘルパー スキル:**

```yaml  theme={null}
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
```

次のような曖昧な説明は避けてください。

```yaml  theme={null}
description: Helps with documents
```

```yaml  theme={null}
description: Processes data
```

```yaml  theme={null}
description: Does stuff with files
```

### 段階的な開示パターン

SKILL.md は、オンボーディング ガイドの目次など、必要に応じてエージェントに詳細な資料を案内する概要として機能します。段階的開示の仕組みの説明については、概要の [スキルの仕組み](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#how-skills-work) を参照してください。

**実践的なガイダンス:**

* 最適なパフォーマンスを得るには、SKILL.md 本文を 500 行以下に保ちます
* この制限に近づくとコンテンツを別のファイルに分割します
* 以下のパターンを使用して、命令、コード、リソースを効果的に整理します

#### 視覚的な概要: 単純なものから複雑なものまで

基本的なスキルは、メタデータと手順を含む SKILL.md ファイルだけで始まります。

<img src="https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-simple-file.png?fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=87782ff239b297d9a9e8e1b72ed72db9" alt="YAML フロントマッターとマークダウン本文を示す単純な SKILL.md ファイル" data-og-width="2048" width="2048" data-og-height="1153" height="1153" data-path="images/agent-skills-simple-file.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-simple -file.png?w=280&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=c61cc33b6f5855809907f7fda94cd80e 280w、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-simple-fil e.png?w=560&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=90d2c0c1c76b36e8d485f49e0810dbfd 560ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-simple-file.png?w=840&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=ad17d231ac7b0bea7e5b4d58fb4aeabb 840ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-simple-file .png?w=1100&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=f5d0a7a3c668435bb0aee9a3a8f8c329 1100w、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-simple-file .png?w=1650&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=0e927c1af9de5799cfe557d12249f6e6 1650ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-simple-file .png?w=2500&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=46bbb1a51dd4c8202a470ac8c80a893d 2500ワット" />

スキルが成長するにつれて、エージェントが必要な場合にのみロードする追加のコンテンツをバンドルできます。

<img src="https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-bundling -content.png?fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=a5e0aa41e3d53985a7e3e43668a33ea3" alt="reference.md や Forms.md などの追加の参照ファイルをバンドルします。" data-og-width="2048" width="2048" data-og-height="1327" height="1327" data-path="images/agent-skills-bundling-content.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-bundling- content.png?w=280&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=f8a0e73783e99b4a643d79eac86b70a2 280w、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-bundling-cont ent.png?w=560&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=dc510a2a9d3f14359416b706f067904a 560ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-bundling-cont ent.png?w=840&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=82cd6286c966303f7dd914c28170e385 840ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-bundling-cont ent.png?w=1100&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=56f3be36c77e4fe4b523df209a6824c6 1100w、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-bundling-cont ent.png?w=1650&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=d22b5161b2075656417d56f41a74f3dd 1650ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-bundling-content.png?w=2500&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=3dd4bdd6850ffcc96c6c45fcb0acd6eb 2500ワット" />

完全な Skill ディレクトリ構造は次のようになります。

```
pdf/
├── SKILL.md              # Main instructions (loaded when triggered)
├── FORMS.md              # Form-filling guide (loaded as needed)
├── reference.md          # API reference (loaded as needed)
├── examples.md           # Usage examples (loaded as needed)
└── scripts/
    ├── analyze_form.py   # Utility script (executed, not loaded)
    ├── fill_form.py      # Form filling script
    └── validate.py       # Validation script
```

#### パターン 1: 参考文献を含む高度なガイド

````markdown  theme={null}
---
name: PDF Processing
description: Extracts text and tables from PDF files, fills forms, and merges documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
---

# PDF Processing

## Quick start

Extract text with pdfplumber:
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## Advanced features

**Form filling**: See [FORMS.md](FORMS.md) for complete guide
**API reference**: See [REFERENCE.md](REFERENCE.md) for all methods
**Examples**: See [EXAMPLES.md](EXAMPLES.md) for common patterns
````

エージェントは、必要な場合にのみ、FORMS.md、REFERENCE.md、または EXAMPLES.md をロードします。

#### パターン 2: ドメイン固有の組織

複数のドメインを持つスキルの場合は、無関係なコンテキストの読み込みを避けるためにコンテンツをドメインごとに整理します。ユーザーが販売指標について質問した場合、エージェントは財務データやマーケティング データではなく、販売関連のスキーマを読み取るだけで済みます。これにより、トークンの使用量が低く抑えられ、コンテキストが重視されます。

```
bigquery-skill/
├── SKILL.md (overview and navigation)
└── reference/
    ├── finance.md (revenue, billing metrics)
    ├── sales.md (opportunities, pipeline)
    ├── product.md (API usage, features)
    └── marketing.md (campaigns, attribution)
```

````markdown SKILL.md theme={null}
# BigQuery Data Analysis

## Available datasets

**Finance**: Revenue, ARR, billing → See [reference/finance.md](reference/finance.md)
**Sales**: Opportunities, pipeline, accounts → See [reference/sales.md](reference/sales.md)
**Product**: API usage, features, adoption → See [reference/product.md](reference/product.md)
**Marketing**: Campaigns, attribution, email → See [reference/marketing.md](reference/marketing.md)

## Quick search

Find specific metrics using grep:

```bash
grep -i "revenue" reference/finance.md
grep -i "pipeline" reference/sales.md
grep -i "api usage" reference/product.md
```
````

#### パターン 3: 条件の詳細

基本的なコンテンツを表示し、高度なコンテンツへのリンクを表示します。

```markdown  theme={null}
# DOCX Processing

## Creating documents

Use docx-js for new documents. See [DOCX-JS.md](DOCX-JS.md).

## Editing documents

For simple edits, modify the XML directly.

**For tracked changes**: See [REDLINING.md](REDLINING.md)
**For OOXML details**: See [OOXML.md](OOXML.md)
```

エージェントは、ユーザーがこれらの機能を必要とする場合にのみ、REDLINING.md または OOXML.md を読み取ります。

### 深くネストされた参照を避ける

エージェントは、他の参照ファイルから参照されているファイルを部分的に読み取ることがあります。ネストされた参照に遭遇した場合、エージェントは次のようなコマンドを使用する可能性があります。 `head -100` ファイル全体を読み取るのではなくコンテンツをプレビューするため、情報が不完全になります。

**参照は SKILL.md から 1 つ下のレベルに保ってください**。すべての参照ファイルは、必要に応じてエージェントが完全なファイルを確実に読み取れるように、SKILL.md から直接リンクする必要があります。

**悪い例: 深すぎる**:

```markdown  theme={null}
# SKILL.md
See [advanced.md](advanced.md)...

# advanced.md
See [details.md](details.md)...

# details.md
Here's the actual information...
```

**良い例: 1 レベルの深さ**:

```markdown  theme={null}
# SKILL.md

**Basic usage**: [instructions in SKILL.md]
**Advanced features**: See [advanced.md](advanced.md)
**API reference**: See [reference.md](reference.md)
**Examples**: See [examples.md](examples.md)
```

### 目次を含む長い参照ファイルを構造化する

100 行を超える参照ファイルの場合は、先頭に目次を含めます。これにより、エージェントは、部分的な読み取りでプレビューする場合でも、利用可能な情報の全範囲を確認できるようになります。

**例**：

```markdown  theme={null}
# API Reference

## Contents
- Authentication and setup
- Core methods (create, read, update, delete)
- Advanced features (batch operations, webhooks)
- Error handling patterns
- Code examples

## Authentication and setup
...

## Core methods
...
```

エージェントは、必要に応じてファイル全体を読んだり、特定のセクションにジャンプしたりできます。

このファイルシステムベースのアーキテクチャがどのように段階的な開示を可能にするかについて詳しくは、以下の「詳細」セクションの「[ランタイム環境](#runtime-environment)」セクションを参照してください。

## ワークフローとフィードバック ループ

### 複雑なタスクにはワークフローを使用する

複雑な操作を明確な連続ステップに分割します。特に複雑なワークフローの場合は、エージェントが応答にコピーして進行中にチェックを入れることができるチェックリストを提供します。

**例 1: 研究合成ワークフロー** (コードのないスキルの場合):

````markdown  theme={null}
## Research synthesis workflow

Copy this checklist and track your progress:

```
Research Progress:
- [ ] Step 1: Read all source documents
- [ ] Step 2: Identify key themes
- [ ] Step 3: Cross-reference claims
- [ ] Step 4: Create structured summary
- [ ] Step 5: Verify citations
```

**Step 1: Read all source documents**

Review each document in the `sources/` directory. Note the main arguments and supporting evidence.

**Step 2: Identify key themes**

Look for patterns across sources. What themes appear repeatedly? Where do sources agree or disagree?

**Step 3: Cross-reference claims**

For each major claim, verify it appears in the source material. Note which source supports each point.

**Step 4: Create structured summary**

Organize findings by theme. Include:
- Main claim
- Supporting evidence from sources
- Conflicting viewpoints (if any)

**Step 5: Verify citations**

Check that every claim references the correct source document. If citations are incomplete, return to Step 3.
````

この例では、コードを必要としない分析タスクにワークフローがどのように適用されるかを示します。チェックリスト パターンは、複雑な複数のステップからなるプロセスに有効です。

**例 2: PDF フォーム入力ワークフロー** (コードを含むスキルの場合):

````markdown  theme={null}
## PDF form filling workflow

Copy this checklist and check off items as you complete them:

```
Task Progress:
- [ ] Step 1: Analyze the form (run analyze_form.py)
- [ ] Step 2: Create field mapping (edit fields.json)
- [ ] Step 3: Validate mapping (run validate_fields.py)
- [ ] Step 4: Fill the form (run fill_form.py)
- [ ] Step 5: Verify output (run verify_output.py)
```

**Step 1: Analyze the form**

Run: `python scripts/analyze_form.py input.pdf`

This extracts form fields and their locations, saving to `fields.json`.

**Step 2: Create field mapping**

Edit `fields.json` to add values for each field.

**Step 3: Validate mapping**

Run: `python scripts/validate_fields.py fields.json`

Fix any validation errors before continuing.

**Step 4: Fill the form**

Run: `python scripts/fill_form.py input.pdf fields.json output.pdf`

**Step 5: Verify output**

Run: `python scripts/verify_output.py output.pdf`

If verification fails, return to Step 2.
````

明確な手順により、エージェントが重要な検証をスキップすることを防ぎます。チェックリストは、あなたとエージェントの両方が複数ステップのワークフローの進行状況を追跡するのに役立ちます。

### フィードバック ループを実装する

**一般的なパターン**: バリデーターを実行 → エラーを修正 → 繰り返し

このパターンにより、出力品質が大幅に向上します。

**例 1: スタイル ガイドへの準拠** (コードのないスキルの場合):

```markdown  theme={null}
## Content review process

1. Draft your content following the guidelines in STYLE_GUIDE.md
2. Review against the checklist:
   - Check terminology consistency
   - Verify examples follow the standard format
   - Confirm all required sections are present
3. If issues found:
   - Note each issue with specific section reference
   - Revise the content
   - Review the checklist again
4. Only proceed when all requirements are met
5. Finalize and save the document
```

これは、スクリプトの代わりに参照ドキュメントを使用した検証ループ パターンを示しています。 「バリデータ」は STYLE\_GUIDE.md であり、エージェントは読み取りと比較によってチェックを実行します。

**例 2: ドキュメント編集プロセス** (コードを含むスキルの場合):

```markdown  theme={null}
## Document editing process

1. Make your edits to `word/document.xml`
2. **Validate immediately**: `python ooxml/scripts/validate.py unpacked_dir/`
3. If validation fails:
   - Review the error message carefully
   - Fix the issues in the XML
   - Run validation again
4. **Only proceed when validation passes**
5. Rebuild: `python ooxml/scripts/pack.py unpacked_dir/ output.docx`
6. Test the output document
```

検証ループはエラーを早期に検出します。

## コンテンツのガイドライン

### 時間に敏感な情報を避ける

古くなってしまう情報は含めないでください。

**悪い例: 時間に左右されやすい** (間違いになります):

```markdown  theme={null}
If you're doing this before August 2025, use the old API.
After August 2025, use the new API.
```

**良い例** (「古いパターン」セクションを使用):

```markdown  theme={null}
## Current method

Use the v2 API endpoint: `api.example.com/v2/messages`

## Old patterns

<details>
<summary>Legacy v1 API (deprecated 2025-08)</summary>

The v1 API used: `api.example.com/v1/messages`

This endpoint is no longer supported.
</details>
```

古いパターンのセクションでは、メインのコンテンツを乱雑にすることなく、歴史的なコンテキストを提供します。

### 一貫した用語を使用する

用語を 1 つ選択し、スキル全体で使用します。

**良好 - 一貫性**:

※ 常に「API endpoint」
※常に「field」
※必ず「extract」してください

**悪い - 一貫性がありません**:

※「API endpoint」、「URL」、「API route」、「path」を混在させてください
※「field」、「box」、「element」、「control」を混在させる
*「extract」、「pull」、「retrieve」、「get」を混在させる

一貫性は、エージェントが指示を理解し、従うのに役立ちます。

## よくあるパターン

### テンプレートパターン

出力形式のテンプレートを提供します。ニーズに合わせて厳密さのレベルを調整してください。

**厳密な要件の場合** (API 応答やデータ形式など):

````markdown  theme={null}
## Report structure

ALWAYS use this exact template structure:

```markdown
# [Analysis Title]

## Executive summary
[One-paragraph overview of key findings]

## Key findings
- Finding 1 with supporting data
- Finding 2 with supporting data
- Finding 3 with supporting data

## Recommendations
1. Specific actionable recommendation
2. Specific actionable recommendation
```
````

**柔軟なガイダンスについて** (適応が役立つ場合):

````markdown  theme={null}
## Report structure

Here is a sensible default format, but use your best judgment based on the analysis:

```markdown
# [Analysis Title]

## Executive summary
[Overview]

## Key findings
[Adapt sections based on what you discover]

## Recommendations
[Tailor to the specific context]
```

Adjust sections as needed for the specific analysis type.
````

### パターンの例

出力の品質がサンプルの表示に依存するスキルの場合は、通常のプロンプトと同様に入力/出力ペアを提供します。

````markdown  theme={null}
## Commit message format

Generate commit messages following these examples:

**Example 1:**
Input: Added user authentication with JWT tokens
Output:
```
feat(auth): implement JWT-based authentication

Add login endpoint and token validation middleware
```

**Example 2:**
Input: Fixed bug where dates displayed incorrectly in reports
Output:
```
fix(reports): correct date formatting in timezone conversion

Use UTC timestamps consistently across report generation
```

**Example 3:**
Input: Updated dependencies and refactored error handling
Output:
```
chore: update dependencies and refactor error handling

- Upgrade lodash to 4.17.21
- Standardize error response format across endpoints
```

Follow this style: type(scope): brief description, then detailed explanation.
````

例は、エージェントが説明だけよりも明確に希望のスタイルと詳細レベルを理解するのに役立ちます。

### 条件付きワークフロー パターン

エージェントを意思決定ポイントに沿ってガイドします。

```markdown  theme={null}
## Document modification workflow

1. Determine the modification type:

   **Creating new content?** → Follow "Creation workflow" below
   **Editing existing content?** → Follow "Editing workflow" below

2. Creation workflow:
   - Use docx-js library
   - Build document from scratch
   - Export to .docx format

3. Editing workflow:
   - Unpack existing document
   - Modify XML directly
   - Validate after each change
   - Repack when complete
```

<ヒント>
  ワークフローが大きくなったり、ステップが多くて複雑になったりする場合は、ワークフローを別のファイルにプッシュすることを検討し、当面のタスクに基づいて適切なファイルを読み取るようにエージェントに指示します。
</ヒント>

## 評価と反復

### 最初に評価を構築する

**広範なドキュメントを作成する前に評価を作成してください。** これにより、スキルが想像上の問題を文書化するのではなく、実際の問題を確実に解決できるようになります。

**評価主導型開発:**

1. **ギャップを特定する**: スキルなしで代表的なタスクでエージェントを実行します。特定の失敗または欠落しているコンテキストを文書化する
2. **評価の作成**: これらのギャップをテストする 3 つのシナリオを構築します。
3. **ベースラインの確立**: スキルなしでエージェントのパフォーマンスを測定します。
4. **最小限の指示を作成します**: ギャップに対処し、評価に合格するのに十分なコンテンツを作成します。
5. **反復**: 評価を実行し、ベースラインと比較し、調整します。

このアプローチにより、決して実現しない可能性のある要件を予測するのではなく、実際の問題を確実に解決できます。

**評価体系**:

```json  theme={null}
{
  "skills": ["pdf-processing"],
  "query": "Extract all text from this PDF file and save it to output.txt",
  "files": ["test-files/document.pdf"],
  "expected_behavior": [
    "Successfully reads the PDF file using an appropriate PDF processing library or command-line tool",
    "Extracts text content from all pages in the document without missing any pages",
    "Saves the extracted text to a file named output.txt in a clear, readable format"
  ]
}
```

<注意>
  この例では、単純なテスト ルーブリックを使用したデータ駆動型の評価を示します。現在、これらの評価を実行するための組み込みの方法は提供されていません。ユーザーは独自の評価システムを作成できます。評価は、スキルの有効性を測定するための信頼できる情報源です。
</注>

### エージェントと繰り返しスキルを開発する

最も効果的なスキル開発プロセスには、エージェント自体が関与します。 1 つのインスタンス (「エージェント A」) を操作して、他のインスタンス (「エージェント B」) で使用されるスキルを作成します。エージェント A は指示の設計と改良を支援し、エージェント B は実際のタスクで指示をテストします。これが機能するのは、基礎となるモデルが効果的なエージェント指示の書き方とエージェントが必要とする情報の両方を理解しているためです。

**新しいスキルの作成:**

1. **スキルなしでタスクを完了する**: 通常のプロンプトを使用してエージェント A の問題に対処します。作業を進めていくと、自然にコンテキストを提供し、設定を説明し、手順に関する知識を共有することになります。どのような情報を繰り返し提供しているかに注目してください。

2. **再利用可能なパターンを特定する**: タスクの完了後、今後の同様のタスクに役立つ、提供したコンテキストを特定します。

   **例**: BigQuery 分析を行った場合は、テーブル名、フィールド定義、フィルタリング ルール (「常にテスト アカウントを除外する」など)、および一般的なクエリ パターンを指定している可能性があります。

3. **エージェント A にスキルの作成を依頼します**: 「先ほど使用したこの BigQuery 分析パターンをキャプチャするスキルを作成します。テーブル スキーマ、命名規則、テスト アカウントのフィルタリングに関するルールを含めます。」

   <ヒント>
     最新のエージェントは、スキルの形式と構造をネイティブに理解します。スキルの作成を支援するために、特別なシステム プロンプトや「ライティング スキル」スキルは必要ありません。エージェントにスキルの作成を依頼するだけで、適切なフロントマターと本文コンテンツを含む適切に構造化された SKILL.md コンテンツが生成されます。
   </ヒント>

4. **簡潔にするための見直し**: エージェント A が不必要な説明を追加していないか確認してください。 「勝率が何を意味するかについての説明を削除してください。エージェントはすでにそれを知っています。」

5. **情報アーキテクチャを改善**: エージェント A にコンテンツをより効果的に整理するよう依頼します。例: 「テーブル スキーマが別の参照ファイルに含まれるようにこれを整理します。後でさらにテーブルを追加する可能性があります。」

6. **同様のタスクでテスト**: 関連するユースケースでエージェント B (スキルがロードされた新しいインスタンス) でスキルを使用します。エージェント B が正しい情報を見つけ、ルールを正しく適用し、タスクを正常に処理するかどうかを観察します。

7. **観察に基づいて繰り返す**: エージェント B が苦労したり、何かを見落としたりした場合は、エージェント A に詳細を返します。「エージェントがこのスキルを使用したとき、Q4 の日付によるフィルタリングを忘れていました。日付フィルタリング パターンに関するセクションを追加する必要がありますか?」

**既存のスキルの反復:**

スキルを向上させる場合も、同じ階層パターンが続きます。次の間を交互に行います。

* **エージェント A** (スキルの向上を支援する専門家) と協力します
* **エージェント B によるテスト** (スキルを使用して実際の作業を実行するエージェント)
* **エージェント B の行動を観察**し、洞察をエージェント A に持ち帰る

1. **実際のワークフローでスキルを使用する**: テスト シナリオではなく、エージェント B (スキルがロードされた) に実際のタスクを与えます。

2. **エージェント B の行動を観察**: エージェント B が苦労しているところ、成功しているところ、予期しない選択をしているところに注目してください。

   **観察の例**: 「エージェント B に地域の売上レポートを依頼したとき、エージェント B はクエリを作成しましたが、スキルでこのルールに言及しているにもかかわらず、テスト アカウントをフィルターで除外するのを忘れていました。」

3. **改善のためにエージェント A に戻ります**: 現在の SKILL.md を共有し、観察した内容を説明します。質問: 「地域レポートを要求したときに、エージェント B がテスト アカウントをフィルターするのを忘れていることに気付きました。スキルにはフィルターについて言及されていますが、十分に目立たないのではないでしょうか?」

4. **エージェント A の提案を確認する**: エージェント A は、ルールをより目立つように再編成するか、「常にフィルタする」ではなく「必ずフィルタする」などのより強い表現を使用するか、ワークフロー セクションを再構築することを提案する可能性があります。

5. **変更を適用してテスト**: エージェント A の改良点でスキルを更新し、同様のリクエストに対してエージェント B で再度テストします。

6. **使用状況に基づいて繰り返します**: 新しいシナリオが発生した場合は、この観察、調整、テストのサイクルを続けます。各反復では、仮定ではなく実際のエージェントの動作に基づいてスキルが向上します。

**チームのフィードバックを収集する:**

1. チームメイトとスキルを共有し、その使い方を観察する
2. 質問します: スキルは期待どおりにアクティブになりますか?指示は明確ですか?何が足りないのでしょうか？
3. フィードバックを取り入れて、独自の使用パターンの盲点に対処します

**このアプローチが機能する理由**: エージェント A はエージェントのニーズを理解し、あなたはその分野の専門知識を提供し、エージェント B は実際の使用方法を通じてギャップを明らかにし、反復的な改善により、仮定ではなく観察された動作に基づいてスキルを向上させます。

### エージェントがどのようにスキルを操作するかを観察する

スキルを反復するときは、エージェントが実際にスキルをどのように使用するかに注意してください。以下に注意してください:

* **予期しない探索パス**: エージェントは予期しない順序でファイルを読み取りますか?これは、構造が思ったほど直感的ではないことを示している可能性があります
* **接続の失敗**: エージェントは重要なファイルへの参照を追跡できませんか?リンクをより明示的または目立つようにする必要がある場合があります
* **特定のセクションへの過度の依存**: エージェントが同じファイルを繰り返し読み取る場合は、代わりにそのコンテンツをメインの SKILL.md に含めるべきかどうかを検討してください。
* **無視されるコンテンツ**: エージェントがバンドルされたファイルにアクセスしない場合、そのファイルは不要であるか、メインの指示で適切に通知されていない可能性があります。

仮定ではなくこれらの観察に基づいて繰り返します。スキルのメタデータ内の「name」と「description」は特に重要です。エージェントは、現在のタスクに応じてスキルをトリガーするかどうかを決定するときにこれらを使用します。スキルが何を行うのか、いつ使用する必要があるのか​​を明確に説明していることを確認してください。

## 避けるべきアンチパターン

### Windows スタイルのパスを避ける

Windows であっても、ファイル パスでは常にスラッシュを使用してください。

* ✓ **良い**: `scripts/helper.py`、 `reference/guide.md`
* ✗ **避けてください**: `scripts\helper.py`、 `reference\guide.md`

Unix スタイルのパスはすべてのプラットフォームで機能しますが、Windows スタイルのパスは Unix システムでエラーを引き起こします。

### あまりにも多くのオプションを提供しないようにする

必要な場合を除き、複数のアプローチを提示しないでください。

````markdown  theme={null}
**Bad example: Too many choices** (confusing):
"You can use pypdf, or pdfplumber, or PyMuPDF, or pdf2image, or..."

**Good example: Provide a default** (with escape hatch):
"Use pdfplumber for text extraction:
```python
import pdfplumber
```

For scanned PDFs requiring OCR, use pdf2image with pytesseract instead."
````

## 上級: 実行可能コードを使用したスキル

以下のセクションでは、実行可能なスクリプトを含むスキルに焦点を当てます。スキルがマークダウン命令のみを使用している場合は、[効果的なスキルのチェックリスト](#checklist-for-effective-skills)に進んでください。

### パントしないで解決します

スキルのスクリプトを作成するときは、エージェントにパントするのではなく、エラー条件を処理します。

**良い例: エラーを明示的に処理します**:

```python  theme={null}
def process_file(path):
    """Process a file, creating it if it doesn't exist."""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        # Create file with default content instead of failing
        print(f"File {path} not found, creating default")
        with open(path, 'w') as f:
            f.write('')
        return ''
    except PermissionError:
        # Provide alternative instead of failing
        print(f"Cannot access {path}, using default")
        return ''
```

**悪い例: エージェントへのパント**:

```python  theme={null}
def process_file(path):
    # Just fail and let the agent figure it out
    return open(path).read()
```

また、「ブードゥー定数」 (オースターハウトの法則) を避けるために、構成パラメーターを正当化して文書化する必要があります。正しい値がわからない場合、エージェントはどのようにして値を決定するのでしょうか?

**良い例: 自己文書化**:

```python  theme={null}
# HTTP requests typically complete within 30 seconds
# Longer timeout accounts for slow connections
REQUEST_TIMEOUT = 30

# Three retries balances reliability vs speed
# Most intermittent failures resolve by the second retry
MAX_RETRIES = 3
```

**悪い例: マジックナンバー**:

```python  theme={null}
TIMEOUT = 47  # Why 47?
RETRIES = 5   # Why 5?
```

### ユーティリティ スクリプトを提供する

エージェントがスクリプトを作成できる場合でも、事前に作成されたスクリプトには次のような利点があります。

**ユーティリティ スクリプトの利点**:

* 生成されたコードよりも信頼性が高い
* トークンを保存します (コンテキストにコードを含める必要はありません)
* 時間を節約します (コード生成は必要ありません)
* 複数の用途にわたって一貫性を確保する

<img src="https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-executable-scripts.png?fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=4bbc45f2c2e0bee9f2f0d5da669bad00" alt="指示ファイルと一緒に実行可能スクリプトをバンドルする" data-og-width="2048" width="2048" data-og-height="1154" height="1154" data-path="images/agent-skills-executable-scripts.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-executable -scripts.png?w=280&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=9a04e6535a8467bfeea492e517de389f 280w、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-executable-scr ipts.png?w=560&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=e49333ad90141af17c0d7651cca7216b 560ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-executable-scr ipts.png?w=840&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=954265a5df52223d6572b6214168c428 840ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-executable-scr ipts.png?w=1100&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=2ff7a2d8f2a83ee8af132b29f10150fd 1100w、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-executable-scr ipts.png?w=1650&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=48ab96245e04077f4d15e9170e081cfb 1650ワット、 https://mintcdn.com/anthropic-claude-docs/4Bny2bjzuGBK7o00/images/agent-skills-executable-scr ipts.png?w=2500&fit=max&auto=format&n=4Bny2bjzuGBK7o00&q=85&s=0301a6c8b3ee879497cc5b5483177c90 2500ワット" />

上の図は、実行可能スクリプトが命令ファイルとともにどのように機能するかを示しています。命令ファイル (forms.md) はスクリプトを参照し、エージェントはその内容をコンテキストにロードせずにスクリプトを実行できます。

**重要な区別**: エージェントが次のことを行うべきかどうかを指示の中で明確にしてください。

* **スクリプトを実行します** (最も一般的): "実行 `analyze_form.py` フィールドを抽出するには」
* **参考資料として読んでください** (複雑なロジックの場合): "を参照してください。 `analyze_form.py` フィールド抽出アルゴリズムの場合

ほとんどのユーティリティ スクリプトでは、信頼性が高く効率的であるため、実行することが推奨されます。スクリプトの実行方法の詳細については、以下の [ランタイム環境](#runtime-environment) セクションを参照してください。

**例**:

````markdown  theme={null}
## Utility scripts

**analyze_form.py**: Extract all form fields from PDF

```bash
python scripts/analyze_form.py input.pdf > fields.json
```

Output format:
```json
{
  "field_name": {"type": "text", "x": 100, "y": 200},
  "signature": {"type": "sig", "x": 150, "y": 500}
}
```

**validate_boxes.py**: Check for overlapping bounding boxes

```bash
python scripts/validate_boxes.py fields.json
# Returns: "OK" or lists conflicts
```

**fill_form.py**: Apply field values to PDF

```bash
python scripts/fill_form.py input.pdf fields.json output.pdf
```
````

### 視覚的な分析を使用する

入力を画像としてレンダリングできる場合は、エージェントに入力を分析させます。

````markdown  theme={null}
## Form layout analysis

1. Convert PDF to images:
   ```bash
   python scripts/pdf_to_images.py form.pdf
   ```

2. Analyze each page image to identify form fields
3. The agent can see field locations and types visually
````

<注意>
  この例では、次のように記述する必要があります。 `pdf_to_images.py` スクリプト。
</注>

エージェントのビジョン機能は、レイアウトと構造を理解するのに役立ちます。

### 検証可能な中間出力を作成する

エージェントが複雑で無制限のタスクを実行する場合、間違いを犯す可能性があります。 「計画-検証-実行」パターンでは、エージェントが最初に構造化された形式で計画を作成し、次にその計画を実行する前にスクリプトで検証することで、エラーを早期に検出します。

**例**: スプレッドシートに基づいて PDF 内の 50 個のフォーム フィールドを更新するようにエージェントに依頼することを想像してください。検証を行わないと、存在しないフィールドが参照されたり、競合する値が作成されたり、必須フィールドが欠落したり、更新が誤って適用されたりする可能性があります。

**解決策**: 上記のワークフロー パターン (PDF フォーム入力) を使用しますが、中間のパターンを追加します。 `changes.json` ファイルは変更を適用する前に検証されます。ワークフローは次のようになります: 分析 → **計画ファイルの作成** → **計画の検証** → 実行 → 検証。

**このパターンが機能する理由:**

* **エラーを早期に検出**: 変更が適用される前に検証によって問題が検出されます。
* **機械検証可能**: スクリプトは客観的な検証を提供します
* **可逆計画**: エージェントは元の計画に触れることなく、計画を反復できます。
* **明確なデバッグ**: エラー メッセージは特定の問題を示しています

**使用する場合**: バッチ操作、破壊的な変更、複雑な検証ルール、一か八かの操作。

**実装のヒント**: エージェントが問題を修正できるように、「フィールド '署名\_日付' が見つかりません。利用可能なフィールド: 顧客\_名前、注文\_合計、署名\_日付\_署名済み」などの特定のエラー メッセージを含む検証スクリプトを冗長にします。

### パッケージの依存関係

スキルは、プラットフォーム固有の制限のあるコード実行環境で実行されます。

* **claude.ai**: npm および PyPI からパッケージをインストールし、GitHub リポジトリからプルすることができます
* **Anthropic API**: ネットワーク アクセスやランタイム パッケージのインストールはありません

SKILL.md 内の必要なパッケージをリストし、[コード実行ツールのドキュメント](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool) で入手できることを確認します。

### 実行環境

スキルは、ファイル システム アクセス、bash コマンド、およびコード実行機能を備えたコード実行環境で実行されます。このアーキテクチャの概念的な説明については、概要の [スキル アーキテクチャ](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#the-skills-architecture) を参照してください。

**これがオーサリングに与える影響:**

**エージェントがスキルにアクセスする方法:**

1. **メタデータが事前に読み込まれています**: 起動時に、すべてのスキルの YAML フロントマターからの名前と説明がシステム プロンプトに読み込まれます。
2. **オンデマンドで読み取られるファイル**: エージェントは、必要に応じてファイル読み取りツールを使用して、ファイルシステムから SKILL.md やその他のファイルにアクセスします。
3. **効率的に実行されるスクリプト**: ユーティリティ スクリプトは、完全な内容をコンテキストにロードせずに bash 経由で実行できます。スクリプトの出力のみがトークンを消費します
4. **大きなファイルに対するコンテキスト ペナルティなし**: 参照ファイル、データ、またはドキュメントは、実際に読み取られるまでコンテキスト トークンを消費しません。

* **ファイル パスは重要です**: エージェントはファイル システムのようにスキル ディレクトリを移動します。スラッシュ (`reference/guide.md`)、バックスラッシュではありません
* **ファイルにわかりやすい名前を付ける**: 内容を示す名前を使用します。 `form_validation_rules.md`、 ない `doc2.md`
* **発見のために整理する**: ドメインまたは機能ごとにディレクトリを構造化する
  * 良い点: `reference/finance.md`、 `reference/sales.md`
  * 悪い： `docs/file1.md`、 `docs/file2.md`
* **包括的なリソースのバンドル**: 完全な API ドキュメント、広範なサンプル、大規模なデータセットが含まれます。アクセスするまでコンテキストペナルティなし
* **確定的な操作にはスクリプトを優先します**: 書き込みます `validate_form.py` エージェントに検証コードの生成を依頼するのではなく、
* **実行意図を明確にする**:
  *「走ってください `analyze_form.py` フィールドを抽出します」(実行)
  *「参照 `analyze_form.py` 抽出アルゴリズムについて」（参考として読んでください）
* **ファイル アクセス パターンをテスト**: 実際のリクエストを使用してテストすることで、エージェントがディレクトリ構造をナビゲートできることを確認します。

**例:**

```
bigquery-skill/
├── SKILL.md (overview, points to reference files)
└── reference/
    ├── finance.md (revenue metrics)
    ├── sales.md (pipeline data)
    └── product.md (usage analytics)
```

ユーザーが収益について尋ねると、エージェントは SKILL.md を読み取り、への参照を確認します。 `reference/finance.md`、そして bash を呼び出してそのファイルだけを読み取ります。 sales.md および product.md ファイルはファイルシステム上に残り、必要になるまでコンテキスト トークンを消費しません。このファイルシステムベースのモデルにより、段階的な開示が可能になります。エージェントは、各タスクに必要なものを正確にナビゲートし、選択的に読み込むことができます。

技術アーキテクチャの詳細については、スキルの概要の [スキルの仕組み](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#how-skills-work) を参照してください。

### MCP ツールのリファレンス

スキルで MCP (Model Context Protocol) ツールを使用する場合は、「ツールが見つかりません」エラーを避けるために、常に完全修飾ツール名を使用してください。

**形式**： `ServerName:tool_name`

**例**：

```markdown  theme={null}
Use the BigQuery:bigquery_schema tool to retrieve table schemas.
Use the GitHub:create_issue tool to create issues.
```

どこ：

* `BigQuery` そして `GitHub` は MCP サーバー名です
* `bigquery_schema` そして `create_issue` それらのサーバー内のツール名です

サーバー プレフィックスがないと、特に複数の MCP サーバーが使用可能な場合、エージェントはツールを見つけられない可能性があります。

### ツールがインストールされていると想定するのは避けてください

パッケージが利用可能であると想定しないでください。

````markdown  theme={null}
**Bad example: Assumes installation**:
"Use the pdf library to process the file."

**Good example: Explicit about dependencies**:
"Install required package: `pip install pypdf`

Then use it:
```python
from pypdf import PdfReader
reader = PdfReader("file.pdf")
```"
````

## 技術的なメモ

### YAML フロントマターの要件

SKILL.md フロントマターには次のものが必要です `name` (最大64文字)および `description` (最大 1024 文字) フィールド。完全な構造の詳細については、[スキルの概要](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#skill-struction) を参照してください。

### トークンの予算

最適なパフォーマンスを得るには、SKILL.md 本文を 500 行以下に保ちます。コンテンツがこれを超える場合は、前述の段階的な開示パターンを使用して、コンテンツを個別のファイルに分割します。アーキテクチャの詳細については、[スキルの概要](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#how-skills-work)を参照してください。

## 効果的なスキルのチェックリスト

スキルを共有する前に、次のことを確認してください。

### コア品質

* [ ] 説明は具体的であり、重要な用語が含まれています
* [ ] の説明には、スキルの機能とそれをいつ使用するかの両方が含まれます
※ [ ] SKILL.md本体は500行以内です
* [ ] 追加の詳細は別のファイルにあります (必要な場合)
* [ ] 時間に依存する情報はありません (または「古いパターン」セクションにあります)
* [ ] 全体で一貫した用語
* [ ] の例は抽象的なものではなく具体的なものです
* [ ] ファイル参照は 1 レベルの深さです
* [ ] 段階的な開示は適切に使用されます
* [ ] ワークフローには明確な手順があります

### コードとスクリプト

* [ ] スクリプトはエージェントにパントするのではなく問題を解決します
* [ ] エラー処理は明示的で役に立ちます
* [ ] 「ブードゥー定数」なし (すべての値は両端揃えで揃えられます)
* [ ] 必要なパッケージが説明書に記載されており、利用可能であることが確認されています
* [ ] スクリプトには明確なドキュメントがあります
* [ ] Windows スタイルのパスはありません (すべてスラッシュ)
* [ ] 重要な操作の検証/検証手順
* [ ] 品質が重要なタスク用のフィードバック ループが含まれています

### テスト

* [ ] 少なくとも 3 つの評価が作成されました
* [ ] Haiku、Sonnet、Opus でテスト済み
* [ ] 実際の使用シナリオでテスト済み
* [ ] チームのフィードバックが組み込まれました (該当する場合)

## 次のステップ

<CardGroupcols={2}>
  <Card title="エージェント スキルを使ってみる" icon="rocket" href="https://platform.claude.com/docs/en/agents-and-tools/agent-skills/quickstart">
    最初のスキルを作成する
  </カード>

  <Card title="クロード コードでスキルを使用する" icon="terminal" href="https://code.claude.com/docs/en/skills">
    クロードコードでスキルを作成および管理する
  </カード>

  <Card title="API でスキルを使用する" icon="code" href="https://platform.claude.com/docs/en/build-with-claude/skills-guide">
    スキルをプログラムでアップロードして使用する
  </カード>
</カードグループ>
