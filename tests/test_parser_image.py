"""画像ファイル単体の取り込み。

画像1枚には見出しもページも無く、書き手が引いた境界が存在しない。txt を
文書全体で1ユニットにしているのと同じ理由で、1ファイル=1ユニットにする。
"""
import pytest
from PIL import Image

from ingest.image_text import CAPTION_PREFIX, OCR_PREFIX
from ingest.models import DOCUMENT
from ingest.parsers import SUPPORTED_SUFFIXES
from ingest.parsers.image_parser import parse_image


@pytest.fixture
def png_path(tmp_path):
    path = tmp_path / "画面.png"
    Image.new("RGB", (320, 200), "white").save(path)
    return path


def _caption(text):
    return lambda _blob: text


def _ocr(text):
    return lambda _blob: text


def test_one_file_becomes_one_document_unit(png_path):
    units = parse_image(png_path, caption_image=_caption("設定画面です。"), ocr_bytes=_ocr("保存"))

    assert len(units) == 1
    assert units[0].location_type == DOCUMENT
    assert units[0].location == 0


def test_the_text_carries_both_the_caption_and_the_characters(png_path):
    units = parse_image(png_path, caption_image=_caption("設定画面です。"), ocr_bytes=_ocr("保存 取消"))

    assert units[0].text == f"{CAPTION_PREFIX}設定画面です。\n{OCR_PREFIX}保存 取消"


def test_the_flags_record_which_engine_contributed(png_path):
    """出典の（OCR）表示と、後からどの経路で入ったかを追うために立てる。"""
    both = parse_image(png_path, caption_image=_caption("図です。"), ocr_bytes=_ocr("文字"))[0]
    assert both.vlm is True
    assert both.ocr is True

    only_ocr = parse_image(png_path, caption_image=None, ocr_bytes=_ocr("文字"))[0]
    assert only_ocr.vlm is False
    assert only_ocr.ocr is True


def test_an_unreadable_image_produces_no_unit(png_path):
    """空チャンクがDBに入ると、どの質問にも弱く一致する。"""
    assert parse_image(png_path, caption_image=None, ocr_bytes=_ocr("")) == []


def test_image_suffixes_are_routed_by_the_registry():
    """拡張子の登録を忘れると、source/ に置いても黙って無視される。

    parse() 越しには呼ばない。parse() は ocr_bytes を受け取らないため、
    既定のOCR（RapidOCRのエンジン生成に実測4.8秒）が本当に走ってしまう。
    振り分け先が正しいことだけを見れば足りる。
    """
    from ingest.parsers import _PARSERS

    assert {".png", ".jpg", ".jpeg"} <= SUPPORTED_SUFFIXES
    assert _PARSERS[".png"] is _PARSERS[".jpg"] is _PARSERS[".jpeg"] is parse_image


def test_a_jpeg_is_handled_by_the_same_parser(tmp_path):
    path = tmp_path / "写真.jpeg"
    Image.new("RGB", (320, 200), "white").save(path)

    units = parse_image(path, caption_image=_caption("桜の写真です。"), ocr_bytes=_ocr(""))

    assert units[0].text == f"{CAPTION_PREFIX}桜の写真です。"
