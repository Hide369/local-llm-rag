"""画像PDFのページをOCRでテキスト化する。

RapidOCR(onnxruntime)を使う。日本語モデル japan_PP-OCRv4_rec_mobile を指定する。

エンジン生成には実測4.8秒かかり、生成後はメモリに常駐する。テキストPDFしか
扱わない場合にこのコストを払わないよう、最初に画像ページへ遭遇するまで生成しない。
"""

# 150/200/300dpiを比較したが精度・速度ともほぼ同じだった。RapidOCRが内部で
# limit_side_len に合わせて縮小するため、これ以上上げても処理時間が増えるだけ。
OCR_DPI = 200

_engine = None


def _build_engine():
    """RapidOCRの実体を生成する。テストではここを差し替える。"""
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

    return RapidOCR(
        params={
            "Rec.lang_type": LangRec.JAPAN,
            "Rec.ocr_version": OCRVersion.PPOCRV4,
            "Rec.model_type": ModelType.MOBILE,
            "Global.log_level": "error",
        }
    )


def reset_engine() -> None:
    """生成済みエンジンを破棄する（主にテスト用）。"""
    global _engine
    _engine = None


def ocr_bytes(data: bytes) -> str:
    """画像のバイト列をOCRし、認識文字列を連結して返す。

    RapidOCRはPNG/JPEGのバイト列をそのまま受け取れる。ocr_page が以前から
    page.get_pixmap().tobytes("png") を渡しており、エンジンへの入力は元から
    バイト列だった。PDF以外の形式（xlsx・docx・md参照先・画像単体）から
    呼べるよう、その入口を切り出しただけである。
    """
    global _engine
    if _engine is None:
        _engine = _build_engine()
    result = _engine(data)
    return " ".join(result.txts) if result.txts else ""


def ocr_page(page) -> str:
    """PyMuPDFのページを画像化してOCRする。

    ラスタライズのDPIはPDF固有の判断なのでここに残す。認識そのものは
    ocr_bytes に任せ、2箇所に写さない。
    """
    return ocr_bytes(page.get_pixmap(dpi=OCR_DPI).tobytes("png"))
