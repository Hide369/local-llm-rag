"""全文検索(BM25)のための語分割とスコア計算。

形態素解析器を使わないのは、辞書に無い語で分割位置が変わるためである。
「UD-0900i」のような型番や新しい専門用語こそ、この検索が救おうとしている
対象であり、そこで分割が揺れては意味がない。文字bigramは辞書を持たない。

このモジュールはベクトルストアにもOllamaにも依存しない純粋な計算である。
"""
import math
import re
import unicodedata
from dataclasses import dataclass

# Unicode対応の \W で区切る。漢字・かなは語構成文字として残り、空白と約物
# だけが境界になる。区切りを跨いだbigramは作らない（実在しない語で一致するため）。
_BOUNDARY = re.compile(r"\W+", re.UNICODE)

# 漢数字を算用数字に寄せる。索引側とクエリ側がどちらも tokenize を通るため、
# ここに置けば対称性は構造的に保証される。本文そのものは書き換えないので、
# 出典に表示される原文は「一人暮らし」のままである。
#
# 十・百・千は入れない。実データ（2026-09-08、本文512種）を数えると、複合数
# （二十三のような形）は0箇所、漢数字の「第○条」も0件である一方、「十分」
# （＝じゅうぶん）が21チャンクある。十を10にすれば得るものが無いまま
# 「十分な休憩」が所要時間の質問に混ざる。単体の漢数字だけを対象にする。
#
# 〇と零を両方持つのは、資料によってどちらの書き方も現れるためである。
_KANJI_DIGITS = str.maketrans("〇零一二三四五六七八九", "00123456789")


def tokenize(text: str) -> list[str]:
    """NFKC正規化して小文字化し、漢数字を算用数字へ寄せ、文字bigramへ分割する。

    正規化は全角/半角と大文字/小文字の揺れを吸収する。実データには全角の
    「ＲＡＧ」と半角の「RAG」が混在する。漢数字も同じ揺れであり、本文の
    「一人暮らし」を質問側が「1人暮らし」と書くことがある。

    1文字のセグメントはbigramが作れず消滅してしまうため、そのまま1トークンとする。
    """
    normalised = unicodedata.normalize("NFKC", text).lower().translate(_KANJI_DIGITS)
    tokens: list[str] = []
    for segment in _BOUNDARY.split(normalised):
        if not segment:
            continue
        if len(segment) == 1:
            tokens.append(segment)
            continue
        tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens


# Okapi BM25の標準的な値。実データで調整が要るのは ingest/retrieval.py の圏内判定
# （RELEVANCE_THRESHOLD）のほうであり、ここは動かさない。
BM25_K1 = 1.2
BM25_B = 0.75


@dataclass(frozen=True)
class BM25Index:
    """転置索引。ids[i] が i 番目の文書のチャンクIDにあたる。

    ディスクへ永続化しない。DBとファイルで状態が二重管理になると、差分取り込みの
    たびに食い違い、しかも例外が出ないため「検索結果が静かに古くなる」。
    信頼できる情報源は常にDBひとつにする（ingest/store.py と同じ方針）。
    """

    ids: list[str]
    postings: dict[str, dict[int, int]]  # トークン → {文書番号: 出現回数}
    lengths: list[int]
    average_length: float

    @property
    def document_count(self) -> int:
        return len(self.ids)


def build(ids: list[str], texts: list[str]) -> BM25Index:
    postings: dict[str, dict[int, int]] = {}
    lengths: list[int] = []
    for number, text in enumerate(texts):
        tokens = tokenize(text)
        lengths.append(len(tokens))
        for token in tokens:
            counts = postings.setdefault(token, {})
            counts[number] = counts.get(number, 0) + 1
    return BM25Index(
        ids=list(ids),
        postings=postings,
        lengths=lengths,
        # 空のインデックスで0除算しないための1.0。search が先に空を返すため
        # この値が実際に使われることはない。
        average_length=(sum(lengths) / len(lengths)) if lengths else 1.0,
    )


def _idf(index: BM25Index, token: str) -> float:
    frequency = len(index.postings.get(token, {}))
    if frequency == 0:
        return 0.0
    return math.log(
        1 + (index.document_count - frequency + 0.5) / (frequency + 0.5)
    )


def search(index: BM25Index, query: str, limit: int) -> list[tuple[str, float]]:
    """スコアの高い順に (チャンクID, スコア) を返す。

    スコア0の文書は含めない。含めるとRRFの順位に無関係な文書が紛れ込む。
    同点はID順にして並びを決定的にする。順位が揺れるとRRFの結果が再現しない。
    """
    if index.document_count == 0:
        return []
    scores: dict[int, float] = {}
    for token in tokenize(query):
        idf = _idf(index, token)
        if idf == 0.0:
            continue
        for number, frequency in index.postings[token].items():
            length_ratio = index.lengths[number] / index.average_length
            denominator = frequency + BM25_K1 * (1 - BM25_B + BM25_B * length_ratio)
            scores[number] = scores.get(number, 0.0) + (
                idf * frequency * (BM25_K1 + 1) / denominator
            )
    ranked = sorted(scores.items(), key=lambda item: (-item[1], index.ids[item[0]]))
    return [(index.ids[number], score) for number, score in ranked[:limit]]
