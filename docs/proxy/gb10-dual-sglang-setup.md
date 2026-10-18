# GB10 ×2 + SGLang + LiteLLM + Claude Code（VS Code）構築手順書

GB10 を2台用意し、推論エンジンに SGLang を使う。1台目で `gpt-oss-120b`、2台目で
`Qwen3-Coder-Next` を動かす。間に LiteLLM を置き、VS Code の Claude Code 拡張の
チャット欄にあるモデル選択プルダウンから2つのモデルを切り替えて、設計とコーディングに使う。

> **関連文書**: 同じ構成を vLLM で組む手順は [gb10-dual-llm-setup.md](gb10-dual-llm-setup.md)
> にある。本書はその SGLang 版で、LiteLLM の設定ファイルは
> [litellm-config-sglang.yaml](litellm-config-sglang.yaml) を使う。

## 1. 構成概要

```
[クライアントPC: VS Code + Claude Code 拡張]
          │  Anthropic Messages API (/v1/messages)
          ▼
[LiteLLM ゲートウェイ :4000]   ← GB10-A 上で稼働（別PCでも可）
     │  モデル名で振り分け（/v1/messages のまま転送）
     ├──────────────────────┐
     ▼                      ▼
[GB10-A :30000]         [GB10-B :30000]
 SGLang                  SGLang
 gpt-oss-120b            qwen3-coder-next
 （設計・レビュー）        （実装・コーディング）
```

| 役割 | ホスト | IP（例） | ポート | served-model-name |
|---|---|---|---|---|
| 設計用LLM | GB10-A | 192.168.10.11 | 30000 | `gpt-oss-120b` |
| コーディング用LLM | GB10-B | 192.168.10.12 | 30000 | `qwen3-coder-next` |
| ゲートウェイ | GB10-A | 192.168.10.11 | 4000 | – |

**ポイント**

- Claude Code の接続先（`ANTHROPIC_BASE_URL`）は1つしか持てない。2台を束ねるために
  LiteLLM を挟み、リクエストの `model` 名で行き先を振り分ける。
- SGLang は Anthropic 互換の `/v1/messages` を最初から備えている（起動オプションは要らない）。
  そのため LiteLLM は `anthropic/` プロバイダで**形式を変換せずに**転送する。OpenAI 形式への
  変換を挟まないので、ツール呼び出しやストリーミングの変換で問題が起きにくい。
- プルダウンには Claude Code の `modelPicker` 設定で2モデルだけを並べる（7章）。

---

## 2. 前提条件

| 項目 | 内容 |
|---|---|
| GB10 ×2 | DGX OS。NVIDIA ドライバ（CUDA 13 対応）、Docker、NVIDIA Container Toolkit が入っていること |
| ネットワーク | 2台とクライアントPCが同一LANにあり、GB10 に固定IPを割り当て済み |
| モデル取得 | 初回だけ huggingface.co からダウンロードする。必要なら `HF_TOKEN` を用意する |
| クライアントPC | VS Code と Claude Code 拡張。`modelPicker` を使うため **Claude Code v2.1.242 以降** |

### SGLang のバージョンとイメージ

- Qwen3-Coder-Next には **SGLang v0.5.8 以降**が必要である（SGLang Cookbook）。
- 現行の SGLang イメージは CUDA 13 環境で作られている。GB10（DGX Spark）でも
  `lmsysorg/sglang:latest` が使われている。モデルによっては専用タグが必要になるので、
  動かないときは SGLang Cookbook のモデルページで「DGX Spark」を選び、表示されたイメージを使う。
- 再現性を保つため、動作を確かめたら `latest` ではなく日付やバージョン付きのタグに固定する。

---

## 3. GB10 共通の準備（A・B 両方）

### 3.1 イメージ取得とキャッシュ用フォルダ

```bash
docker pull lmsysorg/sglang:latest
mkdir -p ~/hf-cache
```

### 3.2 メモリについての注意

GB10 の 128GB は CPU と GPU が共有するユニファイドメモリである。GPU 側が使い切ると
OS ごと固まり、電源を入れ直すまで戻らないことがある（SGLang Cookbook の DGX Spark 注記）。

- `--mem-fraction-static` は 0.80〜0.85 を上限とし、OS 用の余白を残す。
- 長いコンテキストを扱うときは `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` を付ける
  （下のコマンドには入れてある）。
- 余裕があれば、空きメモリ（`MemAvailable`）が数GBを切ったらコンテナを止める監視スクリプトを置く。

---

## 4. GB10-A：gpt-oss-120b の起動

gpt-oss-120b は MXFP4 量子化済みで重みは約65GB なので、GB10 1台に収まる。LiteLLM も
同じ機械で動かすため、`--mem-fraction-static` は少し低めにする。

```bash
docker run -d --name sglang-gptoss --restart unless-stopped \
  --gpus all --ipc=host --shm-size 32g \
  -p 30000:30000 \
  -v ~/hf-cache:/root/.cache/huggingface \
  -e HF_TOKEN \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  lmsysorg/sglang:latest \
  sglang serve \
    --model-path openai/gpt-oss-120b \
    --served-model-name gpt-oss-120b \
    --host 0.0.0.0 --port 30000 \
    --tool-call-parser gpt-oss \
    --reasoning-parser gpt-oss \
    --context-length 131072 \
    --mem-fraction-static 0.80
```

ログは `docker logs -f sglang-gptoss` で確認する。`The server is fired up and ready to roll!`
が出たら起動完了である。

**注意**

- `--served-model-name` は**スラッシュを含めない**。LiteLLM の `model_name` と Claude Code の
  設定でこの名前をそのまま使う。
- `--tool-call-parser` を付けないと、ツール呼び出しが構造化された `tool_use` にならず文字列で
  返る。そうなると Claude Code はファイル編集やコマンド実行ができない。
- gpt-oss のコンテキスト長は最大 131072 である。

---

## 5. GB10-B：Qwen3-Coder-Next の起動

Qwen3-Coder-Next は総パラメータ 80B の MoE（1トークンあたり 3B のみ動く）である。BF16 だと
約160GB で 128GB に載らないので、**FP8 版**（`Qwen/Qwen3-Coder-Next-FP8`、約80GB）を使う。

```bash
docker run -d --name sglang-qwen --restart unless-stopped \
  --gpus all --ipc=host --shm-size 32g \
  -p 30000:30000 \
  -v ~/hf-cache:/root/.cache/huggingface \
  -e HF_TOKEN \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  lmsysorg/sglang:latest \
  sglang serve \
    --model-path Qwen/Qwen3-Coder-Next-FP8 \
    --served-model-name qwen3-coder-next \
    --host 0.0.0.0 --port 30000 \
    --tool-call-parser qwen3_coder \
    --context-length 131072 \
    --mem-fraction-static 0.85
```

**注意**

- 公式コマンド例にある `--tp 2` は**付けない**。各モデルを1台ずつで動かす構成のためである。
- モデル自体は 256K まで扱えるが、Claude Code 側の自動圧縮をモデル間で揃えるため（7.3節）、
  ここでは 131072 に抑えている。
- メモリ不足で起動しないときは `--context-length 65536` に下げる。
- このモデルは Gated DeltaNet を含むハイブリッド構造で、同時に処理できるリクエスト数が
  mamba state 用の領域で決まる。実際の上限は起動ログで確認する。

---

## 6. 動作確認とアクセス制限

### 6.1 各 SGLang を直接確認する

GB10-A またはクライアントPCから実行する。SGLang は `model` の値を検証しないので、
疎通確認では返答が来るかだけを見る。

```bash
for h in 192.168.10.11 192.168.10.12; do
  curl -s http://$h:30000/v1/models; echo
  curl -s http://$h:30000/v1/messages \
    -H "content-type: application/json" \
    -H "anthropic-version: 2023-06-01" \
    -d '{"model":"test","max_tokens":64,"messages":[{"role":"user","content":"hello"}]}'
  echo; echo ----
done
```

### 6.2 ファイアウォール

本書では SGLang を `--api-key` なしで起動する。SGLang の `--api-key` は
`Authorization: Bearer` ヘッダーしか見ず、LiteLLM の `anthropic/` プロバイダは `x-api-key`
ヘッダーで鍵を送るため、組み合わせると 401 になる。そこで SGLang のポートは
**LiteLLM のホストからだけ**届くように絞る。

LiteLLM は Docker を使わずに動かす（7章）ので、4000 番は ufw で制限できる。

```bash
# GB10-A：4000 番（LiteLLM）はクライアントのLANにだけ開ける
sudo ufw allow OpenSSH
sudo ufw allow from 192.168.10.0/24 to any port 4000 proto tcp
sudo ufw enable
```

> **Docker の `-p` で公開したポートには ufw が効かない。** Docker が iptables を直接書き換える
> ので、ufw の規則を通らない。送信元を絞るには `DOCKER-USER` チェーンに規則を足す。
>
> ```bash
> # GB10-A・B の両方で実行：30000 番は GB10-A（LiteLLM）以外からの接続を捨てる
> sudo iptables -I DOCKER-USER -p tcp --dport 30000 ! -s 192.168.10.11 -j DROP
> sudo apt install -y iptables-persistent && sudo netfilter-persistent save   # 再起動後も残す
> ```
>
> 規則を入れたら、クライアントPCから 6.1 の curl を叩き、30000 番に届かないことを必ず確かめる。

---

## 7. LiteLLM ゲートウェイの構築（GB10-A）

### 7.1 インストール

```bash
python3 -m venv ~/litellm-venv
source ~/litellm-venv/bin/activate
pip install 'litellm[proxy]'
```

### 7.2 設定ファイル

同じフォルダの [litellm-config-sglang.yaml](litellm-config-sglang.yaml) を
`~/litellm/litellm-config-sglang.yaml` に置き、`api_base` の IP と `master_key` を環境に
合わせて書き換える。要点は次のとおり。

| 項目 | 値 | 理由 |
|---|---|---|
| `model_name` | `gpt-oss-120b` / `qwen3-coder-next` | Claude Code が送る `model` 名。ここで行き先が決まる |
| `litellm_params.model` | `anthropic/<served-model-name>` | SGLang の `/v1/messages` へ形式を変えずに渡す |
| `api_base` | `http://<IP>:30000` | LiteLLM が末尾に `/v1/messages` を付ける。**`/v1` は付けない** |
| `master_key` | 任意の文字列 | Claude Code の `ANTHROPIC_AUTH_TOKEN` と同じ値にする |

### 7.3 起動

```bash
litellm --config ~/litellm/litellm-config-sglang.yaml --host 0.0.0.0 --port 4000
# うまくいかないときは --detailed_debug を付けて要求と応答を確かめる
```

常駐させる場合は systemd に登録する。

```ini
# /etc/systemd/system/litellm.service
[Unit]
Description=LiteLLM gateway
After=network-online.target docker.service

[Service]
User=<ユーザー名>
ExecStart=/home/<ユーザー名>/litellm-venv/bin/litellm --config /home/<ユーザー名>/litellm/litellm-config-sglang.yaml --host 0.0.0.0 --port 4000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now litellm
journalctl -u litellm -f
```

### 7.4 LiteLLM 経由の動作確認

```bash
for m in gpt-oss-120b qwen3-coder-next; do
  curl -s http://192.168.10.11:4000/v1/messages \
    -H "Authorization: Bearer sk-local-change-me" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "{\"model\":\"$m\",\"max_tokens\":64,\"messages\":[{\"role\":\"user\",\"content\":\"hello\"}]}"
  echo
done
```

両方のモデルから `"content":[...]` を含む応答が返れば成功である。そのとき
`docker logs -f sglang-gptoss`（GB10-A）と `docker logs -f sglang-qwen`（GB10-B）を見て、
それぞれの機械にリクエストが届いていることも確かめる。

---

## 8. クライアント：VS Code の Claude Code 設定

設定は2か所に分けて書く。

| 置き場所 | 書く内容 | 理由 |
|---|---|---|
| VS Code のユーザー設定（`settings.json`） | 接続先と認証トークン | 拡張機能は起動前のログイン確認でこの設定を読む。`~/.claude/settings.json` の値は起動後のプロセスには届くが、ログイン確認には使われない |
| `~/.claude/settings.json`（Windows は `%USERPROFILE%\.claude\settings.json`） | モデルの割り当て、プルダウンの並び、各種の調整 | `modelPicker` はユーザー設定か管理者設定でしか効かない（プロジェクトの設定では無視される） |

### 8.1 VS Code のユーザー設定

コマンドパレットで **Preferences: Open User Settings (JSON)** を開き、次を追記する。

```json
{
  "claudeCode.environmentVariables": [
    { "name": "ANTHROPIC_BASE_URL",   "value": "http://192.168.10.11:4000" },
    { "name": "ANTHROPIC_AUTH_TOKEN", "value": "sk-local-change-me" }
  ]
}
```

`ANTHROPIC_AUTH_TOKEN` は `Authorization: Bearer` ヘッダーで送られ、LiteLLM の
`master_key` はこのヘッダーで照合される。

### 8.2 `~/.claude/settings.json`

```json
{
  "model": "qwen3-coder-next",
  "modelPicker": {
    "replaceBuiltInOptions": true,
    "options": [
      {
        "model": "gpt-oss-120b",
        "label": "gpt-oss-120b（設計・レビュー）",
        "description": "GB10-A / SGLang"
      },
      {
        "model": "qwen3-coder-next",
        "label": "Qwen3-Coder-Next（実装）",
        "description": "GB10-B / SGLang"
      },
      {
        "model": "opusplan",
        "label": "設計→実装 自動切替",
        "description": "プランモードは gpt-oss-120b、実行は Qwen3-Coder-Next"
      }
    ]
  },
  "env": {
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3-coder-next",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3-coder-next",

    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "120000",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "16384",
    "API_TIMEOUT_MS": "600000",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

| 設定 | 意味 |
|---|---|
| `"model"` | 新しいセッションを始めるときのモデル。普段使いの Qwen にしておく |
| `modelPicker.options` | プルダウンに出す行。`model` は LiteLLM の `model_name` と完全に一致させる |
| `modelPicker.replaceBuiltInOptions: true` | Claude の既定モデル行を隠し、上の行（と **Default**、使用中のモデルの行）だけにする |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `opus` の割り当て先。`opusplan` のプランモードでもこれが使われる |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `sonnet` の割り当て先。`opusplan` の実行時と **Default** でこれが使われる |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | タイトル生成などの裏方処理と Explore サブエージェント用。指定しないと存在しない Claude のモデル名を送って失敗する |
| `CLAUDE_CODE_ATTRIBUTION_HEADER=0` | システムプロンプト先頭に毎回変わる識別行が入るのを止める。これがないと SGLang のプレフィックスキャッシュが効かず、毎ターン会話履歴をすべて計算し直す（SGLang 公式が必須としている） |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | 自動圧縮を始める基準のウィンドウ。Claude Code は知らないモデルを 200K と見なすため、131072 の上限を超える前に圧縮させる（下限は 100000 に丸められる） |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | 1回の出力上限。入力と合わせて `--context-length` に収まるようにする |
| `API_TIMEOUT_MS` | ローカル推論は遅いので待ち時間を延ばす（LiteLLM の `timeout: 600` と揃える） |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Anthropic 固有の試験的なフィールドを送らない。400 エラーを防ぐ |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | テレメトリや自動更新など、ゲートウェイ以外への通信を止める。自動更新も止まるので、拡張機能の更新は手動で行う |

> Superpowers プラグインや Context7 MCP の設定がすでにある場合は、ファイルを上書きせず
> `env` などのキーにマージすること。認証トークンをプロジェクトの `.claude/settings.json` に
> 書いてはいけない（リポジトリにコミットされる）。

### 8.3 反映

VS Code を再起動し、Claude Code のパネルを開く。ログイン画面が出ずにチャット欄が開けば、
8.1 の設定が読まれている。`/status` を送り、`Anthropic base URL` が
`http://192.168.10.11:4000`、認証が `ANTHROPIC_AUTH_TOKEN` になっていることを確かめる。

---

## 9. 使い方：プルダウンでのモデル切替

チャット入力欄にあるモデル名のプルダウン（または `/model`）を開くと、8.2 で並べた行が出る。

| 選ぶ行 | 使われるモデル | 向いている作業 |
|---|---|---|
| gpt-oss-120b（設計・レビュー） | GB10-A の gpt-oss-120b | 要件整理、設計、方式比較、コードレビュー |
| Qwen3-Coder-Next（実装） | GB10-B の Qwen3-Coder-Next | 実装、リファクタリング、テスト作成、デバッグ |
| 設計→実装 自動切替（`opusplan`） | プランモードは gpt-oss、実行は Qwen | 設計から実装まで一続きで頼むとき |

**自動切替の流れ**

1. プルダウンで「設計→実装 自動切替」を選ぶ。
2. Shift+Tab でプランモードにして設計を頼む。このとき gpt-oss-120b が計画を立てる。
3. 計画を承認すると実行に移り、Qwen3-Coder-Next が実装する。

会話の途中でモデルを切り替えても履歴はそのまま引き継がれる。ただし相手のサーバーが変わると
プレフィックスキャッシュが使えないので、切り替えた直後の1回目は応答が遅い。

---

## 10. 動作確認チェックリスト

- [ ] 6.1 の curl で、両方の SGLang が `/v1/messages` に応答する
- [ ] 6.2 のとおり、LiteLLM 以外のホストから 30000 番に届かない
- [ ] 7.4 の curl で、LiteLLM 経由で両方のモデルが応答する
- [ ] VS Code の Claude Code がログイン画面を出さずに開き、`/status` にゲートウェイの URL が出る
- [ ] プルダウンに3行（と Default）だけが出る
- [ ] gpt-oss-120b を選ぶと GB10-A の `docker logs` にリクエストが来る
- [ ] Qwen3-Coder-Next を選ぶと GB10-B の `docker logs` にリクエストが来る
- [ ] ファイルの読み書きやコマンド実行などのツール呼び出しが、両方のモデルで成功する
- [ ] 2ターン目以降の応答が1ターン目より速い（プレフィックスキャッシュが効いている）

---

## 11. トラブルシューティング

| 症状 | 確認ポイント |
|---|---|
| VS Code でログイン画面が出る | `claudeCode.environmentVariables` に `ANTHROPIC_AUTH_TOKEN` があるか（8.1）。`~/.claude/settings.json` に書いただけでは足りない |
| 401 | `ANTHROPIC_AUTH_TOKEN` と LiteLLM の `master_key` が一致しているか。SGLang に `--api-key` を付けていないか（6.2） |
| 404 / 接続できない | LiteLLM の `api_base` に `/v1` を付けていないか（`/v1/v1/messages` になる）。ポートが 30000 か。ファイアウォールで LiteLLM 自身を塞いでいないか |
| `model not found`（LiteLLM） | プルダウンの `model`、`ANTHROPIC_DEFAULT_*_MODEL`、LiteLLM の `model_name` が完全に一致しているか |
| プルダウンに Claude のモデルが残る / 行が出ない | Claude Code が v2.1.242 以降か。`modelPicker` を `~/.claude/settings.json`（ユーザー設定）に書いたか（プロジェクト設定では無視される）。JSON の書き間違いがあるとその行は捨てられる |
| ツールが呼ばれず文章だけが返る | SGLang の `--tool-call-parser` を確認する（gpt-oss は `gpt-oss`、Qwen は `qwen3_coder`） |
| 毎ターン遅い | `CLAUDE_CODE_ATTRIBUTION_HEADER=0` が効いているか |
| 400（`context_management` や `Extra inputs are not permitted`） | `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` が入っているか |
| 長い会話の途中でコンテキスト超過 | `/compact` で圧縮して続ける。`CLAUDE_CODE_AUTO_COMPACT_WINDOW` と `CLAUDE_CODE_MAX_OUTPUT_TOKENS` の合計が `--context-length` を超えていないか |
| 応答が途中で切れる / タイムアウト | `API_TIMEOUT_MS` と LiteLLM の `timeout` を延ばす |
| SGLang が起動しない（OOM） | `--context-length` と `--mem-fraction-static` を下げる。Qwen は FP8 版を使っているか |
| GB10 ごと固まった | ユニファイドメモリを使い切った可能性がある。電源を入れ直し、`--mem-fraction-static` を下げてから起動し直す（3.2） |
| GB10 で SGLang のカーネルエラー | SGLang Cookbook のモデルページで DGX Spark 向けのイメージを確かめる。gpt-oss で起きる場合は `--attention-backend triton` を試す |
| 原因がわからない | `litellm ... --detailed_debug` で LiteLLM の要求と応答を見る。Claude Code は `claude --debug` のログ（`~/.claude/debug/`）を見る |

---

## 12. 外部への通信について

- モデルの重みは初回起動時に huggingface.co から取得する。2回目以降は `~/hf-cache` を使う。
  オフラインで運用する場合は、事前に取得したキャッシュを置いてから起動する。
- 質問文・コード・会話履歴は、クライアント → LiteLLM（GB10-A）→ SGLang（GB10-A / B）と
  LAN の中だけを流れる。
- Claude Code は `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` でテレメトリや自動更新を止めて
  いる。WebFetch ツールのドメイン確認は api.anthropic.com へ出ていくので、完全に閉じたい
  場合は `skipWebFetchPreflight: true` も設定する。

---

## 参考

- SGLang: Anthropic-Compatible API（Claude Code との接続）— `docs/basic_usage/anthropic_api.mdx`（sgl-project/sglang）
- SGLang Cookbook: Qwen3-Coder-Next / gpt-oss — https://docs.sglang.ai/
- SGLang インストール（Docker）— https://docs.sglang.ai/docs/get-started/install
- Claude Code: Connect Claude Code to an LLM gateway — https://code.claude.com/docs/en/llm-gateway-connect
- Claude Code: Model configuration — https://code.claude.com/docs/en/model-config
- Claude Code: settings reference（`modelPicker`）— https://code.claude.com/docs/en/settings-reference
- LiteLLM — https://github.com/BerriAI/litellm
