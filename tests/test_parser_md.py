import pytest

from ingest.parsers import parse
from ingest.parsers.md_parser import parse_md

SAMPLE = """---
model_id: UD-0900i
tags: [IoT, スマホ連携]
---

# UD-0900i IoTコンパクト

## 機種概要

打田電器のUD-0900iは、洗濯容量9キログラムのコンパクトなIoTモデルです。

## 設置情報

- 外形寸法：幅598ミリメートル × 奥行き700ミリメートル
- 本体質量：約73キログラム
"""


def _write(tmp_path, text, name="spec.md", newline="\n"):
    path = tmp_path / name
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return path


@pytest.fixture
def sample(tmp_path):
    return _write(tmp_path, SAMPLE)


def test_each_heading_becomes_one_unit(sample):
    units = parse_md(sample)
    assert [u.heading for u in units] == ["機種概要", "設置情報"]


def test_units_are_numbered_from_one(sample):
    units = parse_md(sample)
    assert [u.location for u in units] == [1, 2]
    assert all(u.location_type == "section" for u in units)


def test_every_unit_carries_the_product_title(sample):
    """見出し単位で引いたときに、どの製品の話か分からなくなるのを防ぐ。"""
    assert all("UD-0900i IoTコンパクト" in u.text for u in parse_md(sample))


def test_heading_text_is_part_of_the_unit_text(sample):
    """『設置情報』という語自体が検索語になるため本文に含める。"""
    assert "設置情報" in parse_md(sample)[1].text


def test_markdown_markers_are_stripped(sample):
    """# 記号は検索に寄与せず、埋め込みのトークンを消費するだけ。"""
    assert all("#" not in u.text for u in parse_md(sample))


def test_frontmatter_is_not_indexed(sample):
    """model_id と product_name はH1前置で行き渡るため、YAMLの生テキストは入れない。"""
    assert all("model_id" not in u.text for u in parse_md(sample))
    assert all("tags" not in u.text for u in parse_md(sample))


def test_crlf_does_not_leak_into_headings(tmp_path):
    """実データ30件はすべてCRLF。放置すると見出しの末尾に復帰文字が残り、
    出典が『＞ 設置情報』ではなく復帰文字付きの文字列になる。"""
    carriage_return = chr(13)
    units = parse_md(_write(tmp_path, SAMPLE, newline=carriage_return + "\n"))
    assert [u.heading for u in units] == ["機種概要", "設置情報"]
    assert all(carriage_return not in u.text for u in units)


def test_units_are_not_marked_as_ocr(sample):
    assert all(u.ocr is False for u in parse_md(sample))


def test_file_without_any_heading_becomes_one_unit(tmp_path):
    path = _write(tmp_path, "# タイトル\n\n見出しのない本文がここに入っています。\n")
    units = parse_md(path)
    assert len(units) == 1
    assert units[0].heading == ""
    assert units[0].location == 1
    assert "見出しのない本文" in units[0].text


def test_section_without_a_body_is_dropped(tmp_path):
    """見出しだけのチャンクは検索の役に立たない。"""
    path = _write(tmp_path, "# タイトル\n\n## 空の節\n\n## 中身のある節\n\n本文があります。\n")
    units = parse_md(path)
    assert [u.heading for u in units] == ["中身のある節"]
    assert units[0].location == 1


def test_frontmatter_only_file_produces_nothing(tmp_path):
    assert parse_md(_write(tmp_path, "---\nmodel_id: X\n---\n")) == []


def test_empty_file_produces_nothing(tmp_path):
    assert parse_md(_write(tmp_path, "   \n\n")) == []


def test_dispatch_handles_md(sample):
    assert parse(sample)[0].location_type == "section"


def test_heading_inside_a_code_fence_does_not_split(tmp_path):
    """コードブロック内の ## は見出しではない。誤分割しても例外は出ず静かに壊れる。"""
    fence = "`" * 3
    text = (
        "# タイトル\n\n## 手順\n\n"
        f"{fence}\n## これは見出しではない\n{fence}\n\n"
        "続きの本文がここにあります。\n"
    )
    units = parse_md(_write(tmp_path, text))
    assert [u.heading for u in units] == ["手順"]
    assert "## これは見出しではない" in units[0].text
