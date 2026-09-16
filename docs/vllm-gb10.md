# GB10サーバーにvLLMを立てる（見送り）

Nvidia GB10（DGX Spark / ASUS Ascent GX10 などのOEM機を含む）を推論サーバーにし、
RAGの生成とコーディングエージェントを社内ネットワークの中で完結させるための手順。

> **導入は見送った（2026-09-16）。**
> このリポジトリは Ollama のまま運用する。以下は調査の記録として残してある。
> 手順そのものを確かめた形跡（実機での起動、実測値）は無い。再開するときは、
> コンテナのタグもモデルのハンドルも古くなっている前提で読むこと。
>
> 接続先を vLLM（OpenAI互換）へ切り替える実装は、取り込まずに閉じた
> [PR #75](https://github.com/Hide369/local-llm-rag/pull/75) に残っている。
> 再開するならそこから拾える。

> **この文書の位置づけ**
> 手順とコマンドは NVIDIA の DGX Spark playbook（`nvidia/vllm`、2026-06-12 更新）と
> vLLMの公開情報に基づく。**手元にGB10が無いため実測はしていない**。
> コンテナのタグ、モデルのHFハンドル、フラグ名は版で変わる。導入時に
> [出典](#出典) の各ページで必ず現物を確認すること。所要時間・トークン毎秒の
> 数値をこの文書に書いていないのは、測っていないものを書かないためである。

## 目次

- [GB10で先に知っておくこと](#gb10で先に知っておくこと)
- [1. 前提の確認](#1-前提の確認)
- [2. vLLMコンテナを取得して起動する](#2-vllmコンテナを取得して起動する)
- [3. 常時稼働させる（systemd）](#3-常時稼働させるsystemd)
- [4. 社内ネットワークへの公開と認証](#4-社内ネットワークへの公開と認証)
- [5. モデルの選び方と128GBの割り振り](#5-モデルの選び方と128gbの割り振り)
- [6. コーディングエージェント向けの起動](#6-コーディングエージェント向けの起動)
- [7. 埋め込みとリランカーをvLLMで出す](#7-埋め込みとリランカーをvllmで出す)
- [8. 本リポジトリのRAGとつなぐ](#8-本リポジトリのragとつなぐ)
- [9. トラブルシュート](#9-トラブルシュート)
- [出典](#出典)

## GB10で先に知っておくこと

普通のx86＋RTXサーバーと違う点が3つあり、これを知らないまま始めると最初の1日を
ビルドエラーで溶かす。

**1. aarch64 かつ sm_121 である。** GB10のGPUはBlackwellの `sm_121`（`sm_121a`）で、
これをサポートするのは **CUDA 13.0以降**である。CPU側はArm（`aarch64`）。
PyPIに並ぶ機械学習系のwheelの多くはいまだにCUDA 12.x・x86_64向けにビルドされて
おり、`pip install vllm` がそのまま通る保証はない。素のpip導入を試すと、PyTorchや
Tritonのカーネルが `sm_120` 止まりで、起動時のCUDAカーネル初期化で落ちる、という
既知の壁に当たる（vLLM issue #36821）。**コンテナから入るのが最短で、かつ再現性がある。**
LLVM/Tritonにパッチを当ててソースからビルドする道もあるが、最初の1台では選ぶ理由がない。

**2. ユニファイドメモリ（UMA）である。** 128GBのLPDDR5XをCPUとGPUが共有する。
専用VRAMを持つGPUと違い、`--gpu-memory-utilization 0.8` は「128GBの80%」を意味する。
OSとページキャッシュも同じ物理メモリに乗るため、**複数のvLLMプロセスを常駐させる
なら、各プロセスの `--gpu-memory-utilization` の合計を管理するのは自分の仕事になる**。
足し算を間違えるとOOMする。

**3. メモリ帯域が律速する。** GB10のメモリ帯域は約273GB/sである。データセンター向けの
HBM搭載GPU（数TB/s）と比べると1桁低い。生成（decode）は1トークンごとに重みを読み直す
処理なので、**1本のストリームの応答速度は帯域でほぼ決まる**。一方でプロンプト処理
（prefill）と多重実行はGB10の演算性能が効く。したがって、

- 「1人が短い質問を投げて速く返ってくる」用途では、専用GPU機ほどの体感は出ない
- 「複数人が同時に使う」「RAGで長い文脈を読ませる」「エージェントが裏で回る」
  用途では、まとめて処理できるvLLMの利点が出る

という傾向になる。MoE（Mixture of Experts）モデルは1トークンあたりに読む重みが
少ないため、この機械では密（dense）モデルより有利である。NVIDIAが提示する推奨構成に
MoEが多いのはこのためである。

## 1. 前提の確認

DGX OS（Ubuntuベース）が入った状態から始める。

```bash
# GPUが見えるか。ドライバのバージョンも控えておく
nvidia-smi

# CUDA 13.0 以上であること
nvcc --version

# aarch64 であること（この文書はaarch64前提）
uname -m

# Docker と NVIDIA Container Toolkit
docker --version
docker run --rm --gpus all nvcr.io/nvidia/cuda:13.0.0-base-ubuntu24.04 nvidia-smi
```

最後のコマンドが `nvidia-smi` の出力を返せば、コンテナからGPUが見えている。
権限エラー（`permission denied ... docker.sock`）が出る場合は、sudoを付けるか
dockerグループに入る。

```bash
sudo usermod -aG docker $USER
newgrp docker
```

HuggingFaceのトークンも先に用意する（https://huggingface.co/settings/tokens ）。
ゲートのかかったモデル（Llama系など）はブラウザーでライセンスに同意しないと
落ちてこない。

## 2. vLLMコンテナを取得して起動する

NVIDIAがNGCでGB10向けにビルド済みのvLLMコンテナを配っている。これを使う。

```bash
# 最新タグは https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm/tags で確認する
# （2026-09 時点で確認できたのは 26.06-py3。playbook の例は 26.05.post1-py3）
export VLLM_IMAGE=nvcr.io/nvidia/vllm:26.06-py3
docker pull ${VLLM_IMAGE}
```

起動する。**HuggingFaceのキャッシュを必ずホストにマウントすること**。これを忘れると
コンテナを作り直すたびに数十GBのモデルを落とし直すことになる。

```bash
export HF_TOKEN="<HuggingFaceのトークン>"

docker run -d --name vllm-chat --restart unless-stopped \
  --gpus all --ipc=host \
  -p 127.0.0.1:8000:8000 \
  -e HF_TOKEN="${HF_TOKEN}" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ${VLLM_IMAGE} \
  vllm serve openai/gpt-oss-20b \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.3 \
    --max-model-len 65536 \
    --max-num-seqs 8 \
    --enable-prefix-caching
```

意図を補足する。

|フラグ|なぜそうするか|
|---|---|
|`-p 127.0.0.1:8000:8000`|素の `-p 8000:8000` は全インターフェースに開く。まずループバックだけに閉じ、公開は[4節](#4-社内ネットワークへの公開と認証)で意識的に行う|
|`--ipc=host`|共有メモリ不足によるワーカーのクラッシュを避ける（`--shm-size=16g` でも可）|
|`--gpu-memory-utilization 0.3`|128GBの30%＝約38GB。複数モデルを常駐させる前提で最初から絞る。1モデルだけなら0.8まで上げてよい|
|`--max-model-len`|KVキャッシュの量を決める。長すぎる指定はそれだけでメモリを食う|
|`--max-num-seqs`|同時に処理するリクエスト数の上限。増やすほどスループットは上がるが1本あたりは遅くなる|
|`--enable-prefix-caching`|RAGのように毎回同じ長いプロンプト前半を送る用途で効く|
|`--restart unless-stopped`|再起動後も自動で上がる。systemdで管理するなら[3節](#3-常時稼働させるsystemd)|

起動を待つ。初回はモデルのダウンロードとカーネルのコンパイルがあるので数分から
十数分かかる。

```bash
timeout 1800 bash -c 'until curl -sf http://localhost:8000/health > /dev/null 2>&1; do sleep 10; done' \
  || { echo "起動しなかった"; docker logs vllm-chat | tail -50; }
```

疎通を確認する。

```bash
curl http://localhost:8000/v1/models

curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "messages": [{"role": "user", "content": "12*17"}],
    "max_tokens": 128
  }'
```

`204` が含まれる応答が返れば、推論サーバーとして動いている。

> モデルによっては専用のコンテナと起動フラグが要る。Gemma 4系は
> `vllm/vllm-openai:gemma4-cu130`、DiffusionGemmaは `vllm/vllm-openai:gemma` を使う、
> といった指定がplaybookにある。新しいモデルを載せる前に、そのモデルの
> HFモデルカードとplaybookを見ること。

## 3. 常時稼働させる（systemd）

`--restart unless-stopped` だけでも再起動には追随するが、ログと起動順序を
OSの流儀に乗せたいなら、コンテナをsystemdから起こす。

`/etc/systemd/system/vllm-chat.service`:

```ini
[Unit]
Description=vLLM (chat) on GB10
After=docker.service network-online.target
Requires=docker.service

[Service]
Restart=always
RestartSec=10
# コンテナ自身の再起動ポリシーとは二重にしない
ExecStartPre=-/usr/bin/docker rm -f vllm-chat
ExecStart=/usr/bin/docker run --rm --name vllm-chat \
  --gpus all --ipc=host \
  -p 127.0.0.1:8000:8000 \
  --env-file /etc/vllm/chat.env \
  -v /home/<ユーザー>/.cache/huggingface:/root/.cache/huggingface \
  nvcr.io/nvidia/vllm:26.06-py3 \
  vllm serve openai/gpt-oss-20b \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.3 --max-model-len 65536 \
    --max-num-seqs 8 --enable-prefix-caching
ExecStop=/usr/bin/docker stop vllm-chat
# モデルのロードに時間がかかるので待つ
TimeoutStartSec=1800

[Install]
WantedBy=multi-user.target
```

`HF_TOKEN` と（使うなら）`VLLM_API_KEY` は `/etc/vllm/chat.env` に置き、
`chmod 600` にする。unitファイルに直接書かない。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vllm-chat
journalctl -u vllm-chat -f
```

モデルを複数常駐させるなら、このunitをポートと名前だけ変えて複製する
（`vllm-code.service` → 8001、`vllm-embed.service` → 8002 など）。

## 4. 社内ネットワークへの公開と認証

**vLLMは既定で無認証である。** `--api-key` を付けない限り、到達できる全員が
モデルを使えるし、投げたプロンプトも自由である。社内の他PCから使う時点で、
最低限これを行う。

```bash
# 起動フラグに追加する（VLLM_API_KEY 環境変数でも指定できる）
--api-key "<十分に長いランダム文字列>"
```

クライアントは `Authorization: Bearer <キー>` を付ける。

公開の形は、本リポジトリの [docs/server-deployment.md](server-deployment.md) と
同じ考え方でよい。推論サーバーを直接LANに晒さず、TLSと認証を担うリバースプロキシを
前に置く。

```text
利用者のPC（Streamlit RAG / Codex CLI）
        │ HTTPS :443
        ▼
Nginx（TLS終端・認証）             ← GB10上、または既存の社内プロキシ
        │ HTTP 127.0.0.1:8000 / :8001 / :8002
        ▼
vLLM（chat / code / embed）
```

`ufw` などでポートを絞ることも忘れない。GB10を持ち出す運用（会議室に持って行くなど）が
あるなら、なおさら `0.0.0.0` にvLLMを直接bindしないこと。

## 5. モデルの選び方と128GBの割り振り

NVIDIAがGB10での動作を確認しているモデルは playbook の Model Support Matrix に
一覧がある。用途別に、そこから選ぶのが安全である。

> Nemotron系を軸に、生成・VLM・埋め込みの3本を具体的に選定して載せる手順は
> [docs/vllm-gb10-models.md](vllm-gb10-models.md) に分けてある。下の表は
> 全体像をつかむための一覧である。

|用途|候補|量子化|備考|
|---|---|---|---|
|RAGの回答生成|`openai/gpt-oss-20b`|MXFP4|いま本リポジトリがOllamaで使っているものと同じ系列。移行の比較対象にしやすい|
|RAGの回答生成（大きく）|`openai/gpt-oss-120b`|MXFP4|128GBならMoEの120Bが載る。GB10を買った意味が最も出る枠|
|同上|`nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`|NVFP4|NVIDIA製。NVFP4はBlackwellの4bit形式で、帯域の節約になる|
|コーディングエージェント|`nvidia/Qwen3.6-35B-A3B-NVFP4`|NVFP4|playbookに「Agent Ready」の起動レシピがある（[6節](#6-コーディングエージェント向けの起動)）|
|図表の説明文化（VLM）|`nvidia/Qwen2.5-VL-7B-Instruct-NVFP4`|NVFP4|本リポジトリが `qwen2.5vl:7b` で行っている処理に対応する|
|埋め込み|`BAAI/bge-m3`|—|本リポジトリの既定と同じモデル（[7節](#7-埋め込みとリランカーをvllmで出す)、ただし注意あり）|
|リランカー|`BAAI/bge-reranker-v2-m3`|—|同上。いまはCPUのONNXで動いており、移す必然性は薄い|

**128GBの割り振りを先に決める。** vLLMは起動時に `--gpu-memory-utilization` の分だけ
確保して抱え込む。あとから起動するプロセスのために空きを残すのは自分の責任である。
たとえば3プロセス常駐なら、

|プロセス|用途|`--gpu-memory-utilization`|概算|
|---|---|---|---|
|`vllm-chat`|RAGの回答生成|0.35|約45GB|
|`vllm-code`|コーディングエージェント|0.35|約45GB|
|`vllm-embed`|埋め込み|0.05|約6GB|
|（残り）|OS・ページキャッシュ・他プロセス|—|約30GB|

のように配分する。合計を0.9近くまで詰めるとOSごと不安定になる。**最初は1プロセスで
立ち上げ、実際に使う構成が決まってから分割する**のが手戻りが少ない。

量子化の選び方は単純で、**NVFP4版が公開されているならそれを使う**。Blackwellの
FP4は演算器で直接扱え、重みが小さくなるぶん[帯域の律速](#gb10で先に知っておくこと)も
緩む。gpt-ossは配布時点でMXFP4なのでそのままでよい。BF16のチェックポイントは、
比較検証の用途を除けばGB10で選ぶ理由が薄い。

## 6. コーディングエージェント向けの起動

playbookが載せている「Agent Ready」のレシピをそのまま引く。ツール呼び出しの
パーサーと推論（reasoning）パーサーの指定が入っているのが要点で、これが無いと
エージェントからはツールが使えない。

```bash
docker run -d --name vllm-code --restart unless-stopped \
  --gpus all --ipc=host \
  -p 127.0.0.1:8001:8001 \
  -e HF_TOKEN="${HF_TOKEN}" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  nvidia/Qwen3.6-35B-A3B-NVFP4 \
  --host 0.0.0.0 --port 8001 \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --kv-cache-dtype fp8 \
  --attention-backend flashinfer \
  --moe-backend marlin \
  --gpu-memory-utilization 0.4 \
  --max-model-len 262144 \
  --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --enable-chunked-prefill \
  --async-scheduling \
  --enable-prefix-caching \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3,"moe_backend":"triton"}' \
  --load-format fastsafetensors \
  --reasoning-parser qwen3 \
  --tool-call-parser qwen3_xml \
  --enable-auto-tool-choice
```

`vllm/vllm-openai` イメージはエントリーポイントが `vllm serve` なので、モデル
ハンドルとフラグをそのままコンテナ引数として渡す（NGCイメージとは渡し方が違う）。

エージェント用途で効いているフラグ:

- `--enable-auto-tool-choice` / `--tool-call-parser` — ツール呼び出しをOpenAI互換の
  `tool_calls` として返させる。**エージェントを使うなら必須**
- `--reasoning-parser` — 思考部分を `reasoning_content` に分離する。これが無いと
  思考がそのまま本文に混ざる
- `--max-model-len 262144` — コードベースを読ませるための長い文脈
- `--max-num-seqs 4` — 1人がエージェントを回す前提。同時利用者が増えるなら上げる

### クライアント側の設定

vLLMが出すのは **OpenAI互換API**（`/v1/chat/completions`、`/v1/completions`、
`/v1/embeddings`、`/v1/responses` ほか）である。これに合わせられるツールなら繋がる。

- **Codex CLI** — 本リポジトリが `infra/codex-colab/config.toml.template` で
  組み立てているのと同じ形で、`base_url` をvLLMに向ける。

  ```toml
  model = "nvidia/Qwen3.6-35B-A3B-NVFP4"
  model_provider = "gb10-vllm"
  model_context_window = 262144

  [model_providers.gb10-vllm]
  name = "GB10 vLLM"
  base_url = "http://<GB10のアドレス>:8001/v1"
  wire_api = "chat"          # vLLMは /v1/responses も出すが、まずはchatで確かめる
  env_key = "VLLM_API_KEY"   # --api-key を付けた場合。Bearerで送られる
  ```

- **Cline / Continue / Roo Code など** — 「OpenAI Compatible」のプロバイダーを選び、
  Base URLに `http://<GB10のアドレス>:8001/v1`、モデル名にHFハンドルを入れる。
- **Claude Code** — Anthropic形式のAPIを話すので、**vLLMへ直接は向けられない**。
  使うならAnthropic形式↔OpenAI形式を変換するプロキシを別途挟むことになる。
  GB10のローカルモデルで完結させたいなら、OpenAI互換のエージェントを選ぶほうが素直である。

> **注意** 本リポジトリの `scripts/coding_agent.py`（`coding_agent/`）は、
> ColabのOllamaに繋ぐ専用の起動補助である。接続先にHTTPSを必須とし、
> `/api/tags` `/api/create` `/api/ps` といったOllama固有のAPIでコンテキスト長を
> 設定し、モデル名も `gpt-oss:20b` に固定している（`coding_agent/connection.py`）。
> **vLLMには向けられない。** vLLMを使うなら、上の `config.toml` を手で置くか、
> vLLM向けの経路をコードに足す必要がある。

## 7. 埋め込みとリランカーをvLLMで出す

vLLMは生成だけでなく、埋め込み（pooling）とリランクも出せる。

```bash
# 埋め込み（/v1/embeddings）
docker run -d --name vllm-embed --restart unless-stopped \
  --gpus all --ipc=host -p 127.0.0.1:8002:8002 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ${VLLM_IMAGE} \
  vllm serve BAAI/bge-m3 \
    --host 0.0.0.0 --port 8002 \
    --runner pooling \
    --gpu-memory-utilization 0.05
```

```bash
curl http://localhost:8002/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "BAAI/bge-m3", "input": ["これは埋め込みの確認である"]}'
```

`--runner pooling` の指定名は版で変わっている（古い版は `--task embed`）。
通らなければ `vllm serve --help` で確認する。bge-m3のsparse/ColBERT側の重みまで
使いたい場合は `--hf-overrides '{"architectures": ["BgeM3EmbeddingModel"]}'` が要るが、
本リポジトリは**dense（1024次元）しか使っていない**ので、その指定は不要である。

リランカーは `BAAI/bge-reranker-v2-m3` を同じくpoolingで起動すると
`/v1/rerank`（Jina/Cohere互換）と `/v1/score` が使える。ただし本リポジトリの
リランカーは `onnxruntime` のINT8でCPU実行しており、1問あたり約1.3秒
（README記載の実測値）。GB10へ移せば速くはなるが、**移行の必須項目ではない**。
生成の移行が終わってから考えればよい。

## 8. 本リポジトリのRAGとつなぐ

**ここが一番の落とし穴である。`OLLAMA_HOST` にvLLMのURLを入れても動かない。**

本リポジトリはOllamaの**ネイティブAPI**を直接叩いている。

|呼び出し元|叩いているURL|
|---|---|
|`ingest/chat.py`（`ask_json` / `ask_text` / `stream_chat`）|`{OLLAMA_HOST}/api/chat`|
|`ingest/embedder.py`（`embed_texts` / `embed_query`）|`{OLLAMA_HOST}/api/embed`|

vLLMが出すのは `/v1/...` のOpenAI互換APIだけで、`/api/chat` も `/api/embed` も無い。
`.env` の `OLLAMA_HOST` をvLLMに向ければ、404が返るだけである。
（`coding_agent/` だけは `base_url` に `/v1` を付けており、これはOllamaの
OpenAI互換エンドポイントを使っている。RAG本体とは別経路である。）

取りうる道は3つある。

**(a) GB10にOllamaも入れ、RAGはOllama・エージェントはvLLM（改修ゼロ・推奨の第一歩）**

DGX Spark playbookには `ollama` の項目もあり、GB10でOllamaは動く。RAG側は
`.env` の `OLLAMA_HOST` をGB10のOllamaに向けるだけで済む（[README「ColabのL4 GPUに
接続する」](../README.md#colabのl4-gpuに接続する)と同じ仕組みで、向き先が
ngrokからLANのアドレスに変わるだけである）。vLLMはコーディングエージェント専用に
使う。**まずこれで動かし、RAGの生成をvLLMへ寄せるかは実測してから決める**のが安全である。
Ollamaとの併存では、両者が同じ128GBを食い合う点にだけ注意する。

**(b) OpenAI互換の経路をコードに足す（本命）**

変更が要るのは実質4か所（`ask_json` / `ask_text` / `stream_chat` / `embed_texts`）で、
`OLLAMA_HOST` とは別に `OPENAI_BASE_URL` のような設定を読み、`/v1/chat/completions` と
`/v1/embeddings` を叩く実装を選べるようにする。Ollama経路を消さずに足すこと
（ノートPC単体での利用と、Colab接続が生きているため）。

**(c) 変換プロキシを挟む**

Ollamaネイティブ形式をOpenAI形式へ翻訳する層を自前で立てる。依存と障害点が増える
だけで、(b) より優れる点が無い。採らない。

### 埋め込みを移すときの必須手順

**埋め込みの経路を変えたら、ベクトルDBを作り直すこと。** 同じ `bge-m3` でも、
Ollama（GGUF量子化）とvLLM（safetensors）では出てくるベクトルが完全一致しない。
DBに入っているベクトルと問い合わせのベクトルは同じ経路で作られている必要がある。

```powershell
# 埋め込みの接続先を変えたら、差分ではなく全件を取り込み直す
.\myvenv313\Scripts\python.exe -m scripts.ingest_source --force
```

生成（`/api/chat`）だけを差し替える場合は、DBの作り直しは要らない。
**移行は「生成だけ先に」「埋め込みは後で、再取り込みとセットで」の順が安全である。**

### 外部通信の観点

`AGENTS.md` に、この構成が外へ出す通信の一覧がある。GB10のvLLMを社内に置いた場合、
`OLLAMA_HOST` 相当の宛先が**社内のLANアドレスになる**ため、質問文・会話履歴・
検索でヒットしたチャンク本文・取り込み時の文書本文がマシンの外へ出る範囲は
**社内ネットワークの中に収まる**。ColabのngrokへL4を借りていた構成より、
この点は明確に改善する。

ただし初回のモデル取得は huggingface.co への通信である。オフライン運用にするなら、
`~/.cache/huggingface` を作ったうえでネットワークを切る、という順序で用意する。
リランカーモデルのHEADリクエスト（`ingest/reranker.py`）についても同じ扱いになる。

## 9. トラブルシュート

|症状|原因|対処|
|---|---|---|
|起動時にCUDAカーネル初期化で落ちる|PyTorch/Tritonが `sm_120` 止まりのビルド|NGCの `nvcr.io/nvidia/vllm` か、GB10向けにビルドされたイメージを使う。素のpip導入を避ける|
|メモリはあるはずなのにOOM|UMAのページキャッシュが居座っている|`sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'` でバッファを流す（playbook記載）|
|`CUDA out of memory`|`--max-model-len` / `--max-num-seqs` が大きい|どちらも下げる。複数プロセス常駐なら `--gpu-memory-utilization` の合計を見直す|
|`Cannot access gated repo`|HFのライセンス未同意、またはトークンの権限不足|ブラウザーでモデルページの利用申請を通し、read権限のトークンを取り直す|
|エージェントがツールを呼ばない|`--enable-auto-tool-choice` と `--tool-call-parser` が無い|[6節](#6-コーディングエージェント向けの起動)のレシピに合わせる。パーサー名はモデルごとに違う|
|コンテナを作り直すたびに巨大なDL|HFキャッシュを未マウント|`-v ~/.cache/huggingface:/root/.cache/huggingface` を必ず付ける|
|初回起動が異様に遅い|モデルDLとカーネルのコンパイル|2回目以降は速くなる。`--load-format fastsafetensors` でロード自体も短縮できる|
|`.env` の `OLLAMA_HOST` を向けたのにRAGが404|vLLMに `/api/chat` は無い|[8節](#8-本リポジトリのragとつなぐ)。設定では解決しない。経路の追加が要る|
|GB10のデスクトップで日本語が打てない|IMEが未導入（vLLMとは無関係）|[docs/gb10-japanese-input.md](gb10-japanese-input.md)|

2台以上のGB10をQSFPで繋いで `--tensor-parallel-size 2` 以上で動かす手順
（Rayクラスタ）もplaybookにある。1台に載らないモデルを動かす必要が出てから読めばよい。

## 出典

- [NVIDIA DGX Spark playbook — vLLM for Inference](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/vllm/README.md)（コンテナのタグ、起動フラグ、Agent Readyレシピ、`drop_caches`、Rayクラスタ手順の出どころ。2026-06-12 更新）
- [NVIDIA NGC — vLLM コンテナのタグ一覧](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm/tags)
- [vLLM — OpenAI互換サーバー](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
- [vLLM — Pooling Models（埋め込み・リランク）](https://docs.vllm.ai/en/latest/models/pooling_models/)
- [vLLM issue #36821 — sm_121 / aarch64 でのビルド問題](https://github.com/vllm-project/vllm/issues/36821)
- [vLLM issue #31128 — Blackwell SM121(DGX Spark) 対応](https://github.com/vllm-project/vllm/issues/31128)
- [timothystewart6/vllm-gb10 — GB10（sm_121a）向けにビルドされた非公式イメージ](https://github.com/timothystewart6/vllm-gb10)
- 本リポジトリ内: [docs/gb10-japanese-input.md](gb10-japanese-input.md)（GB10のデスクトップの日本語入力）、
  [docs/server-deployment.md](server-deployment.md)（公開構成の考え方）、
  [README「ColabのL4 GPUに接続する」](../README.md#colabのl4-gpuに接続する)（`OLLAMA_HOST` の差し替え）、
  `ingest/chat.py` / `ingest/embedder.py`（Ollamaネイティブapiの呼び出し箇所）
