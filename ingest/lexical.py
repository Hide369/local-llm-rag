"""全文検索(BM25)のための語分割とスコア計算。

形態素解析器を使わないのは、辞書に無い語で分割位置が変わるためである。
「UD-0900i」のような型番や新しい専門用語こそ、この検索が救おうとしている
対象であり、そこで分割が揺れては意味がない。文字bigramは辞書を持たない。

このモジュールはChromaDBにもOllamaにも依存しない純粋な計算である。
"""
import re
import unicodedata

# Unicode対応の \W で区切る。漢字・かなは語構成文字として残り、空白と約物
# だけが境界になる。区切りを跨いだbigramは作らない（実在しない語で一致するため）。
_BOUNDARY = re.compile(r"\W+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """NFKC正規化して小文字化し、文字bigramへ分割する。

    正規化は全角/半角と大文字/小文字の揺れを吸収する。実データには全角の
    「ＲＡＧ」と半角の「RAG」が混在する。

    1文字のセグメントはbigramが作れず消滅してしまうため、そのまま1トークンとする。
    """
    normalised = unicodedata.normalize("NFKC", text).lower()
    tokens: list[str] = []
    for segment in _BOUNDARY.split(normalised):
        if not segment:
            continue
        if len(segment) == 1:
            tokens.append(segment)
            continue
        tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens
