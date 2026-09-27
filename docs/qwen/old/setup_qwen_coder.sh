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