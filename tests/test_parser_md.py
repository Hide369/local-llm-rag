import pytest

from ingest.parsers import parse
from ingest.parsers.md_parser import parse_md

SAMPLE = """---
model_id: UD-0900i
price_tier: スタンダード
washing_capacity_kg: 9.0
noise_wash_db: 27
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


def test_bom_prefixed_file_parses_the_same_as_without_bom(tmp_path):
    """BOM付きでも \\ufeff が先頭行の '---' にくっつかず、フロントマター判定が
    外れないことを確認する（外れると生YAMLがそのまま索引されてしまう）。"""
    without_bom = _write(tmp_path, SAMPLE, name="without_bom.md")
    with_bom_path = tmp_path / "with_bom.md"
    with_bom_path.write_bytes(b"\xef\xbb\xbf" + without_bom.read_bytes())

    units_without_bom = parse_md(without_bom)
    units_with_bom = parse_md(with_bom_path)

    assert [u.heading for u in units_with_bom] == [u.heading for u in units_without_bom]
    assert [u.text for u in units_with_bom] == [u.text for u in units_without_bom]
    assert all("model_id" not in u.text for u in units_with_bom)


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


def test_scalar_frontmatter_becomes_attributes(sample):
    """noise_wash_db は30製品中24製品で本文に一度も現れない。
    ここで拾わないと索引から永久に失われる。"""
    units = parse_md(sample)
    assert units[0].attributes["model_id"] == "UD-0900i"
    assert units[0].attributes["price_tier"] == "スタンダード"


def test_numeric_attributes_keep_numeric_types(sample):
    """文字列のままだと ChromaDB の $lte が働かず、絞り込みが静かに失敗する。"""
    attributes = parse_md(sample)[0].attributes
    assert attributes["noise_wash_db"] == 27
    assert isinstance(attributes["noise_wash_db"], int)
    assert attributes["washing_capacity_kg"] == 9.0
    assert isinstance(attributes["washing_capacity_kg"], float)


def test_array_attributes_are_skipped(sample):
    """ChromaDBのメタデータはスカラーしか持てず、where も部分一致を扱えない。"""
    assert "tags" not in parse_md(sample)[0].attributes


def test_every_unit_carries_the_same_attributes(sample):
    """どのセクションがヒットしても絞り込めるよう、全ユニットに乗せる。"""
    units = parse_md(sample)
    assert [u.attributes for u in units] == [units[0].attributes] * len(units)


def test_attributes_are_still_not_in_the_unit_text(sample):
    """メタデータとして持つようになっても、埋め込みテキストには入れない。"""
    assert all("model_id" not in u.text for u in parse_md(sample))
    assert all("noise_wash_db" not in u.text for u in parse_md(sample))


def test_nested_yaml_keys_are_skipped(tmp_path):
    """字下げされた行は入れ子の属性であり、平らなメタデータには載せられない。"""
    text = "---\nouter:\n  inner: 1\n---\n\n# タイトル\n\n## 節\n\n本文がここにあります。\n"
    assert "inner" not in parse_md(_write(tmp_path, text))[0].attributes


def test_file_without_frontmatter_has_no_attributes(tmp_path):
    path = _write(tmp_path, "# タイトル\n\n## 節\n\n本文がここにあります。\n")
    assert parse_md(path)[0].attributes == {}


def test_unclosed_frontmatter_yields_no_attributes(tmp_path):
    """閉じられていないなら本文とみなす既存の判断を、属性側でも守る。"""
    path = _write(tmp_path, "---\nmodel_id: X\n\n# タイトル\n\n本文がここにあります。\n")
    assert parse_md(path)[0].attributes == {}
