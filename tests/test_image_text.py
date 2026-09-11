"""画像1枚からテキストを作る。

VLMとOCRは見ているものが違う。VLMは「何の図か」、OCRは「そこに何と書いてあるか」
を返す。Excelに貼ったスクリーンショットのように文字が本体の画像では、VLMの
2〜3文の要約から設定値やメニュー名が落ちる。逆に構成図ではOCRの断片だけが
残っても意味が復元できない。両方を付けるのはそのためである。

片方が落ちてももう片方を捨てないことがこのモジュールの要になる。Ollamaが
止まっているだけで、OCRの読めた文字まで失われるのは割に合わない。
"""
import pytest

from ingest.image_text import (
    CAPTION_PREFIX,
    OCR_PREFIX,
    describe_image,
    has_caption,
    has_ocr,
    is_image_block,
)

IMAGE = b"fake-image-bytes"


def _caption(text):
    return lambda _blob: text


def _ocr(text):
    return lambda _blob: text


def _raises(error):
    def fail(_blob):
        raise error

    return fail


def test_both_results_are_kept_with_the_caption_first():
    """「何の図か」を先に掴んでから細部を読むほうが辿りやすい。"""
    text = describe_image(IMAGE, _caption("業務フローの図です。"), _ocr("受注 出荷"))

    assert text == f"{CAPTION_PREFIX}業務フローの図です。\n{OCR_PREFIX}受注 出荷"


def test_only_the_caption_when_ocr_finds_nothing():
    """写真やグラフには文字が無い。空のOCR行を足しても濁るだけである。"""
    assert describe_image(IMAGE, _caption("桜の写真です。"), _ocr("")) == (
        f"{CAPTION_PREFIX}桜の写真です。"
    )


def test_only_the_ocr_when_the_vlm_is_not_available():
    """VLM未接続でも取り込みは止めない。図の説明が付かないだけである。"""
    assert describe_image(IMAGE, None, _ocr("エラー コード 0x80070005")) == (
        f"{OCR_PREFIX}エラー コード 0x80070005"
    )


def test_a_decoration_with_little_text_is_dropped_entirely():
    """ロゴの数文字が全資料に散らばると、順位を決める力を持たない語ができる。"""
    assert describe_image(IMAGE, _caption("装飾画像"), _ocr("株式会社")) is None


def test_a_decoration_with_enough_text_keeps_the_text():
    """VLMが装飾と見た画像にも、読める文字が十分にあれば中身がある。"""
    text = describe_image(IMAGE, _caption("装飾画像"), _ocr("受付時間は平日9時から18時まで"))

    assert text == f"{OCR_PREFIX}受付時間は平日9時から18時まで"


def test_nothing_at_all_returns_none():
    assert describe_image(IMAGE, None, _ocr("")) is None


def test_a_failing_vlm_does_not_discard_the_ocr_result(capsys):
    """片方の失敗をまとめて握ると、Ollamaが止まっているだけで文字まで失われる。"""
    text = describe_image(
        IMAGE, _raises(RuntimeError("ollama down")), _ocr("在庫 引当"), label="報告.xlsx シート「表」"
    )

    assert text == f"{OCR_PREFIX}在庫 引当"
    assert "報告.xlsx シート「表」" in capsys.readouterr().err


def test_a_failing_ocr_does_not_discard_the_caption(capsys):
    text = describe_image(IMAGE, _caption("構成図です。"), _raises(RuntimeError("onnx error")))

    assert text == f"{CAPTION_PREFIX}構成図です。"
    assert "onnx error" in capsys.readouterr().err


def test_both_failing_returns_none(capsys):
    assert describe_image(IMAGE, _raises(RuntimeError("a")), _raises(RuntimeError("b"))) is None
    assert capsys.readouterr().err.count("警告") == 2


@pytest.mark.parametrize(
    "text, expected",
    [
        (f"{CAPTION_PREFIX}図です。", True),
        (f"{OCR_PREFIX}文字です。", True),
        ("ふつうの本文", False),
        ("", False),
    ],
)
def test_is_image_block_covers_both_prefixes(text, expected):
    """pptx_parser がタイトル判定に使う。OCRだけの画像が漏れると、
    画像の文字がスライドのタイトルとして全ユニットへ複写される。
    """
    assert is_image_block(text) is expected


def test_has_caption_and_has_ocr_report_which_engine_contributed():
    """呼び出し側が ParsedUnit の vlm / ocr フラグを立てるために使う。"""
    both = describe_image(IMAGE, _caption("図です。"), _ocr("文字"))

    assert has_caption(both) is True
    assert has_ocr(both) is True
    assert has_caption(f"{OCR_PREFIX}文字") is False
    assert has_ocr(f"{CAPTION_PREFIX}図です。") is False
