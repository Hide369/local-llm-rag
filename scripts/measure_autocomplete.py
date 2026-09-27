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
