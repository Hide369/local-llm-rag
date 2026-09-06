"""検索の答えになる中身を持たないスライドを見分ける。

目次・章扉・締めのスライドは短くキーワード密度が高いため BM25 がこれを好むが、
中身が無いので上位に来ても質問に答えられない。取り込み時に落とす。

3つの述語はいずれも、想定外の入力に対しては「検出しない」側に倒れる。英語資料や
別テンプレートのスライドを入れても、規則が当たらなくなるだけで、本文を誤って
捨てる事故は起きない。

規則はすべて実コーパス608出現（2026-09-06、セミナー資料7本を含む44ファイル）に
当てて、誤検出ゼロ・取りこぼしゼロを確認している。内訳は章扉24・目次7・締め7。
"""

# 章扉の生の行数（空行を含む）の上限。
# モデル就業規則.pdf の表紙は先頭が全角の「１」で str.isdigit() が真になるが、
# タイトルが空行に挟まれて生の行数が19行ある。本物の章扉は2〜3行しかない。
# 「空行の詰め物があるものは章扉ではない」がこの上限の意味である。
_MAX_DIVIDER_LINES = 4

# 目次スライドの先頭行の長さの上限。「－ 目次 ー」は7字。
# 本文中で目次に言及しているだけのチャンク（Claude_Code_法人導入ガイド_スライド.pdf
# 13ページ、787字が1行で560文字目に「目次」）を弾く。
_MAX_TOC_HEADING_CHARS = 10

_CLOSING_PREFIX = "ご清聴"


def _content_lines(text: str) -> list[str]:
    return [line.strip() for line in text.strip().split("\n") if line.strip()]


def _is_section_divider(text: str) -> bool:
    """「3\\n転移学習とファインチューニング」のような章扉か。"""
    raw_lines = text.strip().split("\n")
    lines = _content_lines(text)
    if len(raw_lines) > _MAX_DIVIDER_LINES or len(lines) < 2:
        return False
    if not lines[0].isdigit():
        return False
    # ページ番号の羅列（モデル就業規則.pdf 34ページ）を弾く。章扉の2行目以降は
    # 見出しの文字列であり、数字だけの行にはならない。
    return not any(line.isdigit() for line in lines[1:])


def _is_table_of_contents(text: str) -> bool:
    lines = _content_lines(text)
    if not lines:
        return False
    return "目次" in lines[0] and len(lines[0]) <= _MAX_TOC_HEADING_CHARS


def _is_closing(text: str) -> bool:
    return text.strip().startswith(_CLOSING_PREFIX)


def is_navigation(text: str) -> bool:
    """検索の答えになる中身を持たないスライドか。"""
    return (
        _is_section_divider(text)
        or _is_table_of_contents(text)
        or _is_closing(text)
    )
