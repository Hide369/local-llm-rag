# GB10を4台スイッチで繋ぎ、vLLMで1つのモデルを分散して動かす

GB10（DGX Spark）4台を200GbEのQSFPスイッチで繋ぎ、1台に載らない大きなモデルを
4台にまたがせて、1つのOpenAI互換エンドポイントとして提供するための手順。
**ネットワークを作る → NCCLで帯域を確かめる → 各台でvLLMコンテナを起動する →
ヘッドのAPIを確かめる**、の順に進める。

> **この文書の位置づけ（2026-11-07）**
> 1台でのvLLMの立て方は [GB10サーバーにvLLMを立てる](vllm-gb10.md)、メモリが
> 足りないときの切り分けは [GB10のvLLMでメモリが枯渇したときの対処](vllm-gb10-memory.md)
> にある。ここは**4台構成で増える部分**だけを書く。
>
> 手順は NVIDIA の DGX Spark playbook（スイッチ接続 2026-08-12 更新、NCCL 2026-10-14 更新、
> vLLMクラスタ 2026-10-22 更新）と vLLM のマルチノードの公式ドキュメントに基づく。
> **NVIDIAの最新のvLLMクラスタ手順のコマンド例は2台分しかなく、4台の例は
> Ray を使う旧版の手順にある。** この文書の4台用のコマンドは、それらを4台へ
> 広げたものである。**実機での起動と実測はしていない。** コンテナのタグ、
> フラグ名、インターフェース名は版と配線で変わるので、導入時に [出典](#出典) の
> 各ページで現物を確認すること。

## 目次

- [先に知っておくこと](#先に知っておくこと)
- [構成と用意するもの](#構成と用意するもの)
- [1. 4台の下準備](#1-4台の下準備)
- [2. スイッチを設定して配線する](#2-スイッチを設定して配線する)
- [3. ConnectXのネットワークを設定する](#3-connectxのネットワークを設定する)
- [4. パスワード無しのSSHを張る](#4-パスワード無しのsshを張る)
- [5. NCCLで帯域を確かめる](#5-ncclで帯域を確かめる)
- [6. モデルを4台に置く](#6-モデルを4台に置く)
- [7. vLLMを4台で起動する](#7-vllmを4台で起動する)
- [8. 動作を確かめる](#8-動作を確かめる)
- [9. 止める・起動し直す](#9-止める起動し直す)
- [別案: Rayで起動する](#別案-rayで起動する)
- [つまずきやすいところ](#つまずきやすいところ)
- [出典](#出典)

## 先に知っておくこと

**1. 4台で512GBの1つの塊になるわけではない。** 各台が重みの1/4とKVキャッシュを
自分の128GBに持つ。`--gpu-memory-utilization` は**各台ごと**の割合である。
1台のOSやOllamaがメモリを食っていると、その1台が足を引っ張って全体が起動しない。
4台すべてで [メモリ枯渇の対処](vllm-gb10-memory.md) の1・2節（競合プロセスの停止と
キャッシュ解放）を行ってから起動する。

**2. GB10は1台にGPUが1つなので、分割の仕方は2つある。**

|分割|フラグ|台間の通信|向いている用途|
|---|---|---|---|
|テンソル並列（推奨）|`--tensor-parallel-size 4`|層ごとに毎回発生し多い|1リクエストの応答を速くしたい。NVIDIAの4台の例もこれ|
|パイプライン並列|`--pipeline-parallel-size 4`|段の境目だけで少ない|台間の帯域が出ないとき。1リクエストは速くならない|

vLLMの公式ドキュメントは「ノード内はテンソル並列、ノード間はパイプライン並列」を
基本としているが、GB10はノード内にGPUが1つしかない。200GbEのRoCEで帯域が出るなら
テンソル並列、5節のNCCLテストで帯域が出ないならパイプライン並列、と決める。
どちらでも `テンソル並列数 × パイプライン並列数 = 4` にする。

**3. 台間の通信路と管理用の通信路は分ける。** 推論中の台間の通信はConnectX-7（QSFP）、
社内LANからのAPI呼び出しやHugging Faceからのモデルのダウンロードは通常のEthernet
（`enP7s7`）を使う。推論中のConnectXの帯域を、台間の通信だけに使うためである。
4節のSSH、6節のモデルの写し、9節の停止はConnectXのIP（`192.168.100.x`）宛てに
行うが、どれも推論の前後に行う作業なので、推論の通信と帯域を取り合わない。

## 構成と用意するもの

```
            社内LAN（管理・API・モデル取得）
     ┌────────┬────────┬────────┬────────┐
   enP7s7   enP7s7   enP7s7   enP7s7
  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
  │node-1│ │node-2│ │node-3│ │node-4│
  │ヘッド│ │      │ │      │ │      │
  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
     │QSFP    │QSFP    │QSFP    │QSFP（各台1本・200Gbps）
  ┌──┴────────┴────────┴────────┴──┐
  │   QSFPスイッチ（1つのブリッジ）   │
  └────────────────────────────────┘
```

|もの|要件|
|---|---|
|GB10|4台。**メモリ容量をそろえる**（すべて128GB）|
|QSFPスイッチ|QSFP56-DD（200Gbps以上）のポートが4つ以上。400Gbpsポートならブレイクアウトで2×200Gbpsに分けてもよい|
|QSFPケーブル|1台に1本。NVIDIA推奨は0.4mのもの。**1本で帯域は出し切れる**|
|ユーザー|4台で同じユーザー名、sudo権限|
|OS|DGX OS を最新にそろえる（NVIDIAのvLLMクラスタ手順は2026年4月版以降を前提にしている）|

この文書のIPとインターフェース名は次で統一する（NVIDIAのplaybookと同じ）。

|台|役割|`enp1s0f1np1`|`enP2p1s0f1np1`|
|---|---|---|---|
|node-1|ヘッド（APIを出す）|192.168.100.1|192.168.101.1|
|node-2|ワーカー|192.168.100.2|192.168.101.2|
|node-3|ワーカー|192.168.100.3|192.168.101.3|
|node-4|ワーカー|192.168.100.4|192.168.101.4|

> **2〜4台ならNVIDIA Sync の Cluster Assistant が推奨経路である。** 配線の確認、
> ConnectXのIP設定、SSHの設定をまとめて行う。Cluster Assistant が成功したら、
> 2〜4節は飛ばして5節へ進んでよい。下は手作業で行う場合の手順である。

## 1. 4台の下準備

4台すべてで行う。

```bash
whoami                  # 4台で同じであること
sudo whoami             # root と出ること
netplan --version
docker ps               # permission denied なら下を実行
sudo usermod -aG docker $USER && newgrp docker
```

ユーザー名がそろっていない場合は、4台に同じユーザー（例: `nvidia`）を作り、
以降はそのユーザーで作業する。

```bash
sudo useradd -m nvidia
sudo usermod -aG sudo,docker nvidia
sudo passwd nvidia
su - nvidia
```

## 2. スイッチを設定して配線する

スイッチの管理画面（CLIかWeb）で次を行う。操作方法はスイッチの取扱説明書に従う。

1. GB10をつなぐ4ポートを有効にする
2. 4ポートを**1つのブリッジ**に入れる（既定のブリッジでもよい）。4台を同じ
   L2セグメントにするためで、ハードウェアオフロードを1ブリッジに限るスイッチもある
3. 各ポートを200Gbpsにする。自動ネゴシエーションで200Gbpsにならないときは、
   自動ネゴシエーションを切り、手動で200Gbps（例: `200G-baseCR4`）に固定する

配線は、**4台とも同じConnectXポート**を使う。NVIDIAの手順に合わせ、Ethernetポートから
遠い側（2番目）のQSFPポートを使う。そろえておかないと、インターフェース名が台ごとに
変わり、NCCLのテストが失敗しやすい。

配線したら4台で確かめる。

```bash
ibdev2netdev
# rocep1s0f0 port 1 ==> enp1s0f0np0 (Down)
# rocep1s0f1 port 1 ==> enp1s0f1np1 (Up)       ← この2つが Up になる
# roceP2p1s0f0 port 1 ==> enP2p1s0f0np0 (Down)
# roceP2p1s0f1 port 1 ==> enP2p1s0f1np1 (Up)

sudo ethtool enp1s0f1np1   | grep Speed   # Speed: 200000Mb/s であること
sudo ethtool enP2p1s0f1np1 | grep Speed
```

1つの物理ポートは2つの論理インターフェース（`enp1s0f1np1` と `enP2p1s0f1np1`）に
見える。どちらも `Up` にならないときは、ケーブルを挿し直して再起動する。速度が
`100000Mb/s` のときは、スイッチ側のポート速度の設定（上の3）を見直す。

## 3. ConnectXのネットワークを設定する

固定IPを割り当てる。**2つの論理インターフェースは別のサブネットにする**
（`192.168.100.x/24` と `192.168.101.x/24`）。同じサブネットにすると経路が曖昧になり、
NCCLの通信が失敗する。

node-1 では次のようにする。node-2〜4 は末尾の `.1` をそれぞれ `.2`〜`.4` に変える。

```bash
sudo tee /etc/netplan/40-cx7.yaml > /dev/null <<'EOF'
network:
  version: 2
  ethernets:
    enp1s0f1np1:
      addresses:
        - 192.168.100.1/24
      dhcp4: no
    enP2p1s0f1np1:
      addresses:
        - 192.168.101.1/24
      dhcp4: no
EOF
sudo chmod 600 /etc/netplan/40-cx7.yaml
sudo netplan apply

ip -4 addr show enp1s0f1np1 | grep inet   # 192.168.100.1/24 が付いていること
```

スイッチにDHCPサーバー機能があるなら、そちらで配ってもよい（その場合は netplan に
`dhcp4: true` だけを書く）。ただし、後の手順でヘッドのIPを固定して使うので、
この文書では固定IPを前提にする。

## 4. パスワード無しのSSHを張る

どれか1台で、NVIDIAの検出スクリプトを使うのが早い。初回は各台のパスワードを聞かれる。

```bash
curl -O https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/connect-two-sparks/assets/discover-sparks
bash ./discover-sparks
```

うまくいかないときは手で配る。4台すべてで次を実行する。

```bash
[ -f ~/.ssh/id_rsa.pub ] || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
for ip in 192.168.100.1 192.168.100.2 192.168.100.3 192.168.100.4; do
  ssh-copy-id -i ~/.ssh/id_rsa.pub "$USER@$ip"
done
```

node-1から確かめる。4台とも、パスワードを聞かれずにホスト名が返ればよい。

```bash
for ip in 192.168.100.1 192.168.100.2 192.168.100.3 192.168.100.4; do ssh "$ip" hostname; done
```

## 5. NCCLで帯域を確かめる

vLLMを動かす前に、4台の間でGPU間通信が出ることを確かめる。**ここで帯域が出ないまま
vLLMへ進むと、遅い・止まる原因の切り分けができなくなる。**

NVIDIAのスクリプトを使うのが早い。node-1で、各台の**管理用IP**（`enP7s7` のアドレス、
普段SSHする先）を渡して実行する。

```bash
curl -fsSL "https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-nccl/assets/setup.sh" -o setup.sh
curl -fsSL "https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-nccl/assets/launch.sh" -o launch.sh

bash setup.sh <node-2の管理IP> <node-3の管理IP> <node-4の管理IP>     # 4台にNCCLとテストをビルド
bash launch.sh --topology switch <node-1の管理IP> <node-2の管理IP> <node-3の管理IP> <node-4の管理IP>
```

手で行う場合は、4台すべてでNCCLとテストをビルドする。NCCLはGB10（`sm_121`）向けに
ソースからビルドする。nccl-tests は v2.19.7 に固定する（v2.20.0以降はシステムの
OpenMPIとリンクできないとNVIDIAが注記している）。

```bash
sudo apt-get update && sudo apt-get install -y libopenmpi-dev
git clone -b v2.31.2-1 https://github.com/NVIDIA/nccl.git ~/nccl/
cd ~/nccl/ && make -j src.build NVCC_GENCODE="-gencode=arch=compute_121,code=sm_121"

export CUDA_HOME="/usr/local/cuda"
export MPI_HOME="/usr/lib/aarch64-linux-gnu/openmpi"
export NCCL_HOME="$HOME/nccl/build/"
export LD_LIBRARY_PATH="$NCCL_HOME/lib:$CUDA_HOME/lib64/:$MPI_HOME/lib:$LD_LIBRARY_PATH"

git clone -b v2.19.7 https://github.com/NVIDIA/nccl-tests.git ~/nccl-tests/
cd ~/nccl-tests/ && make MPI=1
```

node-1から4台で実行する。IPの後ろの `:1` は「1台に1プロセス」の意味で、外さない。

```bash
mpirun -np 4 -H <node-1の管理IP>:1,<node-2の管理IP>:1,<node-3の管理IP>:1,<node-4の管理IP>:1 \
  --mca plm_rsh_agent "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no" \
  -x LD_LIBRARY_PATH=$LD_LIBRARY_PATH \
  -x UCX_NET_DEVICES=enP7s7 \
  -x NCCL_SOCKET_IFNAME=enP7s7 \
  -x OMPI_MCA_btl_tcp_if_include=enP7s7 \
  -x NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 \
  -x NCCL_DEBUG=INFO \
  $HOME/nccl-tests/build/all_gather_perf -b 16G -e 16G 2>&1 | tee nccl-test.log

grep -E "NET/(IB|Socket)" nccl-test.log | head   # NET/IB が出ていること
```

`mpirun` の制御は管理用のEthernetで行い、GPU間のデータはNCCLがConnectXのRoCEを
使う。`NCCL_IB_HCA` と `NCCL_DEBUG` はNVIDIAの手順のコマンドには無く、この文書で
足したものである。`NCCL_IB_HCA` は7節のvLLMと同じHCAを使わせて、テストと本番の
条件をそろえるため、`NCCL_DEBUG=INFO` はRoCEを使えたかをログで確かめるためである。

**ログに `NET/IB` ではなく `NET/Socket` と出たら、その帯域の数値は使えない。**
NCCLがRoCEを使えず、`NCCL_SOCKET_IFNAME` の管理用Ethernet（TCP）へ黙って切り替えた
ときの値で、ConnectXの帯域を測れていない。`NCCL_IB_HCA` の名前（2節の
`ibdev2netdev` の左側）を見直してからやり直す。

`NET/IB` を確かめたうえで、出力の `busbw` を記録しておく。**合格の目安となる帯域の数値は、NVIDIAの
手順に書かれておらず、この文書でも実測していない。** 2台で測った値と大きく
変わらないか、を見る。

## 6. モデルを4台に置く

**4台すべてに、同じパスで同じモデルが必要である。** 各台がHugging Faceのキャッシュ
（`~/.cache/huggingface`）を持ち、コンテナへマウントする。4台で同時にダウンロード
すると社内LANの帯域を4倍使うので、1台で取ってから他の3台へ写してもよい。

```bash
# 4台すべてで（または node-1 で取ってから rsync）
hf auth login                       # ゲート付きのモデルなら
hf download <モデルのHFハンドル>

# node-1 から他の3台へ写す場合（ConnectX経由で速い）
for ip in 192.168.100.2 192.168.100.3 192.168.100.4; do
  rsync -a --mkpath --info=progress2 ~/.cache/huggingface/hub/ "$ip:.cache/huggingface/hub/"
done
```

`--mkpath` は、写し先に `~/.cache/huggingface/hub/` がまだ無いときに作るためのものである
（rsync 3.2.3以降。無いと、写し先の親ディレクトリが無いと言われて失敗する）。

モデルの選び方は [vllm-gb10-models.md](vllm-gb10-models.md) と同じ考え方
（MoE が有利、量子化済みのチェックポイントを選ぶ）を使う。NVIDIAの4台の例は
`MiniMaxAI/MiniMax-M2.5` をテンソル並列4で動かしている。**そのモデルのレシピに
書かれたイメージ・フラグ・環境変数は一揃いで使う**こと（NVIDIAも混ぜないよう
注意している）。

## 7. vLLMを4台で起動する

Rayを使わない、vLLMの組み込みのマルチノード実行で起動する。NVIDIAの最新の
vLLMクラスタ手順もこの方式である。各台で同じコンテナを起動し、同じ `vllm serve` を
**`--node-rank` だけ変えて**実行する。

### 7-1. 各台で値を決める

4台すべてのホストのシェルで設定する。`HEAD_IP` は4台とも node-1 のConnectXのIPにする。

```bash
export HEAD_IP=192.168.100.1                    # 4台とも同じ
export ETH_IF=enp1s0f1np1                       # 各台のConnectXのインターフェース
export IB_IF=rocep1s0f1,roceP2p1s0f1            # 各台のRoCE HCA（ibdev2netdev の左側）
export MASTER_PORT=29501
export IMAGE=nvcr.io/nvidia/vllm:26.06-py3      # 最新タグはNGCで確認する
export HF_CACHE_DIR="$HOME/.cache/huggingface"
```

`IB_IF` は2節の `ibdev2netdev` で `Up` だった行の左側の名前である。別のQSFPポートに
挿した場合は名前が変わる。

### 7-2. 各台でメモリを空ける

4台すべてで、[メモリ枯渇の対処](vllm-gb10-memory.md) の1・2節を行う。

```bash
sudo systemctl stop ollama
docker rm -f vllm_cluster 2>/dev/null
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches
free -h
```

### 7-3. 各台でコンテナを起動する

4台すべてで同じコマンドを実行する。ホストのネットワークをそのまま使い、
NCCLにConnectXとRoCEを使わせる環境変数を渡す。

```bash
docker run --rm -it \
  --name vllm_cluster \
  --privileged --gpus all --ipc host --network host \
  --shm-size=16g \
  --ulimit nofile=1048576:1048576 \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  -e HF_TOKEN="${HF_TOKEN:-}" \
  -e UCX_NET_DEVICES="$ETH_IF" \
  -e NCCL_SOCKET_IFNAME="$ETH_IF" -e NCCL_IB_HCA="$IB_IF" \
  -e NCCL_IB_DISABLE=0 -e NCCL_IGNORE_CPU_AFFINITY=1 \
  -e OMPI_MCA_btl_tcp_if_include="$ETH_IF" \
  -e GLOO_SOCKET_IFNAME="$ETH_IF" -e TP_SOCKET_IFNAME="$ETH_IF" \
  -e HEAD_IP="$HEAD_IP" -e MASTER_PORT="$MASTER_PORT" \
  -v "$HF_CACHE_DIR:/root/.cache/huggingface" \
  -v "$HOME/.cache/vllm:/root/.cache/vllm" \
  --entrypoint /bin/bash "$IMAGE"
```

各台でコンテナの中のシェルが開く。

### 7-4. 各台で `vllm serve` を実行する

コンテナの中で、台ごとに rank を決める。**node-1（ヘッド）だけがAPIを出し、
ほかの3台は `--headless` にする。**

```bash
NODE_ARGS=(--node-rank 0)                 # node-1
NODE_ARGS=(--node-rank 1 --headless)      # node-2
NODE_ARGS=(--node-rank 2 --headless)      # node-3
NODE_ARGS=(--node-rank 3 --headless)      # node-4
```

続けて、4台で同じコマンドを実行する。**node-1を先に**実行し、続けて残りの3台で
実行する。4台がそろうまで起動は待ち合わせる。

```bash
vllm serve <モデルのHFハンドル> \
  --tensor-parallel-size 4 \
  --pipeline-parallel-size 1 \
  --nnodes 4 "${NODE_ARGS[@]}" \
  --master-addr "$HEAD_IP" --master-port "$MASTER_PORT" \
  --host 0.0.0.0 --port 8000 \
  --gpu-memory-utilization 0.8 \
  --max-model-len 32768 \
  --max-num-seqs 4 \
  --kv-cache-dtype fp8 \
  --api-key "<十分に長いランダム文字列>"
```

|フラグ|意味|
|---|---|
|`--tensor-parallel-size 4` / `--pipeline-parallel-size 1`|4台でテンソル並列。帯域が出ないときは `1` と `4` に入れ替える（[先に知っておくこと](#先に知っておくこと)の2）|
|`--nnodes 4` / `--node-rank 0〜3`|台数と各台の番号。ヘッドが0|
|`--master-addr` / `--master-port`|台どうしが待ち合わせる先。4台ともヘッドのConnectXのIPと同じポート|
|`--headless`|ワーカーはAPIを出さない|
|`--gpu-memory-utilization 0.8`|各台の128GBに対する割合。OSの分を残す。落ちるなら下げる|
|`--max-model-len` / `--max-num-seqs`|KVキャッシュの予約を抑えるため、まず小さめに始めて広げる|
|`--api-key`|vLLMは既定で無認証。社内LANへ出すなら必ず付ける|

使うモデルのレシピに、パーサー（`--tool-call-parser` など）、量子化、`--trust-remote-code`
などの指定があれば、4台すべてのコマンドに同じものを足す。コーディングエージェントから
使うなら、道具呼び出しのフラグは必須である（[vllm-gb10-coding-agent.md](vllm-gb10-coding-agent.md)）。

## 8. 動作を確かめる

node-1の別のシェルで確かめる。モデルのロードには時間がかかるので、`/health` が200を
返すまで待つ。

```bash
curl --fail-with-body -i http://127.0.0.1:8000/health

curl http://127.0.0.1:8000/v1/models -H "Authorization: Bearer <api-key>"

curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api-key>" \
  -d '{"model":"<モデルのHFハンドル>","messages":[{"role":"user","content":"こんにちは"}],"max_tokens":64}'
```

確認すること。

- 応答が返る。回答が途中で切れたら `finish_reason` を見る
- 4台すべてのログに、モデルの読み込みとKVキャッシュの確保量が出ている
- NCCLがRoCEを使っている。確かめたいときは、`vllm serve` の前に
  `export NCCL_DEBUG=INFO` を付けて起動し、ログに `NET/IB` が出ることを見る。
  `NET/Socket` と出たら、ConnectXのRDMAではなく普通のTCPで通信しており遅い
- 推論中、4台それぞれで `free -h` の `available` が10GB以上残っている

社内LANのクライアントからは、`127.0.0.1` を node-1 の管理用IPに替えて叩く。
LiteLLM Proxy の背後に置く場合は、node-1 の `http://<管理IP>:8000/v1` を
バックエンドとして登録する（LiteLLMの構成は `docs/proxy/` の手順書を参照）。

## 9. 止める・起動し直す

ヘッドのコンテナを止めると全体が止まる。4台すべてで止めておくと確実である。

```bash
# 4台すべてで（node-1から一括で行う例）
for ip in 192.168.100.1 192.168.100.2 192.168.100.3 192.168.100.4; do
  ssh "$ip" docker stop vllm_cluster
done
```

モデルと実行時のキャッシュはホストに残るので、2回目以降の起動は速い。
起動し直すときは7-2節から行う。

ネットワーク設定を元に戻すときは、4台で次を実行する。スイッチ側は、自動
ネゴシエーションとブリッジの設定を元に戻す。

```bash
sudo rm /etc/netplan/40-cx7.yaml
sudo netplan apply
```

## 別案: Rayで起動する

NVIDIAの旧版のvLLM手順は、4台をRayクラスタにして起動していた（MiniMax-M2.5を
テンソル並列4で動かす例）。組み込みのマルチノード実行で問題が出たときの代替として
残す。コンテナは vLLM の `run_cluster.sh` が起動する。

```bash
# 4台すべてで
wget https://raw.githubusercontent.com/vllm-project/vllm/refs/heads/main/examples/ray_serving/run_cluster.sh
chmod +x run_cluster.sh
export VLLM_IMAGE=nvcr.io/nvidia/vllm:26.06-py3
export MN_IF_NAME=enp1s0f1np1
export VLLM_HOST_IP=$(ip -4 addr show $MN_IF_NAME | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
```

node-1（ヘッド）で:

```bash
bash run_cluster.sh $VLLM_IMAGE $VLLM_HOST_IP --head ~/.cache/huggingface \
  -e VLLM_HOST_IP=$VLLM_HOST_IP \
  -e UCX_NET_DEVICES=$MN_IF_NAME \
  -e NCCL_SOCKET_IFNAME=$MN_IF_NAME \
  -e OMPI_MCA_btl_tcp_if_include=$MN_IF_NAME \
  -e GLOO_SOCKET_IFNAME=$MN_IF_NAME \
  -e TP_SOCKET_IFNAME=$MN_IF_NAME \
  -e RAY_memory_monitor_refresh_ms=0 \
  -e MASTER_ADDR=$VLLM_HOST_IP
```

node-2〜4（ワーカー）で:

```bash
export HEAD_NODE_IP=192.168.100.1
bash run_cluster.sh $VLLM_IMAGE $HEAD_NODE_IP --worker ~/.cache/huggingface \
  -e VLLM_HOST_IP=$VLLM_HOST_IP \
  -e UCX_NET_DEVICES=$MN_IF_NAME \
  -e NCCL_SOCKET_IFNAME=$MN_IF_NAME \
  -e OMPI_MCA_btl_tcp_if_include=$MN_IF_NAME \
  -e GLOO_SOCKET_IFNAME=$MN_IF_NAME \
  -e TP_SOCKET_IFNAME=$MN_IF_NAME \
  -e RAY_memory_monitor_refresh_ms=0 \
  -e MASTER_ADDR=$HEAD_NODE_IP
```

各台の `run_cluster.sh` のシェルは開いたままにする（閉じるとクラスタが止まる）。
node-1で4台そろったことを確かめてから、**node-1でだけ** `vllm serve` を実行する。

```bash
export VLLM_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^node-[0-9]+$')
docker exec $VLLM_CONTAINER ray status          # GPUが4つ見えること

docker exec -it $VLLM_CONTAINER /bin/bash -c '
  vllm serve <モデルのHFハンドル> \
    --tensor-parallel-size 4 \
    --distributed-executor-backend ray \
    --gpu-memory-utilization 0.8 \
    --max-model-len 32768 --max-num-seqs 4 \
    --kv-cache-dtype fp8 \
    --api-key "<十分に長いランダム文字列>"'
```

メモリまわりのフラグは7節とそろえてある。`--gpu-memory-utilization` を省くと既定の
0.9が各台に掛かり、OSの分が残らない（[メモリ枯渇の対処](vllm-gb10-memory.md)）。
7節と比べるための代替なので、条件を変えないこと。

Rayのダッシュボード（`http://<ヘッドのIP>:8265`）は認証が無いので、社内LANの外へ
出さないこと。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|`ibdev2netdev` で `Up` が無い|ケーブルの接続、スイッチのポートが無効|挿し直して再起動。スイッチでポートを有効にする|
|速度が `100000Mb/s`|自動ネゴシエーションで200Gbpsにならない|スイッチ側で自動ネゴシエーションを切り、200Gbpsに固定する|
|`Network unreachable`|netplanの未設定、または2つのインターフェースが同じサブネット|3節の設定を見直し、`sudo netplan apply`|
|`mpirun` が止まる・タイムアウトする|SSHがパスワードを聞いている|4節のSSHを張り直す。`mpirun -np 4 -H ...:1,... hostname` で切り分ける|
|NCCLテストで `libnccl.so.2` が無い|NCCLを4台すべてでビルドしていない|5節のビルドを残りの台で行い、`LD_LIBRARY_PATH` を設定する|
|vLLMの起動が待ったまま進まない|4台のうち1台が起動していない、または `--master-addr` が違う|4台すべてのコンテナのログを見る。1台の失敗でヘッドも止まる|
|1台だけOOMで落ちる|その台にOllamaやキャッシュが残っている|その台で7-2節を行う。`--gpu-memory-utilization` を下げる|
|ログに `NET/Socket` と出る・遅い|NCCLがRoCEを使えていない|`NCCL_IB_HCA` と `--privileged` を確認。帯域が出ないならパイプライン並列へ|
|rsyncで写し先のディレクトリが無いと言われる|写し先に `~/.cache/huggingface` が無い|6節のとおり `--mkpath` を付ける|
|モデルが見つからないと言われる|4台のうちどこかにモデルが無い|6節。4台で同じパスにそろえる|

## 出典

- [NVIDIA DGX Spark playbook — Connect Multiple DGX Sparks Through a Switch](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/playbook-multi-sparks-through-switch/README.md)（スイッチの要件、配線、netplan、SSH、ロールバック。2026-08-12 更新）
- [NVIDIA DGX Spark playbook — Set Up NCCL for Multi-Node GPU Communication](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/playbook-nccl/README.md)（4台・スイッチでのNCCLのビルドとテスト。2026-10-14 更新）
- [NVIDIA DGX Spark playbook — Serve LLMs with vLLM Across DGX Sparks](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/playbook-vllm-cluster/README.md)（組み込みのマルチノード実行のコンテナと環境変数。コマンド例は2台分。2026-10-22 更新）
- [NVIDIA DGX Spark playbook — vLLM for Inference](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/vllm/README.md)（スイッチ経由の4台をRayで束ねる旧版の手順とMiniMax-M2.5の例）
- [NVIDIA Sync — Cluster Assistant](https://docs.nvidia.com/sync/latest/cluster-assistant.html)
- [vLLM — Parallelism and Scaling（マルチノード）](https://docs.vllm.ai/en/latest/serving/parallelism_scaling/)（テンソル並列とパイプライン並列の選び方、`--nnodes` / `--headless`、Ray、`NET/IB` の確認）
- [NVIDIA NGC — vLLM コンテナのタグ一覧](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm/tags)
- 本リポジトリ内: [vllm-gb10.md](vllm-gb10.md)（1台での立て方）、
  [vllm-gb10-memory.md](vllm-gb10-memory.md)（メモリ枯渇の対処）、
  [vllm-gb10-models.md](vllm-gb10-models.md)（モデルの選び方）、
  [vllm-gb10-coding-agent.md](vllm-gb10-coding-agent.md)（コーディングエージェント向けのフラグ）
