# GB10 ×2 ローカルLLM + Claude Code（VS Code）構築手順書

GB10 を2台用意し、1台目に `gpt-oss-120b`、2台目に `Qwen3-Coder-Next` を vLLM で載せ、
LiteLLM で束ねて VS Code の Claude Code からモデルを切り替えて使う手順。

> **関連文書**: GB10 1台を Ollama で直接つなぐ手順は
> [VS CodeのClaude CodeをGB10のQwen3-Coder-Nextへ向ける](../qwen/claude-code-gb10-qwen3-coder-next.md)、
> 1台構成で LiteLLM を挟んでいた旧手順は [claude-code-gb10.md](../claude-code-gb10.md) にある。
> 本書は **2台をモデル名で振り分ける**ためにゲートウェイを置く構成である。

## 1. 構成概要

```
[VS Code + Claude Code 拡張]
          │  Anthropic Messages API (/v1/messages)
          ▼
[LiteLLM ゲートウェイ :4000]   ← GB10-A 上で稼働（別PCでも可）
     │                    │
     ▼                    ▼
[GB10-A :8000]        [GB10-B :8000]
 vLLM                  vLLM
 gpt-oss-120b          qwen3-coder-next
 （設計・レビュー）      （実装・コーディング）
```

| 役割 | ホスト | IP（例） | ポート | served-model-name |
|---|---|---|---|---|
| 設計用LLM | GB10-A | 192.168.10.11 | 8000 | `gpt-oss-120b` |
| コーディング用LLM | GB10-B | 192.168.10.12 | 8000 | `qwen3-coder-next` |
| ゲートウェイ | GB10-A | 192.168.10.11 | 4000 | – |

> **ポイント**: Claude Code の接続先（`ANTHROPIC_BASE_URL`）は1つだけ。2台を束ねるために LiteLLM を挟み、モデル名で振り分ける。

---

## 2. 前提条件

- GB10 ×2（DGX OS、NVIDIA ドライバ・Docker・NVIDIA Container Toolkit 導入済み）
- 両機が同一LANにあり、固定IPを割り当て済み
- Hugging Face アカウント（モデルダウンロード用。必要なら `HF_TOKEN`）
- クライアントPC：VS Code + Claude Code 拡張（**v2.1.129 以降推奨**、後述のモデル自動検出を使う場合）

### vLLM のバージョン・イメージについて
- Qwen3-Coder-Next は **vLLM 0.15.0 以上**が必要。
- GB10（aarch64 / sm121）では vLLM の汎用公式イメージが動かないケースが報告されている。以下のいずれかを使う：
  - NVIDIA NGC の vLLM コンテナ（DGX Spark Playbooks 準拠）
  - コミュニティ版 [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker)
- 以下のコマンド例は `vllm serve` 部分のみ記載。使用するコンテナに合わせて `docker run ... <image> vllm serve ...` の形にする。

---

## 3. GB10-A：gpt-oss-120b の起動

```bash
vllm serve openai/gpt-oss-120b \
  --served-model-name gpt-oss-120b \
  --host 0.0.0.0 --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser openai \
  --reasoning-parser openai_gptoss \
  --enable-prefix-caching \
  --max-model-len 131072 \
  --gpu-memory-utilization 0.80
```

**注意**
- `--served-model-name` は**スラッシュなし**にする（Claude Code は `openai/gpt-oss-120b` のような名前を扱えない）。
- gpt-oss のツール呼び出しは `tool_choice="auto"` のみ対応。
- LiteLLM を同じ GB10-A で動かすので、`--gpu-memory-utilization` はやや控えめに。

---

## 4. GB10-B：Qwen3-Coder-Next の起動

Qwen3-Coder-Next は 80B（MoE）。BF16 だと約160GBで GB10 の128GBに載らないため、**FP8 版**（または AWQ 4bit 版）を使う。

```bash
vllm serve Qwen/Qwen3-Coder-Next-FP8 \
  --served-model-name qwen3-coder-next \
  --host 0.0.0.0 --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --enable-prefix-caching \
  --max-model-len 131072 \
  --gpu-memory-utilization 0.85
```

**注意**
- 公式サンプルの `--tensor-parallel-size 2` は**付けない**（1台構成のため）。
- メモリ不足で起動しない場合は `--max-model-len` を 65536 に下げるか、4bit 量子化版に切り替える。

---

## 5. 各サーバーの動作確認

クライアントPCまたは GB10-A から実行：

```bash
curl http://192.168.10.11:8000/v1/models   # gpt-oss-120b が見えること
curl http://192.168.10.12:8000/v1/models   # qwen3-coder-next が見えること
```

---

## 6. LiteLLM ゲートウェイの構築（GB10-A）

### 6.1 インストール
```bash
pip install 'litellm[proxy]'
# または uv tool install 'litellm[proxy]'
```

### 6.2 設定ファイル
同じフォルダの [litellm-config.yaml](litellm-config.yaml) を配置し、`api_base` の IP と `master_key` を環境に合わせて変更する。

### 6.3 起動
```bash
litellm --config litellm-config.yaml --port 4000
# トラブル時は --detailed_debug を付ける
```

常駐させる場合は systemd サービス化、または Docker（`ghcr.io/berriai/litellm`）で運用する。

### 6.4 動作確認（Anthropic形式）
```bash
for m in gpt-oss-120b qwen3-coder-next; do
  curl -s http://192.168.10.11:4000/v1/messages \
    -H "x-api-key: sk-local-change-me" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "{\"model\":\"$m\",\"max_tokens\":64,\"messages\":[{\"role\":\"user\",\"content\":\"hello\"}]}"
  echo
done
```
両モデルから応答が返ればOK。

---

## 7. クライアント：Claude Code の設定

VS Code 拡張は `~/.claude/settings.json`（Windows では `%USERPROFILE%\.claude\settings.json`）を読む。以下を設定する。

```json
{
  "model": "opusplan",
  "env": {
    "ANTHROPIC_BASE_URL": "http://192.168.10.11:4000",
    "ANTHROPIC_AUTH_TOKEN": "sk-local-change-me",

    "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3-coder-next",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3-coder-next",

    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

| 設定 | 意味 |
|---|---|
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | プルダウンの「Opus」枠 → gpt-oss-120b |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | 「Sonnet」枠 → qwen3-coder-next |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | タイトル生成などの裏方処理 → 軽い qwen3-coder-next |
| `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY` | LiteLLM の `/v1/models` を読み、実モデル名を `/model` ピッカーに「From gateway」として追加（v2.1.129+） |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | テレメトリ等の外部通信を抑止 |
| `"model": "opusplan"` | プランモード＝Opus枠（gpt-oss）、実行＝Sonnet枠（Qwen）に自動切替 |

> Superpowers プラグインや Context7 MCP など既存の設定がある場合は、`env` に追記する形でマージすること。

---

## 8. 使い方：モデルの切り替え

### 方法A：プルダウン / `/model`（手動切替）
- **Opus** を選択 → gpt-oss-120b（設計・レビュー）
- **Sonnet** を選択 → qwen3-coder-next（実装）
- モデル自動検出が有効なら、`gpt-oss-120b` / `qwen3-coder-next` の実名でも選べる

### 方法B：`opusplan`（おすすめ・自動切替）
1. Shift+Tab などでプランモードにし、設計を依頼 → gpt-oss-120b が設計
2. プランを承認して実行 → qwen3-coder-next が実装

---

## 9. 動作確認チェックリスト

- [ ] `curl .../v1/models` で両GB10のモデル名が見える
- [ ] LiteLLM 経由の `/v1/messages` で両モデルが応答する
- [ ] VS Code の Claude Code で `/model` を開き、切り替え候補が表示される
- [ ] Opus 選択時に GB10-A の vLLM ログにリクエストが来る
- [ ] Sonnet 選択時に GB10-B の vLLM ログにリクエストが来る
- [ ] ファイル読み書き・コマンド実行などのツール呼び出しが成功する

---

## 10. トラブルシューティング

| 症状 | 確認ポイント |
|---|---|
| `model not found` | `--served-model-name`・LiteLLM の `model_name`・Claude Code の設定値が完全一致しているか |
| 401 / 認証エラー | `ANTHROPIC_AUTH_TOKEN` と LiteLLM の `master_key` が一致しているか |
| ツールが呼ばれず文章だけ返る | vLLM の `--enable-auto-tool-choice` と `--tool-call-parser`（gpt-oss=`openai`、Qwen=`qwen3_coder`）を確認 |
| 長い会話で途中エラー | `--max-model-len` 超過。値を確認し、Claude Code 側の自動圧縮（`/compact`）を早めに使う |
| Qwen が起動しない（OOM） | FP8 → 4bit 版へ変更、または `--max-model-len` / `--gpu-memory-utilization` を下げる |
| プルダウンに実名が出ない | Claude Code のバージョン（v2.1.129+）と `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` を確認。出なくても Opus/Sonnet 枠で切替可能 |
| 原因不明 | `litellm ... --detailed_debug` でリクエスト/レスポンスを確認 |

---

## 参考
- vLLM: Claude Code integration — https://docs.vllm.ai/en/latest/serving/integrations/claude_code/
- vLLM Recipes: gpt-oss-120b — https://recipes.vllm.ai/openai/gpt-oss-120b
- Qwen3-Coder-Next（Hugging Face）— https://huggingface.co/Qwen/Qwen3-Coder-Next
- LiteLLM: Use Claude Code with Non-Anthropic Models — https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models
- Claude Code: Model configuration — https://code.claude.com/docs/en/model-config
