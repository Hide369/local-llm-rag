# GB10 の Ollama によるタブ補完 設計書

作成日: 2026-09-27

## 1. 何を作るか

社内LANの数人が、Windows の VS Code でコードを書くときに、GB10（DGX Spark）上の
Qwen がカーソル位置の続きを灰色で出し、Tab で確定できるようにする（Copilot 型の
インライン補完）。

GB10 ではすでに Codex 向けのエージェント用モデル `qwen3-coder-next:q8_0-256k` を
Ollama（`:11434`）で常駐させている
（[ollama-gb10-qwen3-coder-next.md](../../qwen/ollama-gb10-qwen3-coder-next.md)）。
今回はこれに**手を入れずに**、同じ筐体へ補完専用の小型モデルを足す。

アプリ（`rag_chat_app.py` ほか）のコードは変えない。成果物は手順書・設定の雛形・
計測スクリプトである（6節）。

## 2. 設計の前提（利用者との合意事項）

| 論点 | 決めたこと |
|---|---|
| 置き場所 | **移行先の GB10 1台。** 別の筐体は用意しない |
| 補完に使うモデル | **補完専用の小型 Qwen を別に置く。** qwen3-coder-next は兼用しない（3節） |
| 利用者 | **社内LANの数人**（Codex の利用者と同じ） |
| 構成 | **案A: 補完専用の Ollama をもう1つ立てる**（3節） |
| 補完用 Ollama のポート | **4000** |
| VS Code の拡張 | **Continue**（補完の役割だけを使う） |

## 3. なぜこの構成か

### 3.1 qwen3-coder-next を兼用しない理由

メモリは足りる（兼用なら増えない）が、次の理由で兼用しない。

1. **補完がエージェントの後ろで待たされる。** Ollama は1モデルあたり
   `OLLAMA_NUM_PARALLEL`（既定1）本しか同時に処理しない。Codex の長い生成の最中は、
   補完の要求が数十秒〜数分返らない。
2. **FIM（カーソルの前後を渡す補完）に対応しているかが未確認。** Ollama の
   `/api/generate` の `suffix` は、モデルのテンプレートが扱える場合にしか効かない。
   qwen2.5-coder の base 版は FIM 対応が定番である。
3. 1打鍵ごとに 80B 級のモデルに文脈を読み直させるのは割に合わない。

### 3.2 Ollama を2つに分ける理由

Ollama の FAQ によると、`OLLAMA_NUM_PARALLEL` は**その Ollama に載るすべての
モデルに同じ値が効き**、必要なメモリは `OLLAMA_NUM_PARALLEL × 文脈長` で増える。

| 案 | 内容 | 採否 |
|---|---|---|
| **A** | 補完専用の Ollama を `:4000` に別に立てる | **採用。** エージェント側の設定を1つも変えず、補完側だけ同時処理数を上げられる |
| B | Ollama は1つのまま、`MAX_LOADED_MODELS=2`、同時処理1 | 不採用。補完どうしが一列に並ぶ。gpt-oss 対策の `MAX_LOADED_MODELS=1` も外すことになる |
| C | Ollama は1つのまま、同時処理数を全体で上げる | 不採用。エージェントの 256K の KV も本数倍になり 128GB を超える恐れがある |

## 4. 構成

```text
Windows（数人）: VS Code + Continue（役割 autocomplete のみ、テレメトリ off）
        │ HTTP（社内LAN）  /api/generate（suffix 付き＝FIM）
        ▼
GB10 ─ ollama-autocomplete.service  :4000（新設）
         OLLAMA_HOST=0.0.0.0:4000
         OLLAMA_NUM_PARALLEL=4
         OLLAMA_MAX_LOADED_MODELS=1
         OLLAMA_KEEP_ALIVE=-1
         OLLAMA_CONTEXT_LENGTH=8192
         OLLAMA_MODELS=/usr/share/ollama/.ollama/models（既存と共有）
         User=ollama
         → qwen2.5-coder:1.5b-base（常駐）
     ─ ollama.service  :11434（変更なし）→ qwen3-coder-next:q8_0-256k
```

- **モデル:** `qwen2.5-coder:1.5b-base` から始める。FIM には instruct 版より base 版が
  向く。`7b-base` へ上げるかは7節の計測で決める。
- **モデルの置き場所:** 既定の `ollama.service` と同じ `User=ollama` と
  `OLLAMA_MODELS` を使い、二重に取得しない。取得は
  `OLLAMA_HOST=127.0.0.1:4000 ollama pull qwen2.5-coder:1.5b-base` で行う。
- **ユニット名:** `ollama-autocomplete.service`。公式のインストールスクリプトが
  書き換えるのは `ollama.service` だけなので、Ollama を更新しても残る。同じ
  実行ファイルを使うため、再起動すれば新しい版で動く。
- **Continue:** `config.yaml` に `provider: ollama`、`model: qwen2.5-coder:1.5b-base`、
  `apiBase: http://<GB10のIP>:4000`、`roles: [autocomplete]` のモデルを1つだけ書く。
  補完に使う文脈の上限（`autocompleteOptions.maxPromptTokens`）は、サーバー側の
  8192 以下にする。超えた分はサーバー側で黙って切り詰められる。
  `defaultCompletionOptions` で `keepAlive: -1` と `contextLength: 8192` を送らせる。
  Continue は既定で `keep_alive` を30分として送り、要求の値がサーバー側の
  `OLLAMA_KEEP_ALIVE=-1` より優先されるため、そのままでは常駐にならない。

## 5. メモリの見積もり（未検証）

同時処理数と文脈長の関係は Ollama の FAQ に従い、1本あたり 8192 トークン × 4本で
見積もる。KV キャッシュはモデルの構成（層数・KV ヘッド数・ヘッドの次元、f16）から
計算した。

| 補完モデル | 重み | KV（8K×4本） | 計算用バッファ込みの合計 |
|---|---|---|---|
| **qwen2.5-coder:1.5b-base** | 約1GB | 約0.9GB | **約2〜3GB** |
| qwen2.5-coder:7b-base | 約4.7GB | 約1.9GB | 約7〜8GB |

エージェント側の約95GB と合わせて、1.5B で約98GB、7B で約103GB。128GB に収まる
見込みである。

## 6. 成果物

| パス | 内容 |
|---|---|
| `docs/qwen/ollama-gb10-autocomplete.md` | 手順書。GB10 側（ポート確認、ユニット追加、ファイアウォール、モデル取得、確認）、Windows 側（Continue 導入、`config.yaml`、テレメトリ off）、計測、元に戻す手順、つまずきやすいところ、出典 |
| `docs/qwen/ollama-autocomplete.service` | systemd ユニットの雛形（4節の環境変数） |
| `docs/qwen/continue-config.yaml` | Continue の設定の雛形（GB10 の IP は置き換える箇所として明示する） |
| `scripts/measure_autocomplete.py` | 応答時間の計測スクリプト（7節）。標準ライブラリだけで書く |
| `tests/test_measure_autocomplete.py` | 計測スクリプトの集計部分のテスト。GB10 へは通信しない |
| `docs/qwen/ollama-gb10-qwen3-coder-next.md`（追記） | 補完用 Ollama を併設したときの注意と、手順書へのリンク |

**最終成果物は手順書である。** 体裁は前回の
[ollama-gb10-qwen3-coder-next.md](../../qwen/ollama-gb10-qwen3-coder-next.md) に揃える。

- 冒頭に構成図、前提（どの手順書を済ませていること）、**未検証である旨の注記**。
- 目次。節の見出しは「GB10: …」「Windows: …」と作業する場所から始める。
- 「0. 何を変えるか」の表（場所・変更・理由）。
- 各節の末尾に「成功の目安」（7.1 の合格の条件を割り振る）。
- 末尾に「元に戻す」（9節）、「つまずきやすいところ」（症状・原因・対処の表）、「出典」。

## 7. 確かめ方と計測

### 7.1 合格の条件

手順書の各段に「成功の目安」として書く。

| # | 確かめること | 合格の条件 |
|---|---|---|
| 1 | FIM が動くか | GB10 上で `curl` を使い、`:4000/api/generate` に `prompt` と `suffix` を付けて送る。返るのが間に入るコードだけで、説明文や `suffix` の繰り返しが混ざらない |
| 2 | メモリ | 両方のモデルを載せた状態で、`:11434` と `:4000` の `ollama ps` がどちらも GPU 100%。`free -h` でスワップが増えていない |
| 3 | 互いに邪魔しないか | Codex に長い生成をさせている最中に補完を送っても、ふだんと変わらない時間で返る |
| 4 | 同時に使えるか | 補完を4本同時に送り、4本とも返って大きく遅れない |
| 5 | Windows | Continue で灰色の候補が出て Tab で確定できる。Continue の出力ログで宛先が `GB10:4000` |
| 6 | 外へ出ないか | `continue.telemetryEnabled` が `false`。Continue にサインインしていない |

### 7.2 計測スクリプト

`scripts/measure_autocomplete.py`:

- 入力: 宛先の URL（既定 `http://127.0.0.1:4000`）、モデル名、回数 N、同時本数
  （1 と 4 を想定）。
- 固定したコード片（FIM の前後、約1,500トークン）を `num_predict=64` で N 回送る。
- Ollama の応答の `total_duration` / `prompt_eval_duration` / `eval_duration` と、
  クライアント側の往復時間について、中央値と p90 を出す。
- 通信の失敗やタイムアウトは件数として数え、集計から外したうえで表示する（握り
  つぶさない）。
- Windows から実行すれば LAN の遅れも含めて測れる。

判断の目安: **4本同時で往復時間の p90 が 500ms 以下**なら実用とみなす。7B も満たす
なら 7B に上げてよい。満たさなければ 1.5B のままにする。500ms は体感の目安として
置いた値で、実際の使用感を見て手順書で改める。

## 8. 気をつける点

1. **2つの Ollama は互いのメモリ使用量を知らない。** それぞれが空きを見積もって
   読み込む。GB10 は CPU と GPU がメモリを共有するので、85GB を読み込むときの
   ファイルキャッシュが「空き」をどう見せるかは実機で確かめる（7.1 の #2）。
2. **ポート 4000 の衝突。** 手順の最初に `ss -ltnp | grep ':4000'` で確かめる。
3. **ファイアウォール。** 社内LANのサブネットからの 4000 番だけを許す。
4. **認証がない。** LAN 内の誰でも使えるのは、今の `:11434` と同じ条件である。
5. **何がどこへ流れるか。** カーソル前後のコードと、Continue が文脈として足す
   コード片（開いているファイルなど）が、社内LANの平文 HTTP で GB10 に届く。
   外部に出うるのは Continue のテレメトリで、手順で `false` にし、Continue の Hub
   にはサインインしないと明記する。このリポジトリのコードが持つ経路ではないため、
   AGENTS.md の外部通信の一覧には足さず、手順書に書く。

## 9. 元に戻す

1. `sudo systemctl disable --now ollama-autocomplete` の後、ユニットファイルを消して
   `sudo systemctl daemon-reload`。
2. ファイアウォールの 4000 番の許可を消す。
3. `ollama rm qwen2.5-coder:1.5b-base`（置き場所を共有しているので `:11434` 経由で
   消せる）。
4. Windows 側は Continue をアンインストールする。

エージェント用の `:11434` には手を入れていないので、ほかに戻すものはない。

## 10. 範囲外

- Continue のチャット・編集・エージェント機能（エージェントは Codex が担う）。
- 認証や TLS の追加（`:11434` と同じ扱いにとどめる）。
- qwen3-coder-next の FIM 対応の検証（兼用しないため）。

## 出典

- Ollama FAQ「How does Ollama handle concurrent requests?」—
  `OLLAMA_NUM_PARALLEL` はモデルごとの同時処理数で既定1、必要メモリは
  `OLLAMA_NUM_PARALLEL × OLLAMA_CONTEXT_LENGTH` で増える
  （https://github.com/ollama/ollama/blob/main/docs/faq.mdx）
- Continue: Autocomplete（Ollama の `qwen2.5-coder:1.5b` を `roles: [autocomplete]`
  で使う例）、Ollama プロバイダーの `apiBase`、VS Code 設定の
  `continue.telemetryEnabled`（既定 `true`）
  （https://github.com/continuedev/continue）
