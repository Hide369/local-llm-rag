"""bge-reranker-v2-m3 (ONNX INT8) で質問とチャンクの関連度を測る。

design: docs/superpowers/specs/2026-08-30-reranker-design.md

クロスエンコーダなので、質問とチャンクを1ペアずつ丸ごとモデルに通す。ベクトル検索の
ように事前計算が効かず、候補数だけ順伝播が要る。そのぶん中身を突き合わせた判断が
できるのがRRFとの違いである。

このモジュールはスコアを返すだけで、並べ替えも件数の絞り込みもしない。順位の決定は
ingest/retrieval.py に集約する（ingest/lexical.py が (id, score) を返すだけで
採否に関与しないのと同じ分担）。

ChromaDBにもOllamaにも依存しない。
"""
import numpy as np

MODEL_REPO = "onnx-community/bge-reranker-v2-m3-ONNX"
MODEL_FILE = "onnx/model_int8.onnx"
TOKENIZER_FILE = "tokenizer.json"

# XLM-RoBERTaのパディングトークンID。モデルを差し替えるときは必ず確認すること。
# 値を間違えると例外は出ないが、パディング部分が実トークンとして扱われスコアが濁る。
PAD_ID = 1

# 切り詰めの上限。実データのチャンクは最大380トークン（spec 3.2節）なので発動
# しないが、将来 CHUNK_SIZE を上げたときの安全弁として残す。
MAX_LENGTH = 512

# i5-1240P（Pコア4＋Eコア8）での実測（spec 3.3節）。既定の16論理コアはEコアを
# 巻き込んで遅くなる。8 = Pコアだけを使い切る値で、既定より1.26倍速い。
# CPUを変えたらこの値は変わる。実測せずに引き継がないこと。
INTRA_OP_THREADS = 8

_session = None
_tokenizer = None


class RerankError(Exception):
    """関連度スコアの取得に失敗した。"""


def _model_paths():
    """モデルとトークナイザをHFの既定キャッシュから取る（無ければダウンロード）。"""
    from huggingface_hub import hf_hub_download

    return (
        hf_hub_download(MODEL_REPO, MODEL_FILE),
        hf_hub_download(MODEL_REPO, TOKENIZER_FILE),
    )


def _build_session():
    """ONNXセッションを生成する。テストではここを差し替える。

    import を関数の中に置くのは、onnxruntime のロードだけで数百msかかるため。
    リランカーを使わない経路（取り込みCLI、条件絞り込みで答える質問）にこの
    コストを持ち込まない。ingest/ocr.py と同じ方針。
    """
    import onnxruntime as ort

    model_path, _ = _model_paths()
    options = ort.SessionOptions()
    options.intra_op_num_threads = INTRA_OP_THREADS
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(model_path, options, providers=["CPUExecutionProvider"])


def _build_tokenizer():
    from tokenizers import Tokenizer

    _, tokenizer_path = _model_paths()
    tokenizer = Tokenizer.from_file(tokenizer_path)
    tokenizer.enable_truncation(max_length=MAX_LENGTH)
    # パディングは _feed() が自前で行う。バッチ内最長に合わせるため、
    # トークナイザ側の固定長パディングは使わない。
    tokenizer.no_padding()
    return tokenizer


def reset_session() -> None:
    """生成済みのセッションとトークナイザを破棄する（主にテスト用）。"""
    global _session, _tokenizer
    _session = None
    _tokenizer = None


def _feed(encodings):
    """バッチ内の最長に合わせてパディングした入力を作る。

    固定512パディングだと計算の6割以上が無駄になる。実チャンクは中央値111・
    最大380トークンで、動的パディングは実測3.6倍速い（spec 3.2節）。
    """
    longest = max(len(e.ids) for e in encodings)
    ids = np.full((len(encodings), longest), PAD_ID, dtype=np.int64)
    mask = np.zeros((len(encodings), longest), dtype=np.int64)
    for row, encoding in enumerate(encodings):
        ids[row, : len(encoding.ids)] = encoding.ids
        mask[row, : len(encoding.ids)] = encoding.attention_mask
    return {"input_ids": ids, "attention_mask": mask}


def rerank(query: str, texts: list[str]) -> list[float]:
    """(query, text) の関連度スコアを texts と同じ並びで返す。

    返すのは生のロジットである。並べ替えには単調増加のシグモイドを通しても
    順位が変わらないため、正規化は表示側（ingest/prompting.py）に任せる。
    """
    if not texts:
        return []
    global _session, _tokenizer
    # モデルの用意（ダウンロード・ONNXロード・トークナイザ構築）と、トークン化までを
    # 外部要因の失敗とみなす。初回呼び出しのここが最も失敗しやすく、しかも
    # spec 6.3 の「増幅器であって関門ではない」が最も要る場面である。包まずに
    # 生の例外を出すと search() をすり抜けて画面にトレースバックが出る。
    try:
        if _session is None:
            _session = _build_session()
        if _tokenizer is None:
            _tokenizer = _build_tokenizer()
        encodings = [_tokenizer.encode(query, text) for text in texts]
    except Exception as error:
        raise RerankError(f"リランカーを準備できませんでした: {error}") from error

    # _feed は外部依存のない純粋な計算なので、包まない。ここで落ちるのは実装の
    # 誤りであり、RerankError にすると「モデルが使えない」と誤って報告されて
    # RRF順への劣化が恒久化し、原因が隠れる。
    feed = _feed(encodings)

    try:
        logits = _session.run(None, feed)[0]
    except Exception as error:
        raise RerankError(f"関連度スコアの計算に失敗しました: {error}") from error
    return [float(value) for value in np.asarray(logits).ravel()]


def check_reranker() -> None:
    """モデルが手元にあるか確認する（無ければここでダウンロードする）。

    質問の途中で無言で止まるのを避けるため、UIで有効にした時点で呼ぶ。
    embedder.check_ollama() / vlm.check_vlm() と同じ役割。
    """
    try:
        _model_paths()
    except Exception as error:
        raise RerankError(
            f"リランカーのモデルを取得できません（{MODEL_REPO}）: {error}"
        ) from error
