"""HTMLの取り込み。

この形式の要点は「本文はタグの隙間にしかない」ことである。生のまま入れると
検索語がマークアップに埋もれ、script/style の中身まで埋め込まれてしまう。
txt と同じく文書全体を1ユニットにし、分割は chunk_units に一任する。
"""
from ingest.models import DOCUMENT
from ingest.parsers import SUPPORTED_SUFFIXES, parse
from ingest.parsers.html_parser import parse_html


def test_tags_are_stripped_and_the_whole_file_is_one_unit(tmp_path):
    """HTMLに書き手が引いた「ページ」の境界は無い。txtと同じ判断で1ユニットにする。"""
    path = tmp_path / "手順書.html"
    path.write_text(
        "<html><body><h1>入館手順</h1><p>受付で<b>社員証</b>を提示する。</p></body></html>",
        encoding="utf-8",
    )

    units = parse_html(path)

    assert len(units) == 1
    assert units[0].location_type == DOCUMENT
    assert "入館手順" in units[0].text
    assert "社員証を提示する。" in units[0].text
    assert "<b>" not in units[0].text


def test_script_and_style_contents_are_dropped(tmp_path):
    """JSとCSSは資料の中身ではない。

    残すと埋め込みベクトルがマークアップ側へ引っ張られ、検索の役に立たない
    チャンクがDBに残る。
    """
    path = tmp_path / "規程.html"
    path.write_text(
        "<html><head><style>body{color:red}</style>"
        "<script>var secret = 'analytics';</script></head>"
        "<body><p>年次有給休暇の付与日数</p></body></html>",
        encoding="utf-8",
    )

    text = parse_html(path)[0].text

    assert "年次有給休暇の付与日数" in text
    assert "color" not in text
    assert "analytics" not in text


def test_block_elements_do_not_run_words_together(tmp_path):
    """ブロックの境目に改行を入れないと、別の段落の語が1語に化ける。

    '第1条' と '第2条' が '第1条第2条' になると、どちらの語でも引けなくなる。
    """
    path = tmp_path / "条文.html"
    path.write_text(
        "<html><body><p>第1条</p><p>第2条</p></body></html>", encoding="utf-8"
    )

    text = parse_html(path)[0].text

    assert "第1条第2条" not in text
    assert "第1条" in text
    assert "第2条" in text


def test_table_cells_keep_their_row(tmp_path):
    """セルを改行で並べると、見出し行との対応が復元できなくなる。

    xlsx_parser がセルを ` | `、行を改行でつなぐのと同じ判断である。
    """
    path = tmp_path / "表.html"
    path.write_text(
        "<html><body><table>"
        "<tr><th>区分</th><th>日数</th></tr>"
        "<tr><td>勤続1年</td><td>10日</td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )

    lines = [line for line in parse_html(path)[0].text.splitlines() if line.strip()]

    assert "区分 | 日数" in lines
    assert "勤続1年 | 10日" in lines


def test_source_indentation_does_not_become_blank_lines(tmp_path):
    """HTMLの空白には意味が無い。整形用の字下げと改行をそのまま残すと、
    タグの境目ごとに空行が生まれ、CHUNK_SIZE(800字)を空白で食いつぶす。

    表の行が空行で隔てられると、見た目の並びも本文と変わってしまう。
    """
    path = tmp_path / "字下げ.html"
    path.write_text(
        """<html>
  <body>
    <table>
      <tr><td>6か月</td><td>10日</td></tr>
      <tr><td>1年6か月</td><td>11日</td></tr>
    </table>
  </body>
</html>
""",
        encoding="utf-8",
    )

    assert parse_html(path)[0].text.splitlines() == [
        "6か月 | 10日",
        "1年6か月 | 11日",
    ]


def test_character_references_are_decoded(tmp_path):
    """&amp; のまま残すと、本文の記号がその語ごと引けなくなる。"""
    path = tmp_path / "実体参照.html"
    path.write_text(
        "<html><body><p>研究&amp;開発部&nbsp;所属</p></body></html>", encoding="utf-8"
    )

    text = parse_html(path)[0].text

    assert "研究&開発部" in text
    assert "&amp;" not in text


def test_the_title_is_kept_as_the_first_line(tmp_path):
    """本文の断片だけが検索に当たったとき、何の資料か分からなくなるのを防ぐ。

    md_parser が各ユニットの先頭にH1を1行付けるのと同じ狙いである。
    """
    path = tmp_path / "無題.html"
    path.write_text(
        "<html><head><title>就業規則</title></head>"
        "<body><p>第3条 始業時刻</p></body></html>",
        encoding="utf-8",
    )

    text = parse_html(path)[0].text

    assert text.startswith("就業規則")
    assert "第3条 始業時刻" in text


def test_a_cp932_file_is_read_without_mojibake(tmp_path):
    """社内で保存されたHTMLはCP932のことがある。txtと同じ判定を共有する。"""
    path = tmp_path / "cp932.html"
    path.write_bytes(
        "<html><body><p>安全衛生委員会</p></body></html>".encode("cp932")
    )

    assert "安全衛生委員会" in parse_html(path)[0].text


def test_a_file_without_body_text_produces_no_units(tmp_path):
    """タグしか無いページでユニットを作ると、空のチャンクがDBに残る。"""
    path = tmp_path / "空.html"
    path.write_text(
        "<html><head><script>var a=1;</script></head><body>  </body></html>",
        encoding="utf-8",
    )

    assert parse_html(path) == []


def test_html_and_htm_are_routed_by_the_registry(tmp_path):
    """拡張子の登録を忘れると、source/ に置いても黙って無視される。"""
    assert {".html", ".htm"} <= SUPPORTED_SUFFIXES

    for name in ("登録確認.html", "登録確認.htm"):
        path = tmp_path / name
        path.write_text("<html><body><p>本文</p></body></html>", encoding="utf-8")
        assert parse(path)[0].text == "本文"


def test_caption_image_is_permanently_ignored(tmp_path):
    """HTMLの img は外部ファイルへの参照であり、埋め込み画像ではない。

    caption_image は他パーサーと署名を揃えるためだけに受け取る（恒久的な無視。
    ingest/parsers/__init__.py のモジュールdocstringを参照）。
    """
    path = tmp_path / "画像入り.html"
    path.write_text(
        "<html><body><p>配置図</p><img src='zu.png'></body></html>", encoding="utf-8"
    )

    text = parse_html(path, caption_image=lambda _bytes: "説明")[0].text

    assert "説明" not in text
