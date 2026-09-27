# GB10のOllamaを Qwen3-Coder-Next（q8_0）に置き換える

GB10（DGX Spark）の Ollama で Codex に使わせるモデルを、`gpt-oss:120b` から
**`qwen3-coder-next:q8_0`** に置き換える手順。推論サーバーは Ollama のまま替えない。

```text
Windows（VS Code + Codex拡張 + config.toml / models.json）
        │ HTTP（社内LAN）/ Responses API
        ▼
GB10 → Ollama :11434 → qwen3-coder-next:q8_0-256k（常駐）
```

**前提:** [GB10のOllamaでコーディングエージェントを動かす](../gb10-coding-agent.md)の
手順で、`gpt-oss:120b-131k` を Codex から使えていること。この文書はその差分だけを書く。

**`gpt-oss:120b` は、Codex から Qwen を使えると確かめるまで消さない。** 消すのは最後の
[9節](#9-gpt-oss120b-を消す任意)で、任意である。それまでは Windows 側の設定を戻す
だけで元に戻れる。

> **未検証である。** Ollama / Codex の仕様とソースを確かめて組んだが、GB10 の実機で
> 通した記録はまだ無い。各段階の「成功の目安」で確かめながら進めること。特に
> [3節](#3-gb10-思考の指定で弾かれないことを確かめる)は、この構成が成り立つかどうかの関門である。

## 目次

- [0. 何を変えるか](#0-何を変えるか)
- [1. GB10: モデルを取得する](#1-gb10-モデルを取得する)
- [2. GB10: 文脈長を伸ばした別名を作る](#2-gb10-文脈長を伸ばした別名を作る)
- [3. GB10: 思考の指定で弾かれないことを確かめる](#3-gb10-思考の指定で弾かれないことを確かめる)
- [4. GB10: 実配置と道具呼び出しを確かめる](#4-gb10-実配置と道具呼び出しを確かめる)
- [5. GB10: 常駐させ、2つ目を載せない](#5-gb10-常駐させ2つ目を載せない)
- [6. Windows: models.json を置き換える](#6-windows-modelsjson-を置き換える)
- [7. Windows: config.toml を書き換える](#7-windows-configtoml-を書き換える)
- [8. 起動して確かめる](#8-起動して確かめる)
- [9. gpt-oss:120b を消す（任意）](#9-gpt-oss120b-を消す任意)
- [元に戻す](#元に戻す)
- [つまずきやすいところ](#つまずきやすいところ)
- [出典](#出典)

## 0. 何を変えるか

|場所|変更|理由|
|---|---|---|
|GB10 Ollama|`qwen3-coder-next:q8_0` を取得し、文脈長 262144 の別名を作る|Ollama の既定の文脈長は短い。gpt-oss と同じく別名に焼く|
|GB10 Ollama|`OLLAMA_MAX_LOADED_MODELS=1` と `OLLAMA_KEEP_ALIVE=-1`|1モデルだけを載せ続ける|
|Windows `models.json`|Qwen の1モデル分に置き換える|文脈長・圧縮位置・思考の強さをここで持つ|
|Windows `config.toml`|`model` を替え、`model_context_window` / `model_auto_compact_token_limit` / `model_reasoning_effort` を消す|とくに思考の強さは残すと Qwen への要求が全部失敗する（下記）|

### なぜ q8_0 か

GB10 のメモリ（128GB）では、gpt-oss:120b と Qwen を同時には載せられない。1モデル
しか載らないなら、その1つに枠を使い切れる8bit版を選ぶ。

|項目|q4_K_M|**q8_0（この手順）**|
|---|---|---|
|重み|52GB|85GB|
|256K の KV + 計算用バッファ|約10GB（見積もり）|同じ|
|合計の見込み|約60GB|**約95GB**（残り約30GB）|
|精度|4bit量子化の劣化がある|ほぼ劣化しない|
|生成速度|速い|**q4 の6割前後の見込み**|

生成速度は、1トークンごとに読む重みの量でほぼ決まる（GB10 のメモリ帯域は 273GB/s）。
このモデルが1トークンに使うのは約3B分だが、8bit ではその読み出しが4bit の約1.7倍に
なる。**遅すぎると感じたら q4_K_M に下げる**（手順はタグ名を替えるだけ）。

### 思考の強さは none で送る

Qwen3-Coder-Next は思考しないモデルである。Ollama は思考しないモデルに思考を指定
されると `400 "…" does not support thinking` を返す。Codex は要求に必ず思考の強さを
付けるので、今の `config.toml` の `model_reasoning_effort = "medium"` を残したまま
`model` だけ替えると、**すべての要求がこれで失敗する。**

`none` だけは「思考しない」という指定になり、通る。そこで `config.toml` からこの行を
消し、`models.json` の `default_reasoning_level` に `none` を持たせる（Codex は
`config.toml` に無ければ `models.json` の値を送る）。

## 1. GB10: モデルを取得する

```bash
df -h /usr/share/ollama ~/.ollama 2>/dev/null   # 85GB 以上の空き（gpt-oss の 65GB はまだ残る）
ollama pull qwen3-coder-next:q8_0                # 約85GB
ollama list                                      # gpt-oss:120b / gpt-oss:120b-131k も残っていること
```

`requires a newer version of Ollama` と出たら Ollama を更新する。Qwen3-Coder-Next は
Qwen3-Next の構造（Gated DeltaNet と注意機構の混成）を持ち、古い Ollama は読めない。

```bash
ollama show qwen3-coder-next:q8_0
```

**成功の目安:**

- Capabilities に **`tools` があり、`thinking` が無い**
- Parameters に `temperature 1` / `top_k 40` / `top_p 0.95`（Qwen の推奨値）

Codex はサンプリングの値を要求に含めないので、ここに入っている値がそのまま効く。
自分で `PARAMETER temperature` などを足す必要は無い。

## 2. GB10: 文脈長を伸ばした別名を作る

**元のモデルは書き換えず、別名で作る。**

```bash
cat <<'EOF' > /tmp/Modelfile.qwen3-coder-next
FROM qwen3-coder-next:q8_0
PARAMETER num_ctx 262144
EOF
ollama create qwen3-coder-next:q8_0-256k -f /tmp/Modelfile.qwen3-coder-next
ollama show qwen3-coder-next:q8_0-256k --parameters   # num_ctx 262144 と temperature 1 など
```

`FROM` で作った別名は、元のテンプレートとパラメータを引き継ぐ。足したのは `num_ctx` だけである。

262144 はこのモデルが素で持つ長さである。KVキャッシュを持つのは48層のうち注意機構の
12層だけなので、256K でも約6GiB の見積もりで済む。**見積もりなので4節で測る。**

## 3. GB10: 思考の指定で弾かれないことを確かめる

**この構成の関門である。** 「`none` は通り、`medium` は弾かれる」ことを確かめる。

```bash
ollama stop gpt-oss:120b-131k 2>/dev/null   # 載っていれば降ろす（同時には載らない）
for effort in none medium; do
  echo "--- effort=${effort}"
  curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:11434/v1/responses \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"qwen3-coder-next:q8_0-256k\",\"input\":\"Reply with OK.\",\"reasoning\":{\"effort\":\"${effort}\"},\"stream\":false}" \
    | tail -c 400
done
```

1回目はモデルの読み込み（85GB）を待つので時間がかかる。

**成功の目安:**

|effort|期待|
|---|---|
|`none`|HTTP 200、本文に `OK`|
|`medium`|HTTP 400、`does not support thinking`|

`medium` が 400 になるのは想定どおりで、`models.json` で `none` を持たせる理由の確認で
ある。**`none` まで 400 になる場合はこの構成は成り立たない。** 先へ進まず、Ollama の版と
エラー文を控えて相談すること。

## 4. GB10: 実配置と道具呼び出しを確かめる

### 全部GPUに載ったか

```bash
curl -s http://127.0.0.1:11434/api/ps | python3 -c "
import json, sys
for m in json.load(sys.stdin)['models']:
    print(m['name'])
    print('  context_length:', m['context_length'])
    print('  size (GiB)    :', round(m['size'] / 2**30, 1))
    print('  fully_on_gpu  :', m['size'] == m['size_vram'])
"
free -g
```

**成功の目安:** 載っているのが `qwen3-coder-next:q8_0-256k` だけで、`context_length: 262144`、
`fully_on_gpu: True`。`size` は 90GiB 前後の見込みである。

`False` なら一部がCPUに落ちている。まず gpt-oss が載ったままでないかを見る。それでも
落ちるなら、2節の `num_ctx` を 131072 にして作り直し、[`models.json`](models.json) の
`context_window` / `max_context_window` を 131072、`auto_compact_token_limit` を 98304 に
揃える。**GB10 と `models.json` の2か所を必ず一緒に変える。**

### 道具を呼んで、結果を返せるか

Codex が送るのと同じ `reasoning: none` を付けて、道具の往復まで確かめる。

```bash
python3 - <<'PY'
import json, urllib.request

URL = "http://127.0.0.1:11434/v1/responses"
MODEL = "qwen3-coder-next:q8_0-256k"
TOOL = {"type": "function", "name": "get_probe_value",
        "description": "Returns the fixed connection probe value.",
        "parameters": {"type": "object", "properties": {}, "required": []}}
PROMPT = "Call get_probe_value exactly once, then tell me the value it returned."

def post(body):
    body |= {"model": MODEL, "tools": [TOOL], "reasoning": {"effort": "none"}, "stream": False}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as res:
        return json.load(res)

first = post({"input": PROMPT})
calls = [o for o in first["output"] if o.get("type") == "function_call"]
print("function_call:", bool(calls))
if calls:
    call = {k: calls[0][k] for k in ("type", "call_id", "name", "arguments")}
    second = post({"input": [{"role": "user", "content": PROMPT}, call,
                             {"type": "function_call_output", "call_id": call["call_id"], "output": "73190462"}]})
    print("used result  :", "73190462" in json.dumps(second["output"]))
PY
```

**成功の目安:** `function_call: True` と `used result  : True`。前者は道具を呼べること、
後者は道具の結果を受け取って続きを話せることで、エージェントの1往復そのものである。

## 5. GB10: 常駐させ、2つ目を載せない

```bash
sudo systemctl edit ollama
```

既にある `OLLAMA_HOST` の行（[Ollama版の4節](../gb10-coding-agent.md#4-gb10側-lanへ公開する)）
の下に2行足す。

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=-1"
```

```bash
sudo systemctl restart ollama
systemctl show ollama -p Environment   # 3つとも並ぶこと
```

|設定|理由|
|---|---|
|`OLLAMA_MAX_LOADED_MODELS=1`|gpt-oss:120b はディスクに残っている。誰かがそれを呼んだとき、Qwen と並べて載せようとすると 128GB を超える。1つに限れば、Qwen を降ろしてから読み込む|
|`OLLAMA_KEEP_ALIVE=-1`|既定では5分使わないとモデルを降ろし、次の要求で 85GB を読み直す。専用機なので載せたままにする|

再起動するとモデルは降りているので、1回載せておく。

```bash
ollama run qwen3-coder-next:q8_0-256k "hi" > /dev/null
ollama ps     # UNTIL が Forever であること
```

GB10 を再起動したときも同じく最初の1回だけ読み込みを待つ。

## 6. Windows: models.json を置き換える

`config.toml` の `model_catalog_json` が指しているファイルを
**`models.json.bak` として残してから**、[`docs/qwen/models.json`](models.json) で置き換える。
置かずに済ませる場合は、この節を飛ばして[7節の「models.json を置かない場合」](#modelsjson-を置かない場合)へ進む。

gpt-oss 用の雛形から変えた点:

|キー|値|
|---|---|
|`slug`|`qwen3-coder-next:q8_0-256k`（**2節で作った名前と一致**）|
|`context_window` / `max_context_window`|262144 / 262144|
|`auto_compact_token_limit`|196608（文脈の3/4。**新設**。今まで `config.toml` に書いていた値）|
|`default_reasoning_level`|`none`|
|`supported_reasoning_levels`|`none` だけ（画面で他を選べないようにする）|
|`default_reasoning_summary`|`none`|
|`comp_hash`|`local-qwen3-coder-next-q8-256k`（他と重複しない値）|

## 7. Windows: config.toml を書き換える

**書き換える前に `config.toml.bak` として複製しておく。**

|操作|行|理由|
|---|---|---|
|変える|`model = "qwen3-coder-next:q8_0-256k"`|2節の名前、`models.json` の `slug` と一致|
|**消す**|`model_reasoning_effort = "medium"`|[0節](#思考の強さは-none-で送る)。残すと全要求が 400|
|消す|`model_context_window = 131072`|`models.json` の 262144 が使われる|
|消す|`model_auto_compact_token_limit = 98304`|`models.json` の 196608 が使われる|
|変える|`stream_idle_timeout_ms = 300000`|120000 から上げる。GB10 の再起動後の読み込みや、長い文脈の最初の処理で切られないように|

変更後の全体（値は自分の環境に合わせる）:

```toml
model = "qwen3-coder-next:q8_0-256k"
model_provider = "gb10-oss"
model_catalog_json = 'C:\Users\you\.codex\models.json'
sandbox_mode = "workspace-write"
approval_policy = "on-request"
web_search = "disabled"
developer_instructions = """
（今までどおり）
"""

[model_providers.gb10-oss]
name = "GB10 Ollama"
base_url = "http://192.168.1.50:11434/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 1
stream_max_retries = 0
stream_idle_timeout_ms = 300000

[windows]
sandbox = "unelevated"

[analytics]
enabled = false
```

`wire_api` は `"responses"` のままにする。**今の Codex は `"chat"` を受け付けず、
設定を読んだ時点でエラーになる。**

### models.json を置かない場合

`models.json` は必須ではない。一覧に無いモデル名に対して、Codex は既定値
（`model_info_from_slug`）で動く。その場合は6節を飛ばし、`config.toml` を次のように書く。

```toml
model = "qwen3-coder-next:q8_0-256k"
model_provider = "gb10-oss"
model_context_window = 262144
model_auto_compact_token_limit = 196608
model_reasoning_summary = "none"
sandbox_mode = "workspace-write"
approval_policy = "on-request"
web_search = "disabled"
developer_instructions = """
（今までどおり）
"""

[model_providers.gb10-oss]
name = "GB10 Ollama"
base_url = "http://192.168.1.50:11434/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 1
stream_max_retries = 0
stream_idle_timeout_ms = 300000

[windows]
sandbox = "unelevated"

[analytics]
enabled = false
```

上の版との違い:

|行|理由|
|---|---|
|`model_catalog_json` を**書かない**|指す先のファイルが無いと、起動時に失敗しうる|
|`model_context_window` / `model_auto_compact_token_limit` を**書く**|`models.json` が持っていた値をここで持つ。書かなければ既定値（文脈 272000 の95%、圧縮はその9割）になる|
|`model_reasoning_summary = "none"` を**書く**|既定値では思考の要約に `auto` を要求する。思考しないモデルなので求めない|
|`model_reasoning_effort` は**書かない**|既定値では思考の強さを送らないので、Qwen が 400 を返すことは無い。書くと上の版と同じく全要求が 400 になる|

**この3行は、必ず最初の `[...]` 見出しより前に書く。** TOML では見出しの後の行はその
見出しに属するので、`[model_providers.gb10-oss]` の下に書くとプロバイダーの設定として
読まれ、全体の設定としては効かない。

置いた場合と比べて失うものは2つある。

- **モデル選択の画面に出ない。** `config.toml` の `model` で使われるだけである
- **スキルの使い方の指示がモデルに渡らない。** 既定値では `include_skills_usage_instructions`
  が `false` になる。Superpowers を使うなら `models.json` を置くほうがよい
  （[8節](#superpowers-について)）

起動ログに `Unknown model … fallback model metadata` と警告が出るが、既定値で動いている
という意味で、エラーではない。

## 8. 起動して確かめる

VS Code を**すべてのウィンドウごと閉じてから**起動し直し、Codex のモデル一覧で
`qwen3-coder-next:q8_0-256k (GB10)` が選ばれていることを見る。

```
このリポジトリの README.md が何を説明しているか、ファイルを読んで答えて
```

- **応答が返ること**
- **ファイルを実際に読みに行くこと** — 読まずに一般論を答えるなら、道具呼び出しが効いていない
- **小さな修正を1つ頼み、編集してテストを走らせるところまで行くこと**

### Superpowers について

モデルを替えても、スキルの**配置**の問題は解決しない。`developer_instructions` は
`.agents/skills/<名前>/SKILL.md` を読むよう指示しているが、Codex のプラグイン機能で
入れた場合、そのパスにはスキルが無い。Codex に「使えるスキルを名前とファイルの
場所つきで列挙して」と聞き、見えているかを先に確かめる
（[Ollama版の「Superpowersスキルをどうするか」](../gb10-coding-agent.md#superpowersスキルをどうするか)）。

### gpt-oss と比べる

置き換えて良くなったかは測って決める。測り方は[Ollama版の8節](../gb10-coding-agent.md#8-効果を測る)と
同じにする（実作業から課題を10件固定、各3回、数えるのは「道具を呼んだか」「テストが
通ったか」の2つ）。gpt-oss 側を測るときは、[元に戻す](#元に戻す)の手順で一時的に戻す。
**9節の前に済ませること。** 消した後では比べられない。

## 9. gpt-oss:120b を消す（任意）

8節までで、Codex から Qwen を使えること、使い続けると決めたことを確かめてから行う。

```bash
ollama rm gpt-oss:120b-131k gpt-oss:120b    # 約65GB 空く
ollama list                                 # qwen3-coder-next の2つだけ残ること
```

Windows 側の `config.toml.bak` / `models.json.bak` も要らなくなる。**消した後で gpt-oss に
戻すには、`ollama pull gpt-oss:120b` で約65GBを取り直し、[Ollama版の2節](../gb10-coding-agent.md#2-gb10側-コンテキスト長を伸ばす)
で別名を作り直すことになる。**

## 元に戻す

9節の前なら、GB10 のモデルは両方そろっている。

Windows 側で `config.toml.bak` と `models.json.bak` を元の名前に戻し、VS Code を
起動し直す。GB10 側は、最初の要求が来たとき Ollama が Qwen を降ろして gpt-oss を
読み込む（`OLLAMA_MAX_LOADED_MODELS=1` のため）。

Qwen をやめると決めたら、GB10 側も片づける。

```bash
ollama rm qwen3-coder-next:q8_0-256k qwen3-coder-next:q8_0   # 約85GB 空く
```

`OLLAMA_KEEP_ALIVE=-1` は gpt-oss にも効くので、そのままでよい（載せたままになる）。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|`400 … does not support thinking`|思考の強さが `none` 以外で送られた|`config.toml` に `model_reasoning_effort` が残っていないか。画面で強さを選んでいないか。新しいスレッドで始める|
|文脈が 131072 までしか使えない|`config.toml` に `model_context_window` が残っている|[7節](#7-windows-configtoml-を書き換える)の3行を消す|
|1回目の要求がタイムアウト|85GB の読み込み待ち|[5節](#5-gb10-常駐させ2つ目を載せない)の最後で先に載せておく。`stream_idle_timeout_ms` を上げる|
|生成が遅い|8bit は4bit より読み出しが多い|許容できなければ q4_K_M に下げる。1・2節のタグと `models.json` の `slug` を `q4_K_M` に替える|
|Codex がモデルを見つけない|`model`・`models.json` の `slug`・`ollama create` の名前の食い違い|3か所に `qwen3-coder-next:q8_0-256k`|
|`fully_on_gpu: False`|gpt-oss が載ったまま、または文脈が長すぎる|`ollama ps` で確認。だめなら 131072 へ（[4節](#4-gb10-実配置と道具呼び出しを確かめる)）|
|`ollama pull` が `requires a newer version`|Ollama が古い|Ollama を更新する|
|ターンが途中で終わる（「〜を読みます:」で止まる）|Qwen3-Coder-Next + Codex で報告がある|「続けて」と送る|
|起動時に `wire_api = "chat" is no longer supported`|`chat` にしている|`"responses"` に戻す|

## 出典

- [Ollama: qwen3-coder-next](https://ollama.com/library/qwen3-coder-next) — タグ（q8_0 は 85GB）、256K、既定のパラメータ
- [Qwen/Qwen3-Coder-Next-GGUF](https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF) — 推奨サンプリング、思考なし
- [Unsloth: Qwen3-Coder-Next](https://unsloth.ai/docs/models/qwen3-coder-next) — 8bit で約85GB
- Ollama のソース `server/routes.go`（思考できないモデルへの思考指定を 400 で弾く）、`openai/openai.go`（`effort: none` を思考なしへ変換する）
- Codex のソース `core/src/client.rs`（`model_reasoning_effort` が無ければ `default_reasoning_level` を送る）、`models-manager/src/model_info.rs`（`config.toml` の値がモデルの値を上書きする）
- [Codex 設定リファレンス](https://learn.chatgpt.com/docs/config-file/config-reference) — `wire_api` は `responses` のみ
- [Qwen3-Coder-Next discussions #15](https://huggingface.co/Qwen/Qwen3-Coder-Next/discussions/15) — Codex でターンが途中で終わる報告
