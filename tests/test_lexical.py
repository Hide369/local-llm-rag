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
    tokens = lexical.tokenize("いぬ ねこ")
    # 同一セグメント内のbigramは作られる
    assert "いぬ" in tokens
    assert "ねこ" in tokens
    # 境界を跨ぐbigramは作られない
    assert "ぬね" not in tokens


def test_kanji_digits_and_arabic_digits_become_the_same_tokens():
    """「一人暮らし」と「1人暮らし」は同じ語である。

    実データ（2026-09-08、本文512種）では「一人」が37チャンク、「三六協定」が
    5チャンクあり、質問側は算用数字で書かれることが多い。索引側とクエリ側は
    どちらもこの関数を通るため、ここで変換すれば対称性は構造的に保証される。
    本文そのものは書き換えないので、表示は「一人暮らし」のままである。
    """
    assert lexical.tokenize("一人暮らし") == lexical.tokenize("1人暮らし")
    assert lexical.tokenize("三六協定") == lexical.tokenize("36協定")


def test_every_kanji_digit_maps_to_its_arabic_digit():
    """〇と零はどちらも0にする。資料により両方の書き方が現れる。"""
    assert lexical.tokenize("〇一二三四五六七八九") == lexical.tokenize("0123456789")
    assert lexical.tokenize("零") == lexical.tokenize("0")


def test_ten_hundred_and_thousand_are_left_alone():
    """十・百・千は数値として解釈しない。

    実データを測ると、複合数（二十三のような形）は0箇所である一方、「十分」
    （＝じゅうぶん）が21チャンクある（2026-09-08、本文512種）。十を10にすると
    「十分な休憩」が「10分な休憩」になり、所要時間を尋ねた質問に混ざる。
    得るものが無く失うものだけがあるため、単体の漢数字だけを変換する。
    """
    assert lexical.tokenize("十分") != lexical.tokenize("10分")
    assert lexical.tokenize("十分") == lexical.tokenize("十分")


def test_empty_text_produces_no_tokens():
    assert lexical.tokenize("") == []


def test_whitespace_only_text_produces_no_tokens():
    assert lexical.tokenize("  \n  ") == []


def _index():
    """語が一切重ならない3文書。順位の判定を明確にするため。"""
    return lexical.build(
        ["a", "b", "c"],
        ["ファインチューニング", "有給休暇", "洗濯容量"],
    )


def test_the_document_containing_the_term_is_returned():
    assert [doc for doc, _ in lexical.search(_index(), "ファインチューニング", limit=3)] == ["a"]


def test_documents_sharing_no_token_score_nothing():
    """スコア0の文書を返すと、無関係な文書がRRFの順位に紛れ込む。"""
    assert lexical.search(_index(), "天気", limit=3) == []


def test_empty_index_returns_nothing():
    assert lexical.search(lexical.build([], []), "何か", limit=3) == []


def test_a_rare_term_outscores_a_common_one():
    """IDF。全文書に出る語は識別力を持たない。文字bigramの部分一致による
    ノイズを押さえているのもこの項である。"""
    index = lexical.build(["a", "b", "c"], ["共通語 希少語", "共通語", "共通語"])
    rare = dict(lexical.search(index, "希少語", limit=3))["a"]
    common = dict(lexical.search(index, "共通語", limit=3))["a"]
    assert rare > common


def test_a_shorter_document_outscores_a_longer_one():
    """文書長による正規化。同じ1回の出現でも、短い文書のほうが主題である。"""
    index = lexical.build(["short", "long"], ["希少語", "希少語 " + "詰め物 " * 30])
    assert lexical.search(index, "希少語", limit=2)[0][0] == "short"


def test_more_occurrences_score_higher():
    index = lexical.build(["once", "twice"], ["希少語 詰め物", "希少語 希少語"])
    assert lexical.search(index, "希少語", limit=2)[0][0] == "twice"


def test_limit_caps_the_number_of_results():
    index = lexical.build(["a", "b", "c"], ["希少語", "希少語", "希少語"])
    assert len(lexical.search(index, "希少語", limit=2)) == 2


def test_results_are_ordered_deterministically():
    """同点の文書はID順にする。順位が揺れるとRRFの結果が再現しなくなる。"""
    index = lexical.build(["c", "a", "b"], ["希少語", "希少語", "希少語"])
    assert [doc for doc, _ in lexical.search(index, "希少語", limit=3)] == ["a", "b", "c"]
