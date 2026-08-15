"""BM25の語分割とスコア計算。

形態素解析器を使わない理由は spec 5.1 を参照。辞書に無い語（型番・新しい
専門用語）で分割が揺れないことが、この検索の存在意義そのものである。
"""
from ingest import lexical


def test_japanese_text_becomes_character_bigrams():
    assert lexical.tokenize("ファイン") == ["ファ", "ァイ", "イン"]


def test_a_single_character_segment_survives_as_one_token():
    """1文字ではbigramが作れない。落とすとその語で引けなくなる。"""
    assert lexical.tokenize("犬") == ["犬"]


def test_width_and_case_are_normalised():
    """全角で書かれた「ＲＡＧ」と半角の「rag」は同じ語である。"""
    assert lexical.tokenize("ＲＡＧ") == lexical.tokenize("rag")


def test_punctuation_separates_segments():
    """型番のハイフンは境界。クエリと本文で同じ分かれ方をすれば一致する。"""
    assert lexical.tokenize("UD-0900i") == lexical.tokenize("ud 0900i")


def test_bigrams_do_not_cross_a_boundary():
    """区切りを跨いだbigramを作ると、実在しない語で一致してしまう。"""
    assert "犬猫" not in lexical.tokenize("犬 猫")


def test_empty_text_produces_no_tokens():
    assert lexical.tokenize("") == []


def test_whitespace_only_text_produces_no_tokens():
    assert lexical.tokenize("  \n  ") == []
