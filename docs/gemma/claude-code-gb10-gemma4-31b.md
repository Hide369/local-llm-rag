# VS CodeのClaude CodeをGB10のGemma 4 31Bへ切り替える（プロキシなし）

[VS CodeのClaude CodeをGB10のQwen3-Coder-Nextへ向ける](../qwen/claude-code-gb10-qwen3-coder-next.md)で
使っている `qwen3-coder-next:q8_0-256k` を、**`gemma4:31b`** に置き換える手順。推論サーバーは
GB10 の Ollama のまま替えず、プロキシも立てない。

```text
Windows（VS Code + Claude Code 拡張 + ~/.claude/settings.json）
        │ HTTP（社内LAN）/ Anthropic Messages API（/v1/messages）
        ▼
GB10 → Ollama :11434 → gemma4:31b-256k（常駐）
```

**前提:** 次の2つが済み、Claude Code から Qwen を使えていること。この文書はその差分だけを書く。

- [GB10のOllamaを Qwen3-Coder-Next（q8_0）に置き換える](../qwen/ollama-gb10-qwen3-coder-next.md)の
  **1〜5節**（とくに5節の `OLLAMA_MAX_LOADED_MODELS=1` / `OLLAMA_KEEP_ALIVE=-1`）
- [VS CodeのClaude CodeをGB10のQwen3-Coder-Nextへ向ける](../qwen/claude-code-gb10-qwen3-coder-next.md)の全体

**`qwen3-coder-next` は、Claude Code から Gemma を使えると確かめるまで消さない。** 消すのは最後の
[7節](#7-qwen3-coder-next-を消す任意)で、任意である。それまでは `settings.json` を戻すだけで元に戻れる。

> **未検証である。** Ollama のモデルページ・ソースと Gemma 4 のモデルカードを確かめて
> 組んだが、GB10 の実機で通した記録はまだ無い。各段階の「成功の目安」で確かめながら進めること。
> 特に[3節](#3-gb10-思考の指定ごとの動きを確かめる)は、この構成が成り立つかどうかの関門である。

**Anthropic が想定・サポートする構成ではない**ことは Qwen のときと同じである。

## 目次

- [0. 何を変えるか](#0-何を変えるか)
- [1. GB10: モデルを取得する](#1-gb10-モデルを取得する)
- [2. GB10: 文脈長を伸ばした別名を作る](#2-gb10-文脈長を伸ばした別名を作る)
- [3. GB10: 思考の指定ごとの動きを確かめる](#3-gb10-思考の指定ごとの動きを確かめる)
- [4. GB10: 実配置と道具呼び出しを確かめる](#4-gb10-実配置と道具呼び出しを確かめる)
- [5. Windows: ~/.claude/settings.json を書き換える](#5-windows-claudesettingsjson-を書き換える)
- [6. 起動して確かめる](#6-起動して確かめる)
- [7. qwen3-coder-next を消す（任意）](#7-qwen3-coder-next-を消す任意)
- [文脈長と圧縮](#文脈長と圧縮)
- [元に戻す](#元に戻す)
- [つまずきやすいところ](#つまずきやすいところ)
- [出典](#出典)

## 0. 何を変えるか

|場所|変更|理由|
|---|---|---|
|GB10 Ollama|`gemma4:31b` を取得し、文脈長 262144 の別名を作る|Ollama の既定の文脈長は短い。Qwen と同じく別名に焼く|
|GB10 Ollama の常駐設定|変えない|Qwen の手順の5節で設定済み。Gemma にもそのまま効く|
|Windows `~/.claude/settings.json`|モデル名の5か所を替え、`CLAUDE_CODE_DISABLE_THINKING` を消す|思考は止められないので、オンで使う（下記）|
|VS Code の settings.json|変えない|`claudeCode.disableLoginPrompt` はそのまま|

### Qwen との違い

|項目|qwen3-coder-next:q8_0|**gemma4:31b**|
|---|---|---|
|構造|MoE（80B のうち1トークンに使うのは約3B）|**Dense（30.7B を毎トークン全部使う）**|
|重み|85GB|**約20GB**（Q4_K_M）|
|文脈長|256K|256K|
|思考|しない|**する（オンとオフの2択。段階は無い）**|
|入力|テキスト|テキストと画像|
|推奨サンプリング|temperature 1 / top_k 40 / top_p 0.95|temperature 1 / top_k 64 / top_p 0.95|

### 生成は Qwen より遅くなる見込み

生成速度は、1トークンごとに読む重みの量でほぼ決まる（GB10 のメモリ帯域は 273GB/s）。
Qwen は MoE で1トークンに約3B分しか読まないが、Gemma 4 31B は dense なので**毎トークン
約20GB を読む。** 単純計算の上限は 273 ÷ 20 ≒ **13トークン/秒**で、Qwen の数分の一になる。
思考がオンなので、答えの前に思考の分も生成する。

Claude Code では、これが Codex より効きやすい。

- システムプロンプトと道具の定義が大きく、最初の要求の読み込み（プレフィル）が長い。2回目
  からは Ollama が先頭一致の KV を再利用するので短くなる
- 会話の題名付けのような裏の軽い要求も同じモデルへ送るので、その分も待つ

メモリには余裕がある（128GB に対して重み約20GB）。

### なぜ gemma4:31b（Q4_K_M）か

|タグ|重み|生成速度の上限|精度|
|---|---|---|---|
|**`gemma4:31b`（この手順）**|約20GB（Q4_K_M）|約13トークン/秒|4bit量子化の劣化がある|
|`gemma4:31b-it-q8_0`|34GB|約8トークン/秒|ほぼ劣化しない|
|`gemma4:31b-it-bf16`|63GB|約4トークン/秒|劣化なし|

Qwen のときは MoE で速度に余裕があったので8bit を選んだ。dense の Gemma では8bit にすると
速度が約6割に落ちるので、既定の4bit から始める。**精度が足りないと感じたら q8_0 に上げる**
（手順はタグ名を替えるだけ）。

### 思考はオンで使う（オフにする設定が効かない）

Qwen のときは `CLAUDE_CODE_DISABLE_THINKING=1` で思考の指定を送らないようにした。
**Gemma ではこれでは思考が止まらない。** Ollama の `/v1/messages` は次のように扱う。

|Claude Code が送る `thinking`|Ollama の扱い|Gemma の思考|
|---|---|---|
|`{"type":"enabled", …}`|思考オン（`budget_tokens` は読まない）|**オン**|
|`{"type":"disabled"}`|思考オフ|オフ|
|**付けない**（`CLAUDE_CODE_DISABLE_THINKING=1` のとき）|指定なし → **思考できるモデルは既定でオン**|**オン**|

Qwen は思考できないモデルだったので「付けない」で思考しなかった。Gemma は思考できるので、
付けなくても Ollama がオンにする。Claude Code の設定から `disabled` を明示して送らせる
方法は確かめられていない。

止められないのなら、Claude Code 側も「思考する前提」に揃えたほうが食い違いが無い。そこで
`CLAUDE_CODE_DISABLE_THINKING` を**消す**。Ollama は `budget_tokens` を読まないので、
`MAX_THINKING_TOKENS` などで思考の長さを絞ることもできない。

## 1. GB10: モデルを取得する

```bash
df -h /usr/share/ollama ~/.ollama 2>/dev/null   # 20GB 以上の空き（Qwen の 85GB はまだ残る）
ollama pull gemma4:31b                           # 約20GB
ollama list                                      # qwen3-coder-next:q8_0 / q8_0-256k も残っていること
```

`requires a newer version of Ollama` と出たら Ollama を更新する。

```bash
ollama show gemma4:31b
```

**成功の目安:**

- Capabilities に **`tools` と `thinking` がある**（`vision` もある）
- Parameters に `temperature 1` / `top_k 64` / `top_p 0.95`（Gemma 4 の推奨値）
- 量子化が `Q4_K_M`

Claude Code はサンプリングの値を Ollama に効く形では送らないので、ここに入っている値が
そのまま効く。自分で `PARAMETER temperature` などを足す必要は無い。

## 2. GB10: 文脈長を伸ばした別名を作る

**元のモデルは書き換えず、別名で作る。**

```bash
cat <<'EOF' > /tmp/Modelfile.gemma4-31b
FROM gemma4:31b
PARAMETER num_ctx 262144
EOF
ollama create gemma4:31b-256k -f /tmp/Modelfile.gemma4-31b
ollama show gemma4:31b-256k --parameters   # num_ctx 262144 と temperature 1 など
```

`FROM` で作った別名は、元のテンプレートとパラメータを引き継ぐ。足したのは `num_ctx` だけである。

262144 はこのモデルが素で持つ長さである。60層のうち多くは直近 1024 トークンだけを見る
層（スライディングウィンドウ）で、文脈全体の KV キャッシュを持つのは一部の層だけである。
ただし全体を見る層の数や KV の大きさは公開資料から読み取れなかったので、**見積もりを
置かずに4節で測る。** 重みが約20GB と小さいので、128GB に収まらないことはまず無い。

## 3. GB10: 思考の指定ごとの動きを確かめる

**この構成の関門である。** [0節](#思考はオンで使うオフにする設定が効かない)の表のとおりに
動くか、`thinking` を付けない・`enabled`・`disabled` の3通りで確かめる。

```bash
ollama stop qwen3-coder-next:q8_0-256k 2>/dev/null   # 載っていれば降ろす
python3 - <<'PY'
import json, urllib.request, urllib.error

URL = "http://127.0.0.1:11434/v1/messages"
CASES = {
    "absent":   None,
    "enabled":  {"type": "enabled", "budget_tokens": 1024},
    "disabled": {"type": "disabled"},
}
for name, thinking in CASES.items():
    body = {"model": "gemma4:31b-256k", "max_tokens": 1024,
            "messages": [{"role": "user", "content": "Reply with OK."}]}
    if thinking is not None:
        body["thinking"] = thinking
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"content-type": "application/json",
                                  "anthropic-version": "2023-06-01", "x-api-key": "ollama"})
    print("--- thinking =", name)
    try:
        with urllib.request.urlopen(req, timeout=600) as res:
            content = json.load(res)["content"]
        print("  HTTP 200 / blocks:", [b["type"] for b in content])
        print("  text:", "".join(b.get("text", "") for b in content)[:80])
    except urllib.error.HTTPError as e:
        print("  HTTP", e.code, e.read().decode()[:300])
PY
```

1回目はモデルの読み込みを待つので時間がかかる。

**成功の目安:**

|thinking|期待|
|---|---|
|`absent`|HTTP 200、blocks が `['thinking', 'text']`（既定でオン）|
|`enabled`|HTTP 200、blocks が `['thinking', 'text']`|
|`disabled`|HTTP 200、blocks が `['text']` だけ|

3つとも text に `OK` が入っていること。

- **`absent` で `thinking` が返らない場合:** Ollama の既定がオフである。この場合は Qwen の
  ときと同じく `CLAUDE_CODE_DISABLE_THINKING=1` で思考を止められる。速さを優先するなら
  5節で消さずに残してよい
- **どれかが 400 になる場合:** この構成は成り立たない。先へ進まず、Ollama の版と
  エラー文を控えて相談すること

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

**成功の目安:** 載っているのが `gemma4:31b-256k` だけで、`context_length: 262144`、
`fully_on_gpu: True`。`size` は重み約20GB に KV と画像用のエンコーダが足された値になる。
**この値を控えておく**（2節で見積もりを置かなかった分の実測である）。

`False` なら一部がCPUに落ちている。まず Qwen が載ったままでないかを見る。それでも
落ちるなら、2節の `num_ctx` を 131072 にして作り直し、[文脈長と圧縮](#文脈長と圧縮)の
`CLAUDE_CODE_MAX_CONTEXT_TOKENS` を足す。

### 道具を呼んで、結果を返せるか

Claude Code と同じく思考オンで、道具の往復まで確かめる。2回目の要求には、1回目の
応答（思考のブロックを含む）をそのまま履歴として戻す。Claude Code もそうするからである。

```bash
python3 - <<'PY'
import json, urllib.request

URL = "http://127.0.0.1:11434/v1/messages"
MODEL = "gemma4:31b-256k"
TOOL = {"name": "get_probe_value",
        "description": "Returns the fixed connection probe value.",
        "input_schema": {"type": "object", "properties": {}, "required": []}}
PROMPT = "Call get_probe_value exactly once, then tell me the value it returned."

def post(messages):
    body = {"model": MODEL, "max_tokens": 2048, "tools": [TOOL], "messages": messages,
            "thinking": {"type": "enabled", "budget_tokens": 1024}}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"content-type": "application/json",
                                  "anthropic-version": "2023-06-01", "x-api-key": "ollama"})
    with urllib.request.urlopen(req, timeout=600) as res:
        return json.load(res)

first = post([{"role": "user", "content": PROMPT}])
uses = [b for b in first["content"] if b["type"] == "tool_use"]
print("blocks       :", [b["type"] for b in first["content"]])
print("tool_use     :", bool(uses), "/ stop_reason:", first["stop_reason"])
if uses:
    second = post([
        {"role": "user", "content": PROMPT},
        {"role": "assistant", "content": first["content"]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": uses[0]["id"],
                                      "content": "73190462"}]},
    ])
    print("used result  :", "73190462" in json.dumps(second["content"]))
PY
```

**成功の目安:** `tool_use     : True / stop_reason: tool_use` と `used result  : True`。
`max_tokens` を Qwen のときの 512 より大きくしてあるのは、思考の分で使い切って道具を
呼ぶ前に止まらないようにするためである。

### 載せたままにする

Qwen の手順の5節で `OLLAMA_KEEP_ALIVE=-1` にしてあるので、Gemma もここで載ったままになる。

```bash
ollama ps     # gemma4:31b-256k だけが載り、UNTIL が Forever であること
```

GB10 を再起動したときは、最初の1回だけ読み込みを待つ。先に `ollama run gemma4:31b-256k "hi" > /dev/null`
で載せておくとよい。

> **補完用の Ollama を併設している場合:** [タブ補完用のQwen](../qwen/ollama-gb10-autocomplete.md)
> の `:4000` は別のサービスなので、この置き換えの影響を受けない。メモリは Qwen のときより
> 空くので、併設の条件が厳しくなることも無い。

## 5. Windows: ~/.claude/settings.json を書き換える

```powershell
Copy-Item $env:USERPROFILE\.claude\settings.json $env:USERPROFILE\.claude\settings.json.qwen.bak
notepad $env:USERPROFILE\.claude\settings.json
```

**書き換える前に `settings.json.qwen.bak` として複製しておく**（上の1行目）。`env` の中だけを
次のように変える。他の設定は残す。

|操作|キー|値|
|---|---|---|
|変える|`ANTHROPIC_MODEL`|`gemma4:31b-256k`（**2節で作った名前と一字一句同じ**）|
|変える|`ANTHROPIC_DEFAULT_OPUS_MODEL` / `…_SONNET_MODEL` / `…_HAIKU_MODEL`|同上|
|変える|`CLAUDE_CODE_SUBAGENT_MODEL`|同上|
|**消す**|`CLAUDE_CODE_DISABLE_THINKING`|[0節](#思考はオンで使うオフにする設定が効かない)。残しても思考は止まらない|
|そのまま|`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` ほか|接続先は同じ GB10 の Ollama|

変更後の `env`（[`docs/gemma/claude-settings.json`](claude-settings.json) と同じ。IP は自分の環境に合わせる）:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "ANTHROPIC_BASE_URL": "http://192.168.1.50:11434",
    "ANTHROPIC_AUTH_TOKEN": "ollama",
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_MODEL": "gemma4:31b-256k",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemma4:31b-256k",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemma4:31b-256k",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemma4:31b-256k",
    "CLAUDE_CODE_SUBAGENT_MODEL": "gemma4:31b-256k",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_TELEMETRY": "1"
  }
}
```

**モデル名は5か所とも替える。** 1つでも Qwen の名前が残ると、その要求のたびに Ollama が
Gemma を降ろして Qwen（85GB）を読み込み直す（`OLLAMA_MAX_LOADED_MODELS=1` のため）。
エラーにならないので気づきにくい。

`claudeCode.environmentVariables`（VS Code の settings.json 1つにまとめる方式）で書いている
場合は、そちらの同じキーを同じように変える。

書き換えたら **VS Code をすべてのウィンドウごと閉じてから起動し直す。**

## 6. 起動して確かめる

Claude Code のパネルを開き、`/status` と打つ。

**成功の目安:** 接続先に `http://192.168.1.50:11434`、モデルに `gemma4:31b-256k` が出る。

続けて、Qwen のときと同じ依頼を出す。

```
このリポジトリの README.md が何を説明しているか、ファイルを読んで答えて
```

- **応答が返ること** — 返らなければ3・4節に戻る。GB10 までは切り分け済みなので、差は設定である
- **思考が表示されること** — 思考のブロックが画面に出れば、0節のとおりオンで動いている
- **ファイルを実際に読みに行くこと** — 読まずに一般論を答えるなら、道具呼び出しが効いていない
- **小さな修正を1つ頼み、編集してテストを走らせるところまで行くこと**

GB10 側でも見ておく。

```bash
ollama ps     # gemma4:31b-256k だけが載っていること（qwen3-coder-next に入れ替わっていない）
journalctl -u ollama --since "5 min ago" | grep -E 'v1/messages|does not support' | tail
```

`POST "/v1/messages"` が 200 で並んでいればよい。`/v1/messages/count_tokens` の 404 は
Qwen のときと同じく想定内である。

### Qwen と比べる

どちらを使うかは測って決める。測り方は[Ollama版の8節](../gb10-coding-agent.md#8-効果を測る)と
同じにする（実作業から課題を10件固定、各3回、数えるのは「道具を呼んだか」「テストが
通ったか」の2つ）。Gemma では速度の差が大きいので、**1課題あたりの所要時間も控える。**
Qwen 側を測るときは、[元に戻す](#元に戻す)の手順で一時的に戻す。
**7節の前に済ませること。** 消した後では比べられない。

## 7. qwen3-coder-next を消す（任意）

6節までで、Claude Code から Gemma を使えること、使い続けると決めたことを確かめてから行う。

```bash
ollama rm qwen3-coder-next:q8_0-256k qwen3-coder-next:q8_0   # 約85GB 空く
ollama list                                                  # gemma4 の2つだけ残ること
```

Windows 側の `settings.json.qwen.bak` も要らなくなる。**消した後で Qwen に戻すには、
`ollama pull qwen3-coder-next:q8_0` で約85GBを取り直し、
[Qwen の手順の2節](../qwen/ollama-gb10-qwen3-coder-next.md#2-gb10-文脈長を伸ばした別名を作る)
で別名を作り直すことになる。**

タブ補完用の `qwen2.5-coder:1.5b-base`（`:4000` の Ollama）は別物なので消さない。

## 文脈長と圧縮

Qwen のときと同じである。Claude Code は知らないモデル名の文脈長を **200K と見なし**、
その手前で会話を圧縮する。Ollama 側は 262144 なので、**このままにしておく。**
余白を残す理由は [Qwen の Claude Code 版の「文脈長と圧縮」](../qwen/claude-code-gb10-qwen3-coder-next.md#文脈長と圧縮)
にある（Ollama は上限を超えた要求をエラーにせず、古い部分を黙って切り捨てる）。

4節で文脈を 131072 に下げた場合は、既定の 200K では Ollama の上限を超える。余白を
残した値（131072 の3/4）を5節の `env` に足す。

```json
"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "98304"
```

## 元に戻す

7節の前なら、GB10 のモデルは両方そろっている。

```powershell
Copy-Item $env:USERPROFILE\.claude\settings.json.qwen.bak $env:USERPROFILE\.claude\settings.json
```

VS Code を起動し直す。GB10 側は、最初の要求が来たとき Ollama が Gemma を降ろして Qwen を
読み込む（`OLLAMA_MAX_LOADED_MODELS=1` のため）。

Gemma をやめると決めたら、GB10 側も片づける。

```bash
ollama rm gemma4:31b-256k gemma4:31b   # 約20GB 空く
```

7節の後（Qwen を消した後）や、`settings.json.qwen.bak` を消した後で Qwen に戻すときは、
[Gemma 4 31B から Qwen3-Coder-Next へ切り替える](../qwen/claude-code-gb10-gemma4-to-qwen3-coder-next.md)の
手順で行う。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|生成が遅い|dense の 31B は毎トークン約20GB を読む（[0節](#生成は-qwen-より遅くなる見込み)）。思考の分も生成する|q8_0 にしていたら既定の Q4_K_M に戻す。それでも遅ければ Qwen に戻す|
|`CLAUDE_CODE_DISABLE_THINKING=1` なのに思考が出る|指定が無いと Ollama は思考を既定でオンにする|想定どおり（[0節](#思考はオンで使うオフにする設定が効かない)）。この行は消してよい|
|ときどき Qwen に入れ替わる、要求のたびに長く待つ|`settings.json` に Qwen の名前が1つ残っている|5か所とも `gemma4:31b-256k` か確かめる。`ollama ps` で載っている名前を見る|
|`model "gemma4…" not found`|`ANTHROPIC_MODEL` と `ollama create` の名前の食い違い|`ollama list` の表記をそのまま写す|
|2回目以降の要求で 400、または思考のブロックについてのエラー|Ollama の思考ブロックには署名（`signature`）が無い。Claude Code が履歴に戻すときに問題になりうる|4節の Python で再現するか見る。そこが通るなら Claude Code 側の扱いである。エラー文を控えて相談する|
|道具を呼ぶ前に応答が切れる|思考で出力の上限を使い切った|4節の `max_tokens` を上げて再現するか見る|
|ファイルを読まずに答える|道具呼び出しが効いていない|4節の Python で切り分ける。そこが通るなら、Claude Code の道具の定義が Gemma に合っていない。**設定では直らない**|
|1回目の要求がとても遅い、または切れる|GB10 の再起動後の読み込み待ち、または長いシステムプロンプトのプレフィル|[4節](#載せたままにする)の最後で先に載せておく|
|`fully_on_gpu: False`|Qwen が載ったまま、または文脈が長すぎる|`ollama ps` で確認。だめなら 131072 へ（[4節](#4-gb10-実配置と道具呼び出しを確かめる)）|
|`ollama pull` が `requires a newer version`|Ollama が古い|Ollama を更新する|
|設定が効かない|JSON の構文エラー|`//` コメントと末尾カンマを消す。消した行の前の行に末尾カンマが残っていないか見る|

## 出典

- [Ollama: gemma4](https://ollama.com/library/gemma4) — 31B は Dense、思考は `<|think|>` で切り替え、Ollama がテンプレートを処理する
- [Ollama: gemma4 のタグ一覧](https://ollama.com/library/gemma4/tags) — `gemma4:31b` は約20GB、`31b-it-q8_0` は 34GB、`31b-it-bf16` は 63GB、いずれも 256K
- [Ollama: gemma4:31b](https://ollama.com/library/gemma4:31b) — Q4_K_M、30.7B、60層、スライディングウィンドウ 1024、既定のパラメータ（temperature 1 / top_k 64 / top_p 0.95）
- [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it) — 推奨サンプリング、局所注意と全体注意の交互配置、関数呼び出しに対応
- Ollama のソース `anthropic/anthropic.go` — `thinking.type` が `enabled` なら思考オン、`disabled` ならオフ、無ければ指定なし。`budget_tokens` は読まない。応答の思考ブロックに `signature` を付けない。履歴の思考ブロックは保持する
- Ollama のソース `server/routes.go` — 思考できるモデルで指定が無ければ思考をオンにする
- Ollama のドキュメント「Thinking」— 対応モデルでは CLI と API で思考が既定でオン
- Claude Code 側の設定項目の出典は [Qwen の Claude Code 版の出典](../qwen/claude-code-gb10-qwen3-coder-next.md#出典)と同じ
