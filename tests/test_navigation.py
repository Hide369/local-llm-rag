"""ナビゲーション用スライドの判定。

捕まえるものより、捕まえてはいけないものを重く見る。規則を緩めると
本文が消えるが、規則が当たらなくなっても消えるものは無いためである。
"""
from ingest.models import SLIDE, ParsedUnit
from ingest.navigation import drop_navigation, is_navigation


# --- 落とすもの（実コーパスから採取） ---

def test_a_section_divider_is_navigation():
    """回帰ケースで1位を取っていた章扉。"""
    assert is_navigation("3\n転移学習とファインチューニング")


def test_a_section_divider_wrapped_over_two_lines_is_navigation():
    """見出しが2行に折り返されていても章扉である。"""
    assert is_navigation("2\nローカルLLMを活用した\n検索精度を上げる仕組み")


def test_a_table_of_contents_is_navigation():
    """回帰ケースで3位を取っていた目次スライド。"""
    assert is_navigation("－ 目次 ー\nRAGの基礎知識\n1\nローカルLLMを活用した検索精度を上げる仕組み\n2")


def test_a_table_of_contents_with_a_different_dash_is_navigation():
    """資料によって末尾の記号が異なる（ー と－）。先頭行に含まれるかで見る。"""
    assert is_navigation("－ 目次 －\n1\nニューラルネットワークの基礎知識\n2")


def test_a_closing_slide_is_navigation():
    assert is_navigation("ご清聴ありがとうございました\nAIとともに、新しい働き方を始めよう")


# --- 落としてはいけないもの（規則の境界） ---

def test_a_cover_page_padded_with_blank_lines_is_not_navigation():
    """モデル就業規則.pdf の表紙。

    先頭が全角の「１」で str.isdigit() は真になる。章扉と分けているのは
    生の行数だけである（表紙19行、本物の章扉は2〜3行）。版数を尋ねる質問に
    必要なので落としてはならない。
    """
    cover = "１ \n \n \n \n \n \n \n \nモデル就業規則 \n \n \n \n \n \n \n \n \n令和７年12 月版 "
    assert not is_navigation(cover)


def test_a_run_of_page_numbers_is_not_navigation():
    """モデル就業規則.pdf 34ページ由来。数字だけの行が続く。

    3行に切り詰めてあるのは、生の行数ガード（4行以下）ではなく数字連続ガードが
    効いていることを確かめるため。原文の長さのままだと行数ガードだけで False に
    なり、数字連続ガードを消してもこのテストは通ってしまう（実行で確認）。
    """
    assert not is_navigation("17\n18\n19")


def test_body_text_that_mentions_a_table_of_contents_is_not_navigation():
    """Claude_Code_法人導入ガイド_スライド.pdf 13ページ由来の断片。

    787字が1行で、560文字目に「目次」が現れる。先頭行の長さで弾く。
    """
    body = "ける 日命名ルールが競ーされているか ロヘッダー・フツタ一・目次の除去 口文断が切れない位置て分割されているか"
    assert not is_navigation(body)


def test_a_short_body_fragment_is_not_navigation():
    """40字以下の本文断片は実在する。長さ単独では判定できない。"""
    assert not is_navigation("。 横展開：コア構成はそのまま")


def test_a_numbered_list_of_content_is_not_navigation():
    """先頭が数字でも、数字の行が続くものは章扉ではない。"""
    assert not is_navigation("1\n最初の項目\n2\n次の項目")


def test_empty_text_is_not_navigation():
    assert not is_navigation("")
    assert not is_navigation("   \n  \n ")


def _slide(text, location):
    return ParsedUnit(text=text, location_type=SLIDE, location=location)


def test_drop_navigation_separates_the_two_groups():
    units = [
        _slide("－ 目次 ー\nRAGの基礎知識\n1", 4),
        _slide("1\nRAGの基礎知識", 5),
        _slide("RAGは検索した文書を根拠にして回答を組み立てる仕組みである。", 6),
        _slide("ご清聴ありがとうございました\nAIとともに、新しい働き方を始めよう", 30),
    ]
    kept, dropped = drop_navigation(units)
    assert [unit.location for unit in kept] == [6]
    assert [unit.location for unit in dropped] == [4, 5, 30]


def test_drop_navigation_keeps_the_original_order():
    """出典の位置は location が持つが、並びが崩れると差分が読みにくくなる。"""
    units = [_slide(f"本文{n}", n) for n in (3, 1, 2)]
    kept, _ = drop_navigation(units)
    assert [unit.location for unit in kept] == [3, 1, 2]


def test_drop_navigation_returns_every_unit_when_none_is_navigation():
    units = [_slide("本文です。これは中身のあるスライドである。", 1)]
    kept, dropped = drop_navigation(units)
    assert kept == units
    assert dropped == []


def test_drop_navigation_does_not_decide_what_to_do_when_everything_drops():
    """全部落ちる場合の判断は呼び出し側に任せる。

    ここで握り潰すと、規則が誤爆して資料が丸ごと消えたことに誰も気づけない。
    scripts/ingest_source.py がこの場合に何も落とさず警告を出す。
    """
    units = [_slide("1\nRAGの基礎知識", 5), _slide("2\n導入手順", 9)]
    kept, dropped = drop_navigation(units)
    assert kept == []
    assert dropped == units
