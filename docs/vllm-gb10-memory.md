# GB10のvLLMでメモリが枯渇したときの対処

GB10上でvLLMを起動したら、メモリを使い切ってOOMで落ちた、あるいはOSごと
応答しなくなった、というときの手順。**確保量を明示的に絞り、競合するプロセスを
止めてから起動し直す**のが基本である。

> **この文書の位置づけ（2026-11-07）**
> vLLMサーバー自体の立て方は [GB10サーバーにvLLMを立てる](vllm-gb10.md)、
> gpt-oss-120b の起動フラグは [GB10のvLLM + gpt-oss-120b でCodexとClaude Codeを使う](vllm-gb10-coding-agent.md)
> にある。ここはその起動が**メモリ不足で通らないときの切り分けと対処**だけを書く。
> フラグ名とその効果は vLLM の公開情報に基づく。**各値は実測していない**ので、
> 保守的な値から始めて、安定を確認しながら戻していくこと。

## 目次

- [なぜ枯渇するか](#なぜ枯渇するか)
- [0. 現状を確認する](#0-現状を確認する)
- [1. 競合プロセスを止める](#1-競合プロセスを止める)
- [2. ページキャッシュを解放する](#2-ページキャッシュを解放する)
- [3. 確保量を絞って起動する](#3-確保量を絞って起動する)
- [4. 起動を確認する](#4-起動を確認する)
- [つまずきやすいところ](#つまずきやすいところ)
- [常時稼働させるとき](#常時稼働させるとき)

## なぜ枯渇するか

GB10はCPUとGPUが128GBのメモリを共有する（[vllm-gb10.md の2項](vllm-gb10.md#gb10で先に知っておくこと)）。
vLLMは起動時に `--gpu-memory-utilization` の割合を**128GB全体に対して**確保して
抱え込む。主な原因は次の3つである。

- **確保割合が大きすぎる。** 既定は0.9（約115GB）。OS・ページキャッシュ・他の
  プロセスの分が残らない
- **同じ機械に別のモデルが載っている。** Ollamaは使い終わったモデルもしばらく
  メモリに保持する。別のvLLMやSGLangが残っていることもある
- **KVキャッシュの予約が大きい。** `--max-model-len` が長いほど、
  `--max-num-seqs` が多いほど、KVキャッシュに多くの領域を予約する

## 0. 現状を確認する

```bash
free -h                              # available 列を見る
nvidia-smi                           # GPUを使っているプロセス
ps aux --sort=-%mem | head -n 15     # メモリ使用量の多い順
ollama ps                            # Ollamaが保持しているモデル
docker ps                            # 残っているvLLMコンテナ
```

GB10では `nvidia-smi` のメモリ欄が実態を表さないことがあるので、空き容量は
`free -h` の `available` で判断する。gpt-oss-120b は重みだけでMXFP4で約60GiBを
使うため、起動前に**80GB以上**空いていることを目安にする。

## 1. 競合プロセスを止める

**OllamaとvLLMを同じGB10で同時に動かさない。**

```bash
ollama stop <モデル名>               # 読み込み中のモデルをアンロード
sudo systemctl stop ollama           # サービスごと止める
sudo systemctl disable ollama        # 自動起動も止めるなら

docker rm -f vllm-code               # 前回のvLLMコンテナが残っていれば
```

止めたあとに `free -h` を再実行し、`available` が増えたことを確かめる。

## 2. ページキャッシュを解放する

ユニファイドメモリでは、モデルファイルを読んだときのページキャッシュが同じ
物理メモリを占める。vLLMの確保が失敗するときは、起動の直前に解放する。

```bash
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches
free -h                              # buff/cache が減ったことを確認
```

実行中のプロセスに害はない。直後のディスク読み込みが一時的に遅くなるだけである。

## 3. 確保量を絞って起動する

[vllm-gb10-coding-agent.md](vllm-gb10-coding-agent.md) の起動例は
`--gpu-memory-utilization 0.85`、`--max-model-len 131072` である。これで落ちる
ときは、いったん下の保守的な値まで下げて起動が通ることを確かめ、そこから
少しずつ戻す。

|フラグ|既定|コーディング用の起動例|まず試す値|効果|
|---|---|---|---|---|
|`--gpu-memory-utilization`|0.9|0.85|0.6|vLLMが確保する割合。最も効く|
|`--max-model-len`|モデルの上限|131072|32768|KVキャッシュの予約量を抑える|
|`--max-num-seqs`|256前後|4|4|同時処理数。1人で使うなら小さくてよい|
|`--kv-cache-dtype`|auto|fp8|fp8|KVキャッシュをほぼ半分にする|
|`--enforce-eager`|無効|無効|落ちるときだけ|CUDAグラフ用のメモリを省く。速度は落ちる|

```bash
export VLLM_IMAGE=nvcr.io/nvidia/vllm:26.06-py3   # 最新タグはNGCで確認する

docker run -d --name vllm-code --restart unless-stopped \
  --gpus all --ipc=host \
  -p 0.0.0.0:8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ${VLLM_IMAGE} \
  vllm serve openai/gpt-oss-120b \
    --host 0.0.0.0 --port 8000 \
    --served-model-name openai/gpt-oss-120b \
    --gpu-memory-utilization 0.6 \
    --max-model-len 32768 \
    --max-num-seqs 4 \
    --kv-cache-dtype fp8 \
    --tool-call-parser openai \
    --enable-auto-tool-choice \
    --api-key "<十分に長いランダム文字列>"
```

`--tool-call-parser openai --enable-auto-tool-choice` と `--api-key` は
メモリとは関係ないが、外すとコーディングエージェントが道具を呼べなくなる、
あるいは無認証になるので残す（理由は [vllm-gb10-coding-agent.md](vllm-gb10-coding-agent.md)）。

まだ落ちる場合は、次の順に**1つずつ**変えて試す。

1. `--enforce-eager` を足す
2. `--gpu-memory-utilization` を0.5へ下げる
3. `--max-model-len` を16384へ下げる

起動が通ったら、逆の順に戻して、落ちない上限を探す。

## 4. 起動を確認する

```bash
docker logs -f vllm-code                         # 起動完了まで待つ
docker logs vllm-code 2>&1 | grep -i "kv cache"  # KVキャッシュの確保量

curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer <api-key>"

curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api-key>" \
  -d '{"model":"openai/gpt-oss-120b","messages":[{"role":"user","content":"こんにちは"}],"max_tokens":64}'

watch -n 2 free -h                               # 推論中のメモリを別端末で見る
```

- 応答が返る
- 推論中も `available` が10GB以上残っている（OSの余裕）
- ログにKVキャッシュの確保量と最大同時処理数が出ている

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|起動時に `CUDA out of memory`|確保割合が空きより大きい|1・2節を実施し、`--gpu-memory-utilization` を0.1ずつ下げる|
|`No available memory for the cache blocks`|重みを載せた後にKVキャッシュの余地がない|`--max-model-len` を下げる。`--kv-cache-dtype fp8` を付ける|
|`max_model_len` がKVキャッシュに収まらないと出る|コンテキスト長が大きすぎる|`--max-model-len` をエラーが示す値以下にする|
|CUDAグラフの取得中に落ちる|グラフ用のメモリが足りない|`--enforce-eager` を足す|
|SSHが固まる・OSが応答しない|OSの分まで使い切った|電源から再起動し、`--gpu-memory-utilization` を0.5以下で起動し直す|
|推論の途中で落ちる|長い入力や同時リクエストでKVが足りない|`--max-num-seqs` と `--max-model-len` を下げる|

## 常時稼働させるとき

[vllm-gb10.md の3節（systemd）](vllm-gb10.md#3-常時稼働させるsystemd) で常駐させる
場合は、Ollamaとの衝突とキャッシュ解放をユニットに書いておくと、手順1・2を
毎回手で行わずに済む。

```ini
[Unit]
Conflicts=ollama.service

[Service]
ExecStartPre=+/bin/sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
```

- `Conflicts=ollama.service` で、vLLMの起動時にOllamaが止まる
- `ExecStartPre` の先頭の `+` は、キャッシュ解放をrootで実行するためのもの
- GB10を2台にして、gpt-oss-120b と Qwen3-Coder-Next を別々の機械に載せれば、
  1台に1モデルとなり、この文書の制約はほぼ考えなくてよくなる。1台に複数の
  プロセスを同居させるときの割り振りは
  [vllm-gb10-models.md の「128GBの割り振り」](vllm-gb10-models.md#128gbの割り振り) を見ること
