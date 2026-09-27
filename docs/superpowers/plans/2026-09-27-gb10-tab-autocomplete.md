# GB10 タブ補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GB10 に補完専用の Ollama（`:4000`、`qwen2.5-coder:1.5b-base`）を併設し、社内LANの VS Code + Continue から Tab 補完を使えるようにする手順書・雛形・計測スクリプトを作る。

**Architecture:** アプリのコードは変えない。GB10 上に2つ目の systemd サービス `ollama-autocomplete.service` を置き、エージェント用 `ollama.service`（`:11434`）とはプロセスを分ける。応答時間は標準ライブラリだけで書いた `scripts/measure_autocomplete.py` で測り、1.5B と 7B のどちらを使うかを決める。

**Tech Stack:** Ollama（systemd, `/api/generate` の `suffix` による FIM）、Continue（VS Code 拡張、`config.yaml`）、Python 3.13 標準ライブラリ（`urllib.request`, `concurrent.futures`）、pytest。

**Spec:** [docs/superpowers/specs/2026-09-27-gb10-tab-autocomplete-design.md](../specs/2026-09-27-gb10-tab-autocomplete-design.md)

## Global Constraints

- エージェント用 `ollama.service`（`:11434`）の設定は1つも変えない。
- 補完用 Ollama のポートは `4000`。ユニット名は `ollama-autocomplete.service`。
- 補完用 Ollama の環境変数: `OLLAMA_HOST=0.0.0.0:4000`、`OLLAMA_NUM_PARALLEL=4`、`OLLAMA_MAX_LOADED_MODELS=1`、`OLLAMA_KEEP_ALIVE=-1`、`OLLAMA_CONTEXT_LENGTH=8192`、`OLLAMA_MODELS=/usr/share/ollama/.ollama/models`、`User=ollama`。
- モデルは `qwen2.5-coder:1.5b-base` で始める。7B（`qwen2.5-coder:7b-base`）へ上げるかは計測で決める。
- 判断の目安: 4本同時で往復時間の p90 が 500ms 以下。
- Continue は `roles: [autocomplete]` のモデル1つだけ。`continue.telemetryEnabled: false`。Hub にはサインインしない。
- `autocompleteOptions.maxPromptTokens` は 8192 以下（本計画では 1536）。
- `scripts/measure_autocomplete.py` は標準ライブラリだけで書く（GB10 へ単体で持っていけるように、`scripts` パッケージからも import しない）。
- 手順書の体裁は [docs/qwen/ollama-gb10-qwen3-coder-next.md](../../qwen/ollama-gb10-qwen3-coder-next.md) に揃える（冒頭の構成図・前提・未検証の注記、目次、「0. 何を変えるか」、節見出しは「GB10: …」「Windows: …」、各節末尾に「成功の目安」、末尾に「元に戻す」「つまずきやすいところ」「出典」）。
- 手順書の文体は既存の docs に合わせ、常体（「〜する」「〜である」）で書く。
- コミットはコンベンショナルコミット、英語。ブランチは `docs/gb10-tab-autocomplete-spec`（作成済み）。
- テストは `.\myvenv313\Scripts\python.exe -m pytest` で実行し、失敗ゼロを確認してから合格と報告する。

## Review Focus

1. **補完用 Ollama にモデルが無い（pull 忘れ・`OLLAMA_MODELS` の不一致）** — 計測スクリプトはトレースバックではなく「HTTP 404: model ... not found」のように Ollama のエラー文を出して終了コード 1 を返すべき。→ Task 1 `test_send_reports_ollama_error_body`。
2. **モデルが未ロードで、1回目だけ数秒かかる** — 読み込み時間が統計に混ざると p90 が不当に悪く出る。ウォームアップの1回は集計から外すべき。→ Task 1 `test_main_excludes_warm_up_from_stats`。
3. **同じ文面を送り続けるとプロンプトのキャッシュが効き、実際より速く見える** — 要求ごとに先頭を変えるべき。→ Task 1 `test_fim_payload_differs_at_the_start`。
4. **サーバーが応答しない・途中で止まる** — タイムアウトで失敗として数え、ほかの要求の集計は続け、終了コード 1 にすべき。→ Task 1 `test_send_times_out_as_failure` と `test_main_returns_1_when_any_request_fails`。
5. **Continue の `modelTimeout` が短く、LAN越しの補完が黙って捨てられる** — 雛形で明示的に 1000ms にし、つまずきやすいところに症状と対処を書くべき。→ Task 2 Step 3 と Task 3 Step 4 の確認。

---

## File Structure

| パス | 責務 |
|---|---|
| `scripts/measure_autocomplete.py`（新規） | FIM 要求の組み立て、送信、集計、表示、CLI |
| `tests/test_measure_autocomplete.py`（新規） | 上記のテスト。ローカルの `http.server` 以外へは通信しない |
| `docs/qwen/ollama-autocomplete.service`（新規） | systemd ユニットの雛形 |
| `docs/qwen/continue-config.yaml`（新規） | Continue の設定の雛形 |
| `docs/qwen/ollama-gb10-autocomplete.md`（新規） | 手順書（最終成果物） |
| `docs/qwen/ollama-gb10-qwen3-coder-next.md`（追記） | 5節に、補完用 Ollama を併設するときの注意とリンク |

---

### Task 1: 計測スクリプト `scripts/measure_autocomplete.py`

**Files:**
- Create: `scripts/measure_autocomplete.py`
- Test: `tests/test_measure_autocomplete.py`

**Interfaces:**
- Consumes: なし
- Produces（Task 3 の手順書が CLI を参照する）:
  - CLI: `python -m scripts.measure_autocomplete [--url URL] [--model MODEL] [--count N] [--concurrency N [N ...]] [--timeout SEC] [--target-ms MS]`。既定値は `--url http://127.0.0.1:4000`、`--model qwen2.5-coder:1.5b-base`、`--count 20`、`--concurrency 1 4`、`--timeout 30`、`--target-ms 500`。終了コードは、ウォームアップの失敗か、計測中に1件でも失敗があれば 1、それ以外は 0。
  - `fim_payload(model: str, index: int) -> dict`
  - `parse_response(body: dict, round_trip_s: float) -> Sample`
  - `percentile(values: list[float], q: float) -> float`
  - `summarize(results: list[Sample | Failure]) -> Summary`
  - `format_summary(summary: Summary, concurrency: int, target_ms: float) -> str`
  - `send(url: str, payload: dict, timeout_s: float) -> Sample | Failure`
  - `run(send_one: Callable[[dict], Sample | Failure], payloads: list[dict], concurrency: int) -> list[Sample | Failure]`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: 純粋関数のテストを書く**

`tests/test_measure_autocomplete.py` を作る。

```python
"""scripts/measure_autocomplete.py のテスト。

GB10 へは通信しない。send() はテスト内で立てたローカルの HTTP サーバーに向ける。
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from scripts import measure_autocomplete as measure


def _body(total_ns=400_000_000, prompt_ns=100_000_000, eval_ns=250_000_000, tokens=1500):
    return {
        "response": "return sum(records)",
        "total_duration": total_ns,
        "prompt_eval_duration": prompt_ns,
        "eval_duration": eval_ns,
        "prompt_eval_count": tokens,
    }


def _sample(round_trip_s):
    return measure.Sample(
        round_trip_s=round_trip_s,
        total_s=round_trip_s,
        prompt_eval_s=0.1,
        eval_s=0.2,
        prompt_tokens=1500,
    )


def test_percentile_uses_nearest_rank():
    values = [float(v) for v in range(10, 0, -1)]  # 並びが崩れていても順に並べて数える
    assert measure.percentile(values, 0.9) == 9.0
    assert measure.percentile(values, 0.5) == 5.0
    assert measure.percentile([3.0], 0.9) == 3.0


def test_percentile_rejects_empty_values():
    with pytest.raises(ValueError):
        measure.percentile([], 0.9)


def test_fim_payload_sends_prefix_suffix_and_limits():
    payload = measure.fim_payload("qwen2.5-coder:1.5b-base", 0)
    assert payload["model"] == "qwen2.5-coder:1.5b-base"
    assert payload["prompt"].strip()
    assert payload["suffix"].strip()
    assert payload["stream"] is False
    assert payload["options"] == {"num_predict": 64, "temperature": 0}


def test_fim_payload_differs_at_the_start():
    first = measure.fim_payload("m", 0)
    second = measure.fim_payload("m", 1)
    # 先頭が違えば Ollama のプロンプトキャッシュは効かない
    assert first["prompt"].splitlines()[0] != second["prompt"].splitlines()[0]
    assert first["suffix"] == second["suffix"]


def test_parse_response_converts_nanoseconds_to_seconds():
    sample = measure.parse_response(_body(total_ns=2_000_000_000), round_trip_s=2.5)
    assert sample.round_trip_s == 2.5
    assert sample.total_s == 2.0
    assert sample.prompt_eval_s == 0.1
    assert sample.eval_s == 0.25
    assert sample.prompt_tokens == 1500


def test_parse_response_rejects_error_body():
    with pytest.raises(ValueError, match="model 'x' not found"):
        measure.parse_response({"error": "model 'x' not found"}, round_trip_s=0.1)


def test_parse_response_names_missing_keys():
    body = _body()
    del body["eval_duration"]
    with pytest.raises(ValueError, match="eval_duration"):
        measure.parse_response(body, round_trip_s=0.1)


def test_summarize_separates_failures_from_samples():
    results = [_sample(0.1), _sample(0.2), measure.Failure("HTTP 500: boom"), _sample(0.3)]
    summary = measure.summarize(results)
    assert summary.succeeded == 3
    assert summary.failures == (measure.Failure("HTTP 500: boom"),)
    assert summary.median["round_trip_s"] == pytest.approx(0.2)
    assert summary.p90["round_trip_s"] == pytest.approx(0.3)
    assert summary.mean_prompt_tokens == 1500


def test_summarize_with_no_samples_has_no_stats():
    summary = measure.summarize([measure.Failure("接続できない: refused")])
    assert summary.succeeded == 0
    assert summary.median == {}
    assert summary.p90 == {}


def test_format_summary_says_within_target():
    text = measure.format_summary(measure.summarize([_sample(0.2)] * 5), concurrency=4, target_ms=500)
    assert "同時 4 本" in text
    assert "成功 5 / 失敗 0" in text
    assert "目安内" in text


def test_format_summary_says_over_target_and_lists_failures():
    results = [_sample(0.9)] * 3 + [measure.Failure("HTTP 500: boom")] * 2
    text = measure.format_summary(measure.summarize(results), concurrency=1, target_ms=500)
    assert "目安超え" in text
    assert "HTTP 500: boom（2 件）" in text


def test_format_summary_without_samples_has_no_verdict():
    text = measure.format_summary(measure.summarize([measure.Failure("x")]), concurrency=1, target_ms=500)
    assert "成功 0 / 失敗 1" in text
    assert "判定" not in text
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_measure_autocomplete.py -v`
Expected: FAIL（`ImportError: cannot import name 'measure_autocomplete' from 'scripts'`）

- [ ] **Step 3: 純粋関数を実装する**

`scripts/measure_autocomplete.py` を作る。

```python
"""GB10 の補完用 Ollama（:4000）の応答時間を測る。

1.5B と 7B のどちらを補完に使うかを、4本同時の往復時間の p90 で決めるために使う
（docs/superpowers/specs/2026-09-27-gb10-tab-autocomplete-design.md 7.2節）。
GB10 へファイル1つで持っていけるよう、標準ライブラリだけで書く。
"""
import argparse
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

DEFAULT_URL = "http://127.0.0.1:4000"
DEFAULT_MODEL = "qwen2.5-coder:1.5b-base"
DEFAULT_TARGET_MS = 500.0
NUM_PREDICT = 64
_NS_PER_S = 1_000_000_000
_REQUIRED_KEYS = ("total_duration", "prompt_eval_duration", "eval_duration", "prompt_eval_count")

# 1関数でおよそ60トークン。前に20個・後ろに5個で合計約1,500トークンになり、
# Continue の maxPromptTokens（1536）と同じくらいの重さで測れる。
_FUNCTION = '''
def load_record_{i}(path, encoding="utf-8"):
    """Read record {i} and return its fields as a dict."""
    with open(path, encoding=encoding) as handle:
        fields = [line.strip().split("=", 1) for line in handle if "=" in line]
    return {{key: value for key, value in fields}}
'''
_PREFIX_FUNCTIONS = 20
_SUFFIX_FUNCTIONS = 5

METRICS = ("round_trip_s", "total_s", "prompt_eval_s", "eval_s")
_LABELS = {
    "round_trip_s": "往復時間",
    "total_s": "total_duration",
    "prompt_eval_s": "prompt_eval_duration",
    "eval_s": "eval_duration",
}


@dataclass(frozen=True)
class Sample:
    round_trip_s: float
    total_s: float
    prompt_eval_s: float
    eval_s: float
    prompt_tokens: int


@dataclass(frozen=True)
class Failure:
    reason: str


@dataclass(frozen=True)
class Summary:
    succeeded: int
    failures: tuple[Failure, ...]
    median: dict[str, float]
    p90: dict[str, float]
    mean_prompt_tokens: float


def fim_payload(model: str, index: int) -> dict:
    """カーソルの前後を渡す FIM の要求を作る。"""
    # 先頭に要求ごとの番号を入れる。同じ文面を送り続けると Ollama がプロンプトの
    # 処理結果を使い回し、prompt の読み込みが実際の補完より速く見える。
    prefix = (
        f"# request {index}\n"
        + "".join(_FUNCTION.format(i=i) for i in range(_PREFIX_FUNCTIONS))
        + "\ndef summarize_records(records):\n    "
    )
    suffix = "\n" + "".join(
        _FUNCTION.format(i=i)
        for i in range(_PREFIX_FUNCTIONS, _PREFIX_FUNCTIONS + _SUFFIX_FUNCTIONS)
    )
    return {
        "model": model,
        "prompt": prefix,
        "suffix": suffix,
        "stream": False,
        "options": {"num_predict": NUM_PREDICT, "temperature": 0},
    }


def parse_response(body: dict, round_trip_s: float) -> Sample:
    """Ollama の応答から時間を取り出す。時間はナノ秒で返ってくる。"""
    if "error" in body:
        raise ValueError(f"Ollama がエラーを返した: {body['error']}")
    missing = [key for key in _REQUIRED_KEYS if key not in body]
    if missing:
        raise ValueError(f"応答に {', '.join(missing)} が無い")
    return Sample(
        round_trip_s=round_trip_s,
        total_s=body["total_duration"] / _NS_PER_S,
        prompt_eval_s=body["prompt_eval_duration"] / _NS_PER_S,
        eval_s=body["eval_duration"] / _NS_PER_S,
        prompt_tokens=body["prompt_eval_count"],
    )


def percentile(values: list[float], q: float) -> float:
    """最近傍順位法の百分位。補間しないので、実際に観測した値のどれかが返る。"""
    if not values:
        raise ValueError("値が1つも無い")
    if not 0 < q <= 1:
        raise ValueError(f"q は 0 より大きく 1 以下: {q}")
    ordered = sorted(values)
    return ordered[math.ceil(q * len(ordered)) - 1]


def summarize(results: list["Sample | Failure"]) -> Summary:
    samples = [r for r in results if isinstance(r, Sample)]
    failures = tuple(r for r in results if isinstance(r, Failure))
    if not samples:
        return Summary(0, failures, {}, {}, 0.0)
    median = {m: statistics.median(getattr(s, m) for s in samples) for m in METRICS}
    p90 = {m: percentile([getattr(s, m) for s in samples], 0.9) for m in METRICS}
    mean_tokens = statistics.fmean(s.prompt_tokens for s in samples)
    return Summary(len(samples), failures, median, p90, mean_tokens)


def format_summary(summary: Summary, concurrency: int, target_ms: float) -> str:
    lines = [f"同時 {concurrency} 本: 成功 {summary.succeeded} / 失敗 {len(summary.failures)}"]
    for reason, count in Counter(f.reason for f in summary.failures).most_common():
        lines.append(f"  失敗: {reason}（{count} 件）")
    if summary.succeeded == 0:
        return "\n".join(lines)
    lines.append(f"  プロンプトの平均トークン数: {summary.mean_prompt_tokens:.0f}")
    for metric in METRICS:
        lines.append(
            f"  {_LABELS[metric]}: 中央値 {summary.median[metric] * 1000:.0f} ms"
            f" / p90 {summary.p90[metric] * 1000:.0f} ms"
        )
    p90_ms = summary.p90["round_trip_s"] * 1000
    verdict = "目安内" if p90_ms <= target_ms else "目安超え"
    lines.append(f"  判定: 往復時間の p90 {p90_ms:.0f} ms（目安 {target_ms:.0f} ms 以下）→ {verdict}")
    return "\n".join(lines)
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_measure_autocomplete.py -v`
Expected: 12 passed

- [ ] **Step 5: 送信・並列実行・CLI のテストを足す**

`tests/test_measure_autocomplete.py` の末尾に足す。

```python
class _Handler(BaseHTTPRequestHandler):
    """テストごとに server.reply（status, body, delay_s）で応答を決める。"""

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        status, body, delay_s = self.server.reply
        time.sleep(delay_s)
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.reply = (200, _body(), 0.0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def _url(httpd):
    return f"http://127.0.0.1:{httpd.server_address[1]}"


def test_send_returns_sample_on_success(server):
    result = measure.send(_url(server), measure.fim_payload("m", 0), timeout_s=5)
    assert isinstance(result, measure.Sample)
    assert result.total_s == pytest.approx(0.4)
    assert result.round_trip_s > 0


def test_send_reports_ollama_error_body(server):
    server.reply = (404, {"error": "model 'qwen2.5-coder:1.5b-base' not found"}, 0.0)
    result = measure.send(_url(server), measure.fim_payload("m", 0), timeout_s=5)
    assert result == measure.Failure("HTTP 404: model 'qwen2.5-coder:1.5b-base' not found")


def test_send_reports_non_json_body(server):
    server.reply = (200, "<html>proxy</html>", 0.0)
    result = measure.send(_url(server), measure.fim_payload("m", 0), timeout_s=5)
    assert isinstance(result, measure.Failure)
    assert result.reason.startswith("応答が JSON でない")


def test_send_times_out_as_failure(server):
    server.reply = (200, _body(), 1.0)
    result = measure.send(_url(server), measure.fim_payload("m", 0), timeout_s=0.2)
    assert isinstance(result, measure.Failure)
    assert result.reason.startswith("接続できない")


def test_run_returns_one_result_per_payload_in_order():
    payloads = [{"index": i} for i in range(6)]
    results = measure.run(lambda p: measure.Failure(str(p["index"])), payloads, concurrency=4)
    assert [r.reason for r in results] == ["0", "1", "2", "3", "4", "5"]


def test_run_rejects_non_positive_concurrency():
    with pytest.raises(ValueError):
        measure.run(lambda p: measure.Failure("x"), [{}], concurrency=0)


def _fake_send(outcomes):
    """呼ばれた payload を記録し、outcomes を順に返す偽の send。"""
    calls = []

    def fake(url, payload, timeout_s):
        calls.append(payload)
        return outcomes[len(calls) - 1] if len(calls) <= len(outcomes) else _sample(0.1)

    return fake, calls


def test_main_excludes_warm_up_from_stats(monkeypatch, capsys):
    # ウォームアップだけ 9 秒かかる（モデルの読み込み）。集計に混ざれば p90 が目安を超える。
    fake, calls = _fake_send([_sample(9.0)])
    monkeypatch.setattr(measure, "send", fake)
    code = measure.main(["--count", "3", "--concurrency", "1"])
    out = capsys.readouterr().out
    assert code == 0
    assert len(calls) == 4  # ウォームアップ1回 + 計測3回
    assert "成功 3 / 失敗 0" in out
    assert "目安内" in out


def test_main_returns_1_when_any_request_fails(monkeypatch, capsys):
    fake, _ = _fake_send([_sample(0.1), _sample(0.1), measure.Failure("HTTP 500: boom")])
    monkeypatch.setattr(measure, "send", fake)
    code = measure.main(["--count", "3", "--concurrency", "1"])
    out = capsys.readouterr().out
    assert code == 1
    assert "HTTP 500: boom（1 件）" in out


def test_main_stops_when_warm_up_fails(monkeypatch, capsys):
    fake, calls = _fake_send([measure.Failure("接続できない: refused")])
    monkeypatch.setattr(measure, "send", fake)
    code = measure.main(["--count", "3"])
    assert code == 1
    assert len(calls) == 1
    assert "接続できない: refused" in capsys.readouterr().err


def test_main_rejects_zero_count():
    with pytest.raises(SystemExit):
        measure.main(["--count", "0"])
```

- [ ] **Step 6: 足したテストが失敗することを確かめる**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_measure_autocomplete.py -v`
Expected: 新しい10件が FAIL（`AttributeError: module 'scripts.measure_autocomplete' has no attribute 'send'` など）、既存12件は PASS

- [ ] **Step 7: 送信・並列実行・CLI を実装する**

`scripts/measure_autocomplete.py` の末尾に足す。

```python
def _error_text(error: urllib.error.HTTPError) -> str:
    raw = error.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)["error"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return raw.strip() or error.reason


def send(url: str, payload: dict, timeout_s: float) -> "Sample | Failure":
    """1回送って結果を返す。失敗は例外にせず Failure で返し、集計で数える。"""
    request = urllib.request.Request(
        f"{url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        return Failure(f"HTTP {error.code}: {_error_text(error)}")
    except OSError as error:  # URLError・タイムアウト・接続拒否はすべて OSError
        return Failure(f"接続できない: {error}")
    round_trip_s = time.perf_counter() - started
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as error:
        return Failure(f"応答が JSON でない: {error}")
    try:
        return parse_response(body, round_trip_s)
    except ValueError as error:
        return Failure(str(error))


def run(
    send_one: Callable[[dict], "Sample | Failure"],
    payloads: list[dict],
    concurrency: int,
) -> list["Sample | Failure"]:
    """payloads を concurrency 本ずつ同時に送る。結果は payloads の順に返す。"""
    if concurrency < 1:
        raise ValueError(f"同時本数は1以上: {concurrency}")
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        return list(pool.map(send_one, payloads))


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"1以上を指定する: {text}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="補完用 Ollama の応答時間を測る")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--count", type=_positive_int, default=20, help="同時本数ごとの要求数")
    parser.add_argument("--concurrency", type=_positive_int, nargs="+", default=[1, 4])
    parser.add_argument("--timeout", type=float, default=30.0, help="1要求あたりの秒数")
    parser.add_argument("--target-ms", type=float, default=DEFAULT_TARGET_MS)
    args = parser.parse_args(argv)

    def send_one(payload: dict) -> "Sample | Failure":
        return send(args.url, payload, args.timeout)

    # モデルが載っていなければ1回目は読み込みを待つ。その時間を統計に混ぜない。
    warm_up = send_one(fim_payload(args.model, -1))
    if isinstance(warm_up, Failure):
        print(f"ウォームアップに失敗した: {warm_up.reason}", file=sys.stderr)
        return 1

    any_failed = False
    index = 0
    for concurrency in args.concurrency:
        payloads = [fim_payload(args.model, index + i) for i in range(args.count)]
        index += args.count
        summary = summarize(run(send_one, payloads, concurrency))
        print(format_summary(summary, concurrency, args.target_ms))
        any_failed = any_failed or bool(summary.failures)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 8: テストが通ることを確かめる**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_measure_autocomplete.py -v`
Expected: 22 passed

- [ ] **Step 9: 全テストが通ることを確かめる**

Run: `.\myvenv313\Scripts\python.exe -m pytest -q`
Expected: 失敗 0（既存テストの件数に 22 件が加わる）

- [ ] **Step 10: CLI のヘルプが出ることを確かめる**

Run: `.\myvenv313\Scripts\python.exe -m scripts.measure_autocomplete --help`
Expected: `--url`、`--model`、`--count`、`--concurrency`、`--timeout`、`--target-ms` が並ぶ。

- [ ] **Step 11: コミット**

```bash
git add scripts/measure_autocomplete.py tests/test_measure_autocomplete.py
git commit -m "feat: measure round-trip latency of the GB10 autocomplete Ollama"
```

---

### Task 2: systemd ユニットと Continue 設定の雛形

**Files:**
- Create: `docs/qwen/ollama-autocomplete.service`
- Create: `docs/qwen/continue-config.yaml`

**Interfaces:**
- Consumes: なし
- Produces（Task 3 の手順書が参照する）: 上の2ファイルのパスと、Continue の `name: Qwen2.5-Coder 1.5B (GB10)`、置き換え箇所 `<GB10のIP>`

- [ ] **Step 1: ユニットの雛形を書く**

`docs/qwen/ollama-autocomplete.service`（改行は LF。`.gitattributes` で扱いが決まっていなければ、`git add --renormalize` 後に `git ls-files --eol docs/qwen/ollama-autocomplete.service` で `w/lf` を確かめる）:

```ini
# GB10 の補完専用 Ollama（:4000）。エージェント用の ollama.service（:11434）とは別に動かす。
# 設計: docs/superpowers/specs/2026-09-27-gb10-tab-autocomplete-design.md
# 置き場所: /etc/systemd/system/ollama-autocomplete.service
[Unit]
Description=Ollama for tab autocomplete (:4000)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:4000"
# ollama.service と同じ置き場所を使い、モデルを二重に取得しない
Environment="OLLAMA_MODELS=/usr/share/ollama/.ollama/models"
# 数人が同時に打つ。同時処理数はこの Ollama にだけ効く
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=-1"
# 1本あたりの文脈長。KV は 8192 × 4本ぶん確保される
Environment="OLLAMA_CONTEXT_LENGTH=8192"

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: ユニットに Global Constraints の値が揃っていることを確かめる**

Run: `Select-String -Path docs\qwen\ollama-autocomplete.service -Pattern 'OLLAMA_HOST=0.0.0.0:4000','OLLAMA_NUM_PARALLEL=4','OLLAMA_MAX_LOADED_MODELS=1','OLLAMA_KEEP_ALIVE=-1','OLLAMA_CONTEXT_LENGTH=8192','OLLAMA_MODELS=/usr/share/ollama/.ollama/models','User=ollama' | Measure-Object | Select-Object -ExpandProperty Count`
Expected: `7`

- [ ] **Step 3: Continue の雛形を書く**

`docs/qwen/continue-config.yaml`:

```yaml
# GB10 の補完用 Ollama（:4000）で、Continue のタブ補完だけを使う。
# 置き場所: %USERPROFILE%\.continue\config.yaml
# <GB10のIP> を GB10 の社内LANのアドレスに置き換える。
# チャット・編集の役割は持たせない（エージェントは Codex が担う）。
name: GB10 Autocomplete
version: 0.0.1
schema: v1

models:
  - name: Qwen2.5-Coder 1.5B (GB10)
    provider: ollama
    model: qwen2.5-coder:1.5b-base
    apiBase: http://<GB10のIP>:4000
    roles:
      - autocomplete
    autocompleteOptions:
      # サーバー側の文脈長 8192 より小さく。超えた分は黙って切り詰められる
      maxPromptTokens: 1536
      debounceDelay: 250
      # LAN 越しなので長めに取る。短いと、間に合わなかった補完が黙って捨てられる
      modelTimeout: 1000
```

- [ ] **Step 4: YAML として読めて、値が揃っていることを確かめる**

Run: `.\myvenv313\Scripts\python.exe -c "import yaml; c = yaml.safe_load(open('docs/qwen/continue-config.yaml', encoding='utf-8')); m = c['models'][0]; assert m['roles'] == ['autocomplete'] and m['model'] == 'qwen2.5-coder:1.5b-base' and m['apiBase'].endswith(':4000') and m['autocompleteOptions']['maxPromptTokens'] <= 8192 and m['autocompleteOptions']['modelTimeout'] == 1000; print('ok')"`
Expected: `ok`
（`ModuleNotFoundError: No module named 'yaml'` の場合は依存を足さず、目視で Step 3 と一致することを確かめ、その旨を報告する）

- [ ] **Step 5: コミット**

```bash
git add docs/qwen/ollama-autocomplete.service docs/qwen/continue-config.yaml
git commit -m "docs: add the systemd unit and Continue config for GB10 autocomplete"
```

---

### Task 3: 手順書 `docs/qwen/ollama-gb10-autocomplete.md` と既存手順書への追記

**Files:**
- Create: `docs/qwen/ollama-gb10-autocomplete.md`
- Modify: `docs/qwen/ollama-gb10-qwen3-coder-next.md`（「## 5. GB10: 常駐させ、2つ目を載せない」の節の末尾）

**Interfaces:**
- Consumes: Task 1 の CLI（`python -m scripts.measure_autocomplete`、既定値、終了コード）、Task 2 の2ファイル
- Produces: 最終成果物

- [ ] **Step 1: 既存の手順書を読み、体裁を写す**

`docs/qwen/ollama-gb10-qwen3-coder-next.md` の全体と、`docs/gb10-coding-agent.md` の「4. GB10側: LANへ公開する」（ファイアウォールの開け方）を読む。見出しの付け方、「成功の目安」の書き方、表の形、「未検証である。」の注記の書き方をそのまま使う。

- [ ] **Step 2: 手順書を書く**

次の節立てで書く（見出しはこのとおり。本文は常体）。各節に書くコマンドと成功の目安は下のとおり。

**冒頭**
- タイトル: `# GB10のOllamaにタブ補完用のQwenを併設する`
- 1段落の概要（同じ GB10 に補完専用の Ollama を `:4000` で立て、VS Code + Continue から Tab 補完を使う。エージェント用 `:11434` は変えない）。
- 構成図（設計書4節の図をそのまま）。
- **前提:** [GB10のOllamaを Qwen3-Coder-Next（q8_0）に置き換える](ollama-gb10-qwen3-coder-next.md) まで済んでいること。
- 注記: `> **未検証である。**` で始め、Ollama の FAQ と Continue のドキュメントを確かめて組んだが GB10 の実機で通した記録は無いこと、メモリの見積もり（5節）が関門であることを書く。

**目次**（下の各節へのリンク）

**0. 何を変えるか** — 表（場所・変更・理由）:
|GB10|`ollama-autocomplete.service` を足す（`:4000`）|同時処理数をエージェント側と分けるため（設計書3.2節の理由を1文で）|
|GB10|ファイアウォールで 4000 番を社内LANにだけ開ける|Windows から届くように|
|GB10|`qwen2.5-coder:1.5b-base` を取得する|FIM には base 版が向く|
|Windows|Continue を入れ、`config.yaml` を置き、テレメトリを切る|補完の役割だけを使う|
続けて「### なぜ Ollama を2つにするか」に設計書3.1・3.2節の要旨（兼用しない理由3つ、案A/B/C の表）と、「### メモリの見込み」に設計書5節の表を載せる。

**1. GB10: ポートと既存の設定を確かめる**
```bash
ss -ltnp | grep ':4000'                       # 何も出なければ空いている
which ollama                                  # /usr/local/bin/ollama であること
systemctl cat ollama | grep -E 'OLLAMA_MODELS|User='
ls /usr/share/ollama/.ollama/models           # blobs と manifests がある
```
成功の目安: 4000 番が空いている。`ollama` の場所が雛形の `ExecStart` と一致する。`ollama.service` が `OLLAMA_MODELS` を上書きしていれば、雛形の `OLLAMA_MODELS` をその値に書き換えると明記する。`which` の結果が違えば `ExecStart` を書き換える。

**2. GB10: 補完用のサービスを足す**
雛形 [ollama-autocomplete.service](ollama-autocomplete.service) を GB10 へ持っていく手順（`scp` で Windows から送る例、または `sudo tee` に貼る例のどちらか1つ）と:
```bash
sudo cp ollama-autocomplete.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ollama-autocomplete
systemctl status ollama-autocomplete --no-pager
curl -s http://127.0.0.1:4000/api/version
curl -s http://127.0.0.1:11434/api/version    # エージェント側も生きている
```
成功の目安: `active (running)`、2つの `curl` がどちらも `{"version":"…"}` を返す。

**3. GB10: 社内LANに 4000 番を開ける**
`docs/gb10-coding-agent.md` の4節と同じ方式で、4000 番だけを社内LANのサブネットに許す（ufw を使っているなら `sudo ufw allow from <社内LANのサブネット> to any port 4000 proto tcp` と `sudo ufw status`）。
Windows から:
```powershell
curl.exe -s http://<GB10のIP>:4000/api/version
```
成功の目安: Windows から `{"version":"…"}` が返る。

**4. GB10: モデルを取得し、FIM を確かめる**
```bash
OLLAMA_HOST=127.0.0.1:4000 ollama pull qwen2.5-coder:1.5b-base
OLLAMA_HOST=127.0.0.1:4000 ollama show --template qwen2.5-coder:1.5b-base | grep -c Suffix   # 1 以上
curl -s http://127.0.0.1:4000/api/generate -d '{
  "model": "qwen2.5-coder:1.5b-base",
  "prompt": "def fib(n):\n    ",
  "suffix": "\n\nprint(fib(10))\n",
  "stream": false,
  "options": {"num_predict": 64, "temperature": 0}
}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["response"])'
```
成功の目安（設計書7.1 #1）: テンプレートに `Suffix` がある。返るのが `fib` の本体だけで、説明文や `print(fib(10))` の繰り返しが混ざらない。

**5. GB10: 両方を載せてメモリを確かめる**
```bash
ollama ps                                     # :11434 に qwen3-coder-next
OLLAMA_HOST=127.0.0.1:4000 ollama ps          # :4000 に qwen2.5-coder
free -h
```
成功の目安（#2）: どちらの `PROCESSOR` 列も `100% GPU`。`free -h` の Swap の used が作業前から増えていない。エージェント側が載っていなければ、先に Codex から1回要求を出して載せてから確かめる。

**6. GB10 / Windows: 応答時間を測る**
Windows のリポジトリから（LAN の遅れも含めて測る）:
```powershell
.\myvenv313\Scripts\python.exe -m scripts.measure_autocomplete --url http://<GB10のIP>:4000
```
GB10 上で測る場合は `scripts/measure_autocomplete.py` をファイル1つだけ持っていき `python3 measure_autocomplete.py` で動く（標準ライブラリだけで書いてある）。
出力の読み方（同時1本と4本の2ブロック、`往復時間` の p90 と「判定」行）、終了コード（失敗が1件でもあれば 1）を書く。
互いに邪魔しないことの確認（#3）: Codex に長い作業をさせている最中に `--concurrency 1` で測り、何もしていないときの値と比べる。
同時に使えることの確認（#4）: 4本同時のブロックで失敗 0。
7B を試す手順: `OLLAMA_HOST=127.0.0.1:4000 ollama pull qwen2.5-coder:7b-base` → `--model qwen2.5-coder:7b-base` で測る（`:4000` は `OLLAMA_MAX_LOADED_MODELS=1` なので 1.5B と入れ替わる）→ 4本同時の p90 が 500ms 以下なら `config.yaml` の `model` と `name` を 7B に替える。以下ならなければ 1.5B に戻す（1.5B で1回要求を出せば入れ替わる）。500ms は体感の目安で、使ってみて改めてよいと書く。
成功の目安: 4本同時で失敗 0、判定が「目安内」。

**7. Windows: Continue を入れる**
- VS Code の拡張機能で「Continue」（発行元 Continue）を入れる。
- **サインインしない。** Hub にもつながない。
- `settings.json`（ユーザー設定）に `"continue.telemetryEnabled": false` を足す。
- 雛形 [continue-config.yaml](continue-config.yaml) を `%USERPROFILE%\.continue\config.yaml` に置き（既存があれば退避してから）、`<GB10のIP>` を置き換える。
- VS Code を完全に終了して起動し直す（拡張の入れ替えは Reload Window では反映しきらない）。
成功の目安（#5, #6）: Python のファイルで関数を書きかけると灰色の候補が出て、Tab で確定できる。VS Code の出力パネルで Continue のログを選び、要求先が `http://<GB10のIP>:4000` であることを確かめる（ログのチャンネル名は Continue の版で変わりうるので、見つからなければ出力パネルの一覧から Continue を含むものを選ぶ）。`continue.telemetryEnabled` が `false` である。

**8. 何がどこへ流れるか**
設計書8節の5番をそのまま（カーソル前後のコードと Continue が足すコード片が社内LANの平文 HTTP で GB10 に届く。外に出うるのはテレメトリだけで、7節で切る。認証は無く `:11434` と同じ条件）。

**元に戻す** — 設計書9節の4手順をコマンド付きで:
```bash
sudo systemctl disable --now ollama-autocomplete
sudo rm /etc/systemd/system/ollama-autocomplete.service
sudo systemctl daemon-reload
sudo ufw delete allow from <社内LANのサブネット> to any port 4000 proto tcp
ollama rm qwen2.5-coder:1.5b-base            # 置き場所を共有しているので :11434 経由で消せる
```
Windows 側は Continue をアンインストールし、`%USERPROFILE%\.continue` を消す。`:11434` には手を入れていないので他に戻すものは無い、と書く。

**つまずきやすいところ** — 表（症状・原因・対処）。少なくとも次の行:
|灰色の候補が出ない|`modelTimeout` が短く、LAN 越しの応答が間に合わず捨てられている／`apiBase` の誤り|`curl.exe` で 4000 番に届くか確かめる。`modelTimeout` を上げる。6節の往復時間と比べる|
|`HTTP 404: model '…' not found`|`:4000` 側でモデルを取得していない、または `OLLAMA_MODELS` が `ollama.service` と違う|4節の `pull`。1節で確かめた値をユニットに書く|
|候補に説明文が混ざる、後ろのコードを繰り返す|instruct 版を指定している、またはテンプレートに `Suffix` が無い|`-base` のタグを使う。4節の `ollama show --template`|
|`ollama-autocomplete` が起動しない（`address already in use`）|4000 番を他が使っている|1節の `ss`。止められなければ設計に戻ってポートを決め直す|
|`permission denied`（モデルの置き場所）|`User=` が `ollama.service` と違う|1節で確かめた `User=` に揃える|
|GB10 の再起動後に qwen3-coder-next が `100% GPU` にならない|2つの Ollama が互いのメモリ使用量を知らない|`sudo systemctl stop ollama-autocomplete` → Codex から1回要求してエージェント側を載せる → `start`。5節で確かめ直す|

**出典** — 設計書の出典2件に加え、`qwen2.5-coder` の Ollama ライブラリページ（https://ollama.com/library/qwen2.5-coder）。

- [ ] **Step 3: 既存の手順書に追記する**

`docs/qwen/ollama-gb10-qwen3-coder-next.md` の「## 5. GB10: 常駐させ、2つ目を載せない」の節の末尾（次の `## 6.` の直前）に足す:

```markdown
> **補完用の Ollama を併設する場合:** タブ補完のために別の Ollama を `:4000` で
> 立てる手順は [GB10のOllamaにタブ補完用のQwenを併設する](ollama-gb10-autocomplete.md)
> にある。この節の `OLLAMA_MAX_LOADED_MODELS=1` と `OLLAMA_KEEP_ALIVE=-1` は
> `:11434` の Ollama にだけ効くので、併設しても変えなくてよい。
```

- [ ] **Step 4: リンク先と Review Focus の記述を確かめる**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import re, pathlib; d = pathlib.Path('docs/qwen'); t = (d / 'ollama-gb10-autocomplete.md').read_text(encoding='utf-8'); bad = [l for l in re.findall(r'\]\(([^)#]+?)(?:#[^)]*)?\)', t) if not l.startswith('http') and not (d / l).exists()]; print('broken:', bad); [print(k, k in t) for k in ('modelTimeout', 'telemetryEnabled', '未検証である', '成功の目安', '元に戻す', 'つまずきやすいところ', '出典', 'scripts.measure_autocomplete')]"
```
Expected: `broken: []`、続く8行がすべて `True`

- [ ] **Step 5: コミット**

```bash
git add docs/qwen/ollama-gb10-autocomplete.md docs/qwen/ollama-gb10-qwen3-coder-next.md
git commit -m "docs: add the procedure for tab autocomplete on the GB10"
```

---

### Task 4: 最終確認

- [ ] **Step 1: 全テスト**

Run: `.\myvenv313\Scripts\python.exe -m pytest -q`
Expected: 失敗 0

- [ ] **Step 2: 実機で確かめていないことを報告に書く**

設計書7.1 の #1〜#6 は GB10 と Windows の実機が要り、この作業環境では実行できない。報告では「手順書・雛形・計測スクリプトを作った。実機での確認は未実施」と区別して書く。
