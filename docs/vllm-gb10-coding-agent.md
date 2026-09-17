# GB10のvLLM + gpt-oss-120b でCodexとClaude Codeを使う

GB10（DGX Spark）に **vLLM** と **`openai/gpt-oss-120b`** を入れ、Windows の VS Code から
**Codex** と **Claude Code** の両方を使えるようにする手順。**MCPは使わない。**

```text
Windows（VS Code）
  ├─ Codex拡張 ──────────── OpenAI互換 /v1 ──────────┐
  └─ Claude Code ── Anthropic /v1/messages ─→ LiteLLM ┤
                                  GB10:4000          │
                                                     ▼
                                          GB10:8000  vLLM
                                                     │
                                          openai/gpt-oss-120b
```

**Codex は vLLM に直結できる。** vLLM が OpenAI 互換APIを出すためである。
**Claude Code だけプロキシが要る。** Claude Code は Anthropic Messages API しか
話さないので、変換する層が1つ要る。MCPは使わないが、ここは避けられない。

> **未検証である。** 手元にGB10が無いため、この手順を通しで実行した記録は無い。
> 各段階に「何が出れば成功か」を書いたので、そこで確かめながら進めること。

## Ollama版との違い

[GB10のOllamaでコーディングエージェントを動かす](gb10-coding-agent.md) との差はここ。

|項目|Ollama版|vLLM版（この文書）|
|---|---|---|
|ポート|11434|8000（vLLM）／4000（LiteLLM）|
|コンテキスト長|`--configure-context` でモデルに焼く|**サーバー起動時の `--max-model-len`**|
|起動補助の `--check` / `--configure-context` / `--probe`|使える|**使えない**（Ollama固有のAPIを叩くため）|
|起動補助の `--setup`|使える|**使える**（Ollamaに触れないため）|
|`wire_api`|`responses`|**`chat` を勧める**（後述）|

**`--setup` だけは使える。** 設定ファイルを組み立てるだけで、Ollamaには一切
アクセスしないためである。確認の3つ（`--check` / `--configure-context` / `--probe`）は
`/api/tags` や `/api/create` を叩くので vLLM では動かない。**代わりに curl で確かめる。**

## 目次

- [1. GB10: vLLMを立てる](#1-gb10-vllmを立てる)
- [2. GB10: 道具呼び出しまで確かめる](#2-gb10-道具呼び出しまで確かめる)
- [3. GB10: Claude Code用のプロキシを立てる](#3-gb10-claude-code用のプロキシを立てる)
- [Windows側に要るもの](#windows側に要るもの)
- [4. Windows: Codexを設定する](#4-windows-codexを設定する)
- [5. Windows: Claude Codeを設定する](#5-windows-claude-codeを設定する)
- [6. 両方を動かして確かめる](#6-両方を動かして確かめる)
- [MCPについて](#mcpについて)
- [元に戻す](#元に戻す)
- [つまずきやすいところ](#つまずきやすいところ)

## 1. GB10: vLLMを立てる

vLLM自体の導入（コンテナの取得、CUDA 13 と `sm_121` の前提、systemd化）は
[GB10サーバーにvLLMを立てる](vllm-gb10.md) にある。ここではコーディング
エージェント向けの起動だけを書く。

```bash
export VLLM_IMAGE=nvcr.io/nvidia/vllm:26.06-py3   # 最新タグはNGCで確認する
export HF_TOKEN="<必要なら>"                       # gpt-oss はゲート無しのはず

docker run -d --name vllm-code --restart unless-stopped \
  --gpus all --ipc=host \
  -p 0.0.0.0:8000:8000 \
  -e HF_TOKEN="${HF_TOKEN}" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ${VLLM_IMAGE} \
  vllm serve openai/gpt-oss-120b \
    --host 0.0.0.0 --port 8000 \
    --served-model-name openai/gpt-oss-120b \
    --tensor-parallel-size 1 \
    --max-model-len 131072 \
    --gpu-memory-utilization 0.85 \
    --max-num-seqs 4 \
    --max-num-batched-tokens 8192 \
    --kv-cache-dtype fp8 \
    --max-cudagraph-capture-size 2048 \
    --stream-interval 20 \
    --no-enable-prefix-caching \
    --tool-call-parser openai \
    --enable-auto-tool-choice \
    --api-key "<十分に長いランダム文字列>"
```

**`--tool-call-parser openai --enable-auto-tool-choice` が要である。** vLLM公式の
gpt-oss recipe が、利用者定義の関数呼び出しにはこの2つが要ると明記している。
**これが無いと、Codex も Claude Code も道具を1つも呼べない。**

そのほかの値の出どころ。

|フラグ|なぜ|
|---|---|
|`--kv-cache-dtype fp8` / `--max-cudagraph-capture-size 2048` / `--max-num-batched-tokens 8192` / `--stream-interval 20` / `--no-enable-prefix-caching`|vLLM recipe の `GPT-OSS_Blackwell.yaml` の内容。**下の注意も読むこと**|
|`--max-model-len 131072`|gpt-oss-120b の上限。KVキャッシュがその分要るので、載らなければ 65536 へ下げる|
|`--gpu-memory-utilization 0.85`|重みがMXFP4で約60GiB。128GBの85%＝約109GBを上限にする。OOMするなら下げる|
|`--max-num-seqs 4`|1人がエージェントを回す前提。同時利用者が増えるなら上げる|
|`--api-key`|**vLLMは既定で無認証。** LANへ開くなら必ず付ける|

> **recipe の Blackwell 判定はGB10に当たらない。** 公式の `launch_server.sh` は
> `compute_cap` が **10.0**（B200/GB200）のときだけ Blackwell 用の設定と
> `VLLM_USE_FLASHINFER_MOE_MXFP4_MXFP8=1` を選ぶ。**GB10 は 12.1 なので、
> あの分岐ではHopper側に落ちる。** 上のフラグは Blackwell 用の内容を手で
> 書き写したもので、環境変数のほうは**GB10で効くか分からないので入れていない**。
> 試すなら1つずつ足して、速度を測ってから残すこと。

起動を待つ。

```bash
timeout 1800 bash -c 'until curl -sf http://localhost:8000/health > /dev/null; do sleep 10; done' \
  || docker logs vllm-code | tail -50
```

`--no-enable-prefix-caching` は recipe の指定に従っている。エージェントは毎ターン
履歴を送り直すので prefix caching が効きそうに見えるが、**gpt-oss では推奨構成から
外されている。** 速度に不満が出たら、そこを外して測り比べる余地がある。

## 2. GB10: 道具呼び出しまで確かめる

**クライアントを設定する前に、ここで確かめる。** 通らなければ、Codex も Claude Code も
設定では直せない。

```bash
KEY=<--api-key に渡した値>

# まず疎通
curl -s http://localhost:8000/v1/models -H "Authorization: Bearer $KEY" | head -c 400

# 生成
curl -s http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-oss-120b","messages":[{"role":"user","content":"12*17"}],"max_tokens":128}'
```

**道具呼び出し。ここがこの手順の関門である。**

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-120b",
    "max_tokens": 256,
    "tools": [{
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Read a file from the workspace.",
        "parameters": {
          "type": "object",
          "properties": {"path": {"type": "string"}},
          "required": ["path"]
        }
      }
    }],
    "tool_choice": "auto",
    "messages": [{"role":"user","content":"README.md の中身を見てほしい"}]
  }'
```

応答に `tool_calls` があり、`function.arguments` が**解釈できるJSON**であること。

- `tool_calls` が返らない → `--tool-call-parser openai --enable-auto-tool-choice` を確認する
- 返るが `arguments` が壊れている → **この構成の限界である。** DGX Spark上で
  エージェント用途を比べた外部のベンチマークでも、gpt-oss:120b がツール呼び出しで
  不正なJSONを出して失敗したという報告がある。設定では直らない

Windows側から届くことも確かめる。

```powershell
curl.exe -H "Authorization: Bearer <KEY>" http://<GB10のIP>:8000/v1/models
```

## 3. GB10: Claude Code用のプロキシを立てる

**Codexしか使わないなら、この節は飛ばしてよい。**

Claude Code は Anthropic Messages API しか話さないので、LiteLLM を1つ挟む。
vLLM は `127.0.0.1` に閉じたままでもよいが、Codex が直接叩く以上どのみち
8000番は開いているので、ここでは同じGB10の上で並べる。

```bash
python3 -m venv ~/litellm && ~/litellm/bin/pip install 'litellm[proxy]'
```

`~/litellm/config.yaml`:

```yaml
model_list:
  - model_name: gpt-oss-120b
    litellm_params:
      # vLLM は hosted_vllm/ を付ける。api_base は /v1 まで。
      model: hosted_vllm/openai/gpt-oss-120b
      api_base: http://127.0.0.1:8000/v1
      api_key: os.environ/VLLM_API_KEY

litellm_settings:
  # Claude Code が送るが vLLM が解さないパラメータを落とす。
  drop_params: true

general_settings:
  master_key: sk-<別の十分に長いランダム文字列>
```

```bash
export VLLM_API_KEY=<vLLMの --api-key と同じ値>
~/litellm/bin/litellm --config ~/litellm/config.yaml --host 0.0.0.0 --port 4000
```

**キーは2本ある。** vLLM の `--api-key`（LiteLLM→vLLM）と、LiteLLM の
`master_key`（Claude Code→LiteLLM）。**同じ値にしない。** 片方が漏れたときに
もう片方で止まる。

Anthropic形式で通るか確かめる。

```bash
curl http://127.0.0.1:4000/v1/messages \
  -H "x-api-key: sk-<master_key>" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"gpt-oss-120b","max_tokens":128,"messages":[{"role":"user","content":"12*17"}]}'
```

## Windows側に要るもの

**使うエージェントによって、要るものが違う。** 片方しか使わないなら、もう片方の
行は不要である。

|用途|要るもの|
|---|---|
|**Codex**|このリポジトリ一式、**Python 3.13（`myvenv313`）**、`requests` と `python-dotenv`、`.env`、Superpowers 6.3.0、VS Code + Codex拡張|
|**Claude Code**|**Node.js / npm**（`@anthropic-ai/claude-code`）、VS Code + Claude Code拡張、`%USERPROFILE%\.claude\settings.json`|

**Claude Code 側に Python は要らない。** 設定は `settings.json` に書くだけで、
このリポジトリも使わない。**Codex 側だけが起動補助（Python）を使う。**

Codex用の最小構成はこれで足りる。`requirements.txt` の全部（pymupdf・streamlit・
onnxruntime など）はRAGアプリ用で、起動補助は触らない。

```powershell
py -3.13 -m venv myvenv313
.\myvenv313\Scripts\python.exe -m pip install requests python-dotenv
```

**Codex でも Python を入れたくないなら**、`config.toml` と `models.json` を
`%USERPROFILE%\.codex\` に手で置く道がある。落ちるものと注意点は
[Ollama版の6.5節](gb10-coding-agent.md#起動補助を使わずに手で書く)と同じ。

## 4. Windows: Codexを設定する

`.env` の接続先を vLLM に向ける。**ポートが 11434 ではなく 8000 になる。**

```dotenv
OLLAMA_HOST=http://<GB10のIP>:8000
```

> 変数名が `OLLAMA_` のままなのは、この名前で `.env` を書いている環境が既に
> あるためである。中身は「推論サーバーのルートURL」で、Ollamaに限らない。

vLLM には `--api-key` を付けたので、キーも書く。

```dotenv
OLLAMA_API_KEY=<vLLMの --api-key と同じ値>
```

設定を作る。**`--setup` だけを使う。** 他のサブコマンドは Ollama 固有のAPIを
叩くので、vLLM では動かない。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup `
  --model openai/gpt-oss-120b --context-size 131072 --wire-api chat
```

### `--wire-api chat` を選ぶ理由

既定は `responses`（Ollama 相手に使ってきた経路）だが、**vLLM では `chat` を
勧める**。vLLM公式の gpt-oss recipe が Responses API の制限として、

> Streaming is fairly barebone at the moment / Tool invocation and output are not
> properly streamed, rather batched.

と明記している。**道具の呼び出しと結果がまとめて返る**のは、エージェントの
用途では効いてくる。`chat` で不満が出たら `--wire-api responses` を試す、の順にする。

### 生成される config.toml

```toml
# BEGIN LOCAL_LLM_MANAGED_CONFIG
model = "openai/gpt-oss-120b"
model_provider = "colab-oss"
model_catalog_json = "C:\\Users\\you\\AppData\\Local\\local-llm\\coding-agent\\codex\\models.json"
model_context_window = 131072
model_auto_compact_token_limit = 98304
...
[model_providers.colab-oss]
name = "Local openai/gpt-oss-120b"
base_url = "http://192.168.1.50:8000/v1"
wire_api = "chat"
requires_openai_auth = false

[model_providers.colab-oss.env_http_headers]
X-API-Key = "OLLAMA_API_KEY"
...
```

`models.json` の `slug` も `openai/gpt-oss-120b` になり、`config.toml` の `model` と
揃う。**食い違うとCodexはモデルを見つけられない**ので、ここは自動で揃うようにしてある。
各キーの意味は [Ollama版の6.5節](gb10-coding-agent.md#65-configtoml-の中身) と同じ。

> **キーの渡り方に1つ弱点がある。** 起動補助は `X-API-Key` ヘッダーで送る形しか
> 持たないが、vLLM が見るのは `Authorization: Bearer` である。`--setup` だけを
> 使ってVS Codeを手で開く場合、`OLLAMA_API_KEY` はプロセスに渡らない。
> **確実なのは、vLLM を `--api-key` 無しで立て、到達範囲をファイアウォールで
> 絞ることである**（LAN内のOllamaと同じ扱い）。認証を残したいなら、
> `# END LOCAL_LLM_MANAGED_CONFIG` より後ろに `[model_providers.colab-oss.http_headers]`
> で `Authorization` を直接書く。**その場合キーが平文で設定ファイルに残る**ので、
> ファイルの権限に注意する。

起動する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup
```

を済ませたうえで、VS Code を開く。`--setup` を付けずに実行すると起動補助が
`--check`（Ollama固有）を呼ぶため、**vLLMでは必ず `--setup` で止める。**
VS Code は手で開き、`CODEX_HOME` を指定する。

```powershell
$env:CODEX_HOME = "$env:LOCALAPPDATA\local-llm\coding-agent\codex"
code .
```

## 5. Windows: Claude Codeを設定する

VS Code の拡張機能から **Claude Code** を入れ、CLIも入れる。

```powershell
npm install -g @anthropic-ai/claude-code
```

`%USERPROFILE%\.claude\settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://192.168.1.50:4000",
    "ANTHROPIC_AUTH_TOKEN": "sk-<LiteLLMのmaster_key>",
    "ANTHROPIC_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-oss-120b",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_TELEMETRY": "1"
  }
}
```

要点は [Claude Code をGB10へ向ける](claude-code-gb10.md#5-windows側-接続先を設定する)
と同じ。**`ANTHROPIC_BASE_URL` に `/v1` を付けない**、**`ANTHROPIC_DEFAULT_HAIKU_MODEL`
を忘れない**（裏で走る処理に使われる）、**`ANTHROPIC_API_KEY` は設定しない**。

設定したら **VS Code を再起動する。**

## 6. 両方を動かして確かめる

同じ問いを両方に投げて、**ファイルを実際に読みに行くか**を見る。

```
このリポジトリの ingest/backend.py が何をしているか、ファイルを読んで説明して
```

読まずに一般論を答えるなら、道具呼び出しが効いていない。2節のcurlに戻る。

GB10側で、どちらの経路も同じvLLMに載っていることを確かめる。

```bash
docker logs --tail 20 vllm-code     # 両方のリクエストがここに出る
nvidia-smi                          # ユニファイドメモリの使用量
```

**片方だけ動く場合の切り分けは早い。** Codex が動いて Claude Code が動かないなら、
差はLiteLLMだけである（3節のcurl）。両方動かないなら、vLLM側（2節のcurl）。

## MCPについて

この構成では MCP を使わない。関係するのは2点だけ。

- **Claude Code** — `ANTHROPIC_BASE_URL` が Anthropic 以外を指すとき、MCP tool search は
  自分で無効になる。今回は使わないので都合がよい
- **Codex** — `config.toml` に `[mcp_servers.*]` を書かなければ何も起動しない。
  書く場合は `# END LOCAL_LLM_MANAGED_CONFIG` より後ろに置く

vLLM 側の `--tool-server` も使わない。あれは gpt-oss の組み込み道具（ブラウザ、
Python実行）をvLLM自身がMCPクライアントとして呼ぶ仕掛けで、**コード編集には要らない。**

## 元に戻す

**GB10側に後始末は要らない。** コンテキスト長はサーバー起動時の `--max-model-len` で
決まり、**モデル自体を書き換えていない**ためである。コンテナを止めれば元に戻る。

```bash
docker rm -f vllm-code      # 必要なら litellm も止める
```

Ollama版はここが違う。`--configure-context` が同名のモデルを `num_ctx` 焼き込みで
作り直すので、**共有サーバー上の状態が変わったままになる**。使うのをやめるときは
`--restore-context` が要る（[Ollama版の「元に戻す」](gb10-coding-agent.md#元に戻す)）。

クライアント側は、Ollama版・vLLM版どちらでも同じである。`.env` の接続先を書き戻し、
`--setup` をやり直す。Claude Code は `settings.json` の `env` ブロックを消すか、
値を書き戻す。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|`--check` が Connection refused|vLLMに `/api/version` は無い|**vLLMでは `--setup` だけを使う。** 確認は2節のcurl|
|`--configure-context` が失敗する|vLLMに `/api/create` は無い|コンテキスト長は vLLM の `--max-model-len` で決める|
|Codexが401|`Authorization: Bearer` が渡っていない|4節の但し書きを読む。vLLMを `--api-key` 無しで立てるのが確実|
|道具を呼ばない|`--tool-call-parser` / `--enable-auto-tool-choice` 未指定|1節のフラグを確認。2節のcurlで切り分ける|
|Claude Codeだけ動かない|LiteLLM|3節のcurl。`model_name` と `ANTHROPIC_MODEL` の一致を見る|
|起動時にOOM|`--max-model-len` か `--gpu-memory-utilization` が大きい|`--max-model-len 65536` へ下げる。それでも駄目なら `--max-num-batched-tokens` を下げる|
|応答が遅い|GB10のメモリ帯域（約273GB/s）が律速|[vllm-gb10.md の帯域の節](vllm-gb10.md#gb10で先に知っておくこと)。設定では埋まらない|

## Ollama版とどちらを使うか

|観点|Ollama版|vLLM版|
|---|---|---|
|手順の短さ|**短い**（`--check` / `--probe` で確認まで自動）|長い（curlで自分で確かめる）|
|実配置の確認|`--probe` が `fully_on_gpu` を見る|`nvidia-smi` と起動ログを自分で読む|
|多重実行|1人向け|**強い**（継続バッチング）|
|Claude Code|プロキシが要る|**同じくプロキシが要る**|

**1人で使うなら Ollama版で足りる。** vLLM を選ぶ理由は、複数人が同時に叩く場合か、
RAG など他の用途と同じサーバーを共有したい場合である。

## 関連

- [GB10のOllamaでコーディングエージェントを動かす](gb10-coding-agent.md)
- [VS CodeのClaude CodeをGB10へ向ける](claude-code-gb10.md) — Ollama版のプロキシ構成
- [GB10サーバーにvLLMを立てる](vllm-gb10.md) — vLLM自体の導入、コンテナ、systemd
- [vLLM GPT-OSS recipe](https://github.com/vllm-project/recipes/blob/main/OpenAI/GPT-OSS.md) — 起動フラグとBlackwell設定の出どころ
