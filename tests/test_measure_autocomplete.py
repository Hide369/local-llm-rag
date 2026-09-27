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


class _Handler(BaseHTTPRequestHandler):
    """テストごとに server.reply（status, body, delay_s）で応答を決める。"""

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        status, body, delay_s = self.server.reply
        time.sleep(delay_s)
        if isinstance(body, bytes):
            data = body
        elif isinstance(body, str):
            data = body.encode()
        else:
            data = json.dumps(body).encode()
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


class _TruncatingHandler(BaseHTTPRequestHandler):
    """Content-Length より短い本文を送って接続を閉じる（途中で切れた応答）。"""

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "1000")
        self.end_headers()
        self.wfile.write(b'{"total_duration": 1')
        self.close_connection = True

    def log_message(self, *args):
        pass


@pytest.fixture
def truncating_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _TruncatingHandler)
    httpd.status = 200
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


@pytest.mark.parametrize(
    ("status", "prefix"),
    [(200, "接続できない"), (500, "HTTP 500: 本文を読めない")],
)
def test_send_reports_truncated_response_as_failure(truncating_server, status, prefix):
    truncating_server.status = status
    result = measure.send(_url(truncating_server), measure.fim_payload("m", 0), timeout_s=5)
    assert isinstance(result, measure.Failure)
    assert result.reason.startswith(prefix)


def test_send_reports_non_utf8_body(server):
    server.reply = (200, b'{"response": "\x80"}', 0.0)  # UTF-8 として不正なバイト
    result = measure.send(_url(server), measure.fim_payload("m", 0), timeout_s=5)
    assert isinstance(result, measure.Failure)
    assert result.reason.startswith("応答が JSON でない")
