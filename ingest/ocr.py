"""画像PDFのページをOCRでテキスト化する。

RapidOCR(onnxruntime)を使う。日本語モデル japan_PP-OCRv4_rec_mobile を指定する。

エンジン生成には実測4.8秒かかり、生成後はメモリに常駐する。テキストPDFしか
扱わない場合にこのコストを払わないよう、最初に画像ページへ遭遇するまで生成しない。
"""

# 150/200/300dpiを比較したが精度・速度ともほぼ同じだった。RapidOCRが内部で
# limit_side_len に合わせて縮小するため、これ以上上げても処理時間が増えるだけ。
OCR_DPI = 200

_engine = None
# 起動に失敗した理由。覚えておくのは、オフラインでは起動の試み1回ごとに
# モデル取得の待ちが乗り、白紙ページのたびに払うと取り込みが進まないため。
# 代わりに、モデルを入れた後はプロセスの再起動が要る（メッセージに書く）。
_engine_error = None


class OcrUnavailableError(Exception):
    """OCRエンジンを起動できない（モデルが手元に無く取得もできない等）。

    個々の画像の読み取り失敗と区別するために分けてある。pdf_parser は
    これだけを握ってページを飛ばし、それ以外の失敗は隠さない。
    """


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
    """生成済みエンジンと、覚えている起動失敗を破棄する（主にテスト用）。"""
    global _engine, _engine_error
    _engine = None
    _engine_error = None


def _get_engine():
    """エンジンを返す。起動できなければ OcrUnavailableError。"""
    global _engine, _engine_error
    if _engine is None and _engine_error is None:
        try:
            _engine = _build_engine()
        except Exception as error:  # noqa: BLE001  モデル取得・読み込みの何が落ちるか保証がない
            _engine_error = (
                f"OCRエンジンを起動できません: {error}"
                "（モデルを入れた後は、アプリまたは取り込みを起動し直してください）"
            )
    if _engine_error is not None:
        raise OcrUnavailableError(_engine_error)
    return _engine


def ocr_bytes(data: bytes) -> str:
    """画像のバイト列をOCRし、認識文字列を連結して返す。

    RapidOCRはPNG/JPEGのバイト列をそのまま受け取れる。ocr_page が以前から
    page.get_pixmap().tobytes("png") を渡しており、エンジンへの入力は元から
    バイト列だった。PDF以外の形式（xlsx・docx・md参照先・画像単体）から
    呼べるよう、その入口を切り出しただけである。
    """
    result = _get_engine()(data)
    return " ".join(result.txts) if result.txts else ""


def ocr_page(page) -> str:
    """PyMuPDFのページを画像化してOCRする。

    ラスタライズのDPIはPDF固有の判断なのでここに残す。認識そのものは
    ocr_bytes に任せ、2箇所に写さない。
    """
    return ocr_bytes(page.get_pixmap(dpi=OCR_DPI).tobytes("png"))
