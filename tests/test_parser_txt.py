"""プレーンテキストの取り込み。

文字コードの判定がこの形式のすべてである。Windowsで作られたテキストはCP932が
現役であり、UTF-8を決め打つと日本語のファイルが丸ごと読めない。
"""
import pytest

from ingest.models import DOCUMENT
from ingest.parsers import SUPPORTED_SUFFIXES, parse
from ingest.parsers.txt_parser import parse_txt


def test_the_whole_file_is_one_unit(tmp_path):
    """txtに区切りの手がかりは無い。分割は後段のchunk_unitsに任せる。"""
    path = tmp_path / "議事録.txt"
    path.write_text("会議名：キックオフ\n決定事項：RAGを導入する\n", encoding="utf-8")

    units = parse_txt(path)

    assert len(units) == 1
    assert units[0].location_type == DOCUMENT
    assert "キックオフ" in units[0].text
    assert "RAGを導入する" in units[0].text


def test_a_cp932_file_is_read_without_mojibake(tmp_path):
    """CP932で保存された日本語が読めること。

    utf-8で決め打つとUnicodeDecodeErrorになり、その資料は取り込みに失敗した
    ものとして丸ごと落ちる。Windowsのメモ帳が既定でこの符号化を使っていた
    以上、社内資料には現に混ざる。
    """
    path = tmp_path / "cp932.txt"
    path.write_bytes("年次有給休暇の付与日数\n".encode("cp932"))

    units = parse_txt(path)

    assert units[0].text.strip() == "年次有給休暇の付与日数"


def test_a_utf8_bom_does_not_leak_into_the_text(tmp_path):
    """BOMが本文の先頭に残ると、その語で引けなくなる。"""
    path = tmp_path / "bom.txt"
    path.write_bytes(b"\xef\xbb\xbf" + "就業規則\n".encode("utf-8"))

    units = parse_txt(path)

    assert units[0].text.startswith("就業規則")


def test_an_empty_file_produces_no_units(tmp_path):
    """空の資料でユニットを作ると、意味の無いチャンクがDBに残る。"""
    path = tmp_path / "空.txt"
    path.write_text("   \n\n", encoding="utf-8")

    assert parse_txt(path) == []


def test_txt_is_routed_by_the_registry(tmp_path):
    """拡張子の登録を忘れると、source/ に置いても黙って無視される。"""
    path = tmp_path / "登録確認.txt"
    path.write_text("本文", encoding="utf-8")

    assert ".txt" in SUPPORTED_SUFFIXES
    assert parse(path)[0].text == "本文"


def test_caption_image_is_permanently_ignored(tmp_path):
    """txtには埋め込み画像という概念が無い。

    docx/xlsx/mdと違って将来ワイヤリングする計画は無く、caption_imageは
    署名を他パーサーと揃えるためだけに受け取る恒久的な無視である
    （ingest/parsers/__init__.py の設計書12節を参照）。
    """
    path = tmp_path / "議事録.txt"
    path.write_text("会議名：キックオフ\n", encoding="utf-8")

    text = parse_txt(path, caption_image=lambda _bytes: "説明")[0].text

    assert "説明" not in text
