import pytest
from PIL import Image

from ingest.image_text import CAPTION_PREFIX, OCR_PREFIX
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


@pytest.fixture
def sample_with_image(tmp_path):
    """本文が画像参照を1つ持つMarkdown。参照先には実在するPNGを置く。

    caption_imageが実際に呼ばれる経路を用意するため sample とは別に持つ。
    sample を流用すると「画像参照が無いので呼ばれない」だけの、恒真になりかねない
    アサーションになってしまう。
    """
    Image.new("RGB", (200, 100), "white").save(tmp_path / "photo.png")
    text = (
        "# タイトル\n\n"
        "## 現地写真\n\n"
        "設置後の状態はこちら。\n\n"
        "![現地写真](photo.png)\n"
    )
    return _write(tmp_path, text, name="report_with_image.md")


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
    """文字列のままだと $lte が数値比較にならず、絞り込みが静かに失敗する。"""
    attributes = parse_md(sample)[0].attributes
    assert attributes["noise_wash_db"] == 27
    assert isinstance(attributes["noise_wash_db"], int)
    assert attributes["washing_capacity_kg"] == 9.0
    assert isinstance(attributes["washing_capacity_kg"], float)


def test_array_attributes_are_skipped(sample):
    """メタデータはスカラーだけの平らな辞書に保ち、where も部分一致を扱わない。

    値そのものは捨てず _array_values が本文へ載せる（別のテストで確認する）。
    """
    assert "tags" not in parse_md(sample)[0].attributes


def test_every_unit_carries_the_same_attributes(sample):
    """どのセクションがヒットしても絞り込めるよう、全ユニットに乗せる。"""
    units = parse_md(sample)
    assert [u.attributes for u in units] == [units[0].attributes] * len(units)


def test_attributes_are_still_not_in_the_unit_text(sample):
    """メタデータとして持つようになっても、埋め込みテキストには入れない。"""
    assert all("model_id" not in u.text for u in parse_md(sample))
    assert all("noise_wash_db" not in u.text for u in parse_md(sample))


def test_array_values_become_part_of_the_unit_text(sample):
    """配列はメタデータに載せられない。捨てずに本文で拾い、検索に効かせる。

    スカラー属性と扱いが分かれるのは、where で絞り込めるかどうかが違うため。
    数値や単一の文字列は where が扱えるのでメタデータに置き、配列は扱えないので
    本文に置く。どちらも「検索できる形にする」という目的は同じである。
    """
    assert all("スマホ連携" in u.text for u in parse_md(sample))


def test_array_values_are_placed_after_the_title(sample):
    """値だけを空白区切りで、タイトルの直後に置く。

    キー名を伴わないのは、`tags` のような語が全チャンクに現れると検索の語彙が
    汚れるためである。位置をタイトル直後にするのは、本文より前に置くことで
    セクションの中身を薄めずに済むという判断による。
    """
    assert parse_md(sample)[0].text.startswith("UD-0900i IoTコンパクト\nIoT スマホ連携\n")


def test_every_array_key_contributes_its_values(tmp_path):
    """対象は tags に限らない。キー名をコードに固定しない。

    ingest/conditions.py の available_keys と同じ方針である。資料を入れ替えても
    コードを直さずに追従させる。
    """
    path = _write(
        tmp_path,
        "---\ntags: [静音]\ntarget_users: [学生, 単身赴任]\n---\n\n# 型番\n\n## 概要\n\n本文\n",
    )
    text = parse_md(path)[0].text
    assert "静音" in text
    assert "学生" in text
    assert "単身赴任" in text


def test_file_without_array_attributes_keeps_its_text_unchanged(tmp_path):
    """配列が無ければ本文は一切変わらない。空行も足さない。"""
    path = _write(tmp_path, "---\nmodel_id: X1\n---\n\n# タイトル\n\n## 見出し\n\n本文\n")
    assert parse_md(path)[0].text == "タイトル\n見出し\n本文"


def test_empty_array_adds_nothing(tmp_path):
    """空配列は値を持たない。空行を挟むと埋め込みテキストが無意味に伸びる。"""
    path = _write(tmp_path, "---\ntags: []\n---\n\n# タイトル\n\n## 見出し\n\n本文\n")
    assert parse_md(path)[0].text == "タイトル\n見出し\n本文"


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


def test_caption_image_is_now_wired_up(sample_with_image):
    """Task 7でcaption_imageが本文へ反映されるようになった。

    Task 3が固定していた「反映されない」ふるまいはここで期限切れになる。
    sample_with_image は実際に画像参照を1つ含むため、説明文がその位置に入る。
    """
    text = "\n".join(
        u.text
        for u in parse_md(
            sample_with_image, caption_image=lambda _bytes: "説明", ocr_bytes=lambda _b: ""
        )
    )

    assert "説明" in text
    assert "![現地写真]" not in text


def _write_png(path, color="red"):
    Image.new("RGB", (300, 180), color).save(path)


def test_an_image_reference_is_replaced_in_place(tmp_path):
    """画像が前後の文と一緒に1つのセクション（=1チャンク）に入るようにする。"""
    _write_png(tmp_path / "admin.png")
    path = tmp_path / "手順書.md"
    path.write_text(
        "# 管理手順\n\n## 権限変更\n手順は以下の画面で行う。\n"
        "![管理画面](admin.png)\n権限は管理者のみ。\n",
        encoding="utf-8",
    )

    text = parse_md(
        path, caption_image=lambda _blob: "ユーザー一覧の画面です。", ocr_bytes=lambda _b: "追加 削除"
    )[0].text

    assert text.index("手順は以下の画面で行う。") < text.index("ユーザー一覧の画面です。")
    assert text.index("追加 削除") < text.index("権限は管理者のみ。")
    assert "![管理画面]" not in text


def test_an_image_inside_a_code_fence_is_left_alone(tmp_path):
    """フェンス内はコード例であり、そこに書かれたリンクは資料そのものではない。"""
    _write_png(tmp_path / "admin.png")
    path = tmp_path / "書き方.md"
    path.write_text(
        "# 書き方\n\n## 記法\n" "```\n![管理画面](admin.png)\n```\n",
        encoding="utf-8",
    )

    text = parse_md(path, caption_image=lambda _blob: "画面です。", ocr_bytes=lambda _b: "")[0].text

    assert "![管理画面](admin.png)" in text
    assert CAPTION_PREFIX not in text


def test_a_remote_image_is_not_fetched(tmp_path):
    """外部へ出る通信を増やさない（AGENTS.md の方針）。"""
    path = tmp_path / "外部.md"
    path.write_text("# 外部\n\n## 図\n![図](https://example.com/a.png)\n", encoding="utf-8")
    calls = []

    parse_md(path, caption_image=lambda blob: calls.append(blob) or "図です。", ocr_bytes=lambda _b: "")

    assert calls == []


def test_a_missing_image_is_reported_and_the_body_survives(tmp_path):
    """画面からmdだけをアップロードした場合は必ずこの経路に入る。"""
    path = tmp_path / "手順書.md"
    path.write_text("# 手順\n\n## 節\n本文は残る。\n![無い](images/none.png)\n", encoding="utf-8")
    missing = []

    units = parse_md(
        path,
        caption_image=lambda _blob: "図です。",
        on_missing_image=missing.append,
        ocr_bytes=lambda _b: "",
    )

    assert "本文は残る。" in units[0].text
    assert "![無い]" not in units[0].text
    assert missing == ["images/none.png"]


def test_an_image_reference_escaping_the_directory_is_refused(tmp_path):
    """資料が指定した文字列をそのままファイルシステムへ渡す唯一の箇所である。"""
    secret = tmp_path / "secret.png"
    _write_png(secret)
    folder = tmp_path / "docs"
    folder.mkdir()
    path = folder / "手順書.md"
    path.write_text("# 手順\n\n## 節\n![外](../secret.png)\n", encoding="utf-8")
    calls = []
    missing = []

    parse_md(
        path,
        caption_image=lambda blob: calls.append(blob) or "図です。",
        on_missing_image=missing.append,
        ocr_bytes=lambda _b: "",
    )

    assert calls == []
    assert missing == ["../secret.png"]


def test_an_unreadable_image_loses_its_link_notation(tmp_path):
    """![](…) が残っても検索の役に立たず、回答へ引き写されると嘘になる。"""
    _write_png(tmp_path / "logo.png")
    path = tmp_path / "手順書.md"
    path.write_text("# 手順\n\n## 節\n本文。\n![ロゴ](logo.png)\n", encoding="utf-8")

    text = parse_md(path, caption_image=lambda _blob: "装飾画像", ocr_bytes=lambda _b: "")[0].text

    assert "![ロゴ]" not in text
    assert "本文。" in text


def test_md_without_images_is_unchanged(tmp_path):
    """既存の30件の取り込み結果が変わらないこと。"""
    path = tmp_path / "製品.md"
    path.write_text("# UD-0900i\n\n## 設置情報\n幅は600mmです。\n", encoding="utf-8")

    text = parse_md(path, caption_image=lambda _blob: "図です。")[0].text

    assert text == "UD-0900i\n設置情報\n幅は600mmです。"
