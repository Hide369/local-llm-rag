# Claude Code から context7 を使う

クライアントPCの Claude Code（VS Code 拡張・CLI 共通）に context7 を登録し、
社内固有の情報をクエリに含めないルールを効かせるまでの手順である。モデルが GB10 の
ローカル LLM であっても、context7 の MCP サーバへ繋ぐのは **クライアントPC** で
ある。GB10 側の設定は変えない。

Codex 版の登録手順は [mcp-server.md](mcp-server.md) の「`~/.codex/config.toml` への
登録」にある。Claude Code 自体の導入と `CLAUDE.md` の置き場所は
[claude-code-vscode.md](claude-code-vscode.md) にある。

## 前提

- Claude Code の CLI が入っている（`claude --version` が通る。拡張機能だけでは
  `claude` コマンドは使えない。[claude-code-vscode.md](claude-code-vscode.md) 第1章）
- クライアントPCから `https://mcp.context7.com` へ HTTPS で出られる

## 何が外へ出るか

context7 は社外のサービスである。登録する前に、送るものと送らないものを把握しておく。

| 送られる | 送られない |
| --- | --- |
| モデルが組み立てた検索文（`query`） | 元のプロンプト全文 |
| ライブラリ名または ID（`libraryName` / `libraryId`） | ソースコード・開いているファイル |
| API キー、MCP クライアント名とバージョン | 会話履歴 |

送った `query` は次のように扱われる（[Context7: Data Privacy](https://context7.com/docs/security/data-privacy)）。

- 結果の並べ替えのため、先方が使う外部 LLM（OpenAI・Google Gemini・Anthropic）に渡る
- 精度改善のため匿名で保存される。API ログは30日保持される
- 機密を除いた検索文にする、という歯止めは**ツール説明文の指示をモデルが守ること**に
  依存している。ローカル LLM がこれを確実に守る保証はない

このため、本リポジトリでは `AGENTS.md` の「外部ドキュメントの参照」節に、クエリへ
書いてよいもの・いけないものを明示している（第3章）。クエリの送信自体を社内規程が
許さない場合は context7 を使わず、`scripts/fetch_docs.py` で公式ドキュメントを
取り込んでローカルの `search_documents` で引く。

## 1. API キーを用意する

[Context7 のダッシュボード](https://context7.com/dashboard)で発行する。キーは
`ctx7sk-` で始まり、無償で取得できる。未設定でも動作するが、レート制限が厳しくなる。

キーは Windows の環境変数に置き、設定ファイルには値を書かない（Codex 版と同じ方針。
[mcp-server.md](mcp-server.md) の「context7 の API キーは値を書かない」）。

```powershell
setx CONTEXT7_API_KEY "ctx7sk-..."
```

`setx` は**それ以降に起動したプロセス**にしか効かない。VS Code とターミナルを
すべて閉じてから開き直す。

```powershell
# 開き直したターミナルで確認する
$env:CONTEXT7_API_KEY
```

## 2. context7 を登録する

統合ターミナルで、`user` スコープ（そのPCの全リポジトリ）に登録する。

```powershell
claude mcp add --transport http --scope user context7 https://mcp.context7.com/mcp --header 'CONTEXT7_API_KEY: ${CONTEXT7_API_KEY}'
```

- **ヘッダの値は必ずシングルクォートで囲む。** ダブルクォートだと PowerShell が
  `${CONTEXT7_API_KEY}` をその場で展開し、キーの値が `~/.claude.json` に平文で
  残る。シングルクォートなら `${CONTEXT7_API_KEY}` という文字列のまま保存され、
  Claude Code が起動時に環境変数から展開する
- `npx` 方式（`@upstash/context7-mcp`）ではなく `url` 方式を使う理由は Codex 版と
  同じで、Windows での `npx.cmd` の躓きを避けるためである
- `npx ctx7 setup --claude` でも登録できるが、OAuth で発行したキーを設定ファイルに
  直接書き込み、スキルも追加する。キーの置き場所を揃えるため、本リポジトリでは
  上のコマンドを使う
- プラグイン版（`/plugin install context7@context7-marketplace`）は
  `CONTEXT7_API_KEY` を読まない。本手順では使わない

`project` スコープ（`.mcp.json`）にはしない。context7 はリポジトリを問わず使う
ものであり、キーの扱いを各リポジトリに持ち込む理由がない。

### 登録できたか確かめる

```powershell
claude mcp list
```

`context7` が **Connected** で出れば正しい。

## 3. ルールを効かせる

MCP の登録が教えるのは接続先だけである。**いつ context7 を使うか**と、**クエリに
何を書いてはいけないか**は、`CLAUDE.md` で教える。

### 本リポジトリで開発する人

追加の作業はない。リポジトリ直下の `CLAUDE.md` が `@AGENTS.md` を取り込んでおり、
`AGENTS.md` の「外部ドキュメントの参照」節にルールが書いてある。ルールを変えるときは
`AGENTS.md` 側を直す（二重管理にしない）。

### 別のリポジトリでも使う人：`~/.claude/CLAUDE.md`

context7 は `user` スコープで登録したので、他のリポジトリでも呼ばれる。そこでも
ルールが効くよう、`~/.claude/CLAUDE.md` に `AGENTS.md` の「外部ドキュメントの参照」
節から、先頭の2項目（`context7` で調べること、社内固有の情報をクエリに含めないこと
とその下の箇条書き）を貼る。**既にファイルがある場合は追記する（上書きしない）。**

```powershell
notepad $env:USERPROFILE\.claude\CLAUDE.md
```

リランカーの HEAD・`fetch_docs.py`・`OLLAMA_HOST` の項は本リポジトリ固有の説明で
あり、貼らなくてよい。

## 4. 動作確認

Claude Code を開き直し、新しい会話で次の順に確かめる。

1. `/mcp` で `context7` が **Connected** であることを見る
2. `/context` の **Memory files** に、ルールを書いた `CLAUDE.md` が出ることを見る
3. 普通に引けるか確かめる

   ```text
   use context7 with /vercel/next.js for app router setup
   ```

   `resolve-library-id` / `query-docs` のツール呼び出しが出れば接続は正しい
4. **社内の語が漏れないか確かめる。** わざと社内の語を混ぜて頼む

   ```text
   local-llm-rag の retriever.py で使っている chromadb の検索を速くしたい。context7 で調べて
   ```

   ツール呼び出しを展開し、`query` 引数に `local-llm-rag` や `retriever.py` が
   **含まれず**、`chromadb query performance` のような一般的な表現になっていれば
   合格である

4 で社内の語が混ざる場合は、`AGENTS.md` の NG/OK 例を、実際に混ざった語に近い
ものへ増やして再試験する。それでも混ざるモデルでは、`CLAUDE.md` は強制ではない
ことを踏まえ、context7 を使わない運用（`scripts/fetch_docs.py` で取り込んだ
ローカルの技術ドキュメントを引く）に切り替える。

## 5. うまくいかないとき

| 症状 | 原因と対処 |
| --- | --- |
| `/mcp` で `Failed`、または 401 | 環境変数が Claude Code に渡っていない。`setx` 後に VS Code を全部閉じたか確かめる。`$env:CONTEXT7_API_KEY` が空なら第1章からやり直す |
| 起動時に設定の読み込みエラー | `${CONTEXT7_API_KEY}` を参照しているのに環境変数が未設定である。キーを設定するか、キー無しで使うなら `--header` を付けずに登録し直す（`claude mcp remove context7 --scope user`） |
| `~/.claude.json` にキーの値が書かれている | 登録時にダブルクォートを使った。削除して第2章のコマンドで登録し直す |
| ツールが呼ばれず、モデルの知識だけで答える | `CLAUDE.md` のルールが読まれていない（`/context` で確認）。読まれているのに呼ばれない場合は [mcp-tool-not-called.md](mcp-tool-not-called.md) を見る |
| 429（レート制限） | API キー未設定、または無償枠の上限。キーを設定する |

## 制限

- `CLAUDE.md` のルールは強制ではない。クエリから社内の語を除くのはモデルの判断で
  あり、第4章の試験に通っても毎回の遵守は保証されない
- 送った `query` は先方に保存される。保存の無効化は Enterprise プランの機能である
- 完全に閉じた環境が要る場合は、context7 ではなく `scripts/fetch_docs.py` による
  取り込み（`docs/superpowers/specs/2026-09-12-latest-docs-ingestion-design.md`）を使う
