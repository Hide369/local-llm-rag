# 画像資料の取り込みとアップロードUIの改善 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 画像の中にある情報（スクリーンショットの文字、図の意味、drawio のラベル）を索引に入れ、アップロードダイアログの一覧を使える形にする。

**Architecture:** 「画像バイト列 → 索引に入れるテキスト」を `ingest/image_text.py` 1つに集め、md / xlsx / docx / pdf / pptx / 画像単体の6経路がそこを通る。drawio だけは XML にラベル文字が構造化されたまま入っているので、画像化せず XML から読む。パーサーの署名を `(path, caption_image=None, on_missing_image=None)` に揃え、ディスパッチャから拡張子ごとの分岐を無くす。

**Tech Stack:** Python 3.13 / RapidOCR (onnxruntime) / Ollama qwen2.5vl / openpyxl / python-docx / python-pptx / PyMuPDF / Pillow / Streamlit / pytest

**Spec:** `docs/superpowers/specs/2026-09-11-image-ingestion-design.md`

## Global Constraints

- **仮想環境は `myvenv313`。** テストは `myvenv313/Scripts/python.exe -m pytest` で走らせる。PowerShell では `&&` が使えない（`A; if ($?) { B }`）。
- **新しい依存は追加しない。** `requirements.txt` は変更しない。`pillow==12.3.0` は既に入っている。
- **テストはネットワークもモデルも使わない。** `caption_image` と `ocr_bytes` は引数でフェイクを渡す。実機が要るテストには `@pytest.mark.integration` を付ける（`pytest.ini` の `addopts = -m "not integration"` で既定では走らない）。
- **バイナリをリポジトリに置かない。** テスト用の xlsx / docx / pptx / png は `tmp_path` にその場で生成する（`tests/test_parsers_office.py` の既存の作法）。
- **コメントは「なぜ」を書く。** このリポジトリの既存コードは判断の理由を日本語のコメントで残している。同じ密度で書くこと。
- **コミットはコンベンショナルコミット形式**（`feat:` `fix:` `docs:` `test:` `refactor:`）。メッセージは英語。
- **ブランチは `feat/image-ingestion`。** master へ直接コミットしない。
- **接頭辞の文字列は仕様どおりに一致させること。** `"[図の説明] "` と `"[画像内の文字] "`（どちらも末尾に半角スペース1つ）。既存の PDF/PPTX のチャンクと表記が揃わなくなる。
- **`ParsedUnit` は frozen dataclass。** 後から属性を書き換えられない。組み立て終えてから作ること。

---

### Task 1: `ocr_bytes` — OCR をバイト列で呼べるようにする

OCR は今 `ocr_page(page)` しか口が無く、PyMuPDF の page オブジェクトを持つ PDF からしか呼べない。バイト列を受ける口を開ける。挙動は変えない。

**Files:**
- Modify: `ingest/ocr.py:38-42`
- Test: `tests/test_ocr.py`

**Interfaces:**
- Consumes: なし（最初のタスク）
- Produces: `ingest.ocr.ocr_bytes(data: bytes) -> str` — 認識した文字列を半角スペースで連結して返す。1文字も認識しなければ `""`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ocr.py` の末尾（`test_dpi_is_200` の後、`@pytest.mark.integration` のテストの前）に足す。ファイル冒頭の import に `ocr_bytes` を加えること（`from ingest.ocr import OCR_DPI, ocr_bytes, ocr_page, reset_engine`）。

```python
def test_ocr_bytes_recognizes_from_raw_bytes(monkeypatch):
    """PDF以外の形式は page オブジェクトを持たない。バイト列で呼べる口が要る。"""
    monkeypatch.setattr(
        ocr_module, "_build_engine", lambda: (lambda _img: _FakeResult(["エラー", "コード"]))
    )
    assert ocr_bytes(b"fake-png-bytes") == "エラー コード"


def test_ocr_bytes_returns_empty_string_when_nothing_is_recognized(monkeypatch):
    monkeypatch.setattr(
        ocr_module, "_build_engine", lambda: (lambda _img: _FakeResult(None))
    )
    assert ocr_bytes(b"fake-png-bytes") == ""


def test_ocr_page_delegates_to_ocr_bytes(blank_page, monkeypatch):
    """ラスタライズ(DPI指定)はPDF側の責務、認識は ocr_bytes の責務に分ける。

    委譲していることを見ておかないと、両方に認識ロジックが写された状態が
    テストを通ってしまう。
    """
    received = []
    monkeypatch.setattr(ocr_module, "ocr_bytes", lambda data: received.append(data) or "文字")

    assert ocr_page(blank_page) == "文字"
    assert len(received) == 1
    assert received[0].startswith(b"\x89PNG")
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_ocr.py -v
```

Expected: FAIL — `ImportError: cannot import name 'ocr_bytes' from 'ingest.ocr'`

- [ ] **Step 3: 実装する**

`ingest/ocr.py` の `ocr_page` を次で置き換える。

```python
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
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_ocr.py tests/test_parser_pdf.py -v
```

Expected: PASS（`test_engine_is_not_created_until_first_use` と `test_engine_is_built_only_once` を含め全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/ocr.py tests/test_ocr.py
git commit -m "feat: allow OCR to be called with raw image bytes"
```

---

### Task 2: `ingest/image_text.py` — 画像からテキストを作る共通モジュール

仕様 4節。VLM と OCR を組み合わせ、装飾画像を捨て、片方の失敗でもう片方を巻き添えにしない。

**Files:**
- Create: `ingest/image_text.py`
- Test: `tests/test_image_text.py`（新規）

**Interfaces:**
- Consumes: `ingest.ocr.ocr_bytes(data: bytes) -> str`（Task 1）
- Produces:
  - `ingest.image_text.CAPTION_PREFIX = "[図の説明] "`
  - `ingest.image_text.OCR_PREFIX = "[画像内の文字] "`
  - `ingest.image_text.describe_image(image_bytes: bytes, caption_image=None, ocr_bytes=None, label: str = "") -> str | None`
  - `ingest.image_text.is_image_block(text: str) -> bool`
  - `ingest.image_text.has_caption(text: str) -> bool` / `has_ocr(text: str) -> bool` — 呼び出し側が `ParsedUnit.vlm` / `.ocr` を立てるために使う

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_image_text.py` を新規作成する。

```python
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
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_image_text.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.image_text'`

- [ ] **Step 3: 実装する**

`ingest/image_text.py` を新規作成する。

```python
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
    扱わない取り込みでRapidOCRのエンジン生成（実測4.8秒）を避けるためである。
    """
    if ocr_bytes is None:
        from ingest.ocr import ocr_bytes as ocr_bytes_impl

        ocr_bytes = ocr_bytes_impl

    caption = _run(caption_image, image_bytes, label, "画像の説明取得")
    text = _run(ocr_bytes, image_bytes, label, "画像のOCR")

    if caption == DECORATION:
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
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_image_text.py -v
```

Expected: PASS（13件）

- [ ] **Step 5: コミット**

```bash
git add ingest/image_text.py tests/test_image_text.py
git commit -m "feat: add shared image-to-text module combining VLM and OCR"
```

---

### Task 3: パーサー署名の統一と `image_parser`（.png / .jpg / .jpeg）

仕様 6節・12節。ディスパッチャから拡張子ごとの分岐を消し、画像単体のパーサーを足す。

**Files:**
- Create: `ingest/parsers/image_parser.py`
- Modify: `ingest/parsers/__init__.py`（全体）, `ingest/parsers/docx_parser.py:13`, `ingest/parsers/txt_parser.py:40`, `ingest/parsers/md_parser.py:141`, `ingest/parsers/xlsx_parser.py:41`, `ingest/parsers/pdf_parser.py:52`, `ingest/parsers/pptx_parser.py:170`
- Test: `tests/test_parser_image.py`（新規）, `tests/test_parsers_office.py`

**Interfaces:**
- Consumes: `ingest.image_text.describe_image / has_caption / has_ocr`（Task 2）
- Produces:
  - `ingest.parsers.image_parser.parse_image(path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]`
  - `ingest.parsers.parse(path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]` — 全パーサーがこの3引数の署名を持つ
  - `SUPPORTED_SUFFIXES` に `.png` `.jpg` `.jpeg` が加わる

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_image.py` を新規作成する。

```python
"""画像ファイル単体の取り込み。

画像1枚には見出しもページも無く、書き手が引いた境界が存在しない。txt を
文書全体で1ユニットにしているのと同じ理由で、1ファイル=1ユニットにする。
"""
import io

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
```

さらに `tests/test_parsers_office.py` に、署名が揃ったことを確かめるテストを足す。

```python
def test_every_parser_accepts_the_same_keyword_arguments(tmp_path, docx_path):
    """ディスパッチャが拡張子ごとに引数を出し分けないための約束である。

    署名がずれると parse() に if が戻り、形式を足すたびにそこが伸びる。
    """
    import inspect

    from ingest.parsers import _PARSERS

    for suffix, parser in _PARSERS.items():
        parameters = inspect.signature(parser).parameters
        assert "caption_image" in parameters, suffix
        assert "on_missing_image" in parameters, suffix
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parser_image.py tests/test_parsers_office.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.parsers.image_parser'`

- [ ] **Step 3: 実装する**

`ingest/parsers/image_parser.py` を新規作成する。

```python
"""画像ファイル単体のテキスト化。

1ファイル=1ユニットにする。画像1枚には見出しもページも無く、書き手が引いた
境界の手がかりが存在しないためで、txt_parser が文書全体を1ユニットにしているのと
同じ判断である。

.drawio.png のようにXMLを埋め込んだPNGもここへ来る。埋め込みXMLの取り出しは
行わず、画像として読む（設計書15節）。
"""
from pathlib import Path

from ingest.image_text import describe_image, has_caption, has_ocr
from ingest.models import DOCUMENT, ParsedUnit


def parse_image(path: Path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]:
    """画像1枚をユニットにする。読めなければ空リストを返す。

    ocr_bytes はテストで差し替えるための引数である（pdf_parser の ocr_page と
    同じ形）。省略時は describe_image が ingest.ocr を遅延importする。

    on_missing_image は受け取るが使わない。全パーサーの署名を揃えるためである
    （設計書12節）。
    """
    text = describe_image(
        path.read_bytes(), caption_image, ocr_bytes=ocr_bytes, label=path.name
    )
    if text is None:
        # 読めなかった画像はユニットを作らない。空チャンクがDBに入ると
        # どの質問にも弱く一致する（xlsx_parser が空シートを飛ばすのと同じ）。
        return []
    return [
        ParsedUnit(
            text=text,
            location_type=DOCUMENT,
            location=0,
            ocr=has_ocr(text),
            vlm=has_caption(text),
        )
    ]
```

`ingest/parsers/__init__.py` を次で置き換える。

```python
"""拡張子に応じて適切なパーサーへ振り分ける。

新しい形式に対応するときは、パーサーを1つ書いて _PARSERS に登録するだけでよい。
そのために全パーサーの署名を揃えてある。使わない引数を受け取るパーサーが
あるが、使う側だけに足すとこのディスパッチャが拡張子を見て引数を出し分ける
ことになり、形式を足すたびに分岐が伸びる（設計書12節）。
"""
from pathlib import Path

from ingest.models import ParsedUnit
from ingest.parsers.docx_parser import parse_docx
from ingest.parsers.image_parser import parse_image
from ingest.parsers.md_parser import parse_md
from ingest.parsers.pdf_parser import parse_pdf
from ingest.parsers.pptx_parser import parse_pptx
from ingest.parsers.txt_parser import parse_txt
from ingest.parsers.xlsx_parser import parse_xlsx


class UnsupportedFormatError(Exception):
    """取り込み対象外の拡張子を渡された。"""


_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".pptx": parse_pptx,
    ".md": parse_md,
    ".txt": parse_txt,
    ".xlsx": parse_xlsx,
    ".png": parse_image,
    ".jpg": parse_image,
    ".jpeg": parse_image,
}

SUPPORTED_SUFFIXES = set(_PARSERS)


def parse(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    return parser(path, caption_image=caption_image, on_missing_image=on_missing_image)
```

`.drawio` はここには**まだ入れない**。`drawio_parser` は Task 4 で作るので、今 import を書くとこのモジュールが読み込めなくなる。Task 4 で1行ずつ足す。

既存5パーサーの署名を揃える。本文のロジックは変えない。

```python
# ingest/parsers/docx_parser.py
def parse_docx(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:

# ingest/parsers/txt_parser.py — どちらも使わない。署名を揃えるためだけに受ける。
def parse_txt(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:

# ingest/parsers/md_parser.py
def parse_md(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:

# ingest/parsers/xlsx_parser.py
def parse_xlsx(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:

# ingest/parsers/pdf_parser.py — ocr_page は既存のまま末尾に残す
def parse_pdf(path: Path, caption_image=None, on_missing_image=None, ocr_page=None) -> list[ParsedUnit]:

# ingest/parsers/pptx_parser.py
def parse_pptx(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
```

`parse_pdf` は `ocr_page` を第2引数にしていた。位置引数で呼んでいる箇所が無いことを確認してから末尾へ移すこと。

```
myvenv313/Scripts/python.exe -m pytest tests/test_parser_pdf.py -v
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/ -v
```

Expected: PASS（全件。`test_parser_image.py` 6件が新規に通る）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/ tests/test_parser_image.py tests/test_parsers_office.py
git commit -m "feat: ingest standalone png and jpeg images"
```

---

### Task 4: `drawio_parser` と `diagram` 出典

仕様 7節。XML からラベル文字を取り出す。OCR も VLM も通さない。

**Files:**
- Create: `ingest/parsers/drawio_parser.py`
- Modify: `ingest/models.py:14`（`DIAGRAM` 追加）, `ingest/parsers/__init__.py`（`.drawio` 登録）, `ingest/retrieval.py:88-110`（`_one_citation`）, `scripts/ingest_source.py:98`（`_POSITION_LABELS`）
- Test: `tests/test_parser_drawio.py`（新規）, `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `ingest.models.ParsedUnit`
- Produces:
  - `ingest.models.DIAGRAM = "diagram"`
  - `ingest.parsers.drawio_parser.parse_drawio(path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]`
  - 出典表示 `構成図.drawio 図「業務フロー」`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_drawio.py` を新規作成する。

```python
"""draw.io の図の取り込み。

.drawio は mxGraph の XML であり、図形のラベル文字が構造化されたまま
ファイルの中にある。画像化してOCRにかけるのは、手元にある正解を捨てて
推測し直すのと同じで、誤認識を新たに持ち込むことになる。
"""
import base64
import urllib.parse
import zlib

import pytest

from ingest.models import DIAGRAM
from ingest.parsers import SUPPORTED_SUFFIXES, parse
from ingest.parsers.drawio_parser import parse_drawio

_MODEL = (
    '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="2" value="&lt;b&gt;受注&lt;/b&gt;&lt;br&gt;登録" vertex="1" parent="1">'
    '<mxGeometry x="40" y="200" width="120" height="60"/></mxCell>'
    '<mxCell id="3" value="在庫引当" vertex="1" parent="1">'
    '<mxGeometry x="40" y="40" width="120" height="60"/></mxCell>'
    '<object label="承認" id="4"><mxCell vertex="1" parent="1">'
    '<mxGeometry x="300" y="40" width="120" height="60"/></mxCell></object>'
    "</root></mxGraphModel>"
)


def _pack(xml):
    """draw.io の既定の格納形式: URLエンコード → raw deflate → base64。"""
    return base64.b64encode(
        zlib.compress(urllib.parse.quote(xml, safe="").encode())[2:-4]
    ).decode()


@pytest.fixture
def compressed_path(tmp_path):
    path = tmp_path / "構成図.drawio"
    path.write_text(
        f'<mxfile><diagram name="業務フロー" id="a">{_pack(_MODEL)}</diagram></mxfile>',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def plain_path(tmp_path):
    """draw.io は設定で圧縮を切れる。両方を受けないと片方が丸ごと落ちる。"""
    path = tmp_path / "非圧縮.drawio"
    path.write_text(
        f'<mxfile><diagram name="業務フロー" id="a">{_MODEL}</diagram></mxfile>',
        encoding="utf-8",
    )
    return path


def test_a_compressed_diagram_is_read(compressed_path):
    assert "在庫引当" in parse_drawio(compressed_path)[0].text


def test_an_uncompressed_diagram_is_read(plain_path):
    assert "在庫引当" in parse_drawio(plain_path)[0].text


def test_each_page_becomes_one_unit(tmp_path):
    """ページは書き手が引いた区切りそのものである。PDFのページと同じ扱いにする。"""
    path = tmp_path / "二枚.drawio"
    path.write_text(
        f'<mxfile><diagram name="一枚目" id="a">{_pack(_MODEL)}</diagram>'
        f'<diagram name="二枚目" id="b">{_pack(_MODEL)}</diagram></mxfile>',
        encoding="utf-8",
    )

    units = parse_drawio(path)

    assert len(units) == 2
    assert [unit.location_type for unit in units] == [DIAGRAM, DIAGRAM]
    assert [unit.location for unit in units] == [1, 2]
    assert [unit.heading for unit in units] == ["一枚目", "二枚目"]


def test_labels_are_ordered_top_to_bottom_then_left_to_right(compressed_path):
    """XML上の並びは作成順であり、図を読む順とは一致しない。"""
    text = parse_drawio(compressed_path)[0].text

    assert text.index("在庫引当") < text.index("承認")
    assert text.index("承認") < text.index("受注")


def test_object_labels_are_collected_too(compressed_path):
    """カスタムプロパティ付きの図形は object/@label を使う。
    片方だけを見ると図の半分が黙って消える。
    """
    assert "承認" in parse_drawio(compressed_path)[0].text


def test_html_in_a_label_is_stripped(compressed_path):
    """タグを残すと索引にも入り、Streamlitの画面にも文字として出る。"""
    text = parse_drawio(compressed_path)[0].text

    assert "<b>" not in text
    assert "受注 登録" in text


def test_the_page_name_leads_the_text(compressed_path):
    """ページ単体で引かれたとき何の図か分からなくなるのを防ぐ。
    md_parser がH1を、xlsx_parser がシート名を先頭に置くのと同じ。
    """
    assert parse_drawio(compressed_path)[0].text.startswith("業務フロー")


def test_a_page_without_labels_produces_no_unit(tmp_path):
    path = tmp_path / "空.drawio"
    empty = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
    path.write_text(
        f'<mxfile><diagram name="空" id="a">{_pack(empty)}</diagram></mxfile>', encoding="utf-8"
    )

    assert parse_drawio(path) == []


def test_drawio_is_routed_by_the_registry(compressed_path):
    assert ".drawio" in SUPPORTED_SUFFIXES
    assert parse(compressed_path)[0].heading == "業務フロー"
```

`tests/test_retrieval.py` に出典のテストを足す（既存の `_one_citation` のテストの近くに置くこと）。

```python
def test_a_diagram_citation_names_the_page():
    """drawio は1ファイルに複数ページが入る。どのページの話か示せないと照合できない。"""
    hit = Hit(
        text="業務フロー\n受注 登録",
        distance=0.1,
        occurrences=[
            {
                "source": "構成図.drawio",
                "location_type": "diagram",
                "location": 1,
                "heading": "業務フロー",
            }
        ],
    )

    assert hit.citation == "構成図.drawio 図「業務フロー」"


def test_a_diagram_without_a_page_name_falls_back_to_the_file_name():
    hit = Hit(
        text="受注 登録",
        distance=0.1,
        occurrences=[
            {"source": "構成図.drawio", "location_type": "diagram", "location": 1, "heading": ""}
        ],
    )

    assert hit.citation == "構成図.drawio"
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parser_drawio.py tests/test_retrieval.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.parsers.drawio_parser'`

- [ ] **Step 3: 実装する**

`ingest/models.py` の位置種別に1行足す。

```python
SHEET = "sheet"
# draw.io のページ。1ファイルに複数入る。
DIAGRAM = "diagram"
```

`ingest/parsers/drawio_parser.py` を新規作成する。

```python
"""draw.io の図のテキスト抽出。

design: docs/superpowers/specs/2026-09-11-image-ingestion-design.md 7節

この形式だけは describe_image を通らない。.drawio は mxGraph の XML であり、
図形のラベル文字が構造化されたままファイルの中にある。画像化してOCRにかけるのは、
手元にある正解を捨てて推測し直すのと同じである。加えて画像化には draw.io
デスクトップ版のCLIが要り、サーバー環境へ外部バイナリを1つ増やすことになる。

失うのは図の見た目の説明だけである。矢印の向きや囲みの入れ子は取れない。
"""
import base64
import binascii
import re
import sys
import urllib.parse
import zlib
from pathlib import Path
from xml.etree import ElementTree

from ingest.models import DIAGRAM, ParsedUnit

# ラベルにはHTMLが入る（実測: '<b>受注</b><br>登録'）。落とさないとタグの文字列が
# そのまま索引され、StreamlitのMarkdownにも文字として出る（answer_text が
# 回答側で同じ問題を扱っている）。
_TAG = re.compile(r"<[^>]+>")

# 座標を持たない要素（辺のラベル等）を末尾へ送るための番兵。
_NO_POSITION = float("inf")


def _unpack(payload: str) -> str:
    """<diagram> の中身をXMLの文字列にする。

    draw.io の既定は base64(raw deflate(urlencode(XML))) だが、設定で圧縮を
    切れる。両方を受けないと、切ってある資料が丸ごと落ちる。

    zlib.decompress の -15 は raw deflate（zlibヘッダ無し）を指す。省くと必ず
    zlib.error になる。
    """
    text = payload.strip()
    if not text:
        return ""
    if text.startswith("<"):
        return text
    raw = zlib.decompress(base64.b64decode(text), -15)
    return urllib.parse.unquote(raw.decode("utf-8"))


def _label(element) -> str:
    """図形のラベル文字。mxCell は value、object は label に持つ。

    片方だけを見ると、カスタムプロパティ付きの図形が黙って消える。
    """
    return element.get("value") or element.get("label") or ""


def _position(element):
    """読み順（行優先）で並べるための整列キー。

    XML上の並び順は作成順であり、図を読む順とは一致しない。pptx_parser が
    シェイプに対して抱えているのと同じ問題・同じ解き方である。
    """
    geometry = element.find("mxGeometry")
    if geometry is None:
        # object は mxGeometry を子の mxCell 側に持つ。
        cell = element.find("mxCell")
        geometry = cell.find("mxGeometry") if cell is not None else None
    if geometry is None:
        return (_NO_POSITION, _NO_POSITION)
    return (float(geometry.get("y", 0)), float(geometry.get("x", 0)))


def _clean(label: str) -> str:
    """HTMLを落とし、1行の文字列にする。<br> は空白にする。"""
    text = _TAG.sub(" ", label)
    return " ".join(text.split())


def _page_labels(model_xml: str) -> list[str]:
    model = ElementTree.fromstring(model_xml)
    elements = [element for element in model.iter() if _label(element)]
    elements.sort(key=_position)
    return [text for text in (_clean(_label(element)) for element in elements) if text]


def parse_drawio(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    """1ページ=1ユニットで読む。caption_image / on_missing_image は使わない。"""
    root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    units: list[ParsedUnit] = []
    for diagram in root.iter("diagram"):
        name = diagram.get("name", "")
        try:
            labels = _page_labels(_unpack(diagram.text or ""))
        except (zlib.error, binascii.Error, ElementTree.ParseError, UnicodeDecodeError) as error:
            # 1ページの失敗で他のページと他の資料を道連れにしない
            # （pdf_parser._describe_images と同じ方針）。
            print(
                f"警告: 図を読めませんでした（{path.name} 図「{name}」）: {error}",
                file=sys.stderr,
            )
            continue
        if not labels:
            # ラベルが1つも無いページはユニットを作らない。空チャンクは
            # どの質問にも弱く一致する。
            continue
        units.append(
            ParsedUnit(
                # ページ名を本文の先頭に置く。ページ単体で引かれたとき何の図か
                # 分からなくなるのを防ぐためで、xlsx_parser がシート名を、
                # md_parser がH1を置いているのと同じ判断である。
                text="\n".join([name, *labels] if name else labels),
                location_type=DIAGRAM,
                # 通し番号にするのはページ名の重複でチャンクIDが衝突しない
                # ようにするため。表示には heading を使う。
                location=len(units) + 1,
                heading=name,
            )
        )
    return units
```

`ingest/parsers/__init__.py` に `from ingest.parsers.drawio_parser import parse_drawio` と `".drawio": parse_drawio,` を足す（Task 3 で保留していた行）。

`ingest/retrieval.py` の `_one_citation` に分岐を1つ足す。`elif location_type == "section":` の**前**に置くこと。

```python
        elif location_type == "diagram":
            # ページ名で示す。通し番号（location）は利用者にとって意味がない。
            heading = metadata.get("heading")
            if heading:
                source = f"{source} 図「{heading}」"
```

`scripts/ingest_source.py` の `_POSITION_LABELS` はそのままでよい。`DIAGRAM` はラベルを持たない形式（`heading` を出す側）なので、`_dropped_positions` の `groups.setdefault("", …)` 経路に入り、ページ名が出る。この判断をコメントで残すこと。

```python
# 位置の呼び方は ingest/retrieval.py の Hit._one_citation() に揃える。
# 利用者が画面で見る出典と同じ言い方でないと、どのスライドの話か照合できない。
# diagram（drawio）と section（Markdown）と sheet（Excel）はここに載せない。
# 通し番号が利用者にとって意味を持たず、_dropped_positions が heading を出すため。
_POSITION_LABELS = {PAGE: "p.", SLIDE: "スライド"}
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/ -v
```

Expected: PASS（全件。`test_parser_drawio.py` 10件と `test_retrieval.py` の新規2件を含む）

- [ ] **Step 5: コミット**

```bash
git add ingest/models.py ingest/parsers/ ingest/retrieval.py scripts/ingest_source.py tests/test_parser_drawio.py tests/test_retrieval.py
git commit -m "feat: ingest drawio diagrams by extracting shape labels"
```

---

### Task 5: docx の埋め込み画像

仕様 10節。段落の読み順に差し込み、段落に現れない画像（表・ヘッダー）は末尾に付ける。

**Files:**
- Modify: `ingest/parsers/docx_parser.py`（全体）
- Test: `tests/test_parsers_office.py`

**Interfaces:**
- Consumes: `ingest.image_text.describe_image / has_caption / has_ocr`（Task 2）
- Produces: `parse_docx(path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parsers_office.py` に足す。ファイル冒頭の import に `from docx.shared import Inches` と `from ingest.image_text import CAPTION_PREFIX, OCR_PREFIX` を加えること。

```python
@pytest.fixture
def docx_with_images_path(tmp_path):
    """段落中の画像と、表のセルに入れた画像を持つdocx。

    表のセルの画像を入れるのは、実測で document.paragraphs に現れないことが
    分かっているためである（関係IDは存在するのに、どの段落のXPathにも出てこない）。
    """
    shot = tmp_path / "shot.png"
    Image.new("RGB", (300, 180), "red").save(shot)
    logo = tmp_path / "logo.png"
    Image.new("RGB", (40, 40), "black").save(logo)

    doc = Document()
    doc.add_paragraph("障害報告")
    doc.add_picture(str(shot), width=Inches(3))
    doc.add_paragraph("上記のダイアログが表示された。")
    table = doc.add_table(rows=1, cols=1)
    table.rows[0].cells[0].paragraphs[0].add_run().add_picture(str(logo), width=Inches(0.4))

    path = tmp_path / "報告.docx"
    doc.save(path)
    return path


def test_docx_inserts_an_image_at_its_paragraph_position(docx_with_images_path):
    """1ユニットにまとめる形式なので、本文のどこへ入るかがそのまま読みやすさになる。"""
    text = parse_docx(
        docx_with_images_path,
        caption_image=lambda blob: "エラーダイアログです。" if len(blob) > 200 else "装飾画像",
        ocr_bytes=lambda _blob: "",
    )[0].text

    assert text.index("障害報告") < text.index("エラーダイアログです。")
    assert text.index("エラーダイアログです。") < text.index("上記のダイアログが表示された。")


def test_docx_appends_images_that_no_paragraph_references(docx_with_images_path):
    """表のセル・ヘッダー・浮動配置の画像は document.paragraphs に現れない。

    段落を辿るだけでは黙って落ちる。位置は失うが、失うのは本文のどこにも
    紐づかない画像だけである。
    """
    text = parse_docx(
        docx_with_images_path,
        caption_image=lambda blob: "スクリーンショット" if len(blob) > 200 else "組織図です。",
        ocr_bytes=lambda _blob: "",
    )[0].text

    assert "組織図です。" in text
    assert text.index("上記のダイアログが表示された。") < text.index("組織図です。")


def test_docx_without_images_is_unchanged(docx_path):
    """画像を持たない議事録の取り込み結果が変わらないこと。"""
    text = parse_docx(docx_path, caption_image=lambda _blob: "図です。")[0].text

    assert CAPTION_PREFIX not in text
    assert text == "会議名：キックオフ\n決定事項：RAGを導入する"


def test_docx_with_only_an_image_still_produces_a_unit(tmp_path):
    """現行の空判定は「中身が無い」ことを根拠にしている。画像があるなら中身はある。"""
    shot = tmp_path / "only.png"
    Image.new("RGB", (300, 180), "blue").save(shot)
    doc = Document()
    doc.add_picture(str(shot), width=Inches(3))
    path = tmp_path / "画像だけ.docx"
    doc.save(path)

    units = parse_docx(path, caption_image=lambda _blob: "青い画像です。", ocr_bytes=lambda _b: "")

    assert len(units) == 1
    assert "青い画像です。" in units[0].text


def test_docx_flags_record_the_engines(docx_with_images_path):
    unit = parse_docx(
        docx_with_images_path,
        caption_image=lambda _blob: "図です。",
        ocr_bytes=lambda _blob: "読めた文字",
    )[0]

    assert unit.vlm is True
    assert unit.ocr is True


def test_docx_adds_nothing_when_neither_engine_finds_anything(docx_with_images_path):
    """読めなかった画像でブロックを作らない。空の接頭辞行だけが残るのを避ける。"""
    text = parse_docx(docx_with_images_path, ocr_bytes=lambda _blob: "")[0].text

    assert CAPTION_PREFIX not in text
    assert OCR_PREFIX not in text


def test_docx_does_not_touch_images_when_no_engine_is_given(docx_with_images_path, monkeypatch):
    """VLMもOCRも渡されなければ、画像の走査そのものを行わない。

    渡されていないのに走査すると、describe_image が ingest.ocr を遅延import
    して実機のOCRエンジン（実測4.8秒）を起こす。
    """
    import ingest.parsers.docx_parser as module

    def _fail(*args, **kwargs):
        raise AssertionError("エンジンが未指定なら画像を読んではいけない")

    monkeypatch.setattr(module, "describe_image", _fail)

    assert "障害報告" in parse_docx(docx_with_images_path)[0].text
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parsers_office.py -v -k docx
```

Expected: FAIL — `parse_docx() got an unexpected keyword argument 'ocr_bytes'`

- [ ] **Step 3: 実装する**

`ingest/parsers/docx_parser.py` を次で置き換える。

```python
"""Word文書のテキスト抽出。

docxにはページの概念が（レンダリングするまで）存在しないため、
文書全体を1つのユニットとして扱う。

1ユニットにまとめる以上、埋め込み画像を本文のどの位置へ入れるかがそのまま
読みやすさになる。段落を走査し、その段落に画像があればその場に差し込む。
"""
from pathlib import Path

from docx import Document

from ingest.image_text import describe_image, has_caption, has_ocr
from ingest.models import DOCUMENT, ParsedUnit


def _paragraph_image_ids(paragraph) -> list[str]:
    """段落に埋め込まれた画像の関係ID。読み順で返る。

    ._p は python-docx の私的属性である。公開APIに段落中の画像を辿る口が
    無い。xlsx_parser の ws._images と同じ扱いで、requirements.txt で
    バージョンを固定していることと、テストが画像1枚を検出することをもって
    受け入れる。
    """
    return list(paragraph._p.xpath(".//a:blip/@r:embed"))


def _image_parts(document) -> dict:
    """関係ID → 画像パート。本文に紐づかない画像を拾うためにも使う。"""
    return {
        rid: part
        for rid, part in document.part.related_parts.items()
        if part.content_type.startswith("image/")
    }


def parse_docx(path: Path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]:
    """文書全体を1ユニットにする。on_missing_image は使わない（署名を揃えるため）。

    ocr_bytes はテストで差し替えるための引数である（pdf_parser の ocr_page と
    同じ形）。省略時は describe_image が ingest.ocr を遅延importする。
    """
    document = Document(path)
    parts = _image_parts(document)
    # 画像を読む手立てが1つも無いなら、走査もしない。従来どおり段落だけを読む。
    read_images = bool(parts) and (caption_image is not None or ocr_bytes is not None)

    blocks: list[str] = []
    seen: set[str] = set()
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            blocks.append(paragraph.text)
        if not read_images:
            continue
        for rid in _paragraph_image_ids(paragraph):
            part = parts.get(rid)
            if part is None or rid in seen:
                continue
            seen.add(rid)
            described = describe_image(
                part.blob, caption_image, ocr_bytes=ocr_bytes, label=path.name
            )
            if described:
                blocks.append(described)

    # 表のセル・ヘッダー・浮動配置の画像は document.paragraphs に現れない
    # （実測で確認済み）。段落を辿るだけでは黙って落ちるため、残りを末尾に付ける。
    # 表の中まで辿る実装より短く、取りこぼしを構造的に無くせる。位置は失うが、
    # 失うのは本文のどこにも紐づかない画像だけである。
    if read_images:
        for rid, part in parts.items():
            if rid in seen:
                continue
            described = describe_image(
                part.blob, caption_image, ocr_bytes=ocr_bytes, label=path.name
            )
            if described:
                blocks.append(described)

    text = "\n".join(blocks)
    if not text.strip():
        return []
    return [
        ParsedUnit(
            text=text,
            location_type=DOCUMENT,
            location=0,
            ocr=has_ocr(text),
            vlm=has_caption(text),
        )
    ]
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parsers_office.py -v
```

Expected: PASS（既存の docx / pptx テストを含め全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/docx_parser.py tests/test_parsers_office.py
git commit -m "feat: read images embedded in docx documents"
```

---

### Task 6: xlsx の埋め込み画像

仕様 9節。要望6の本体。`read_only=True` では画像が見えないので、画像を読むときだけ2回目のロードを行う。

**Files:**
- Modify: `ingest/parsers/xlsx_parser.py`
- Test: `tests/test_parser_xlsx.py`

**Interfaces:**
- Consumes: `ingest.image_text.describe_image / has_caption / has_ocr`（Task 2）
- Produces: `parse_xlsx(path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_xlsx.py` に足す。冒頭の import に次を加えること。

```python
from openpyxl.drawing.image import Image as XLImage
from PIL import Image

from ingest.image_text import CAPTION_PREFIX, OCR_PREFIX
```

```python
@pytest.fixture
def book_with_image_path(tmp_path):
    """スクリーンショットを貼ったブック。要望6そのものの形である。"""
    shot = tmp_path / "shot.png"
    Image.new("RGB", (300, 180), "red").save(shot)

    book = Workbook()
    sheet = book.active
    sheet.title = "障害報告"
    sheet.append(["件名", "ログインできない"])
    sheet.add_image(XLImage(str(shot)), "B4")

    path = tmp_path / "報告.xlsx"
    book.save(path)
    return path


def test_an_embedded_image_is_read(book_with_image_path):
    """read_only=True では画像が一切見えない。これが要望6の原因だった。"""
    text = parse_xlsx(
        book_with_image_path,
        caption_image=lambda _blob: "エラーダイアログです。",
        ocr_bytes=lambda _blob: "コード 0x80070005",
    )[0].text

    assert f"{CAPTION_PREFIX}エラーダイアログです。" in text
    assert f"{OCR_PREFIX}コード 0x80070005" in text


def test_the_image_goes_after_the_rows(book_with_image_path):
    """行の途中へ差し込むと「セル | セル」の1行構造が壊れる。"""
    text = parse_xlsx(
        book_with_image_path,
        caption_image=lambda _blob: "エラーダイアログです。",
        ocr_bytes=lambda _blob: "",
    )[0].text

    assert text.index("件名 | ログインできない") < text.index("エラーダイアログです。")


def test_the_flags_record_the_engines(book_with_image_path):
    unit = parse_xlsx(
        book_with_image_path,
        caption_image=lambda _blob: "図です。",
        ocr_bytes=lambda _blob: "文字",
    )[0]

    assert unit.vlm is True
    assert unit.ocr is True


def test_a_sheet_with_only_an_image_still_produces_a_unit(tmp_path):
    """空シートを飛ばす判断は「中身が無い」ことが根拠である。画像はその例外になる。"""
    shot = tmp_path / "only.png"
    Image.new("RGB", (300, 180), "blue").save(shot)
    book = Workbook()
    book.active.title = "画像だけ"
    book.active.add_image(XLImage(str(shot)), "A1")
    path = tmp_path / "画像だけ.xlsx"
    book.save(path)

    units = parse_xlsx(path, caption_image=lambda _blob: "青い画像です。", ocr_bytes=lambda _b: "")

    assert len(units) == 1
    assert units[0].heading == "画像だけ"
    assert "青い画像です。" in units[0].text


def test_the_workbook_is_opened_once_when_no_image_reader_is_given(book_with_image_path, monkeypatch):
    """画像を読まないときに2回開くと、既存の取り込み時間がただ伸びる。"""
    import ingest.parsers.xlsx_parser as module

    opens = []
    real = module.load_workbook

    def counting(path, **kwargs):
        opens.append(kwargs)
        return real(path, **kwargs)

    monkeypatch.setattr(module, "load_workbook", counting)
    parse_xlsx(book_with_image_path)

    assert len(opens) == 1
    assert opens[0].get("read_only") is True


def test_an_empty_sheet_without_images_still_produces_no_unit(tmp_path):
    """画像対応を入れても、本当に空のシートは飛ばし続ける。"""
    book = Workbook()
    book.active.title = "空"
    book.create_sheet("中身あり").append(["値"])
    path = tmp_path / "空あり.xlsx"
    book.save(path)

    units = parse_xlsx(path, caption_image=lambda _blob: "図です。", ocr_bytes=lambda _b: "")

    assert len(units) == 1
    assert units[0].heading == "中身あり"
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parser_xlsx.py -v
```

Expected: FAIL — `parse_xlsx() got an unexpected keyword argument 'caption_image'` または画像が本文に現れない

- [ ] **Step 3: 実装する**

`ingest/parsers/xlsx_parser.py` の import と `parse_xlsx` を次で置き換える（`_CELL_SEPARATOR` と `_row_text` はそのまま残す）。

```python
from pathlib import Path

from openpyxl import load_workbook

from ingest.image_text import describe_image, has_caption, has_ocr
from ingest.models import SHEET, ParsedUnit
```

```python
def _image_bytes(image) -> bytes | None:
    """openpyxl の画像オブジェクトからバイト列を取り出す。

    実測（openpyxl 3.1.5）では、ファイルから読んだブックの image.ref は
    BytesIO になる。一方、その場で組み立てたブックではパスや PIL の Image に
    なりうるため、両方を受ける。

    _images は openpyxl の私的APIである。公開APIに画像を取り出す口が無い。
    退避先（zipfileで xl/media と xl/drawings のrelsを辿る）は設計書9.2に
    記録してある。
    """
    ref = getattr(image, "ref", None)
    if ref is None:
        return None
    if hasattr(ref, "getvalue"):
        return ref.getvalue()
    if hasattr(ref, "save"):
        import io

        buffer = io.BytesIO()
        ref.save(buffer, format=getattr(ref, "format", None) or "PNG")
        return buffer.getvalue()
    try:
        return Path(str(ref)).read_bytes()
    except OSError:
        return None


def _anchor_key(image):
    """セルの読み順（行→列）に揃えるための整列キー。"""
    anchor = getattr(image, "anchor", None)
    start = getattr(anchor, "_from", None)
    if start is None:
        return (0, 0)
    return (getattr(start, "row", 0), getattr(start, "col", 0))


def _sheet_images(path: Path, caption_image, ocr_bytes) -> dict[str, list[str]]:
    """シート名 → 画像の説明ブロック。

    本文の抽出は read_only=True のままにする（行を逐次読むためメモリを食わない）。
    しかし read_only=True では Worksheet._images が空のままで、画像は一切
    見えない。これが「Excelに貼ったスクリーンショットが読めない」原因だった。
    画像を読むときだけ2回目のロードを行い、読まないときは1回で済ませる。
    """
    book = load_workbook(path)
    try:
        described: dict[str, list[str]] = {}
        for sheet in book.worksheets:
            blocks = []
            for image in sorted(sheet._images, key=_anchor_key):
                blob = _image_bytes(image)
                if blob is None:
                    continue
                text = describe_image(
                    blob,
                    caption_image,
                    ocr_bytes=ocr_bytes,
                    label=f"{path.name} シート「{sheet.title}」",
                )
                if text:
                    blocks.append(text)
            if blocks:
                described[sheet.title] = blocks
        return described
    finally:
        book.close()


def parse_xlsx(path: Path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]:
    # data_only=True は数式ではなく計算結果を取る。'=SUM(A1:A2)' を索引しても
    # 利用者が読む値はどこにも残らず、検索でも回答でも使えない。
    # Excelが計算結果を保存していないブックでは値が None になるが、その場合に
    # 数式を代わりに入れることはしない。数式は本文ではないためである。
    images = (
        _sheet_images(path, caption_image, ocr_bytes)
        if caption_image is not None or ocr_bytes is not None
        else {}
    )
    book = load_workbook(path, data_only=True, read_only=True)
    try:
        units: list[ParsedUnit] = []
        for sheet in book.worksheets:
            lines = [text for text in (_row_text(row) for row in sheet.iter_rows(values_only=True)) if text]
            blocks = images.get(sheet.title, [])
            if not lines and not blocks:
                # 空シートはブックに残りがちである。ユニットを作ると空の
                # チャンクがDBに入り、どの質問にも弱く一致する。
                # 画像だけのシートは例外である。中身が無いのではなく、
                # 中身が画像の側にある。
                continue
            # 画像は行の後ろに置く。途中へ差し込むと _row_text が作る
            # 「セル | セル」の1行構造が壊れる。
            text = "\n".join([sheet.title, *lines, *blocks])
            units.append(
                ParsedUnit(
                    # シート名を本文の先頭に置く。シート単体で検索に引かれたとき
                    # 何の表なのか分からなくなるのを防ぐためで、md_parser が
                    # 各セクションにH1を付けているのと同じ判断である。
                    text=text,
                    location_type=SHEET,
                    # 通し番号にするのはシート名の重複でチャンクIDが衝突しない
                    # ようにするため。表示にはheadingを使う。
                    location=len(units) + 1,
                    heading=sheet.title,
                    ocr=has_ocr(text),
                    vlm=has_caption(text),
                )
            )
        return units
    finally:
        # read_only=True はファイルハンドルを開いたままにする。閉じないと
        # Windowsではそのブックを別プロセスが開けなくなる。
        book.close()
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parser_xlsx.py -v
```

Expected: PASS（既存8件＋新規6件）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/xlsx_parser.py tests/test_parser_xlsx.py
git commit -m "feat: read screenshots embedded in Excel sheets"
```

---

### Task 7: Markdown の画像参照と、見つからない画像の報告

仕様 8節。`![alt](path)` をその場で説明文に置き換え、見つからない参照を `IngestReport` へ運ぶ。

**Files:**
- Modify: `ingest/parsers/md_parser.py`, `scripts/ingest_source.py:36-49`（`IngestReport`）, `scripts/ingest_source.py:120-177`（`_ingest_one`）, `scripts/ingest_source.py:346-364`（`main` の結果表示）, `ingest/prompting.py:103-133`（`format_report`）
- Test: `tests/test_parser_md.py`, `tests/test_ingest_source.py`, `tests/test_prompting.py`

**Interfaces:**
- Consumes: `ingest.image_text.describe_image / has_caption / has_ocr`（Task 2）
- Produces:
  - `parse_md(path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]`
  - `on_missing_image(reference: str) -> None` — 見つからなかった参照先の文字列をそのまま渡す
  - `IngestReport.missing_images: dict[str, list[str]]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_md.py` に足す。import に `from PIL import Image` と `from ingest.image_text import CAPTION_PREFIX, OCR_PREFIX` を加えること。

```python
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
```

`tests/test_ingest_source.py` に足す。既存の `collection` / `source_dir` フィクスチャ、`_write_md()` ヘルパー、`_FakeSession` クラスをそのまま使う。

```python
def test_missing_images_are_collected_per_source(source_dir, collection):
    """見つからない画像は、どの資料のどの参照先だったのかまで残す。

    件数だけでは追えない。dropped を件数ではなく現物で持っているのと同じ理由。
    画面からmdだけをアップロードした利用者が必ず通る経路でもある。
    """
    _write_md(source_dir, "手順書.md", "# 手順\n\n## 節\n本文は残る。\n![無い](images/none.png)\n")

    report = ingest_directory(
        source_dir,
        collection,
        session=_FakeSession(),
        caption_image=lambda _blob: "図です。",
    )

    assert report.missing_images == {"手順書.md": ["images/none.png"]}
    # 取り込み自体は成功している。画像が付かなかっただけである。
    assert report.indexed["手順書.md"] >= 1
    assert report.failed == {}


def test_no_missing_images_key_when_every_reference_resolves(source_dir, collection):
    """1件も無いときにキーを作ると、0件なのか機能が働いていないのか区別できない。"""
    _write_md(source_dir, "製品.md", "# UD-0900i\n\n## 設置情報\n幅は600mmです。\n")

    report = ingest_directory(source_dir, collection, session=_FakeSession())

    assert report.missing_images == {}
```

`tests/test_prompting.py` に足す。

```python
def test_the_report_names_the_images_that_were_not_found():
    """画面からmdだけを上げた利用者に、何が取り込まれなかったのかを伝える。"""
    report = IngestReport(
        indexed={"手順書.md": 2},
        missing_images={"手順書.md": ["images/admin.png", "images/list.png"]},
    )

    line = format_report(report)

    assert "画像が見つかりません 手順書.md: images/admin.png、images/list.png" in line


def test_the_report_stays_quiet_when_no_image_is_missing():
    """0件なのか機能が働いていないのか、読み手が区別できなくなるのを防ぐ。"""
    assert "画像が見つかりません" not in format_report(IngestReport(indexed={"a.md": 1}))
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parser_md.py tests/test_ingest_source.py tests/test_prompting.py -v
```

Expected: FAIL — `parse_md() got an unexpected keyword argument 'ocr_bytes'` / `IngestReport` に `missing_images` が無い

- [ ] **Step 3: 実装する**

`ingest/parsers/md_parser.py` に画像の差し替えを足す。import に次を加える。

```python
import re
import sys

from ingest.image_text import describe_image, has_caption, has_ocr
```

モジュール定数と関数を `_FENCE` の下に足す。

```python
# ![alt](path) と ![alt](path "title")。altは空でもよい。パスに空白は許さない
# （Markdownでは <> で囲む記法になるが、この資料群には現れない）。
_IMAGE = re.compile(r'!\[[^\]]*\]\(\s*([^)\s]+)(?:\s+"[^"]*")?\s*\)')

# 取りに行かない参照。http(s) は外部へ出る通信になり（AGENTS.md の方針）、
# data: はこの資料群に現れない。
_REMOTE_PREFIXES = ("http://", "https://", "data:")


def _resolve(reference: str, base: Path) -> Path | None:
    """参照先をmdのあるディレクトリからの相対で解決する。

    資料が指定した文字列をそのままファイルシステムへ渡す唯一の箇所である。
    .. を辿って外へ出る参照は拒む。取り込みは利用者がアップロードした資料にも
    走るため、資料の中身が読める範囲を資料自身に決めさせてはいけない。
    """
    candidate = (base / urllib.parse.unquote(reference)).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _replace_images(line: str, base: Path, path_name: str, caption_image, ocr_bytes, on_missing_image) -> str:
    """1行の中の画像参照を説明文へ置き換える。

    行ごと消して末尾へ集めるのではなくその場で置き換えるのは、画像が前後の文と
    一緒に1つのセクション（=1チャンク）に入るようにするためである。

    読めなかった画像はリンク記法ごと消す。![](…) を残しても検索の役に立たず、
    回答へ引き写されると存在しない画像を指すことになる。
    """

    def _one(match):
        reference = match.group(1)
        if reference.startswith(_REMOTE_PREFIXES):
            # 記法をそのまま残す。取りに行かないと決めた以上、説明文は作れない。
            return match.group(0)
        resolved = _resolve(reference, base)
        if resolved is None:
            print(
                f"警告: 画像が見つかりません（{path_name}）: {reference}",
                file=sys.stderr,
            )
            if on_missing_image is not None:
                on_missing_image(reference)
            return ""
        return describe_image(
            resolved.read_bytes(),
            caption_image,
            ocr_bytes=ocr_bytes,
            label=f"{path_name} {reference}",
        ) or ""

    return _IMAGE.sub(_one, line)
```

`import urllib.parse` をファイル冒頭に加えること。

`parse_md` のループを次にする（フェンス判定は既存のまま使い、フェンス外の行だけ差し替える）。

```python
def parse_md(path: Path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]:
    attributes, array_values, body_lines = _split_frontmatter(_read_lines(path))
    title = ""
    sections: list[tuple[str, list[str]]] = []
    heading: str = ""
    body: list[str] = []
    in_fence = False
    # 画像を読む手立てが1つも無いなら走査もしない。従来の取り込み結果と
    # 1バイトも変わらないことを保証するため。
    read_images = caption_image is not None or ocr_bytes is not None

    for line in body_lines:
        if line.startswith(_FENCE):
            in_fence = not in_fence
        elif not in_fence:
            if line.startswith("## "):
                sections.append((heading, body))
                heading, body = line[3:].strip(), []
                continue
            if not title and line.startswith("# "):
                title = line[2:].strip()
                continue
            if read_images and "![" in line:
                line = _replace_images(
                    line, path.parent, path.name, caption_image, ocr_bytes, on_missing_image
                )
                if not line.strip():
                    # 画像だけの行が読めなかった場合、空行だけが残る。
                    continue
        body.append(line)
    sections.append((heading, body))
```

ユニット生成部で `ocr` / `vlm` フラグを立てる。

```python
        unit_text = "\n".join(
            part for part in (title, array_values, section_heading, text) if part
        )
        units.append(
            ParsedUnit(
                text=unit_text,
                location_type=SECTION,
                location=len(units) + 1,
                heading=section_heading,
                attributes=attributes,
                ocr=has_ocr(unit_text),
                vlm=has_caption(unit_text),
            )
        )
```

`scripts/ingest_source.py` の `IngestReport` に1フィールド足す。

```python
    # 資料キー → 見つからなかった画像の参照先。件数だけでは、どの画像が
    # 抜けたのか追えない。dropped を件数ではなく現物で持っているのと同じ理由。
    missing_images: dict[str, list[str]] = field(default_factory=dict)
```

`_ingest_one` の `parse` 呼び出しを次にする。

```python
    notify(f"処理中: {source}")
    missing: list[str] = []
    try:
        units = parse(path, caption_image=caption_image, on_missing_image=missing.append)
```

`report.indexed[source] = len(chunks)` の直後に足す。

```python
    if missing:
        # 取り込みは成功している。画像が付かなかったことだけを伝える。
        report.missing_images[source] = missing
        notify(f"画像が見つかりません: {source} — {'、'.join(missing)}")
```

`ingest/prompting.py` の `format_report` の `if report.kept_all_navigation:` の**前**に足す。

```python
    # 1件も無いときは行を出さない。常に出すと、0件なのか機能が働いていないのか
    # 読み手が区別できない（dropped と同じ判断）。
    for source, references in report.missing_images.items():
        lines.append(f"画像が見つかりません {source}: {'、'.join(references)}")
```

`scripts/ingest_source.py` の `main()` の結果表示にも同じ行を足す（`if report.kept_all_navigation:` の前）。

```python
    for source, references in report.missing_images.items():
        print(f"画像が見つかりません {source}: {'、'.join(references)}")
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/ -v
```

Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/md_parser.py ingest/prompting.py scripts/ingest_source.py tests/test_parser_md.py tests/test_ingest_source.py tests/test_prompting.py
git commit -m "feat: ingest images referenced from markdown files"
```

---

### Task 8: pdf / pptx を `image_text` に寄せる

仕様 11節。VLM だけだった経路に OCR が加わり、2箇所に写されていた判断が消える。

**Files:**
- Modify: `ingest/parsers/pdf_parser.py:26-49`, `ingest/parsers/pptx_parser.py:30,70-84,87-100,170-184`
- Test: `tests/test_parser_pdf.py`, `tests/test_parsers_office.py`

**Interfaces:**
- Consumes: `ingest.image_text.describe_image / is_image_block / has_caption / has_ocr`（Task 2）
- Produces: 変更なし（既存の署名を保つ）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_pdf.py` に足す。既存の `pdf_with_large_image` フィクスチャ（300×300 の PNG を貼った PDF）と `pdf_with_small_image`（40×40）をそのまま使う。import に `from ingest.image_text import CAPTION_PREFIX, OCR_PREFIX` を加えること。

```python
def test_an_embedded_image_contributes_its_characters_too(pdf_with_large_image):
    """スライドやPDFに貼ったスクリーンショットの文字が読めない、という
    Excelと同じ問題がこの2形式にも等しくある。
    """
    units = parse_pdf(
        pdf_with_large_image,
        ocr_page=lambda _page: "",
        caption_image=lambda _blob: "構成図です。",
        ocr_bytes=lambda _blob: "受注 出荷",
    )

    assert f"{CAPTION_PREFIX}構成図です。" in units[0].text
    assert f"{OCR_PREFIX}受注 出荷" in units[0].text


def test_a_small_image_is_still_skipped(pdf_with_small_image):
    """OCRが加わっても、ロゴ・アイコンの閾値判定は変えない。"""
    calls = []

    parse_pdf(
        pdf_with_small_image,
        ocr_page=lambda _page: "",
        caption_image=lambda _blob: calls.append(1) or "図です。",
        ocr_bytes=lambda _blob: calls.append(1) or "文字",
    )

    assert calls == []
```

`tests/test_parsers_office.py` に足す。

```python
def test_a_slide_whose_only_content_is_an_image_does_not_become_a_title(tmp_path):
    """OCRだけが取れた画像は [画像内の文字] で始まる。is_image_block が
    2つの接頭辞を見ないと、画像の文字がスライドのタイトルとして
    全ユニットへ複写される。
    """
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    picture = io.BytesIO(_png_bytes(400, 400))
    slide.shapes.add_picture(picture, Inches(1), Inches(1), Inches(3), Inches(3))
    box = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(4), Inches(1))
    box.text_frame.text = "本文のテキスト"
    path = tmp_path / "図が上.pptx"
    prs.save(path)

    units = parse_pptx(path, caption_image=lambda _blob: "", ocr_bytes=lambda _blob: "画像の文字")

    assert all(not unit.text.startswith(OCR_PREFIX) for unit in units)
    assert any("本文のテキスト" in unit.text for unit in units)
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_parser_pdf.py tests/test_parsers_office.py -v
```

Expected: FAIL — `parse_pdf() got an unexpected keyword argument 'ocr_bytes'`

- [ ] **Step 3: 実装する**

`ingest/parsers/pdf_parser.py` の `_describe_images` を次で置き換え、`parse_pdf` に `ocr_bytes=None` を足して渡す。`"[図の説明] "` のベタ書きは `image_text.CAPTION_PREFIX` に置き換える。

```python
from ingest.image_text import CAPTION_PREFIX, describe_image, has_caption, has_ocr


def _describe_images(doc, page, page_number, source_name, caption_image, ocr_bytes) -> list[str]:
    """ページに埋め込まれた図・写真を説明文と文字にする。1枚失敗しても残りは続ける。

    画像の取り出し自体が失敗することもある（壊れたxref等）ため、取り出しは
    ここで握る。caption_image / ocr_bytes 側の失敗は describe_image が
    別々に握っており、片方が落ちてももう片方の結果は残る。
    """
    blocks = []
    for xref, _smask, width, height, *_rest in page.get_images(full=True):
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            continue
        try:
            image_bytes = doc.extract_image(xref)["image"]
        except Exception as error:
            print(
                f"警告: 画像を取り出せませんでした（{source_name} p.{page_number}）: {error}",
                file=sys.stderr,
            )
            continue
        text = describe_image(
            image_bytes, caption_image, ocr_bytes=ocr_bytes, label=f"{source_name} p.{page_number}"
        )
        if text:
            blocks.append(text)
    return blocks
```

`parse_pdf` の中は、`captions` が既に接頭辞付きのブロックになる点だけ変える。

```python
            captions = (
                _describe_images(doc, page, number, path.name, caption_image, ocr_bytes)
                if caption_image is not None or ocr_bytes is not None
                else []
            )

            if needs_ocr:
                if captions:
                    # スキャンページは埋め込み画像の説明で置き換える。
                    text = "\n\n".join(captions)
                    used_vlm = has_caption(text)
                    used_ocr = has_ocr(text)
                else:
                    text = ocr_page(page).strip()
                    used_ocr = True
            elif captions:
                for block in captions:
                    text = f"{text}\n\n{block}".strip()
                used_vlm = has_caption(text)
                used_ocr = has_ocr(text)
```

`ingest/parsers/pptx_parser.py`:
- `_CAPTION_PREFIX = "[図の説明] "` の定義を消し、`from ingest.image_text import describe_image, has_caption, has_ocr, is_image_block` を足す。
- `_picture_block` を `describe_image` を呼ぶ形に置き換える。
- `_split_title` の `block.startswith(_CAPTION_PREFIX)` を `is_image_block(block)` にする。
- `parse_pptx` の `vlm=_CAPTION_PREFIX in text` を `vlm=has_caption(text), ocr=has_ocr(text)` にする。
- `parse_pptx` / `_blocks` / `_picture_block` に `ocr_bytes` を通す。
- `_blocks` の `caption_image is not None` という条件を `caption_image is not None or ocr_bytes is not None` にする。

```python
def _picture_block(shape, slide_number: int, path_name: str, caption_image, ocr_bytes) -> str | None:
    try:
        blob = shape.image.blob
    except Exception as error:
        print(
            f"警告: 画像を取り出せませんでした（{path_name} スライド{slide_number}）: {error}",
            file=sys.stderr,
        )
        return None
    return describe_image(
        blob, caption_image, ocr_bytes=ocr_bytes, label=f"{path_name} スライド{slide_number}"
    )
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/ -v
```

Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/pdf_parser.py ingest/parsers/pptx_parser.py tests/test_parser_pdf.py tests/test_parsers_office.py
git commit -m "refactor: route pdf and pptx images through the shared image module"
```

---

### Task 9: アップロードダイアログの並びとスクロール

仕様 13節。要望4・5。

**Files:**
- Modify: `rag_chat_app.py:188-202`
- Test: `tests/test_rag_chat_app.py`

**Interfaces:**
- Consumes: なし
- Produces: なし（画面の変更のみ）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rag_chat_app.py` に足す。`_open_upload_dialog` と `_stub_open_store` は既存のものを使う。

```python
def test_the_close_button_comes_before_the_uploaded_list(app):
    """一覧の下にあると、資料が増えたときダイアログの外へ流れて押せなくなる。"""
    collection = open_real_store(":memory:")
    for index in range(8):
        collection.add(
            ids=[f"chunk-{index}"],
            documents=[f"本文{index}"],
            embeddings=[[0.1, 0.2]],
            metadatas=[{"source": f"uploads/資料{index}.md"}],
        )

    with patch("ingest.store.open_store", lambda *a, **k: collection):
        app.run()
        _open_upload_dialog(app)

    keys = [button.key for button in app.button if button.key]
    assert "close_upload_dialog" in keys
    assert keys.index("close_upload_dialog") < keys.index("delete_uploads/資料0.md")


def _pixel_heights(node, found):
    """要素ツリーを辿って、高さを固定したコンテナの高さを集める。

    app.get("vertical_block") では取れない（実測で0件）。高さ付きコンテナは
    Block として現れ、proto.height_config.pixel_height に値が入る。
    ダイアログの中身もこの走査で届くことを実測で確認している
    （FileUploader・Column・Divider が見つかる）。
    葉の要素は children を持たないため、getattr で受けること。
    """
    children = getattr(node, "children", None)
    if children is None:
        return found
    items = children.values() if isinstance(children, dict) else children
    for child in items:
        config = getattr(getattr(child, "proto", None), "height_config", None)
        if config is not None and getattr(config, "pixel_height", 0):
            found.append(config.pixel_height)
        _pixel_heights(child, found)
    return found


def test_the_uploaded_list_is_inside_a_fixed_height_container(app):
    """高さを固定するとStreamlitが縦スクロールを出す。固定しないと
    件数の分だけダイアログが縦に伸び、下の要素が画面外へ出る。
    """
    collection = open_real_store(":memory:")
    collection.add(
        ids=["chunk-1"],
        documents=["本文"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"source": "uploads/資料.md"}],
    )

    with patch("ingest.store.open_store", lambda *a, **k: collection):
        app.run()
        _open_upload_dialog(app)

    assert not app.exception
    assert 240 in _pixel_heights(app._tree, [])


def test_no_container_is_drawn_when_nothing_was_uploaded(app):
    """空の箱だけが残るのを避ける。"""
    with patch("ingest.store.open_store", _stub_open_store({"source": "議事録.docx"})):
        app.run()
        _open_upload_dialog(app)

    assert 240 not in _pixel_heights(app._tree, [])
```

- [ ] **Step 2: テストを走らせて落ちることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app.py -v -k upload
```

Expected: FAIL。現状のボタンの並びは実測で
`['open_upload_dialog', 'run_upload', 'delete_uploads/資料.md', 'close_upload_dialog']` であり、
`close_upload_dialog` が `delete_…` より後ろにある。高さ付きコンテナも0件で、`240 in […]` が落ちる。

- [ ] **Step 3: 実装する**

`rag_chat_app.py` の `upload_dialog` の末尾（`st.success(format_report(report))` の後）を次で置き換える。

```python
    # 「閉じる」を一覧より先に置く。一覧の下にあると、資料が増えたときに
    # ダイアログの外へ流れて押せなくなる。
    if st.button("閉じる", key="close_upload_dialog"):
        st.session_state.upload_dialog_open = False
        st.rerun()

    sources = uploaded_sources(collection)
    if sources:
        st.divider()
        st.caption("アップロード済みの資料")
        # 高さを固定するとStreamlitが縦スクロールを出す。固定しないと件数の
        # 分だけダイアログが縦に伸び、下の要素が画面外へ出る。
        # 一覧が空のときはコンテナごと出さない。空の箱だけが残るのを避ける。
        with st.container(height=240, border=True):
            for source in sources:
                name, remove = st.columns([4, 1])
                name.write(source[len(UPLOAD_PREFIX):])
                if remove.button("削除", key=f"delete_{source}"):
                    # 空のチャンク列を渡すとその資料はDBから消える（ingest/store.py）。
                    store.replace_source(collection, source, [], [])
                    st.rerun()
```

- [ ] **Step 4: テストが通ることを確かめる**

```
myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app.py -v
```

Expected: PASS（既存のダイアログのテスト6件を含め全件）

- [ ] **Step 5: 実際の画面で確かめる**

```
myvenv313/Scripts/python.exe -m streamlit run rag_chat_app.py
```

「資料をアップロード」を開き、(a) 「閉じる」が一覧の上にあること、(b) 一覧がボックスに入り右にスクロールバーが出ること、(c) 削除ボタンが従来どおり効くこと、を目で確かめる。

- [ ] **Step 6: コミット**

```bash
git add rag_chat_app.py tests/test_rag_chat_app.py
git commit -m "feat: scroll the uploaded file list and move the close button above it"
```

---

### Task 10: ドキュメントの更新

仕様 17節。

**Files:**
- Modify: `README.md`（対応形式・運用手順・既知の制約）, `docs/処理箇所マップ.md`, `docs/依存関係一覧.md`
- Test: なし（文書のみ）

**Interfaces:**
- Consumes: Task 1〜9 で確定した実装
- Produces: なし

- [ ] **Step 1: 取り込み時間を実測する**

README に書く数字を推測で埋めない。`source/` を `--force` で流し、所要時間を測る。

```
myvenv313/Scripts/python.exe -m scripts.ingest_source --force --with-vlm
```

VLM に繋がらない環境なら `--with-vlm` を外し、「OCR のみの場合」として測る。どちらの条件で測ったかを README に明記すること。

- [ ] **Step 2: README を直す**

- 対応形式の一覧に `.png` `.jpg` `.jpeg` `.drawio` を足す。
- docx / xlsx / md も埋め込み画像を読むようになったことを書く。
- **`--force` での再取り込みが1回要る**ことを運用手順に書く。pdf/pptx の既存チャンクは OCR を通っておらず、ファイルの内容が変わらないため差分取り込みでは拾われない。
- 「既知の制約」に3項目を足す。
  - drawio はラベル抽出であり、矢印の向きや囲みの入れ子は取れない。
  - `ws._images`（openpyxl）と `paragraph._p`（python-docx）は私的 API であり、上げたときに黙って空になりうる。
  - 「装飾画像」の閾値10文字は未実測の仮値である。
  - Markdown が参照する画像は、画面からのアップロードでは必ず見つからない（md だけが送られるため）。取り込みは通り、報告に参照先が出る。
- Step 1 で測った取り込み時間へ数字を差し替える。

- [ ] **Step 3: `docs/処理箇所マップ.md` を直す**

`ingest/image_text.py` `ingest/parsers/image_parser.py` `ingest/parsers/drawio_parser.py` の行を足し、`ocr.py` の行に `ocr_bytes` を加える。

- [ ] **Step 4: `docs/依存関係一覧.md` を直す**

新しい依存は無い。`pillow` の用途欄に「xlsx 埋め込み画像の読み出し（openpyxl 経由）」を足す。`requirements.txt` は変更しない。

- [ ] **Step 5: 全テストを最後に一度通す**

```
myvenv313/Scripts/python.exe -m pytest tests/ -v
```

Expected: PASS（全件。失敗0件であることを出力で確認してから完了と報告すること）

- [ ] **Step 6: コミット**

```bash
git add README.md docs/処理箇所マップ.md docs/依存関係一覧.md
git commit -m "docs: describe image ingestion across all document formats"
```

---

## 実装順の依存

```
Task 1 (ocr_bytes)
   └─ Task 2 (image_text)
         ├─ Task 3 (署名統一 + image_parser)
         │     └─ Task 4 (drawio)   ← parsers/__init__.py を触るので Task 3 の後
         ├─ Task 5 (docx)
         ├─ Task 6 (xlsx)
         ├─ Task 7 (md + 報告)
         └─ Task 8 (pdf/pptx 移行)
Task 9 (UI)    ← 他と独立。いつでもよい
Task 10 (文書) ← 全部の後
```

Task 5・6・7・8 は互いに独立で、順序を入れ替えてよい。ただし全て Task 3（署名統一）の後に行うこと。
