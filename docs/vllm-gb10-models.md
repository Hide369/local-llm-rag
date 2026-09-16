# GB10で使うモデルの選定と導入手順（RAG向け・見送り）

[docs/vllm-gb10.md](vllm-gb10.md) でvLLMが立った前提で、**生成・VLM・埋め込みの3本を
何にして、どう載せるか**を決める。用途は本リポジトリの日本語RAG（回答生成・図表の
説明文化・埋め込み）と、コーディングエージェントである。

> **RAG向けの選定は見送った（2026-09-16）。**
> RAG本体は Ollama（`gpt-oss:20b` / `bge-m3` / `qwen2.5vl:7b`）のまま運用する。
> 以下は調査の記録として残してある。**ここで挙げたモデルを実機で動かしてはいない。**
> 日本語の生成品質を現行の `gpt-oss:20b` と比べた実測も無い。
>
> **コーディングエージェント向けにはvLLMを使う。** そちらのモデルは
> `openai/gpt-oss-120b` で、選定も起動フラグもこの文書とは別である
> （[GB10のvLLM + gpt-oss-120b でCodexとClaude Codeを使う](vllm-gb10-coding-agent.md)）。

> **この文書の位置づけ**
> 選定の根拠と起動フラグは、NVIDIAのDGX Spark playbook、vLLM公式のレシピ集
> （`vllm-project/recipes`）、各モデルのモデルカードに基づく。**手元にGB10が
> 無いため実測していない。** トークン毎秒や実メモリの数値を書いていないのは、
> 測っていないものを書かないためである。モデルのHFハンドル、量子化版の有無、
> フラグ名は版で変わるので、導入時に[出典](#出典)で現物を確認すること。

## 目次

- [結論](#結論)
- [なぜこの3本なのか](#なぜこの3本なのか)
- [128GBの割り振り](#128gbの割り振り)
- [導入手順](#導入手順)
  - [0. 共通の準備](#0-共通の準備)
  - [1. 生成 — Nemotron-3-Super-120B-A12B-NVFP4](#1-生成--nemotron-3-super-120b-a12b-nvfp4)
  - [2. 生成（軽量版）— Nemotron-3-Nano-30B-A3B](#2-生成軽量版-nemotron-3-nano-30b-a3b)
  - [3. VLM — Nemotron-3-Nano-Omni-30B-A3B-Reasoning](#3-vlm--nemotron-3-nano-omni-30b-a3b-reasoning)
  - [4. 埋め込み — Nemotron-3-Embed-1B](#4-埋め込み--nemotron-3-embed-1b)
  - [5. リランカー（任意）](#5-リランカー任意)
  - [6. まとめて常駐させる](#6-まとめて常駐させる)
- [本リポジトリに入れるときに必要な変更](#本リポジトリに入れるときに必要な変更)
- [移行の順序](#移行の順序)
- [出典](#出典)

## 結論

|役割|モデル|量子化|なぜ|
|---|---|---|---|
|**生成**（RAG回答・エージェント）|`nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`|NVFP4|120B中12Bだけを活性化するMoEで、NVFP4の重みは約60GiB。**128GBのGB10に1台で載る上限クラス**。日本語がサポート言語に入っており、1Mトークン文脈とツール呼び出しに対応する|
|生成（軽量代替）|`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8`|FP8|30B中3B活性化。vLLM公式レシピに**DGX Spark専用の起動例がある**唯一のNemotron。VLMと埋め込みを同時常駐させたいならこちら|
|**VLM**（図表の説明文化）|`nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4`|NVFP4|画像・動画・音声・テキストを1モデルで扱う。C-RADIOv4-Hの視覚エンコーダーで**文書理解（図表・スクリーンショット）に強い**。本リポジトリのVLM用途はまさにこれ|
|VLM（軽量代替）|`nvidia/Qwen2.5-VL-7B-Instruct-NVFP4`|NVFP4|いま使っている `qwen2.5vl:7b` の直系。プロンプトを変えずに移れる|
|**埋め込み**|`nvidia/Nemotron-3-Embed-1B-NVFP4`|NVFP4|RTEBで首位を取った系列。評価対象34言語に日本語を含む。2048次元。1Bなので取り込みのバッチ処理が速い|
|埋め込み（現状維持）|`BAAI/bge-m3`|—|1024次元。**コード変更ゼロで移れる**唯一の選択肢|
|リランカー（任意）|`nvidia/llama-nemotron-rerank-1b-v2`|—|26言語（日本語含む）のクロスエンコーダー。8192トークンまで。現状はCPUのONNXで足りている|

**最初に読むべき注意が2つある。**

1. **埋め込みを替えると、ベクトルDBの作り直しとコード変更が必ず要る。**
   `ingest/embedder.py:19` に `EMBED_DIM = 1024` がハードコードされている。
   Nemotron-3-Embedは2048次元なので、この定数の変更と `--force` での全件再取り込みが
   要る。さらにこのモデルは `query:` / `passage:` の接頭辞を前提にしており、
   検索側と取り込み側で付け分ける実装が要る（[後述](#本リポジトリに入れるときに必要な変更)）。
   **埋め込みは最後に移すこと。**
2. **Nemotron 3は推論（reasoning）モデルである。** 思考を出す。`--reasoning-parser` を
   付けないと思考が本文に混ざり、`ingest/chat.py` の `ask_json`（JSONだけを期待する
   経路）が壊れる。起動フラグでの指定は必須である。

## なぜこの3本なのか

GB10の制約（[docs/vllm-gb10.md](vllm-gb10.md#gb10で先に知っておくこと)）に照らすと、
選定の軸は3つに絞られる。

**軸1: MoEであること。** GB10のメモリ帯域は約273GB/sで、生成の速さは事実上ここで
決まる。1トークンごとに全重みを読む密モデルは、この機械では重い。Nemotron 3は
Super（120B中12B活性化）もNano（30B中3B活性化）もMoEで、しかもハイブリッド
Mamba-Transformerである。**1トークンあたりに読む量が少ない構成**なので、GB10とは
相性がよい。120Bという規模をこの筐体で選べるのは、この構造のおかげである。

**軸2: NVFP4であること。** BlackwellのFP4は演算器で直接扱える。重みが小さくなれば
帯域の制約も緩む。Nemotron 3 Superは**NVFP4で学習された**チェックポイントが
配られており、後から4bitに潰したものとは品質の前提が違う。BF16版（約147GBが必要）は
そもそもGB10に載らないので、ここは選択の余地がない。

**軸3: 日本語が公式のサポート言語に入っていること。** Nemotron-3-Superの
サポート言語は英語・フランス語・ドイツ語・イタリア語・**日本語**・スペイン語・
中国語である。Nemotron-3-Embedの評価は34言語で、こちらにも日本語が入っている。
社内資料が日本語である以上、ここは外せない。

そのうえで正直に書いておく。**日本語の生成品質について、Nemotron 3 と Qwen3 系や
現行の `gpt-oss:20b` を比べた実測は持っていない。** サポート言語に入っていることと、
日本語の社内文書で期待通りに答えることは別である。[移行の順序](#移行の順序)で、
既存のOllama構成と並走させて比べる手順を書いたので、切り替えの判断はその結果で
行うこと。

## 128GBの割り振り

vLLMは起動時に `--gpu-memory-utilization` の分を確保して抱え込む。GB10はCPUと
GPUが同じ128GBを共有するので、**合計の管理は自分の仕事**である。

### 構成A: 品質優先（推奨）

生成にSuper 120Bを充て、VLMは常駐させない。**図表の説明文化は取り込み（`ingest_source`）
のときにしか動かない処理**なので、常駐させる必要がそもそも無い。

|プロセス|モデル|`--gpu-memory-utilization`|概算|
|---|---|---|---|
|`vllm-chat`|Nemotron-3-Super-120B-A12B-NVFP4|0.72|約92GB（重み約60GiB＋KV）|
|`vllm-embed`|Nemotron-3-Embed-1B-NVFP4|0.03|約4GB|
|（空き）|OS・ページキャッシュ・取り込み時のVLM|—|約30GB|

取り込みを回すときだけ、空き枠にVLMを立てる。Omni 30BのNVFP4は重みが約17GBなので、
この30GBの枠に `--gpu-memory-utilization 0.18` 程度で収まる。終わったら落とす。

### 構成B: 3本を常時上げておく

同時利用者が複数いる、取り込みを随時回す、応答の速さを優先する、という場合。

|プロセス|モデル|`--gpu-memory-utilization`|概算|
|---|---|---|---|
|`vllm-chat`|Nemotron-3-Nano-30B-A3B-FP8|0.35|約45GB|
|`vllm-vlm`|Nemotron-3-Nano-Omni-30B-A3B-NVFP4|0.25|約32GB|
|`vllm-embed`|Nemotron-3-Embed-1B-NVFP4|0.03|約4GB|
|（空き）|OS・ページキャッシュ|—|約47GB|

**構成Aから始めることを勧める。** 1本ずつ立てて、その都度 `nvidia-smi` と
`free -h` で実際の消費を見てから次を足すほうが、原因の切り分けが効く。
合計を0.9近くまで詰めるとOSごと不安定になる。

## 導入手順

### 0. 共通の準備

[docs/vllm-gb10.md](vllm-gb10.md) の1〜4節（前提確認、コンテナ取得、systemd、
公開と認証）を先に済ませておく。以下はその続きである。

```bash
export VLLM_IMAGE=nvcr.io/nvidia/vllm:26.06-py3   # 最新タグはNGCで確認する
export HF_TOKEN="<HuggingFaceのトークン>"   # ゲート付きモデルを扱う場合だけ
mkdir -p ~/.cache/huggingface
```

以下のモデルはすべてHuggingFaceから落ちてくるが、**ゲート付きでなければログイン
もトークンも要らない**。ゲート有無の判定、匿名で落とす手順、HFを使わない経路
（`ollama pull` / NGC / ModelScope / 別マシンで取って搬入）は
[docs/vllm-gb10.md の入手経路とオフライン運用](vllm-gb10.md#入手経路とオフライン運用)に
まとめてある。閉域で運用するなら、外に出られるマシンで先に取って
`~/.cache/huggingface` を搬入し、`HF_HUB_OFFLINE=1` を立てる。

以降のコマンドは共通部分をまとめて `vllm_run()` として書く。

```bash
vllm_run() {   # 使い方: vllm_run <コンテナ名> <ホスト側ポート> -- <vllm serve の引数...>
  local name=$1 port=$2; shift 3   # 3つ目の "--" を捨てる
  docker run -d --name "$name" --restart unless-stopped \
    --gpus all --ipc=host \
    -p 127.0.0.1:${port}:${port} \
    -e HF_TOKEN="${HF_TOKEN}" \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    "${VLLM_IMAGE}" "$@"
}
```

### 1. 生成 — Nemotron-3-Super-120B-A12B-NVFP4

ハイブリッドMamba-Transformer MoEなので、通常のTransformerには無いフラグが要る。

```bash
vllm_run vllm-chat 8000 -- \
  vllm serve nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
    --host 0.0.0.0 --port 8000 \
    --trust-remote-code \
    --tensor-parallel-size 1 \
    --max-model-len 131072 \
    --gpu-memory-utilization 0.72 \
    --max-num-seqs 8 \
    --max-num-batched-tokens 16384 \
    --kv-cache-dtype fp8 \
    --mamba-cache-mode align \
    --mamba-ssm-cache-dtype float32 \
    --enable-prefix-caching \
    --reasoning-parser nemotron_v3 \
    --tool-call-parser qwen3_xml \
    --enable-auto-tool-choice
```

|フラグ|意図|
|---|---|
|`--mamba-ssm-cache-dtype float32`|Mambaの状態キャッシュ。精度優先なら `float32`。新しい版では `float16` で速くなる代わりに精度がわずかに落ちる|
|`--mamba-cache-mode align`|ハイブリッドSSM層のメモリ確保の仕方。NVIDIAのレシピが指定している|
|`--kv-cache-dtype fp8`|KVキャッシュを半分にする。長文脈のRAGでは効き目が大きい|
|`--reasoning-parser nemotron_v3`|**必須**。思考を `reasoning_content` へ分離する。付けないと本文に混ざる|
|`--tool-call-parser qwen3_xml` / `--enable-auto-tool-choice`|コーディングエージェントに使うなら必須|
|`--max-model-len 131072`|モデル自体は1Mまで対応するが、KVキャッシュがその分要る。**128GBで1Mを指定してはいけない**。まず131072で立て、足りなければ上げる|

**地雷が2つある。**

- **MTP（Multi-Token Prediction）の投機デコードは、最初は付けないこと。**
  NVIDIAのレシピには `--speculative-config '{"method":"mtp","num_speculative_tokens":3}'`
  があるが、起動時に20GB以上を追加で食ってOOMする報告がある。GB10の128GBでは
  効いてくる。**素で立ち上げてから、空きを見て足す**順にする。
- **Mambaのprefix caching と MTP の併用でクラッシュする既知バグ**がある
  （vLLM issue #39809）。RAGでは prefix caching のほうが効くので、迷ったら
  `--enable-prefix-caching` を残してMTPを捨てる。

疎通を確認する。

```bash
curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
  "messages": [{"role":"user","content":"社内規程のRAGを作っている。日本語で1文だけ自己紹介して。"}],
  "max_tokens": 256
}' | python3 -m json.tool
```

`choices[0].message.content` に日本語の本文、`reasoning_content` に思考が分かれて
入っていれば、パーサーが効いている。**本文側に `<think>` のような痕跡が混ざって
いたら、`--reasoning-parser` の指定を見直す。**

### 2. 生成（軽量版）— Nemotron-3-Nano-30B-A3B

vLLM公式のレシピ集に、**DGX Spark向けの起動例がそのまま載っている**数少ない
モデルである。Superが重すぎる、VLMも常駐させたい、という場合はこちら。

このモデルは推論パーサーを**プラグインとして外から渡す**点が特殊である。

```bash
# ホスト側に落として、コンテナへマウントする
mkdir -p ~/vllm-plugins && cd ~/vllm-plugins
wget https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/resolve/main/nano_v3_reasoning_parser.py
```

```bash
docker run -d --name vllm-chat --restart unless-stopped \
  --gpus all --ipc=host -p 127.0.0.1:8000:8000 \
  -e HF_TOKEN="${HF_TOKEN}" \
  -e VLLM_USE_FLASHINFER_MOE_FP8=1 \
  -e VLLM_FLASHINFER_MOE_BACKEND=throughput \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v ~/vllm-plugins:/plugins \
  ${VLLM_IMAGE} \
  vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8 \
    --host 0.0.0.0 --port 8000 \
    --trust-remote-code \
    --tensor-parallel-size 1 \
    --max-model-len 262144 \
    --max-num-seqs 8 \
    --gpu-memory-utilization 0.35 \
    --kv-cache-dtype fp8 \
    --async-scheduling \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_coder \
    --reasoning-parser-plugin /plugins/nano_v3_reasoning_parser.py \
    --reasoning-parser nano_v3
```

FP8版では `--kv-cache-dtype fp8` と2つの `VLLM_*` 環境変数を、BF16版では
`--kv-cache-dtype auto` を使う（レシピの指定どおり）。`--async-scheduling` は
「常に付けることを推奨」とされている。

NVFP4版（`...-30B-A3B-NVFP4`）も公開されているが、playbookの動作確認表に
載っているのはBF16とFP8である。NVFP4を使うならハンドルの存在と起動可否を
自分で確かめること。

### 3. VLM — Nemotron-3-Nano-Omni-30B-A3B-Reasoning

画像・動画・音声・テキストを1モデルで扱う。本リポジトリが使うのは画像1枚→日本語の
説明文だけなので、能力としては過剰だが、**文書に貼られた図表・スクリーンショットの
理解**という一番効いてほしい部分が強い。

```bash
vllm_run vllm-vlm 8003 -- \
  vllm serve nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4 \
    --host 0.0.0.0 --port 8003 \
    --trust-remote-code \
    --max-model-len 131072 \
    --max-num-seqs 4 \
    --gpu-memory-utilization 0.25 \
    --reasoning-parser nemotron_v3
```

> **先にモデルカードを読むこと。** playbookは、このモデルを「モデル固有の
> 配備手順が要るもの」として名指ししている。動画を扱うなら
> `--video-pruning-rate 0.5` や `--media-io-kwargs '{"video":{"fps":2,"num_frames":256}}'`
> といった指定が別途要る。画像だけなら不要である。

画像で確認する。vLLMはOpenAI互換なので、**Ollamaの `images: [base64]` ではなく
`image_url` に data URL を入れる**形になる。ここは本リポジトリの `ingest/vlm.py` を
そのままでは使えない点である（[後述](#本リポジトリに入れるときに必要な変更)）。

```bash
B64=$(base64 -w0 /path/to/figure.png)
curl http://localhost:8003/v1/chat/completions -H "Content-Type: application/json" -d "{
  \"model\": \"nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4\",
  \"messages\": [{\"role\":\"user\",\"content\":[
    {\"type\":\"text\",\"text\":\"この画像に写っている図表の内容を、日本語で2〜3文にまとめて説明してください。\"},
    {\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/png;base64,${B64}\"}}
  ]}],
  \"max_tokens\": 512
}" | python3 -m json.tool
```

軽く済ませたいなら `nvidia/Qwen2.5-VL-7B-Instruct-NVFP4` に差し替える。重みが
小さく（`--gpu-memory-utilization 0.08` 程度）、いまOllamaで使っている
`qwen2.5vl:7b` と同じ系列なので、`ingest/vlm.py` の `CAPTION_PROMPT` を
書き換えずに済む可能性が高い。**まずこちらで経路を通し、品質に不満が出てから
Omniへ上げる**のが手戻りが少ない。

### 4. 埋め込み — Nemotron-3-Embed-1B

```bash
vllm_run vllm-embed 8002 -- \
  vllm serve nvidia/Nemotron-3-Embed-1B-NVFP4 \
    --host 0.0.0.0 --port 8002 \
    --runner pooling \
    --max-model-len 4096 \
    --max-num-batched-tokens 4096 \
    --gpu-memory-utilization 0.03
```

プーリング方式（平均プーリング）はチェックポイントの `config.json` に入っており、
vLLMが自動で読む。**`--override-pooler-config` で上書きしないこと**（検索品質が
落ちる）。

**このモデルは接頭辞を前提にしている。** 検索の問い合わせには `query: `、
取り込む文書側には `passage: ` を付ける。付け忘れると、動きはするが精度が落ちる。
静かに悪くなるので気づきにくい。

```bash
curl http://localhost:8002/v1/embeddings -H "Content-Type: application/json" -d '{
  "model": "nvidia/Nemotron-3-Embed-1B-NVFP4",
  "input": ["passage: 有給休暇は入社6か月後に10日付与される。"]
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['data'][0]['embedding']))"
```

`2048` と出れば期待どおりである。**この2048という数字が、次の節の作業量を決める。**

`BAAI/bge-m3` のまま行くなら、[docs/vllm-gb10.md の7節](vllm-gb10.md#7-埋め込みとリランカーをvllmで出す)の
コマンドを使う。1024次元なので `EMBED_DIM` を触らずに済む。

### 5. リランカー（任意）

```bash
vllm_run vllm-rerank 8004 -- \
  vllm serve nvidia/llama-nemotron-rerank-1b-v2 \
    --host 0.0.0.0 --port 8004 \
    --runner pooling \
    --gpu-memory-utilization 0.03
```

`/v1/rerank`（Jina／Cohere互換）に問い合わせ文と候補の配列を渡す。

ただし本リポジトリのリランカーは `onnxruntime` のINT8でCPU実行しており、
1問あたり約1.3秒（READMEの実測値）で足りている。**移行の必須項目ではない。**
生成と埋め込みが落ち着いてから考えればよい。

### 6. まとめて常駐させる

[docs/vllm-gb10.md の3節](vllm-gb10.md#3-常時稼働させるsystemd)のsystemd unitを、
ポートと名前とモデルだけ変えて複製する。`vllm-chat.service`（8000）、
`vllm-embed.service`（8002）、必要なら `vllm-vlm.service`（8003）。

構成Aで運用するなら、VLMのunitは `enable` せず、取り込みのときだけ
`sudo systemctl start vllm-vlm` して、終わったら止める。

## 本リポジトリに入れるときに必要な変更

**設定だけでは繋がらない。** 理由は [docs/vllm-gb10.md の8節](vllm-gb10.md#8-本リポジトリのragとつなぐ)の
とおりで、このアプリはOllamaのネイティブAPIを直接叩いている。モデルを替えると、
それに加えて以下が要る。

|変更箇所|いま|vLLM＋Nemotronでは|
|---|---|---|
|`ingest/embedder.py:19`|`EMBED_DIM = 1024`|`2048`（Nemotron-3-Embed-1B）。bge-m3のままなら変更不要|
|`ingest/embedder.py`（`embed_texts` / `embed_query`）|`/api/embed` に生のテキスト|`/v1/embeddings`。**取り込み側に `passage: `、検索側に `query: ` を付け分ける**|
|`ingest/chat.py`（`ask_json`）|`"format": "json"`|vLLMでは `response_format: {"type":"json_object"}`（構造化出力）。**このキーは効かないので必ず置き換える**|
|`ingest/chat.py`（`NUM_CTX = 8192`）|`options.num_ctx` で指定|vLLMは起動時の `--max-model-len` で決まり、リクエストごとには指定しない。**推論モデルは思考でトークンを食うため、8192相当のままだと回答が出ないまま打ち切られる**（この定数のコメントにある `gpt-oss:20b` での実測と同じ現象が、より強く出る）|
|`ingest/chat.py`（応答の取り出し）|`message.content`|`choices[0].message.content`。思考は `reasoning_content` に分かれる（`--reasoning-parser` 前提）|
|`ingest/vlm.py`|`messages[].images: [base64]`|`content` を配列にして `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}`|
|ベクトルDB|1024次元で構築済み|**次元を変えたら `--force` で全件取り込み直し**。差分取り込みでは直らない|
|`ingest/retrieval.py:40`|`RELEVANCE_THRESHOLD = 0.50`|**測り直しが要る。** 埋め込みモデルが変われば距離の分布そのものが変わる。圏内・圏外を分ける唯一の関門なので、この値が合わないと圏外の質問にも答えてしまう|

```powershell
# 埋め込みのモデルまたは経路を変えたら、必ずこれを実行する
.\myvenv313\Scripts\python.exe -m scripts.ingest_source --force
```

`EMBED_DIM` はテストが7ファイルから参照している（`tests/test_store.py` ほか）。
定数を変えればテスト側は追随するが、**実在のDBは追随しない**。ここを取り違えると、
検索が黙って的外れになる（次元が合わなければエラーになるが、接頭辞の付け忘れは
エラーにならない）。

## 移行の順序

一度に全部替えないこと。壊れたときに、モデルのせいか経路のせいか切り分けられなくなる。

1. **GB10にOllamaを入れ、いまのモデルのまま `.env` の `OLLAMA_HOST` を向ける。**
   これで「サーバーが変わった影響」だけを先に確認できる。改修はゼロである。
2. **vLLMでNemotron-3-Super（または Nano）を立て、curlだけで日本語の応答品質を見る。**
   社内資料から実際にあった質問を10問ほど選び、いまの `gpt-oss:20b` の答えと
   並べて読む。**ここで納得できなければ、以降へ進む意味がない。**
3. **生成の経路だけをvLLMに向ける。** `ingest/chat.py` にOpenAI互換の経路を足す。
   DBは触らないので、いつでも戻せる。
4. **VLMを移す。** まず `Qwen2.5-VL-7B-Instruct-NVFP4` で `ingest/vlm.py` の
   画像の渡し方を直し、通ってからOmniへ上げるか決める。取り込みをやり直すので、
   資料の少ない環境で先に試すこと。
5. **最後に埋め込み。** `EMBED_DIM` と接頭辞を直し、`--force` で全件取り込み直す。
   取り込み直す前に、`vector_store.sqlite3` を退避しておくこと。

各段階で `scripts/check_retrieval.py` を回し、検索が期待どおりの資料を引けているかを
見ること。生成の良し悪しより先に、**検索が壊れていないこと**を確かめる。

特に手順5のあとは必須である。このスクリプトは「関連する質問の最大距離 ≤ しきい値 <
圏外の質問の最小距離」が成り立つかを測るもので、**埋め込みモデルを替えたら、まず
ここが崩れる**。崩れていれば `RELEVANCE_THRESHOLD` を測り直した値に入れ替える。
スクリプトの冒頭にも「成り立たない場合はしきい値の再調整か、チャンクサイズ・
埋め込みモデルの見直しが必要」と書いてある。**その「見直し」を、いままさに
こちらから引き起こしている**ということである。

## 出典

- [NVIDIA DGX Spark playbook — vLLM for Inference](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/vllm/README.md)（Spark上での動作確認モデル一覧、`gpu-memory-utilization` の目安）
- [vLLM Recipes — NVIDIA Nemotron-3-Nano-30B-A3B](https://github.com/vllm-project/recipes/blob/main/NVIDIA/Nemotron-3-Nano-30B-A3B.md)（DGX Spark専用の起動例、推論パーサープラグイン、`async-scheduling` と `mamba-ssm-cache-dtype` の指針）
- [vLLM issue #39809 — Mamba prefix caching と MTP の併用でクラッシュ](https://github.com/vllm-project/vllm/issues/39809)
- [Nemotron 3 Nano Omni（論文）](https://arxiv.org/abs/2604.24954)（視覚・音声エンコーダーの構成と256K文脈）
- [Nemotron 3 Super（論文）](https://arxiv.org/abs/2604.12374)（ハイブリッドMamba-Transformer MoEの構成）
- NVIDIA公式のモデルカード（HuggingFace / build.nvidia.com）— サポート言語、量子化版の有無、`query:` / `passage:` の接頭辞、モデル固有の配備手順。**導入時は必ずこちらを正とすること**
- 本リポジトリ内: [docs/vllm-gb10.md](vllm-gb10.md)（vLLM自体の導入）、
  `ingest/embedder.py` / `ingest/chat.py` / `ingest/vlm.py`（変更が要る箇所）
