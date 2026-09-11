# MCPのツールが呼ばれないときの切り分け

Codex から社内資料の MCP サーバへ接続できているのに、`search_documents` が一度も
呼ばれず DB を検索できない、という症状の調べ方である。

サーバの構築手順は [mcp-server-network.md](mcp-server-network.md)（複数PC・HTTP）と
[mcp-server.md](mcp-server.md)（1台・stdio）にある。本書は、そこまで済んだうえで
ツールが呼ばれない場合を扱う。

## 症状

- Codex からプロンプトを送るとサーバには到達する
- モデルに「使えるツールを列挙して」と頼むと `mcp__..._search_documents` が挙がる
- しかし実際の質問では一度も呼ばれず、モデルが自分の知識で答える
- ツール名を明示して「これを使え」と頼んでも呼ばれない

## 先に読むこと

**「ツールが列挙できる」ことは「呼べる」ことの証明にならない。** Codex が MCP ツールの
一覧をプロンプトの文章として入れていれば、モデルは名前を復唱できる。しかし
`tools` 配列に入っていなければ呼びようがない。この2つは別の事実である。

**サーバのログでは判別できない。** アクセスログはどの JSON-RPC メソッドが来たかを
区別しない。接続の握手（`initialize` / `tools/list`）も実際の検索（`tools/call`）も
同じ1行に見える。

```text
INFO:  127.0.0.1:61507 - "POST /mcp HTTP/1.1" 200 OK   ← initialize
INFO:  127.0.0.1:61507 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:  127.0.0.1:61507 - "POST /mcp HTTP/1.1" 200 OK   ← tools/list
INFO:  127.0.0.1:61507 - "POST /mcp HTTP/1.1" 200 OK   ← tools/call
```

握手は接続した時点で必ず起きるので、ツールが1度も呼ばれなくても到達記録は残る。

## 測定済みの事実（2026-09-11、Colab L4 / gpt-oss:20b）

**次の項目は調査済みである。同じことを繰り返さないこと。** 環境が変わったときだけ
測り直せばよい。

| 容疑者 | 判定 | 根拠 |
| --- | --- | --- |
| MCPサーバの広告と検索 | 無実 | HTTPで直接叩き、`tools/list` が正しいスキーマを返し、`tools/call` が実DBから4件返した |
| モデルの function call 能力 | 無実 | `--probe` のツール往復が成功 |
| `mcp__` 接頭辞つきの長い名前 | 無実 | `mcp__local_docs__search_documents` で自発的に呼んだ |
| 日本語の説明文・実物のスキーマ | 無実 | 実物と同じ説明・スキーマで14/15回呼んだ |
| コンテキスト長の不足 | 無実 | `/v1/responses` 経由（num_ctxを渡す口が無い）でも65536で読み込まれた |
| VRAM | ほぼ無実 | 64k・完全GPU配置で実測12.1 GiB。24GBあれば足りる |

つまり **正しく渡せばモデルは呼ぶ**。残る未知は「Codex が渡しているか」だけである。

### 呼び出しには揺れがある

同一の payload でも毎回呼ぶとは限らない。実測は 14/15（約93%）で、2/3 に落ちた
回もあった。gpt-oss:20b にはパラメータとして `temperature 1` が焼き込まれている
（`/api/show` で確認できる）。

ただし **93%と「一度も呼ばれない」は違う症状である。** 揺れを理由にしないこと。

## 手順1: サーバ側を確かめる

クライアントを介さず、HTTP で直接叩く。ここが通ればサーバは無実である。

```powershell
# 1. initialize（セッションIDを取る）
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
$r = Invoke-WebRequest -Uri http://<サーバIP>:8080/mcp -Method Post -Body $body `
  -ContentType "application/json" -Headers @{ Accept = "application/json, text/event-stream" }
$r.Headers["mcp-session-id"]
```

`serverInfo` に `local_docs` が含まれれば正しい。パスは `/mcp` である。`/` に投げると
404 になる。

**応答は SSE（`text/event-stream`）で返る。** 1つのイベントが複数の `data:` 行に
分かれることがあるので、先頭行だけを読むと JSON が途中で切れる。行を連結してから
解釈すること。文字コードは UTF-8 である。ライブラリの推測に任せると日本語が化ける。

## 手順2: モデル側を確かめる

Colab 経由で使っている場合は、このリポジトリの診断が使える。

```powershell
# 接続・モデル能力（推論しない）
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --check

# GPU配置・コンテキスト長・ツール往復を一度に見る
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe
```

`--check` の `capabilities` に `tools` があること、`--probe` の
`tools.completed` が `true` になることを見る。

ローカルの Ollama を使っている場合は、実際の配置を直接見る。

```powershell
ollama ps
nvidia-smi
```

`PROCESSOR` が `100% GPU` でなく、`CONTEXT` が極端に小さければ、そこが原因の
可能性がある。gpt-oss:20b は 64k・完全GPU配置で約12.1 GiB を使う。

### コンテキスト長についての注意

`--probe` は Ollama の**ネイティブAPI**で `options: {num_ctx: 65536}` を明示的に
渡している。一方 **Codex は `/v1/responses`（OpenAI互換）を使い、この API に
`num_ctx` は無い。** Codex からコンテキスト長を要求する手段は存在しない。

したがって `--probe` が64kを報告しても、Codex が同じ値で動く保証はない。両者を
一致させるのが `--configure-context` であり、`/api/create` で `num_ctx` を
モデル自体に焼き込む。**Ollama を動かしている機械ごとに実行が要る。**

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context
```

焼かれているかは `/api/show` の `parameters` に `num_ctx` があるかで分かる。
バックアップモデル `gpt-oss:20b-before-coding-agent` の有無でも判断できる。

ただし実測では、焼いていなくても Ollama は既定で65536を確保した。**この項目は
「確認すべき」であって「必ず原因」ではない。**

## 手順3: Codexが何を送っているかを見る

ここまでで原因が出なければ、送信内容を直接観測する。推測を重ねないこと。

[scripts/proxy_log.py](../scripts/proxy_log.py) を Codex と Ollama の間に挟む。
このファイルは単体で動き、プロジェクトの他のモジュールを import しない。
**Codex が動いている機械へこの1枚だけコピーすればよい**（Python と requests だけ要る）。

### 手順

1. プロキシを起動する（別ウィンドウ）

```powershell
python proxy_log.py
# 上流が別の場所にあるなら
python proxy_log.py --upstream https://<ngrokのURL>
```

2. `~/.codex/config.toml` の `base_url` をプロキシへ向ける。**元の値を控えておく。**

```toml
[model_providers.<名前>]
base_url = "http://127.0.0.1:11500/v1"
```

3. Codex から1回質問する

```text
社内資料で懲戒解雇について調べて
```

4. `proxy_log.txt` を読む

5. **`base_url` を元に戻す**

### ログの読み方

ツールが渡されており、モデルが呼んだ場合:

```text
[23:59:10] --- POST /v1/responses ---
[23:59:10]   model='gpt-oss:20b'  stream=True  本文=821バイト
[23:59:10]   tools配列: 1件
[23:59:10]     - mcp__local_docs__search_documents  (type=function) ← これ
[23:59:14]   ✅ モデルが呼んだツール: ['mcp__local_docs__search_documents']
```

判定は次のとおりである。

| ログ | 意味 | 次にすること |
| --- | --- | --- |
| `★ ツールが1件も入っていない` | Codex がツールを渡していない | Codex 側の設定を疑う（下記） |
| `★ search_documents が tools に無い` | 他のツールは渡しているが MCP ツールだけ落ちている | MCP サーバの登録と承認設定を疑う |
| ツールは載っているが `❌ モデルはツールを呼ばなかった` | 渡してはいる | ツール数・instructions の長さ・temperature を疑う |

**本文の全文は記録しない。** 社内資料の断片や API キーが混ざりうるためで、ツール名と
件数、入力の長さだけを出す。今回の判定にはそれで足りる。

## 設定を置く場所を間違えていないか

`~/.codex/AGENTS.md` に「社内資料の参照」節を置く指示が
[mcp-server-network.md](mcp-server-network.md) にあるが、**これが読まれない起動経路が
存在する。**

`scripts/coding_agent.py` で VS Code を起動した場合、`CODEX_HOME` が専用フォルダ
（`%LOCALAPPDATA%\local-llm\coding-agent\...\codex`）へ差し替えられる
（`coding_agent/environment.py` の `child_env.update({"CODEX_HOME": ...})`）。
この経路では `~/.codex/config.toml` も `~/.codex/AGENTS.md` も一切読まれない。

| 起動経路 | 読まれる設定 |
| --- | --- |
| 通常の VS Code / Codex | `~/.codex/config.toml`、`~/.codex/AGENTS.md` |
| `scripts.coding_agent` 経由 | `%LOCALAPPDATA%\local-llm\coding-agent\...\codex\` 配下 |

どちらを使っているかで、設定を直す場所が変わる。後者では
`infra/codex-colab/models.json` の `experimental_supported_tools` と、コーディングに
寄った `base_instructions` も効く。前者では効かない。

## ツールを呼ぶ判断はどこにあるか

`config.toml` が教えるのは接続先だけである。**どの質問で検索するか**はエージェントの
判断であり、ツールの説明文（「社内資料を検索し、根拠となる原文を出典つきで返す」）は
呼ぶべき条件を含まない。

その判断を与えるのが `AGENTS.md` の「社内資料の参照」節である。置き場所は上表の
とおり起動経路による。

ただし **ツール名を明示して頼んでも呼ばれないなら、この節の問題ではない。**
その場合は手順3へ進むこと。

## まだ潰せていないもの

2026-09-11 時点で、次は未確認である。

- 移植先（クライアント機）の `ollama ps` による実コンテキスト長と GPU 配置
- Codex が実際に送っている `tools` 配列の中身（手順3で確定する）
- Codex が同時に渡すツールの数と instructions の長さが、20Bクラスのモデルの
  ツール選択に与える影響

最後の項目は、モデルを増強すると改善が見込める部類である。ツール選択は規模と
訓練に強く依存する能力であり、現構成で完全に詰め切れない可能性は残る。
