# GB10のOllamaにタブ補完用のQwenを併設する

GB10（DGX Spark）に**補完専用の Ollama をもう1つ**、ポート `4000` で立てる。そこに
小型の `qwen2.5-coder:1.5b-base` を常駐させ、Windows の VS Code + Continue から
Copilot のようなタブ補完（灰色の候補を Tab で確定）を使う。エージェント用の
Ollama（`:11434`、qwen3-coder-next）の設定は1つも変えない。

```text
Windows（数人）: VS Code + Continue（役割 autocomplete のみ、テレメトリ off）
        │ HTTP（社内LAN）  /api/generate（suffix 付き＝FIM）
        ▼
GB10 ─ ollama-autocomplete.service  :4000（この手順で足す）
         OLLAMA_NUM_PARALLEL=4 / OLLAMA_CONTEXT_LENGTH=8192
         → qwen2.5-coder:1.5b-base（常駐）
     ─ ollama.service  :11434（変更なし）→ qwen3-coder-next:q8_0-256k
```

**前提:** [GB10のOllamaを Qwen3-Coder-Next（q8_0）に置き換える](ollama-gb10-qwen3-coder-next.md)
まで済んでいること。設計の経緯は
[設計書](../superpowers/specs/2026-09-27-gb10-tab-autocomplete-design.md)にある。

> **未検証である。** Ollama の FAQ と Continue のドキュメントを確かめて組んだが、GB10 の
> 実機で通した記録はまだ無い。各段階の「成功の目安」で確かめながら進めること。特に
> [5節](#5-gb10-両方を載せてメモリを確かめる)は、2つの Ollama を同じメモリに並べて
> 成り立つかどうかの関門である。

## 目次

- [0. 何を変えるか](#0-何を変えるか)
- [1. GB10: ポートと既存の設定を確かめる](#1-gb10-ポートと既存の設定を確かめる)
- [2. GB10: 補完用のサービスを足す](#2-gb10-補完用のサービスを足す)
- [3. GB10: 社内LANから届くか確かめる](#3-gb10-社内lanから届くか確かめる)
- [4. GB10: モデルを取得し、FIM を確かめる](#4-gb10-モデルを取得しfim-を確かめる)
- [5. GB10: 両方を載せてメモリを確かめる](#5-gb10-両方を載せてメモリを確かめる)
- [6. GB10: 応答時間を測る](#6-gb10-応答時間を測る)
- [7. Windows: Continue を入れる](#7-windows-continue-を入れる)
- [8. 何がどこへ流れるか](#8-何がどこへ流れるか)
- [元に戻す](#元に戻す)
- [つまずきやすいところ](#つまずきやすいところ)
- [出典](#出典)

## 0. 何を変えるか

|場所|変更|理由|
|---|---|---|
|GB10|`ollama-autocomplete.service` を足す（`:4000`）|同時処理数をエージェント側と分ける（下記）|
|GB10|`qwen2.5-coder:1.5b-base` を取得する|FIM（カーソルの前後を渡す補完）には instruct 版より base 版が向く|
|Windows|Continue を入れ、`config.yaml` を置き、テレメトリを切る|補完の役割だけを使う|

### なぜ qwen3-coder-next を兼用しないか

1. **補完がエージェントの後ろで待たされる。** Ollama は1モデルあたり
   `OLLAMA_NUM_PARALLEL`（既定1）本しか同時に処理しない。Codex の長い生成の最中は、
   補完が数十秒〜数分返らない。
2. **FIM に対応しているかが未確認。** `/api/generate` の `suffix` は、モデルの
   テンプレートが扱える場合にしか効かない。qwen2.5-coder の base 版は FIM 対応が定番である。
3. 1打鍵ごとに 80B 級のモデルに文脈を読み直させるのは割に合わない。

### なぜ Ollama を2つにするか

`OLLAMA_NUM_PARALLEL` は**その Ollama に載るすべてのモデルに同じ値が効き**、必要な
メモリは `OLLAMA_NUM_PARALLEL × 文脈長` で増える（Ollama の FAQ）。

|案|内容|採否|
|---|---|---|
|**A**|補完専用の Ollama を `:4000` に別に立てる|**採用。** エージェント側を変えず、補完側だけ同時処理数を上げられる|
|B|Ollama は1つのまま `MAX_LOADED_MODELS=2`、同時処理1|補完どうしが一列に並ぶ。gpt-oss 対策の `MAX_LOADED_MODELS=1` も外すことになる|
|C|Ollama は1つのまま、同時処理数を全体で上げる|エージェントの 256K の KV も本数倍になり、128GB を超える恐れがある|

### メモリの見込み（未検証）

1本あたり 8192 トークン × 4本で見積もった。KV はモデルの構成（層数・KV ヘッド数・
ヘッドの次元、f16）から計算した値である。

|補完モデル|重み|KV（8K×4本）|計算用バッファ込みの合計|
|---|---|---|---|
|**qwen2.5-coder:1.5b-base**|約1GB|約0.9GB|**約2〜3GB**|
|qwen2.5-coder:7b-base|約4.7GB|約1.9GB|約7〜8GB|

エージェント側の約95GB と合わせて、1.5B で約98GB、7B で約103GB。128GB に収まる見込みである。

## 1. GB10: ポートと既存の設定を確かめる

```bash
ss -ltnp | grep ':4000'                       # 何も出なければ空いている
which ollama                                  # /usr/local/bin/ollama であること
systemctl cat ollama | grep -E 'OLLAMA_MODELS|User='
ls /usr/share/ollama/.ollama/models           # blobs と manifests がある
```

**成功の目安:**

- 4000 番が空いている。塞がっていて止められないなら、先へ進まずポートを決め直す。
- `which ollama` の結果が雛形の `ExecStart=/usr/local/bin/ollama serve` と一致する。
  違えば、2節で雛形の `ExecStart` をその場所に書き換える。
- `systemctl cat ollama` に `User=ollama` がある。`OLLAMA_MODELS` の行が**出ない**なら
  既定の置き場所（`/usr/share/ollama/.ollama/models`）を使っているので雛形のままでよい。
  **出たら**、2節で雛形の `OLLAMA_MODELS` をその値に書き換える。ここが食い違うと、補完側
  からモデルが見えない（または二重に取得する）。

## 2. GB10: 補完用のサービスを足す

雛形 [ollama-autocomplete.service](ollama-autocomplete.service) を、`models.json` と同じく
ブラウザーから1ファイルだけ落とし、Windows から GB10 へ送る。

```powershell
scp .\ollama-autocomplete.service <ユーザー>@<GB10のIP>:~/
```

1節で書き換えが要ると分かった箇所は、送る前に直しておく。GB10 側で置いて起動する。

```bash
sudo cp ~/ollama-autocomplete.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ollama-autocomplete
systemctl status ollama-autocomplete --no-pager
curl -s http://127.0.0.1:4000/api/version
curl -s http://127.0.0.1:11434/api/version    # エージェント側も生きている
```

|設定|理由|
|---|---|
|`OLLAMA_HOST=0.0.0.0:4000`|社内LANから届くように。`:11434` とは別のポート|
|`OLLAMA_MODELS`（`ollama.service` と同じ）|モデルを二重に取得しない|
|`OLLAMA_NUM_PARALLEL=4`|数人が同時に打つ。この Ollama にだけ効く|
|`OLLAMA_MAX_LOADED_MODELS=1`|補完用に載せるのは1つだけ。7B を試すときは 1.5B と入れ替わる|
|`OLLAMA_KEEP_ALIVE=-1`|降ろさない。補完のたびに読み込みを待たせない|
|`OLLAMA_CONTEXT_LENGTH=8192`|1本あたりの文脈長。Continue 側の `maxPromptTokens`（1536）より十分大きい|

ユニット名が `ollama.service` と別なので、Ollama を公式のインストールスクリプトで更新
しても書き換えられない。同じ実行ファイルを使うため、`sudo systemctl restart
ollama-autocomplete` で新しい版になる。

**成功の目安:** `active (running)`。2つの `curl` がどちらも `{"version":"…"}` を返す。

## 3. GB10: 社内LANから届くか確かめる

Windows 側から確かめる。

```powershell
curl.exe http://<GB10のIP>:4000/api/version
```

> **Ollamaに認証は無い。** `:11434` と同じく、そのLANから届く全員が補完用のモデルを
> 使える。社内の信頼できるセグメントに限ること。届く範囲が広いなら、ファイアウォールで
> 4000 番の送信元を絞る（[Ollama版の4節](../gb10-coding-agent.md#4-gb10側-lanへ公開する)
> と同じ扱い）。

**成功の目安:** Windows から `{"version":"…"}` が返る。

## 4. GB10: モデルを取得し、FIM を確かめる

補完用の Ollama に向けて取得する。置き場所は共有なので、どちらの Ollama からも見える。

```bash
OLLAMA_HOST=127.0.0.1:4000 ollama pull qwen2.5-coder:1.5b-base
OLLAMA_HOST=127.0.0.1:4000 ollama show --template qwen2.5-coder:1.5b-base | grep -c Suffix
```

2行目は 1 以上になること。テンプレートが `suffix` を扱えるという意味である。

カーソルの前（`prompt`）と後ろ（`suffix`）を渡して、間を埋めさせる。

```bash
curl -s http://127.0.0.1:4000/api/generate -d '{
  "model": "qwen2.5-coder:1.5b-base",
  "prompt": "def fib(n):\n    ",
  "suffix": "\n\nprint(fib(10))\n",
  "stream": false,
  "options": {"num_predict": 64, "temperature": 0}
}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["response"])'
```

**成功の目安:** テンプレートに `Suffix` がある。返るのが `fib` の本体だけで、説明文や
`print(fib(10))` の繰り返しが混ざらない。

## 5. GB10: 両方を載せてメモリを確かめる

**この構成の関門である。** 2つの Ollama は互いのメモリ使用量を知らず、それぞれが自分で
空きを見積もって読み込む。GB10 は CPU と GPU がメモリを共有するので、並べて成り立つかは
実機で確かめるしかない。

エージェント側が載っていなければ、先に載せる。

```bash
ollama run qwen3-coder-next:q8_0-256k "hi" > /dev/null
```

```bash
ollama ps                                     # :11434 側
OLLAMA_HOST=127.0.0.1:4000 ollama ps          # :4000 側
free -h
```

**成功の目安:** どちらの `PROCESSOR` 列も `100% GPU`、`UNTIL` が `Forever`。`free -h` の
Swap の `used` が作業前から増えていない。

エージェント側が `100% GPU` にならないなら、補完側を止めて順番を入れ替える
（[つまずきやすいところ](#つまずきやすいところ)の最後の行）。それでも収まらなければ、
先へ進まず `ollama ps` と `free -h` の出力を控えて相談すること。

## 6. GB10: 応答時間を測る

補完は遅ければ使われない。[`scripts/measure_autocomplete.py`](../../scripts/measure_autocomplete.py)
で、4本同時に送ったときの往復時間を測る。標準ライブラリだけで書いてあるので、この
ファイル1つを GB10 へ送れば `python3` でそのまま動く。

```powershell
scp .\measure_autocomplete.py <ユーザー>@<GB10のIP>:~/
```

```bash
python3 ~/measure_autocomplete.py
```

既定では `http://127.0.0.1:4000` の `qwen2.5-coder:1.5b-base` に、同時1本と同時4本でそれぞれ
20回送る。1回目はモデルの読み込みを待つことがあるので、集計の前に1回だけ送って捨てる。
要求ごとに先頭の行を変えてあり、Ollama のプロンプトキャッシュで実際より速く見えることは無い。

出力は同時本数ごとに1ブロックで、見るのは `往復時間` の p90 と最後の「判定」行である。

```text
同時 4 本: 成功 20 / 失敗 0
  プロンプトの平均トークン数: …
  往復時間: 中央値 … ms / p90 … ms
  …
  判定: 往復時間の p90 … ms（目安 500 ms 以下）→ 目安内
```

失敗が1件でもあれば理由ごとの件数を出し、終了コードが 1 になる。

Windows に Python があれば、同じファイルで LAN の遅れも含めて測れる
（`python measure_autocomplete.py --url http://<GB10のIP>:4000`）。

### エージェントと邪魔し合わないか

Codex に長い作業をさせている最中に、同時1本だけで測る。

```bash
python3 ~/measure_autocomplete.py --concurrency 1
```

何もしていないときの値と大きく変わらなければよい。

### 7B を試す

```bash
OLLAMA_HOST=127.0.0.1:4000 ollama pull qwen2.5-coder:7b-base
python3 ~/measure_autocomplete.py --model qwen2.5-coder:7b-base
```

`:4000` は `OLLAMA_MAX_LOADED_MODELS=1` なので、7B を呼ぶと 1.5B と入れ替わる。4本同時の
p90 が 500ms 以下なら、7節の `config.yaml` の `model` と `name` を 7B に替えてよい。
超えるなら 1.5B に戻す（`python3 ~/measure_autocomplete.py` を1回走らせれば 1.5B が載り直す）。
500ms は体感の目安として置いた値である。使ってみて遅い・速すぎると感じたら
`--target-ms` で変え、この節を直すこと。

**成功の目安:** 同時4本で失敗 0、判定が「目安内」。Codex の作業中でも同時1本の値が
大きく悪化しない。

## 7. Windows: Continue を入れる

1. VS Code の拡張機能で **Continue**（発行元 Continue）を入れる。
2. **サインインしない。** Continue の Hub にもつながない。
3. ユーザー設定の `settings.json` に1行足し、利用状況の送信を切る（既定は `true`）。

   ```json
   "continue.telemetryEnabled": false
   ```

4. 雛形 [continue-config.yaml](continue-config.yaml) を `%USERPROFILE%\.continue\config.yaml`
   に置く。既にあれば `config.yaml.bak` として残してから置き換える。`<GB10のIP>` を
   GB10 のアドレスに置き換える。
5. VS Code を**完全に終了してから**起動し直す。拡張の入れ替えは「Reload Window」では
   反映しきらないことがある。

雛形の要点:

|キー|値|理由|
|---|---|---|
|`roles`|`autocomplete` だけ|チャット・編集は持たせない（エージェントは Codex が担う）|
|`apiBase`|`http://<GB10のIP>:4000`|`:11434` ではない|
|`maxPromptTokens`|1536|サーバー側の文脈長 8192 より小さく。超えた分は黙って切り詰められる|
|`modelTimeout`|1000（ms）|LAN 越しなので長めに取る。短いと、間に合わなかった補完が黙って捨てられる|

**成功の目安:**

- Python のファイルで関数を書きかけると、灰色の候補が出て Tab で確定できる。
- VS Code の出力パネルで Continue のログを選び、要求先が `http://<GB10のIP>:4000` である
  （ログのチャンネル名は Continue の版で変わりうる。一覧から Continue を含むものを選ぶ）。
- `continue.telemetryEnabled` が `false` で、Continue にサインインしていない。

## 8. 何がどこへ流れるか

- カーソル前後のコードと、Continue が文脈として足すコード片（開いているファイルなど）が、
  社内LANの**平文の HTTP** で GB10 に届く。
- 外へ出うるのは Continue のテレメトリだけで、7節で切っている。サインインしなければ
  Hub にもつながない。
- 認証は無い。LAN 内の誰でも使えるのは `:11434` と同じ条件である。

このリポジトリのコードが持つ通信経路ではないので、AGENTS.md の外部通信の一覧には
載せていない。

## 元に戻す

GB10 側:

```bash
sudo systemctl disable --now ollama-autocomplete
sudo rm /etc/systemd/system/ollama-autocomplete.service
sudo systemctl daemon-reload
ollama rm qwen2.5-coder:1.5b-base            # 置き場所を共有しているので :11434 経由で消せる
ollama rm qwen2.5-coder:7b-base 2>/dev/null  # 6節で試していれば
```

4000 番のためにファイアウォールへ足した許可があれば消す。

Windows 側は Continue をアンインストールし、`%USERPROFILE%\.continue` を消す（退避した
`config.yaml.bak` が要らなければ一緒に）。

エージェント用の `:11434` には手を入れていないので、ほかに戻すものは無い。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|灰色の候補が出ない|`modelTimeout` が短く、LAN 越しの応答が間に合わずに捨てられている。または `apiBase` の誤り|3節の `curl.exe` で届くか確かめる。6節の往復時間の p90 より `modelTimeout` を大きくする|
|`HTTP 404: model '…' not found`|`:4000` 側で取得していない、または `OLLAMA_MODELS` が `ollama.service` と違う|[4節](#4-gb10-モデルを取得しfim-を確かめる)の `pull`。[1節](#1-gb10-ポートと既存の設定を確かめる)で確かめた値をユニットに書く|
|候補に説明文が混ざる、後ろのコードを繰り返す|instruct 版を指定している、またはテンプレートに `Suffix` が無い|`-base` のタグを使う。4節の `ollama show --template`|
|`ollama-autocomplete` が起動しない（`address already in use`）|4000 番を他が使っている|1節の `ss`。止められなければポートを決め直す|
|`permission denied`（モデルの置き場所）|`User=` が `ollama.service` と違う|1節で確かめた `User=` に揃える|
|`ExecStart` が見つからない（`status=203/EXEC`）|`ollama` の場所が雛形と違う|1節の `which ollama` の結果に `ExecStart` を直す|
|GB10 の再起動後に qwen3-coder-next が `100% GPU` にならない|2つの Ollama が互いのメモリ使用量を知らない|`sudo systemctl stop ollama-autocomplete` → エージェント側を載せる（5節）→ `sudo systemctl start ollama-autocomplete` → 補完側に1回要求して載せる。5節で確かめ直す|

## 出典

- [Ollama FAQ「How does Ollama handle concurrent requests?」](https://github.com/ollama/ollama/blob/main/docs/faq.mdx) — `OLLAMA_NUM_PARALLEL` はモデルごとの同時処理数で既定1、必要メモリは `OLLAMA_NUM_PARALLEL × OLLAMA_CONTEXT_LENGTH` で増える
- [Ollama: qwen2.5-coder](https://ollama.com/library/qwen2.5-coder) — タグ（`1.5b-base` / `7b-base`）
- [Continue: Autocomplete](https://github.com/continuedev/continue/blob/main/docs/customize/deep-dives/autocomplete.mdx) — Ollama の `qwen2.5-coder:1.5b` を `roles: [autocomplete]` で使う例、`autocompleteOptions`
- [Continue: Ollama](https://github.com/continuedev/continue/blob/main/docs/customize/model-providers/top-level/ollama.mdx) — リモートの Ollama を `apiBase` で指す
- [Continue: 設定の場所](https://github.com/continuedev/continue/blob/main/docs/customize/deep-dives/configuration.mdx) — Windows は `%USERPROFILE%\.continue\config.yaml`
- Continue の `extensions/vscode/package.json` — `continue.telemetryEnabled`（既定 `true`）
