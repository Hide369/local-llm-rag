はい。現在の **GB10 + Ollama + gpt-oss:120b** から、

**Ollama停止 → gpt-oss:120b削除 → llama.cpp導入 → Qwen3-Coder-Next Q4_K_Mを256Kで起動 → systemd常駐 → VS CodeのCodexから接続**

までを一気に構築できます。

一点重要なのは、現在のCodexはResponses APIを使うため、`llama-server`も**Responses API対応版**を使う必要があります。現在のllama.cppには `/v1/responses` が実装されています。([GitHub][1])

---

# 1. 最終構成

GB10側：

```text
┌────────────────────────────────────────────┐
│                  GB10                      │
│                                            │
│  systemd                                  │
│     │                                      │
│     ↓                                      │
│  llama-server                              │
│     │                                      │
│     ├─ Qwen3-Coder-Next Q4_K_M             │
│     ├─ Context = 256K                      │
│     ├─ Flash Attention                     │
│     ├─ GPU Offload                         │
│     └─ OpenAI Responses API                │
│                                            │
│        http://GB10-IP:4000/v1             │
└───────────────────┬────────────────────────┘
                    │
                    │ LAN
                    ↓
          ┌─────────────────────┐
          │ VS Code             │
          │ Codex               │
          │                     │
          │ config.toml         │
          └─────────────────────┘
```

Qwen公式も `Qwen3-Coder-Next-GGUF:Q4_K_M` をllama.cppから直接取得して起動する方法を案内しています。([Hugging Face][2])

---

# 2. GB10側の完全自動セットアップ

今回は**systemdから確実に実行できるように、llama.cppの実体を `/opt/llama.cpp` に配置**する方式をおすすめします。

また、Qwen3-Coder-NextはCodexからツール呼び出しを行うため、`--jinja`を有効にします。

### `setup_qwen_coder.sh`

```bash
#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# Configuration
# ============================================================

INSTALL_DIR="/opt/llama.cpp"
CACHE_DIR="/opt/llama-cache"

SERVICE_NAME="qwen3-coder"
SERVICE_USER="llama"

MODEL="Qwen/Qwen3-Coder-Next-GGUF:Q4_K_M"
MODEL_ALIAS="qwen3-coder-next"

HOST="0.0.0.0"
PORT="4000"

# 256K Context
CTX_SIZE="262144"

# Single Coding Agent
PARALLEL="1"

# ============================================================
# Root check
# ============================================================

if [[ "$EUID" -ne 0 ]]; then
    echo "Please run as root:"
    echo "  sudo bash $0"
    exit 1
fi

echo
echo "============================================================"
echo " Qwen3-Coder-Next / GB10 Setup"
echo "============================================================"
echo

# ============================================================
# 1. Stop current Ollama model
# ============================================================

echo "[1/8] Stopping Ollama model..."

if command -v ollama >/dev/null 2>&1; then
    ollama stop gpt-oss:120b 2>/dev/null || true
fi

# ============================================================
# 2. Remove gpt-oss:120b
# ============================================================

echo "[2/8] Removing gpt-oss:120b..."

if command -v ollama >/dev/null 2>&1; then
    ollama rm gpt-oss:120b 2>/dev/null || true
fi

# ============================================================
# 3. Stop and disable Ollama
# ============================================================

echo "[3/8] Stopping Ollama service..."

if systemctl list-unit-files | grep -q '^ollama.service'; then
    systemctl disable --now ollama.service || true
fi

# ============================================================
# 4. Create llama user
# ============================================================

echo "[4/8] Creating llama system user..."

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    useradd \
        --system \
        --create-home \
        --home-dir /var/lib/llama \
        --shell /usr/sbin/nologin \
        "$SERVICE_USER"
fi

# ============================================================
# 5. Install llama.cpp
# ============================================================

echo "[5/8] Installing llama.cpp..."

mkdir -p "$INSTALL_DIR"
mkdir -p "$CACHE_DIR"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then

    apt-get update

    apt-get install -y \
        git \
        cmake \
        build-essential \
        curl

    git clone \
        https://github.com/ggml-org/llama.cpp.git \
        "$INSTALL_DIR"

else

    cd "$INSTALL_DIR"

    git fetch origin
    git pull --ff-only
fi

# ------------------------------------------------------------
# Build CUDA version
# ------------------------------------------------------------

cd "$INSTALL_DIR"

rm -rf build

cmake -B build \
    -DGGML_CUDA=ON \
    -DCMAKE_BUILD_TYPE=Release

cmake --build build \
    --config Release \
    -j"$(nproc)" \
    --target llama-server

# ============================================================
# 6. Permissions
# ============================================================

echo "[6/8] Setting permissions..."

chown -R "$SERVICE_USER:$SERVICE_USER" "$CACHE_DIR"

# ============================================================
# 7. Create systemd service
# ============================================================

echo "[7/8] Creating systemd service..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Qwen3-Coder-Next llama.cpp Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple

User=${SERVICE_USER}
Group=${SERVICE_USER}

Environment="LLAMA_CACHE=${CACHE_DIR}"

WorkingDirectory=${INSTALL_DIR}

ExecStart=${INSTALL_DIR}/build/bin/llama-server \
    -hf ${MODEL} \
    -a ${MODEL_ALIAS} \
    --host ${HOST} \
    --port ${PORT} \
    --ctx-size ${CTX_SIZE} \
    --n-gpu-layers 999 \
    --flash-attn on \
    --parallel ${PARALLEL} \
    --jinja \
    --metrics

Restart=always
RestartSec=10

LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

# ============================================================
# 8. Enable and start
# ============================================================

echo "[8/8] Starting Qwen3-Coder-Next..."

systemctl daemon-reload

systemctl enable "$SERVICE_NAME.service"

systemctl restart "$SERVICE_NAME.service"

echo
echo "============================================================"
echo " Setup completed"
echo "============================================================"
echo
echo "Service:"
echo "  systemctl status ${SERVICE_NAME}"
echo
echo "Logs:"
echo "  journalctl -u ${SERVICE_NAME} -f"
echo
echo "API:"
echo "  http://<GB10-IP>:${PORT}/v1"
echo
echo "Model:"
echo "  ${MODEL_ALIAS}"
echo
echo "Context:"
echo "  ${CTX_SIZE} tokens (256K)"
echo
```

---

# 3. 実行

例えば、

```bash
nano setup_qwen_coder.sh
```

に保存して、

```bash
chmod +x setup_qwen_coder.sh
```

そして、

```bash
sudo ./setup_qwen_coder.sh
```

です。

---

# 4. Ollamaについて

このスクリプトでは、

```bash
ollama stop gpt-oss:120b
```

↓

```bash
ollama rm gpt-oss:120b
```

↓

```bash
systemctl disable --now ollama.service
```

という順番にしています。

つまり、

```text
gpt-oss:120b
    ↓
削除

Ollama service
    ↓
停止
    ↓
自動起動も無効
```

になります。

**Ollamaそのものはアンインストールしません。**

将来的にOllamaを再利用する可能性があるなら、この方が安全です。

---

# 5. systemdでの管理

以後は、

```bash
sudo systemctl status qwen3-coder
```

で状態確認。

ログを見る場合は、

```bash
sudo journalctl -u qwen3-coder -f
```

停止：

```bash
sudo systemctl stop qwen3-coder
```

再起動：

```bash
sudo systemctl restart qwen3-coder
```

自動起動を無効化：

```bash
sudo systemctl disable qwen3-coder
```

です。

---

# 6. 起動確認

まずGB10上で、

```bash
curl http://127.0.0.1:4000/v1/models
```

を実行します。

例えば、

```json
{
  "data": [
    {
      "id": "qwen3-coder-next",
      ...
    }
  ]
}
```

のように返ってくればOKです。

さらにResponses APIも確認できます。

現在のllama.cppには、

```text
POST /v1/responses
```

が実装されています。([GitHub][1])

---

# 7. VS Code側のCodex設定

ここが今回かなり重要です。

現在のCodexではカスタムプロバイダーを、

```toml
model_provider = "llama"

[model_providers.llama]
```

で定義できます。

OpenAI公式の現在の`config.toml`仕様でも、`model_provider`は`model_providers`で定義したIDを指定し、カスタムプロバイダーには`base_url`、`wire_api`、`requires_openai_auth`などを設定できます。([OpenAI Developers][3])

### `~/.codex/config.toml`

```toml
#:schema https://developers.openai.com/codex/config-schema.json

# 1. 使用するモデルとプロバイダの指定
model = "qwen3-coder-next"
model_provider = "llama"

# 2. 安全性・実行権限の設定（コーディングエージェント用）never / on-request
approval_policy = "never"
sandbox_mode = "workspace-write"

# 3. 推論プロセスの設定
model_reasoning_effort = "high"

# 4. 自前推論サーバー (llama-server) のプロバイダ定義
[model_providers.llama]
name = "llama.cpp"
base_url = "http://GB10のIPアドレス:4000/v1"
wire_api = "chat"
requires_openai_auth = false
```

# 変更完了後の動作確認コマンド
クライアント端末のターミナルから curl を叩いて、llama-server から正しく応答が得られるかテストします。
```
curl http://192.168.31.26:4000/health
```

```
curl http://192.168.31.26:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer no-key" \
  -d '{
    "model": "qwen3-coder-next",
    "input": "Hello!"
  }'
```

---

# 9. APIキーは不要にできる

今回のLAN内専用サーバーなら、

```toml
requires_openai_auth = false
```

として、APIキーなしで接続できます。

ただし、`llama-server`を

```text
--host 0.0.0.0
```

にしているので、**GB10の4000番ポートがLAN上からアクセス可能になります。**

したがって、インターネット側から直接4000を開けないことを強くおすすめします。

より安全にするなら、後でllama-serverのAPIキー機能またはファイアウォールを設定できます。

---

# 10. Codexの接続イメージ

VS Code側：

```text
┌─────────────────────────┐
│ VS Code                 │
│                         │
│ Codex                   │
│   │                     │
│   │ config.toml         │
│   ↓                     │
│ model=qwen3-coder-next  │
│ provider=llama          │
└────────────┬────────────┘
             │
             │ HTTP
             ↓
┌─────────────────────────┐
│ GB10                    │
│                         │
│ llama-server :4000      │
│        │                │
│        ↓                │
│ Qwen3-Coder-Next        │
│ Q4_K_M                  │
│ 256K Context            │
│                         │
└─────────────────────────┘
```

---

# 11. ただし、1点だけ変更を推奨

今回の目的は**Coding Agent**なので、私は最初は、

```text
256K
+
parallel = 1
```

にします。

つまり、

```text
--ctx-size 262144
--parallel 1
```

です。

128GB GB10で、

```text
Qwen3-Coder-Next Q4_K_M
+
256K KV Cache
+
Coding Agent
```

を動かす場合、複数並列にするとKV Cacheの使用量が増えるためです。

**まず1エージェントを安定動作させる → VRAM使用量を確認 → 必要なら`--parallel 2`**という順番がよいです。

---

## さらに重要な点

今回の構成では、以前の

```text
Ollama
  ↓
gpt-oss:120b
```

から、

```text
llama.cpp
  ↓
Qwen3-Coder-Next Q4_K_M
  ↓
llama-server
  ↓
Codex
```

に完全に切り替わります。

そして、**CodexからGitLabリポジトリを操作しながら、後からChromaのRAGやSuperpowersを組み込む**こともできます。

なお、Qwen3-Coder-Next + llama.cppについては、GB10上での動作報告があり、llama.cpp側ではQwen3-Coder-Nextについて性能改善が継続しています。([GitHub][5])

**一つだけ修正しておきたい点があります。** 上のセットアップスクリプトはllama.cppをソースからビルドする方式なので、GB10のCUDA環境によっては追加のCUDA開発パッケージが必要です。もし現在のGB10が**DGX Spark標準のUbuntu環境**なら、そこに合わせて `CUDA/GB10向けビルドを含めた完全版の `setup_qwen_coder.sh` にした方が確実です。

[1]: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md?utm_source=chatgpt.com "llama.cpp/tools/server/README.md at master · ggml-org/llama.cpp · GitHub"
[2]: https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF/blob/main/Qwen3-Coder-Next-Q4_K_M/Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf?utm_source=chatgpt.com "Qwen3-Coder-Next-Q4_K_M/Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf · Qwen/Qwen3-Coder-Next-GGUF at main"
[3]: https://developers.openai.com/ja-JP/docs/config-file/config-reference?utm_source=chatgpt.com "構成リファレンス | ChatGPT Learn"
[4]: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server.cpp?utm_source=chatgpt.com "llama.cpp/tools/server/server.cpp at master · ggml-org/llama.cpp · GitHub"
[5]: https://github.com/ggml-org/llama.cpp/issues/19305?utm_source=chatgpt.com "Eval bug: Qwen3-Coder-Next Poor Outputs · Issue #19305 · ggml-org/llama.cpp · GitHub"
