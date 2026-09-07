"""検索の答えになる中身を持たないスライドを見分ける。

目次・章扉・締めのスライドは短くキーワード密度が高いため BM25 がこれを好むが、
中身が無いので上位に来ても質問に答えられない。取り込み時に落とす。

**規則は日本語のセミナー資料の書式に強く結び付いている。** 英語資料や別テンプレート
のスライドを入れれば、規則が当たらなくなって取りこぼす側に倒れる。ただし
「本文を誤って捨てる事故は起きない」わけではない。次のものは実行で確認した誤検出で、
いずれも落ちてしまう。

- 先頭が数字だけの行で始まる短い本文（「38\\n年次有給休暇は、雇入れの日から…」）
- 「目次」で始まる10字以下の見出しを持つ本文（「目次の作り方\\nWord では…」）
- 丸数字で始まる本文（「①\\n転移学習の概要…」。'①'.isdigit() は真である）

本文を実際に守っているのは _MAX_DIVIDER_LINES（生の行数）である。
モデル就業規則.pdf は1〜9ページすべてが「先頭の内容行が数字のみ」になる。
PDFのページ番号が本文の先頭に来るためで、9ページとも普通の本文でありながら、
生の行数（16〜38行）だけで生き残っている（2026-09-07、この1ファイルを単体で
パースして確認。94ユニット中9件）。この限界は設計書2.4節に挙げてあり、
tests/test_navigation.py が現状の挙動をそのまま表明している。

規則はすべて実コーパス608出現（2026-09-06、セミナー資料7本を含む44ファイル）に
当てて、誤検出ゼロ・取りこぼしゼロを確認している。内訳は章扉24・目次7・締め7。
"""

from ingest.models import ParsedUnit

# 章扉の生の行数（空行を含む）の上限。
# モデル就業規則.pdf の表紙は先頭が全角の「１」で str.isdigit() が真になるが、
# タイトルが空行に挟まれて生の行数が19行ある。本物の章扉は2〜3行しかない。
# 「空行の詰め物があるものは章扉ではない」がこの上限の意味である。
#
# この上限は表紙1枚のためのものではない。モデル就業規則.pdf は1〜9ページ
# すべてが「先頭の内容行が数字のみ」であり（PDFのページ番号が本文の先頭に
# 来るため）、9ページとも生の行数（16〜38行）だけで本文として残っている。
# 値を上げると9ページ分の本文が黙って消える。
_MAX_DIVIDER_LINES = 4

# 目次スライドの先頭行の長さの上限。「－ 目次 ー」は7字。
# 本文中で目次に言及しているだけのチャンク（Claude_Code_法人導入ガイド_スライド.pdf
# 13ページ、787字が1行で560文字目に「目次」）を弾く。
_MAX_TOC_HEADING_CHARS = 10

_CLOSING_PREFIX = "ご清聴"

# 締めスライドの本文全体の長さの上限。
# 実コーパスの締めスライドは33字（「ご清聴ありがとうございました\nAIとともに、
# 新しい働き方を始めよう」、設計書1.1節）。接頭辞だけで見ていると
# 「ご清聴ありがとうございました。続いて質疑応答に移ります。Q: …」のように
# 締めの挨拶で始まって中身が続く本文まで落ちる（実行で確認、69字）。
# 実測33字のほぼ倍を上限に置き、これを超えるものは締めではなく本文とみなす。
# 挨拶1行＋短い1行という締めスライドの形からすると、27字の余裕は
# もう1行ぶんに相当する。
_MAX_CLOSING_CHARS = 60


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
    """「ご清聴ありがとうございました」のような締めスライドか。

    長さの上限があるのは、締めの挨拶で始まって中身が続く本文を残すためである。
    上限より短ければ中身があっても落ちる点は変わらない（既知の限界）。
    """
    stripped = text.strip()
    return (
        stripped.startswith(_CLOSING_PREFIX) and len(stripped) <= _MAX_CLOSING_CHARS
    )


def is_navigation(text: str) -> bool:
    """検索の答えになる中身を持たないスライドか。"""
    return (
        _is_section_divider(text)
        or _is_table_of_contents(text)
        or _is_closing(text)
    )


def drop_navigation(
    units: list[ParsedUnit],
) -> tuple[list[ParsedUnit], list[ParsedUnit]]:
    """残すユニットと、落としたユニットを (残す, 落とす) の順で返す。

    落としたものを件数ではなく現物で返すのは、呼び出し側が「何を」落としたか
    報告できるようにするためである。件数だけでは、誤検出が起きたときに何が
    消えたのか追えない。

    全ユニットが落ちる場合の判断はここでは行わない。握り潰すと、資料が丸ごと
    DBから消えたことに誰も気づけない。scripts/ingest_source.py がこの場合に
    何も落とさず警告を出す。
    """
    kept: list[ParsedUnit] = []
    dropped: list[ParsedUnit] = []
    for unit in units:
        target = dropped if is_navigation(unit.text) else kept
        target.append(unit)
    return kept, dropped
