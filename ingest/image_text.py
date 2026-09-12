"""画像1枚を、索引に入れるテキストにする。

design: docs/superpowers/specs/2026-09-11-image-ingestion-design.md

VLM(ingest/vlm.py)は「何の図か」を、OCR(ingest/ocr.py)は「そこに何と書いて
あるか」を返す。見ているものが違うので両方を付ける。Excelやスライドに貼った
スクリーンショットは文字が本体であり、VLMの2〜3文の要約からは設定値やメニュー名が
落ちる。逆に構成図はOCRの断片だけでは意味が復元できない。

この判断は以前 pdf_parser と pptx_parser に写して書かれていた。形式が7つに
増えるにあたって、ここ1箇所へ集めている。
"""
import sys

CAPTION_PREFIX = "[図の説明] "
OCR_PREFIX = "[画像内の文字] "

# VLMにこの語を返させている（ingest/vlm.py の CAPTION_PROMPT）。内容のない
# 装飾画像であることの合図である。
DECORATION = "装飾画像"

# 装飾と判定された画像でも、これ以上の文字が読めていれば中身があるとみなす。
# 下回る場合に捨てるのは、ロゴに含まれる社名の断片のような数文字が全資料に
# 散らばるのを防ぐため。全チャンクに現れる語は順位を決める力を持たず、
# ベクトルを一様に濁らせる（pptx_parser._clean がフッタを落とすのと同じ理由）。
# 未実測の仮値であり、実データを入れてから調整する前提。
MIN_OCR_CHARS_FOR_DECORATION = 10


def _run(function, image_bytes, label, what):
    """片方のエンジンを呼ぶ。失敗しても例外を外へ出さない。

    VLMとOCRを別々に握るのがこの関数の存在理由である。まとめて1つの try に
    入れると、Ollamaが止まっているだけでOCRの読めた文字まで捨てることになる。
    1枚の画像の失敗が本文を道連れにしないのは pdf_parser の既存方針
    （_describe_images）と同じ。
    """
    if function is None:
        return ""
    try:
        return (function(image_bytes) or "").strip()
    except Exception as error:  # noqa: BLE001  どのエンジンが何を投げるか保証がない
        where = f"（{label}）" if label else ""
        print(f"警告: {what}に失敗しました{where}: {error}", file=sys.stderr)
        return ""


def describe_image(image_bytes, caption_image=None, ocr_bytes=None, label="") -> str | None:
    """画像1枚の説明文と、その中の文字を1本のテキストにする。

    どちらも得られなければ None を返す。空文字ではなく None にするのは、
    呼び出し側が「ブロックごと入れない」判断を素直に書けるようにするため。

    ocr_bytes を省略すると ingest.ocr を遅延importして既定でOCRする。
    caption_image と非対称なのは、OCRが外部サービスを必要とせず疎通確認も
    要らないためで、呼び出し側が毎回渡す理由がない。遅延importは、テキストしか
    扱わない取り込みでRapidOCRのエンジン生成(実測4.8秒)を避けるためである。
    """
    if ocr_bytes is None:
        from ingest.ocr import ocr_bytes as ocr_bytes_impl

        ocr_bytes = ocr_bytes_impl

    caption = _run(caption_image, image_bytes, label, "画像の説明取得")
    text = _run(ocr_bytes, image_bytes, label, "画像のOCR")

    # 「装飾画像。」「装飾画像です」のように句点や語尾が付いても判定を外さない。
    # ただし startswith にはしない。それだと「装飾画像として使われている実際の
    # 図」のような本物の説明文まで巻き込んで捨ててしまう。
    if caption.rstrip("。.") == DECORATION:
        # 装飾と見られた画像は説明を捨てる。文字が十分にあるときだけ残す。
        caption = ""
        if len(text) < MIN_OCR_CHARS_FOR_DECORATION:
            text = ""

    lines = []
    if caption:
        lines.append(f"{CAPTION_PREFIX}{caption}")
    if text:
        lines.append(f"{OCR_PREFIX}{text}")
    return "\n".join(lines) if lines else None


def is_image_block(text: str) -> bool:
    """describe_image が作ったブロックかどうか。

    pptx_parser が「先頭ブロックをスライドのタイトルにしてよいか」の判定に使う。
    接頭辞が2つに増えたため、startswith の書き写しをやめてここに集約する。
    """
    return text.startswith(CAPTION_PREFIX) or text.startswith(OCR_PREFIX)


def has_caption(text) -> bool:
    """VLM由来の行を含むか。呼び出し側が ParsedUnit.vlm を立てるために使う。"""
    return bool(text) and CAPTION_PREFIX in text


def has_ocr(text) -> bool:
    """OCR由来の行を含むか。呼び出し側が ParsedUnit.ocr を立てるために使う。"""
    return bool(text) and OCR_PREFIX in text
