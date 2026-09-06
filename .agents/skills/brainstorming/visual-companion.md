# ビジュアルコンパニオンガイド

モックアップ、図、オプションを表示するためのブラウザベースのビジュアル ブレーンストーミング コンパニオンです。

## いつ使用するか

セッションごとではなく、質問ごとに決定します。テスト: **ユーザーはこれを読むよりも見た方がよく理解できますか?**

**コンテンツ自体が視覚的な場合はブラウザを使用します**:

- **UI モックアップ** — ワイヤーフレーム、レイアウト、ナビゲーション構造、コンポーネント設計
- **アーキテクチャ図** — システム コンポーネント、データ フロー、関係マップ
- **並べて視覚的に比較** — 2 つのレイアウト、2 つの配色、2 つのデザイン方向を比較します。
- **洗練されたデザイン** — 質問が見た目と雰囲気、間隔、視覚的な階層に関する場合
- **空間関係** — ステート マシン、フローチャート、図としてレンダリングされたエンティティ関係

**コンテンツがテキストまたは表形式の場合はターミナルを使用します**:

- **要件と範囲に関する質問** - 「X とは何を意味しますか?」、「どの機能が範囲内ですか?」
- **概念的な A/B/C の選択** — 言葉で説明されたアプローチの中から選択する
- **トレードオフ リスト** — 長所/短所、比較表
- **技術的な決定** — API 設計、データ モデリング、アーキテクチャ アプローチの選択
- **質問の明確化** — 視覚的な好みではなく、言葉で答えられるものすべて

UI トピックに関する質問は、自動的に視覚的な質問にはなりません。 「どんな魔法使いが欲しいの？」概念的です - ターミナルを使用してください。 「次のウィザードのレイアウトのうち、どれが適切だと思いますか?」視覚的です - ブラウザを使用してください。

## 仕組み

サーバーは HTML ファイルのディレクトリを監視し、最新のファイルをブラウザに提供します。 HTML コンテンツを書き込むと、 `screen_dir`、ユーザーはブラウザにそれを表示し、クリックしてオプションを選択できます。選択内容は次の場所に記録されます `state_dir/events` 次のターンにそれを読みます。

**コンテンツの断片と完全なドキュメント:** HTML ファイルが次で始まる場合 `<!DOCTYPE` または `<html`の場合、サーバーはそれをそのまま提供します (ヘルパー スクリプトを挿入するだけです)。それ以外の場合、サーバーはコンテンツをフレーム テンプレートに自動的にラップし、ヘッダー、CSS テーマ、接続ステータス、およびすべてのインタラクティブ インフラストラクチャを追加します。 **デフォルトでは、コンテンツのフラグメントを書き込みます。** ページを完全に制御する必要がある場合にのみ、完全なドキュメントを書き込みます。

## セッションの開始

```bash
# Start AFTER the user approves the companion. --open auto-opens their browser on
# the first screen; --project-dir persists mockups and enables same-port restart.
scripts/start-server.sh --project-dir /path/to/project --open

# Returns: {"type":"server-started","port":52341,
#           "url":"http://localhost:52341/?key=ab12…",
#           "screen_dir":"/path/to/project/.superpowers/brainstorm/12345-1706000000/content",
#           "state_dir":"/path/to/project/.superpowers/brainstorm/12345-1706000000/state"}
```

保存 `screen_dir` そして `state_dir` 返答より。と `--open`、最初の画面を押すとブラウザーが自動的に開きます。ユーザーにブラウザーを開くように求める必要はありませんが、フォールバックとして URL を共有します (ヘッドレス/リモート設定は自動的に開きません)。

** URL にはセッション キー (`?key=…`).** サーバーはリクエストを拒否します
これがないと、常にユーザーに **完全な** URL を提供します。 `url` フィールド —
決してクエリ文字列を削除したり、裸の文字列を渡したりしないでください。 `http://host:port`。の
キーは HTTP および WebSocket アクセスをゲートするため、ブラウザ タブまたは別のマシンがオンになります。
ネットワークは画面を読み取ったり、イベントを挿入したりできません。最初のロード後、
ブラウザは Cookie を介してキーを記憶しているため、リロードして `/files/*` 資産の働き
繰り返さずに。

**接続情報の検索:** サーバーは起動 JSON を次の場所に書き込みます。 `$STATE_DIR/server-info`。サーバーをバックグラウンドで起動し、stdout をキャプチャしなかった場合は、そのファイルを読んで URL とポートを取得します。使用するとき `--project-dir`、 チェック `<project>/.superpowers/brainstorm/` セッションディレクトリ用。

**注:** プロジェクトのルートを次のように渡します `--project-dir` モックアップはそのまま残ります `.superpowers/brainstorm/` そしてサーバーが再起動しても生き残れます。これがないと、ファイルは次の場所に移動します。 `/tmp` そして片づけてもらう。ユーザーに追加を促す `.superpowers/` に `.gitignore` まだ存在していない場合。

**プラットフォームごとのサーバーの起動:**

**クロード コード:**
```bash
# Default mode works — the script backgrounds the server itself.
scripts/start-server.sh --project-dir /path/to/project --open
```

Windows では、スクリプトが自動検出してフォアグラウンド モードに切り替わります (ツール呼び出しがブロックされます)。使用 `run_in_background: true` Bash ツール呼び出しでサーバーが会話のターンを超えて存続できるようにしてから、読み取ります `$STATE_DIR/server-info` 次のターンで URL とポートを取得します。

**コーデックス:**
```bash
# Codex reaps background processes. The script auto-detects CODEX_CI and
# switches to foreground mode. Run it normally — no extra flags needed.
scripts/start-server.sh --project-dir /path/to/project --open
```

**Gemini CLI:**
```bash
# Use --foreground and set is_background: true on your shell tool call
# so the process survives across turns
scripts/start-server.sh --project-dir /path/to/project --open --foreground
```

**コパイロット CLI:**
```bash
# Start it with Copilot CLI's non-blocking/background shell mechanism so the
# server survives across turns. Keep --foreground so the harness, not the
# script, owns backgrounding. The launcher is a .sh, so invoke it via bash
# (on Windows, call Git Bash's bash.exe from the PowerShell tool).
bash scripts/start-server.sh --project-dir /path/to/project --open --foreground
```

**その他の環境:** サーバーは、会話が切り替わるまでバックグラウンドで実行し続ける必要があります。環境で分離されたプロセスが発生する場合は、次を使用します。 `--foreground` そして、プラットフォームのバックグラウンド実行メカニズムを使用してコマンドを起動します。

URL がブラウザから到達できない場合 (リモート/コンテナ化セットアップでよくあること)、非ループバック ホストをバインドします。

```bash
scripts/start-server.sh \
  --project-dir /path/to/project \
  --host 0.0.0.0 \
  --url-host localhost
```

使用 `--url-host` 返された URL JSON にどのホスト名が出力されるかを制御します。

## ループ

1. **サーバーが動作していることを確認**し、**HTML を新しいファイルに書き込みます** `screen_dir`:
   - **必須: URL を参照したり、画面をプッシュしたりする前に、サーバーが生きていることを確認してください。** 以下を確認してください。 `$STATE_DIR/server-info` 存在し、 `$STATE_DIR/server-stopped` しません。シャットダウンした場合は、次のコマンドで再起動します `start-server.sh` **同じものを使用 `--project-dir`** — 同じポートを再利用するため、ユーザーが開いているタブは自動的に再接続され (サーバーがダウンしている間は「一時停止」オーバーレイが表示されます)、新しい URL を送信する必要はありません。サーバーは 4 時間アイドル状態になると自動的に終了します (次のように構成可能) `--idle-timeout-minutes`）。
   - セマンティックなファイル名を使用します。 `platform.html`、 `visual-style.html`、 `layout.html`
   - **ファイル名は決して再利用しないでください** - 各画面に新しいファイルが取得されます
   - ファイル作成ツールを使用します。 **cat/heredoc は決して使用しないでください** (ターミナルにノイズがダンプされます)
   - サーバーは最新のファイルを自動的に提供します

2. **ユーザーに今後の予定を伝えてターンを終了します:**
   - URL を思い出させます (最初だけでなくすべてのステップで)
   - 画面上の内容をテキストで簡単に要約します (例: 「ホームページの 3 つのレイアウト オプションを表示」)
   - ターミナルで次のように応答するように依頼します。「見てみて、どう思うか教えてください。必要に応じて、クリックしてオプションを選択してください。」

3. **次のターン** — ユーザーが端末で応答した後:
   - 読む `$STATE_DIR/events` 存在する場合 - これには、ユーザーのブラウザー操作 (クリック、選択) が JSON 行として含まれます。
   - ユーザーの端末テキストと結合して全体像を取得します
   - ターミナルメッセージが主要なフィードバックです。 `state_dir/events` 構造化されたインタラクション データを提供します

4. **反復または前進** — フィードバックによって現在の画面が変更された場合は、新しいファイルを書き込みます (例: `layout-v2.html`）。現在のステップが検証された場合にのみ、次の質問に進んでください。

5. **ターミナルに戻るときにアンロード** — 次のステップでブラウザが必要ない場合 (明確な質問、トレードオフの議論など)、待機画面を押して古いコンテンツをクリアします。

   ```html
   <!-- ファイル名:waiting.html (またはwaiting-2.htmlなど) -->
   <div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
     <p class="subtitle">ターミナルで続行します...</p>
   </div>
   「」

   これにより、会話が進んでいる間、ユーザーが解決された選択肢を見つめることができなくなります。次の視覚的な質問が表示されたら、通常どおり新しいコンテンツ ファイルをプッシュします。

6. 完了するまで繰り返します。

## コンテンツフラグメントの書き込み

ページ内に含まれるコンテンツのみを記述します。サーバーは、それをフレーム テンプレートに自動的にラップします (ヘッダー、テーマ CSS、接続ステータス、およびすべてのインタラクティブ インフラストラクチャ)。

**最小限の例:**

```html
<h2>Which layout works better?</h2>
<p class="subtitle">Consider readability and visual hierarchy</p>

<div class="options">
  <div class="option" data-choice="a" onclick="toggleSelect(this)">
    <div class="letter">A</div>
    <div class="content">
      <h3>Single Column</h3>
      <p>Clean, focused reading experience</p>
    </div>
  </div>
  <div class="option" data-choice="b" onclick="toggleSelect(this)">
    <div class="letter">B</div>
    <div class="content">
      <h3>Two Column</h3>
      <p>Sidebar navigation with main content</p>
    </div>
  </div>
</div>
```

それでおしまい。いいえ `<html>`、CSSなし、なし `<script>` タグが必要です。サーバーはそのすべてを提供します。

## 利用可能な CSS クラス

フレーム テンプレートは、コンテンツに次の CSS クラスを提供します。

### オプション (A/B/C の選択)

```html
<div class="options">
  <div class="option" data-choice="a" onclick="toggleSelect(this)">
    <div class="letter">A</div>
    <div class="content">
      <h3>Title</h3>
      <p>Description</p>
    </div>
  </div>
</div>
```

**複数選択:** 追加 `data-multiselect` ユーザーが複数のオプションを選択できるようにコンテナに追加します。クリックするたびに、アイテムの選択したスタイルが切り替わります。

```html
<div class="options" data-multiselect>
  <!-- same option markup — users can select/deselect multiple -->
</div>
```

### カード (ビジュアルデザイン)

```html
<div class="cards">
  <div class="card" data-choice="design1" onclick="toggleSelect(this)">
    <div class="card-image"><!-- mockup content --></div>
    <div class="card-body">
      <h3>Name</h3>
      <p>Description</p>
    </div>
  </div>
</div>
```

### モックアップコンテナ

```html
<div class="mockup">
  <div class="mockup-header">Preview: Dashboard Layout</div>
  <div class="mockup-body"><!-- your mockup HTML --></div>
</div>
```

### 分割ビュー (並べて表示)

```html
<div class="split">
  <div class="mockup"><!-- left --></div>
  <div class="mockup"><!-- right --></div>
</div>
```

### 長所/短所

```html
<div class="pros-cons">
  <div class="pros"><h4>Pros</h4><ul><li>Benefit</li></ul></div>
  <div class="cons"><h4>Cons</h4><ul><li>Drawback</li></ul></div>
</div>
```

### モック要素 (ワイヤーフレーム構成要素)

```html
<div class="mock-nav">Logo | Home | About | Contact</div>
<div style="display: flex;">
  <div class="mock-sidebar">Navigation</div>
  <div class="mock-content">Main content area</div>
</div>
<button class="mock-button">Action Button</button>
<input class="mock-input" placeholder="Input field">
<div class="placeholder">Placeholder area</div>
```

### タイポグラフィとセクション

- `h2` — ページのタイトル
- `h3` — セクション見出し
- `.subtitle` — タイトルの下の二次テキスト
- `.section` — 下マージンのあるコンテンツ ブロック
- `.label` — 小さな大文字のラベルテキスト

## ブラウザイベントの形式

ユーザーがブラウザでオプションをクリックすると、その操作が記録されます。 `$STATE_DIR/events` (1 行に 1 つの JSON オブジェクト)。新しい画面を押すと、ファイルは自動的にクリアされます。

```jsonl
{"type":"click","choice":"a","text":"Option A - Simple Layout","timestamp":1706000101}
{"type":"click","choice":"c","text":"Option C - Complex Grid","timestamp":1706000108}
{"type":"click","choice":"b","text":"Option B - Hybrid","timestamp":1706000115}
```

完全なイベント ストリームには、ユーザーの探索パスが表示されます。ユーザーは、決定する前に複数のオプションをクリックする可能性があります。最後 `choice` 通常、イベントは最終的な選択ですが、クリックのパターンから、尋ねる価値のある躊躇や好みが明らかになる場合があります。

もし `$STATE_DIR/events` 存在しない場合、ユーザーはブラウザを操作しませんでした。端末のテキストのみを使用してください。

## デザインのヒント

- **質問に対するスケールの忠実度** — レイアウトにはワイヤーフレーム、洗練された質問には洗練されたもの
- **各ページの質問の説明** — 「どのレイアウトがよりプロフェッショナルだと感じますか?」 「どれかを選ぶ」だけではなく
- **次に進む前に反復します** — フィードバックによって現在の画面が変更された場合は、新しいバージョンを作成します
- **1 画面あたり最大 2 ～ 4 のオプション**
- **重要な場合は実際のコンテンツを使用してください** — 写真ポートフォリオには、実際の画像 (Unsplash) を使用します。プレースホルダーのコンテンツにより、デザインの問題がわかりにくくなります。
- **モックアップはシンプルにしてください** — ピクセル完璧なデザインではなく、レイアウトと構造に重点を置きます

## ファイルの命名

- セマンティック名を使用します。 `platform.html`、 `visual-style.html`、 `layout.html`
- ファイル名を再利用しないでください。各画面は新しいファイルでなければなりません
- 反復の場合: 次のようなバージョンの接尾辞を追加します。 `layout-v2.html`、 `layout-v3.html`
- サーバーは変更時間ごとに最新のファイルを提供します

## クリーンアップ

```bash
scripts/stop-server.sh $SESSION_DIR
```

セッションが使用された場合 `--project-dir`、モックアップ ファイルは次の場所に保持されます。 `.superpowers/brainstorm/` 後の参考のために。のみ `/tmp` セッションは停止時に削除されます。

## 参照

- フレーム テンプレート (CSS リファレンス): `scripts/frame-template.html`
- ヘルパー スクリプト (クライアント側): `scripts/helper.js`
