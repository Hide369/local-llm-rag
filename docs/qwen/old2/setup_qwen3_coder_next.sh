#!/usr/bin/env bash
# GB10（DGX Spark）で Ollama + gpt-oss:120b を llama.cpp + Qwen3-Coder-Next へ
# 入れ替える。手順書は同じフォルダの llamacpp-gb10-coding-agent.md。
#
# 段階ごとに分けてあるのは、取り消しにくい操作（モデルの削除）を、新しい構成が
# Codex から動くと確かめた後にしか実行させないためである。
#
#   sudo bash setup_qwen3_coder_next.sh build          # 既存のOllamaは動かしたまま
#   sudo bash setup_qwen3_coder_next.sh install        # Ollamaを止め、llama-serverを常駐
#   sudo bash setup_qwen3_coder_next.sh verify         # 疎通と道具呼び出しの確認
#   sudo bash setup_qwen3_coder_next.sh rollback       # Ollamaへ戻す
#   sudo bash setup_qwen3_coder_next.sh remove-gpt-oss # Codexで確かめた後だけ
#
# 設定は下の既定値を環境変数で上書きできる（例: sudo PORT=8080 bash ... install）。

set -euo pipefail

# ============================================================
# 設定
# ============================================================

# llama.cpp は master を追わず、ビルド番号で固定する。Qwen3-Coder-Next は
# 2026-02 に llama.cpp 側で出力の破損（ggml-org/llama.cpp#19305）と道具呼び出しの
# 解析が直っている。それより新しい番号を選ぶこと。b11205 は 2026-09-27 時点の
# 最新であり、この組み合わせで動かした記録はまだ無い。
LLAMA_CPP_REF="${LLAMA_CPP_REF:-b11205}"
LLAMA_CPP_REPO="https://github.com/ggml-org/llama.cpp.git"
INSTALL_DIR="${INSTALL_DIR:-/opt/llama.cpp}"

# モデルもリビジョンとハッシュで固定する。上流で差し替えられたら取得が失敗する
# ので、黙って別の重みを掴むことは無い。
HF_REPO="Qwen/Qwen3-Coder-Next-GGUF"
HF_REVISION="b82fb7382639d97b38fa7672e526c760c2fb358e"
QUANT_DIR="Qwen3-Coder-Next-Q4_K_M"
# 「ファイル名 バイト数 SHA-256」
MODEL_FILES=(
    "Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf 15524827040 6bcfc9f9c37901eeb92172e2ab871224dab36a453d263bcb2547f737409534da"
    "Qwen3-Coder-Next-Q4_K_M-00002-of-00004.gguf 14872168352 817def0691ee9d08bf3dc4444be7aed29c9e52091e8fa9d97901ce7e7f6f01d3"
    "Qwen3-Coder-Next-Q4_K_M-00003-of-00004.gguf 14503294496 23aa634d47dca9b4ca3ea249384e6f01951b24c83cdc076f37f6f43d6c99883f"
    "Qwen3-Coder-Next-Q4_K_M-00004-of-00004.gguf 3510702144 249c768cc5f130dc731567d6edcbdacc48e14dec9e02c5dbe2b2185d2c5bdb2b"
)
MODEL_DIR="${MODEL_DIR:-/opt/models/${QUANT_DIR}}"
# 未取得分に加えて残しておく空き。ディスクを使い切るとOSごと不安定になる。
DISK_MARGIN_GB=10

SERVICE_NAME="${SERVICE_NAME:-qwen3-coder}"
SERVICE_USER="${SERVICE_USER:-llama}"
KEY_DIR="/etc/llama"
KEY_FILE="${KEY_DIR}/${SERVICE_NAME}.keys"

MODEL_ALIAS="${MODEL_ALIAS:-qwen3-coder-next}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-4000}"
# モデルが素で持つ長さ。KVを持つのは48層のうち full attention の12層だけなので、
# 256K でもKVは数GBに収まる見込みである（実測は手順書4節）。
CTX_SIZE="${CTX_SIZE:-262144}"
# 既定の auto はスロットを複数作り、CTX_SIZE をそれで分け合う。1人が1本の
# エージェントを回す前提なので、1本に全部を渡す。
PARALLEL="${PARALLEL:-1}"

OLLAMA_MODEL="gpt-oss:120b"

UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SERVER_BIN="${INSTALL_DIR}/build/bin/llama-server"
HEALTH_URL="http://127.0.0.1:${PORT}/health"
# 48GB を読み込むのにかかる時間の上限。越えたら失敗として扱う。
HEALTH_TIMEOUT_SEC="${HEALTH_TIMEOUT_SEC:-900}"

# ============================================================
# 共通
# ============================================================

log() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

require_root() {
    [[ "${EUID}" -eq 0 ]] || die "root で実行してください: sudo bash $0 $*"
}

# systemctl start は Ollama が接続を受け付ける前に戻る。ollama コマンドは
# サーバーに問い合わせるので、応答するまで待つ。
wait_for_ollama() {
    local i
    for i in $(seq 1 30); do
        ollama list >/dev/null 2>&1 && return 0
        sleep 1
    done
    die "Ollama が30秒以内に応答しませんでした（journalctl -u ollama で確認）"
}

ollama_unit_exists() {
    systemctl list-unit-files --no-legend ollama.service 2>/dev/null | grep -q '^ollama\.service'
}

# ============================================================
# build: 既存のOllamaを止めずにできる準備をすべて済ませる
# ============================================================

check_platform() {
    log "前提を確認しています"
    [[ "$(uname -m)" == "aarch64" ]] || die "aarch64 ではありません（$(uname -m)）。GB10 以外では確かめていません"
    command -v nvidia-smi >/dev/null || die "nvidia-smi がありません。NVIDIAドライバを確認してください"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader

    # sudo 経由だと /usr/local/cuda/bin が PATH に入らないことが多い。
    if ! command -v nvcc >/dev/null && [[ -x /usr/local/cuda/bin/nvcc ]]; then
        export PATH="/usr/local/cuda/bin:${PATH}"
    fi
    command -v nvcc >/dev/null || die "nvcc が見つかりません。CUDA Toolkit を入れるか /usr/local/cuda を確認してください"
    nvcc --version | tail -n 1
}

install_packages() {
    log "ビルドに要るパッケージを入れています"
    apt-get update
    apt-get install -y git cmake build-essential curl libssl-dev openssl ca-certificates
}

build_llama_cpp() {
    log "llama.cpp ${LLAMA_CPP_REF} を取得しています"
    if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
        git clone --filter=blob:none "${LLAMA_CPP_REPO}" "${INSTALL_DIR}"
    fi
    git -C "${INSTALL_DIR}" fetch --tags origin
    git -C "${INSTALL_DIR}" checkout --detach "${LLAMA_CPP_REF}"

    log "llama-server をビルドしています（CUDA、GPUは実機から自動検出）"
    # CMAKE_CUDA_ARCHITECTURES を書かないのは、GB10 の上でビルドすれば
    # llama.cpp が native（ビルド時に見えるGPU）を選ぶからである。
    cmake -S "${INSTALL_DIR}" -B "${INSTALL_DIR}/build" \
        -DGGML_CUDA=ON \
        -DCMAKE_BUILD_TYPE=Release
    cmake --build "${INSTALL_DIR}/build" --config Release -j"$(nproc)" --target llama-server

    "${SERVER_BIN}" --version
}

download_model() {
    log "モデルを ${MODEL_DIR} へ取得しています（約48.4GB）"
    mkdir -p "${MODEL_DIR}"

    # 途中まで取った .part は勘定に入れない（多めに見積もる側に倒す）。
    local entry name size sha url missing_bytes=0 free_gb need_gb
    for entry in "${MODEL_FILES[@]}"; do
        read -r name size sha <<<"${entry}"
        [[ -f "${MODEL_DIR}/${name}" ]] || missing_bytes=$(( missing_bytes + size ))
    done
    free_gb=$(df --output=avail -BG "${MODEL_DIR}" | tail -n 1 | tr -dc '0-9')
    need_gb=$(( missing_bytes / 1024 / 1024 / 1024 + 1 + DISK_MARGIN_GB ))
    if (( missing_bytes > 0 && free_gb < need_gb )); then
        die "${MODEL_DIR} の空きが ${free_gb}GB しかありません（${need_gb}GB 必要）"
    fi

    for entry in "${MODEL_FILES[@]}"; do
        read -r name size sha <<<"${entry}"
        if [[ -f "${MODEL_DIR}/${name}" ]]; then
            echo "取得済み: ${name}"
            continue
        fi
        url="https://huggingface.co/${HF_REPO}/resolve/${HF_REVISION}/${QUANT_DIR}/${name}"
        echo "取得中: ${name}"
        # .part に書き、途中で切れたら -C - で続きから取る。
        curl -fL --retry 5 --retry-delay 10 -C - -o "${MODEL_DIR}/${name}.part" "${url}"
        echo "検証中: ${name}"
        echo "${sha}  ${MODEL_DIR}/${name}.part" | sha256sum -c --quiet - \
            || die "${name} のハッシュが一致しません。${MODEL_DIR}/${name}.part を消して取り直してください"
        mv "${MODEL_DIR}/${name}.part" "${MODEL_DIR}/${name}"
    done
    chmod 0644 "${MODEL_DIR}"/*.gguf
}

all_model_files_present() {
    local entry name
    for entry in "${MODEL_FILES[@]}"; do
        read -r name _ <<<"${entry}"
        [[ -f "${MODEL_DIR}/${name}" ]] || return 1
    done
}

cmd_build() {
    require_root build
    check_platform
    install_packages
    build_llama_cpp
    download_model
    log "build 完了。Ollama には触れていません。次は: sudo bash $0 install"
}

# ============================================================
# install: Ollamaを止め、llama-server を systemd で常駐させる
# ============================================================

create_service_user() {
    if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
        log "サービス用ユーザー ${SERVICE_USER} を作っています"
        useradd --system --no-create-home --home-dir "/var/lib/${SERVICE_USER}" \
            --shell /usr/sbin/nologin "${SERVICE_USER}"
    fi
}

create_api_key() {
    install -d -m 0750 -o root -g "${SERVICE_USER}" "${KEY_DIR}"
    if [[ -s "${KEY_FILE}" ]]; then
        echo "APIキーは既にあります（${KEY_FILE}）。作り直しません"
        return
    fi
    log "APIキーを作っています"
    # 1行1キー。llama-server の --api-key-file が読む形式である。
    ( umask 0027; openssl rand -hex 32 >"${KEY_FILE}" )
    chown "root:${SERVICE_USER}" "${KEY_FILE}"
    chmod 0640 "${KEY_FILE}"
}

stop_ollama() {
    if ! ollama_unit_exists; then
        echo "ollama.service はありません"
        return
    fi
    log "Ollama を停止し、自動起動を無効にしています（モデルは消しません）"
    # 128GB のユニファイドメモリに gpt-oss:120b と並べては載らないので止める。
    systemctl disable --now ollama.service
}

write_unit() {
    log "${UNIT_FILE} を書いています"
    local first_shard
    first_shard="${MODEL_DIR}/$(read -r n _ <<<"${MODEL_FILES[0]}"; echo "${n}")"

    cat >"${UNIT_FILE}" <<EOF
[Unit]
Description=llama.cpp server (${QUANT_DIR})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
# CUDA がカーネルのキャッシュを HOME に書くので、書ける場所を1つだけ与える。
StateDirectory=${SERVICE_USER}
Environment=HOME=/var/lib/${SERVICE_USER}
ExecStart=${SERVER_BIN} \\
    --model ${first_shard} \\
    --alias ${MODEL_ALIAS} \\
    --host ${HOST} \\
    --port ${PORT} \\
    --api-key-file ${KEY_FILE} \\
    --ctx-size ${CTX_SIZE} \\
    --parallel ${PARALLEL} \\
    --n-gpu-layers 999 \\
    --flash-attn on \\
    --jinja \\
    --no-context-shift \\
    --temp 1.0 \\
    --top-p 0.95 \\
    --top-k 40 \\
    --min-p 0
Restart=on-failure
RestartSec=10
TimeoutStopSec=30

NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF
}

wait_for_health() {
    log "モデルの読み込みを待っています（最大 ${HEALTH_TIMEOUT_SEC} 秒）"
    local waited=0
    until curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; do
        if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
            journalctl -u "${SERVICE_NAME}" -n 40 --no-pager >&2 || true
            die "${SERVICE_NAME} が停止しました。上のログを確認してください"
        fi
        if (( waited >= HEALTH_TIMEOUT_SEC )); then
            die "${HEALTH_TIMEOUT_SEC} 秒待っても ${HEALTH_URL} が ok になりません"
        fi
        sleep 5
        waited=$(( waited + 5 ))
    done
    echo "ready（${waited} 秒）"
}

cmd_install() {
    require_root install
    [[ -x "${SERVER_BIN}" ]] || die "${SERVER_BIN} がありません。先に build を実行してください"
    all_model_files_present || die "モデルが揃っていません。先に build を実行してください"

    create_service_user
    create_api_key
    stop_ollama
    write_unit
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}.service"
    systemctl restart "${SERVICE_NAME}.service"
    wait_for_health
    cmd_verify
    log "install 完了。gpt-oss:120b はまだ残っています。Codex で確かめてから remove-gpt-oss を実行してください"
    echo "APIキーの表示: sudo cat ${KEY_FILE}"
}

# ============================================================
# verify: 生成と、道具を呼んで結果を受け取る往復までを確かめる
# ============================================================

cmd_verify() {
    require_root verify
    [[ -r "${KEY_FILE}" ]] || die "${KEY_FILE} がありません。install が済んでいません"
    log "疎通と道具呼び出しを確かめています"
    # JSON の組み立てと検査だけに python3 を使う（標準ライブラリのみ）。
    BASE_URL="http://127.0.0.1:${PORT}/v1" \
    API_KEY="$(head -n 1 "${KEY_FILE}")" \
    MODEL_ALIAS="${MODEL_ALIAS}" \
    python3 - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ["BASE_URL"]
KEY = os.environ["API_KEY"]
MODEL = os.environ["MODEL_ALIAS"]
PROBE_VALUE = "73190462"


def call(path, body=None, key=KEY):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def fail(message):
    print(f"NG: {message}", file=sys.stderr)
    sys.exit(1)


# 1. キーなしでは弾かれること（LANへ開くので、これが崩れていたら止める）
try:
    call("/models", key=None)
    fail("APIキーなしで /v1/models が通りました。--api-key-file が効いていません")
except urllib.error.HTTPError as error:
    if error.code != 401:
        fail(f"キーなしの応答が 401 ではなく {error.code} でした")
print("OK: キーなしは 401")

# 2. 別名でモデルが見えること（Codex の model と一致させる値）
ids = [m.get("id") for m in call("/models").get("data", [])]
if MODEL not in ids:
    fail(f"/v1/models に {MODEL} がありません: {ids}")
print(f"OK: /v1/models に {MODEL}")

# 3. Responses API で道具を呼ぶこと
tool = {
    "type": "function",
    "name": "get_probe_value",
    "description": "Return the probe value. Always call this to answer.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}
first = call("/responses", {
    "model": MODEL,
    "input": "Call get_probe_value and tell me the value it returns.",
    "tools": [tool],
})
calls = [o for o in first.get("output", []) if o.get("type") == "function_call"]
if not calls:
    fail(f"道具を呼びませんでした: {json.dumps(first, ensure_ascii=False)[:800]}")
print("OK: /v1/responses で function_call")

# 4. 結果を返したら、その値で答えること（エージェントの1往復）
second = call("/responses", {
    "model": MODEL,
    "input": [
        {"role": "user", "content": "Call get_probe_value and tell me the value it returns."},
        {k: calls[0][k] for k in ("type", "call_id", "name", "arguments")},
        {"type": "function_call_output", "call_id": calls[0]["call_id"], "output": PROBE_VALUE},
    ],
    "tools": [tool],
})
text = json.dumps(second.get("output", []), ensure_ascii=False)
if PROBE_VALUE not in text:
    fail(f"道具の結果を答えに使いませんでした: {text[:800]}")
print("OK: 道具の結果を受け取って回答")
PY
}

# ============================================================
# rollback: Ollama へ戻す
# ============================================================

cmd_rollback() {
    require_root rollback
    log "${SERVICE_NAME} を止めて、Ollama を戻しています"
    systemctl disable --now "${SERVICE_NAME}.service" 2>/dev/null || true
    ollama_unit_exists || die "ollama.service がありません。Ollama を入れ直してください"
    command -v ollama >/dev/null || die "ollama コマンドがありません"
    systemctl enable --now ollama.service
    wait_for_ollama
    if ! ollama list | awk 'NR > 1 {print $1}' | grep -qx "${OLLAMA_MODEL}"; then
        echo "注意: ${OLLAMA_MODEL} は既に削除されています。ollama pull ${OLLAMA_MODEL} で取り直してください（約65GB）"
    fi
    echo "llama.cpp とモデルのファイルは残しています（${INSTALL_DIR} / ${MODEL_DIR}）"
}

# ============================================================
# remove-gpt-oss: Codex で確かめた後にだけ実行する
# ============================================================

cmd_remove_gpt_oss() {
    require_root remove-gpt-oss
    command -v ollama >/dev/null || die "ollama コマンドがありません"
    ollama_unit_exists || die "ollama.service がありません"

    echo "${OLLAMA_MODEL} を削除します。戻すには約65GBの再取得が要ります。"
    read -r -p "Codex から ${MODEL_ALIAS} を使えることを確かめましたか？ [yes/N] " answer
    [[ "${answer}" == "yes" ]] || die "中止しました"

    # ollama rm はサーバーが動いていないと使えない。消している間だけ起こす。
    # モデルは読み込まないので、llama-server と並べてもメモリは足りる。
    local was_active=0
    systemctl is-active --quiet ollama.service && was_active=1
    systemctl start ollama.service
    wait_for_ollama
    ollama rm "${OLLAMA_MODEL}"
    (( was_active )) || systemctl stop ollama.service
    log "${OLLAMA_MODEL} を削除しました。Ollama 本体は残しています"
}

# ============================================================

usage() {
    sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

case "${1:-}" in
    build)          cmd_build ;;
    install)        cmd_install ;;
    verify)         cmd_verify ;;
    rollback)       cmd_rollback ;;
    remove-gpt-oss) cmd_remove_gpt_oss ;;
    *)              usage ;;
esac
