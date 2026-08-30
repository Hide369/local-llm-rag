"""リランカーの単体テスト。実モデル（570MB）は integration マーカーの2本だけで使う。

パディングとマスクの検証は純粋関数 _feed() に対して行う。トークナイザもONNXも
要らないため、ネットワークもモデルも無しで境界条件を正確に突ける。

rerank() 側のテストは _build_session と _build_tokenizer の**両方**を差し替える。
どちらか一方でも実物が残ると、単体テストがモデルの取得を伴ってしまう。
差し替えに monkeypatch を使うのは、モジュール属性への素の代入だと後続のテストへ
漏れるため。autouse の reset_session() は _session / _tokenizer しか戻さない。
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import ingest.reranker as reranker_module
from ingest.reranker import (
    INTRA_OP_THREADS,
    MAX_LENGTH,
    PAD_ID,
    RerankError,
    _feed,
    rerank,
    reset_session,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


class _Encoding:
    """tokenizers.Encoding のうち _feed() が使う2つの属性だけを持つ。"""

    def __init__(self, ids):
        self.ids = ids
        self.attention_mask = [1] * len(ids)


class _FakeTokenizer:
    def __init__(self, lengths):
        self._lengths = list(lengths)
        self.calls = []

    def encode(self, query, text):
        self.calls.append((query, text))
        return _Encoding(list(range(2, 2 + self._lengths.pop(0))))


class _FakeSession:
    """run() に渡された入力を記録し、決め打ちのロジットを返す偽のONNXセッション。"""

    def __init__(self, logits=None):
        self.calls = []
        self._logits = logits

    def run(self, _output_names, feed):
        self.calls.append(feed)
        rows = len(feed["input_ids"])
        values = self._logits if self._logits is not None else list(range(rows))
        return [np.array(values[:rows], dtype=np.float32).reshape(rows, 1)]


@pytest.fixture(autouse=True)
def _clean_session():
    reset_session()
    yield
    reset_session()


@pytest.fixture
def stub(monkeypatch):
    """_build_session と _build_tokenizer をまとめて差し替える。"""

    def _stub(token_lengths, logits=None):
        session = _FakeSession(logits)
        tokenizer = _FakeTokenizer(token_lengths)
        monkeypatch.setattr(reranker_module, "_build_session", lambda: session)
        monkeypatch.setattr(reranker_module, "_build_tokenizer", lambda: tokenizer)
        return session, tokenizer

    return _stub


# --- _feed(): パディングとマスク（純粋関数。モデルもトークナイザも不要） ---


def test_feed_pads_to_the_longest_row_not_to_max_length():
    """固定512だと計算の6割以上が無駄になる。実測3.6倍の差（spec 3.2節）。"""
    feed = _feed([_Encoding([5, 6, 7]), _Encoding([8, 9])])
    assert feed["input_ids"].shape == (2, 3)
    assert feed["input_ids"].shape[1] < MAX_LENGTH


def test_feed_pads_short_rows_with_pad_id_and_masks_them():
    feed = _feed([_Encoding([5, 6, 7]), _Encoding([8])])
    assert feed["input_ids"][1].tolist() == [8, PAD_ID, PAD_ID]
    assert feed["attention_mask"][1].tolist() == [1, 0, 0]


def test_feed_keeps_the_longest_row_fully_masked_in():
    feed = _feed([_Encoding([5, 6, 7]), _Encoding([8])])
    assert feed["attention_mask"][0].tolist() == [1, 1, 1]


def test_feed_uses_int64_as_the_model_expects():
    """モデルの入力は tensor(int64)。int32を渡すと実行時に落ちる。"""
    feed = _feed([_Encoding([5, 6])])
    assert feed["input_ids"].dtype == np.int64
    assert feed["attention_mask"].dtype == np.int64


# --- rerank(): スコアの並びと失敗の扱い ---


def test_scores_follow_the_order_of_the_given_texts(stub):
    """スコアは texts と同じ並びで返る。取り違えると順位が丸ごと壊れる。"""
    stub([10, 10, 10], logits=[2.5, -1.0, 0.5])
    assert rerank("質問", ["A", "B", "C"]) == pytest.approx([2.5, -1.0, 0.5])


def test_every_text_is_paired_with_the_query(stub):
    _, tokenizer = stub([10, 10])
    rerank("この質問", ["本文A", "本文B"])
    assert tokenizer.calls == [("この質問", "本文A"), ("この質問", "本文B")]


def test_empty_texts_returns_empty_without_building_anything(monkeypatch):
    """候補0件の呼び出しで570MBのロードを起こさない。"""
    calls = []
    monkeypatch.setattr(
        reranker_module, "_build_session", lambda: calls.append("session")
    )
    monkeypatch.setattr(
        reranker_module, "_build_tokenizer", lambda: calls.append("tokenizer")
    )
    assert rerank("質問", []) == []
    assert calls == []


def test_the_session_is_built_only_once(monkeypatch):
    """570MBのロードを毎回やらない。"""
    calls = []

    def _build():
        calls.append(1)
        return _FakeSession()

    monkeypatch.setattr(reranker_module, "_build_session", _build)
    monkeypatch.setattr(
        reranker_module, "_build_tokenizer", lambda: _FakeTokenizer([10, 10])
    )
    rerank("質問", ["本文"])
    rerank("質問", ["本文"])
    assert len(calls) == 1


def test_a_failing_session_raises_rerank_error(monkeypatch):
    """ONNXの失敗はRerankErrorに包む。retrieval側がこれを捕まえて劣化させる。"""

    class _Broken:
        def run(self, *_args, **_kwargs):
            raise RuntimeError("onnx exploded")

    monkeypatch.setattr(reranker_module, "_build_session", lambda: _Broken())
    monkeypatch.setattr(
        reranker_module, "_build_tokenizer", lambda: _FakeTokenizer([10])
    )
    with pytest.raises(RerankError):
        rerank("質問", ["本文"])


def test_a_failing_session_build_raises_rerank_error(monkeypatch):
    """初回ビルドの失敗も RerankError に包む。ここを外すと search() をすり抜けて
    画面に生のトレースバックが出る（spec 6.3）。"""

    def _explode():
        raise OSError("model file is corrupt")

    monkeypatch.setattr(reranker_module, "_build_session", _explode)
    monkeypatch.setattr(
        reranker_module, "_build_tokenizer", lambda: _FakeTokenizer([10])
    )
    with pytest.raises(RerankError):
        rerank("質問", ["本文"])


def test_a_failing_tokenizer_build_raises_rerank_error(monkeypatch):
    def _explode():
        raise OSError("tokenizer.json is unreadable")

    monkeypatch.setattr(reranker_module, "_build_session", lambda: _FakeSession())
    monkeypatch.setattr(reranker_module, "_build_tokenizer", _explode)
    with pytest.raises(RerankError):
        rerank("質問", ["本文"])


def test_a_bug_in_feed_is_not_disguised_as_a_model_failure(monkeypatch):
    """純粋計算の失敗を RerankError に包まない。包むと実装ミスが「モデルが
    使えない」と誤報告され、RRF順への劣化が恒久化して原因が隠れる。"""
    monkeypatch.setattr(reranker_module, "_build_session", lambda: _FakeSession())
    monkeypatch.setattr(
        reranker_module, "_build_tokenizer", lambda: _FakeTokenizer([10])
    )

    def _broken_feed(_encodings):
        raise KeyError("input_id")

    monkeypatch.setattr(reranker_module, "_feed", _broken_feed)
    with pytest.raises(KeyError):
        rerank("質問", ["本文"])


# --- 定数と遅延生成 ---


def test_threads_are_eight():
    """i5-1240PでPコアだけを使い切る値。既定16論理コアより1.26倍速い（spec 3.3節）。"""
    assert INTRA_OP_THREADS == 8


def test_onnxruntime_is_not_imported_at_module_import_time():
    """遅延生成の回帰検知。ingest/ocr.py の同名テストと同じ手法。

    同一プロセス内で _session is None を見ても、autouseフィクスチャが毎回
    reset_session() を呼ぶため常に真になり検証にならない。別プロセスで
    import 直後の sys.modules を見る。
    """
    script = (
        "import sys\n"
        "import ingest.reranker\n"
        "assert 'onnxruntime' not in sys.modules, "
        "'onnxruntime was imported at ingest.reranker import time'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr


# --- 実モデル ---


@pytest.mark.integration
def test_the_real_model_ranks_a_relevant_text_above_an_unrelated_one():
    """実機確認。初回は570MBのダウンロードが走る。"""
    relevant = (
        "1-6. 生成AI活用のポイント\n"
        "RAGやファインチューニングを活用することで、ある程度回避することが可能。"
        "事前学習済モデルに追加学習させ、LLMを再生成する"
    )
    unrelated = "第38条 年次有給休暇は、雇入れの日から6か月間継続勤務した労働者に対して付与する"
    scores = rerank("ファインチューニングについて教えてほしい", [relevant, unrelated])
    assert scores[0] > scores[1]


@pytest.mark.integration
def test_the_real_tokenizer_truncates_to_max_length():
    """将来CHUNK_SIZEを上げたときの安全弁。実データ（最大380トークン）では発動しない。

    切り詰めは実物のトークナイザの設定なので、偽物では検証にならない。
    """
    tokenizer = reranker_module._build_tokenizer()
    assert len(tokenizer.encode("質問", "あ" * 5000).ids) <= MAX_LENGTH
