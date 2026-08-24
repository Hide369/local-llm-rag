# PDF/PPTX埋め込み画像のVLMキャプション化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PDF/PPTXに埋め込まれた図表・写真をVLM(Vision Language Model)で日本語の説明文にし、周辺テキストと同じチャンクに含めて検索対象にする。

**Architecture:** 新規 `ingest/vlm.py` が `ingest/embedder.py` と同じパターン（session注入・指数バックオフ）でOllamaの `/api/chat` を呼ぶ。`pdf_parser.py` / `pptx_parser.py` は既存の `ocr_page` 注入パターンを踏襲し、新しい `caption_image` パラメータ（既定 `None` = 無効）を追加する。`scripts/ingest_source.py` に `--with-vlm` フラグを足し、指定時だけ実際の `vlm.caption_image` を渡す。

**Tech Stack:** Python 3.13, requests, pymupdf, python-pptx, pytest（既存スタックのまま追加ライブラリなし。Pillowはpython-pptxの既存の依存として既にvenvにある）。

**Spec:** [docs/superpowers/specs/2026-08-24-vlm-image-captioning-design.md](../specs/2026-08-24-vlm-image-captioning-design.md)

## Global Constraints

- コマンドは必ず `myvenv313\Scripts\python.exe -m pytest ...` のように `python.exe -m` 経由で実行する（ランチャーが壊れているため）。
- `OLLAMA_HOST` は `ingest/embedder.py` の値をそのまま再利用する。独自の接続経路・環境変数を増やさない。
- 画像サイズ閾値はPDF最小 `150×150px`、PPTX最小 `1.0インチ角`（いずれも仮値。実データでの再calibrationは本計画の範囲外＝spec 14節）。
- 対象拡張子はPDF/PPTXのみ。DOCX/MDは対象外（spec 14節）。
- `rag_chat_app.py` の「差分を取り込む」ボタンや `ingest_directory()` の既定の呼び出し方は変更しない。`--with-vlm` を明示指定したCLI実行時のみ有効にする。
- 個々の画像のキャプション取得に失敗しても、そのページ/スライドの他のテキストは失わずに処理を続ける（1ファイル単位で処理を続ける既存方針を画像単位に広げる）。

---

## File Structure

- Create: `ingest/vlm.py` — Ollama VLMへの問い合わせ（`caption_image`・`check_vlm`・`VlmError`）
- Create: `tests/test_vlm.py`
- Modify: `ingest/models.py` — `ParsedUnit.vlm: bool` フィールド追加
- Modify: `ingest/chunker.py` — `vlm` フラグをChunkメタデータへ複写
- Modify: `tests/test_chunker.py` — `vlm` フラグ伝播のテスト追加
- Modify: `ingest/parsers/pdf_parser.py` — 埋め込み画像の抽出・フィルタ・キャプション追記
- Modify: `tests/test_parser_pdf.py`
- Modify: `ingest/parsers/pptx_parser.py` — PICTUREシェイプの抽出・フィルタ・キャプション追加
- Modify: `tests/test_parsers_office.py`
- Modify: `ingest/parsers/__init__.py` — `parse()` が `caption_image` をpdf/pptxにだけ橋渡し
- Modify: `scripts/ingest_source.py` — `--with-vlm` フラグ、`ingest_directory()` への配線
- Modify: `README.md` — `--with-vlm` の使い方を追記

---

### Task 1: `ingest/vlm.py` — `caption_image`（リトライ付き）

**Files:**
- Create: `ingest/vlm.py`
- Test: `tests/test_vlm.py`

**Interfaces:**
- Consumes: `ingest.embedder.OLLAMA_HOST`（既存の環境変数解決済み定数）
- Produces: `caption_image(image_bytes: bytes, session=None) -> str`、`VlmError(Exception)`、モジュール定数 `VLM_MODEL: str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_vlm.py` を新規作成する。

```python
import base64

import pytest
import requests

import ingest.vlm as vlm
from ingest.vlm import VLM_MODEL, VlmError, caption_image


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    """POSTされたペイロードを記録し、あらかじめ決めた応答を返す。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.payloads = []

    def post(self, url, json, timeout):
        self.payloads.append(json)
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def get(self, url, timeout):
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _reply(text):
    return _FakeResponse({"message": {"content": text}})


def test_sends_image_as_base64_to_the_configured_model():
    session = _FakeSession([_reply("赤い四角形の画像です。")])
    result = caption_image(b"fake-image-bytes", session=session)
    assert result == "赤い四角形の画像です。"
    payload = session.payloads[0]
    assert payload["model"] == VLM_MODEL
    assert payload["messages"][0]["images"] == [
        base64.b64encode(b"fake-image-bytes").decode("ascii")
    ]


def test_strips_surrounding_whitespace():
    session = _FakeSession([_reply("  説明文  \n")])
    assert caption_image(b"x", session=session) == "説明文"


def test_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(vlm.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("boom"), _reply("説明")])
    assert caption_image(b"x", session=session) == "説明"


def test_backoff_is_exponential(monkeypatch):
    waits = []
    monkeypatch.setattr(vlm.time, "sleep", waits.append)
    session = _FakeSession(
        [requests.ConnectionError("x"), requests.ConnectionError("x"), _reply("説明")]
    )
    caption_image(b"x", session=session)
    assert waits == [1, 2]


def test_gives_up_after_all_attempts(monkeypatch):
    monkeypatch.setattr(vlm.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("x")] * 4)
    with pytest.raises(VlmError):
        caption_image(b"x", session=session)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vlm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.vlm'`

- [ ] **Step 3: 最小実装を書く**

`ingest/vlm.py` を新規作成する。

```python
"""Ollama の VLM(Vision Language Model) にPDF/PPTX埋め込み画像の説明文を作らせる。

design: docs/superpowers/specs/2026-08-24-vlm-image-captioning-design.md
"""
import base64
import time

import requests

from ingest.embedder import OLLAMA_HOST

VLM_MODEL = "qwen2.5vl:7b"

CAPTION_PROMPT = (
    "この画像に写っている図表・写真の内容を、日本語で2〜3文にまとめて説明してください。"
    "ロゴやアイコンなど内容のない装飾画像であれば「装飾画像」とだけ答えてください。"
)

_MAX_ATTEMPTS = 4  # embedder.pyと同じ: 初回 + 3回の再試行（1秒 → 2秒 → 4秒）
_TIMEOUT = 120


class VlmError(Exception):
    """画像の説明取得に失敗した。"""


def caption_image(image_bytes: bytes, session=None) -> str:
    """画像1枚を日本語の説明文にする。"""
    own_session = session is None
    session = session or requests.Session()
    try:
        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": VLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": CAPTION_PROMPT,
                    "images": [base64.b64encode(image_bytes).decode("ascii")],
                }
            ],
            "stream": False,
        }
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                return response.json()["message"]["content"].strip()
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise VlmError(
            f"{OLLAMA_HOST} への画像説明リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
        )
    finally:
        if own_session:
            session.close()
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vlm.py -v`
Expected: PASS（5件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vlm.py tests/test_vlm.py
git commit -m "feat: add VLM caption_image with retry/backoff"
```

---

### Task 2: `ingest/vlm.py` — `check_vlm`（起動前疎通確認）

**Files:**
- Modify: `ingest/vlm.py`
- Test: `tests/test_vlm.py`

**Interfaces:**
- Consumes: Task 1の `VlmError`, `VLM_MODEL`
- Produces: `check_vlm(session=None) -> None`（未接続/モデル未pullで `VlmError` を送出）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_vlm.py` の末尾に追加する。

```python
def test_check_vlm_raises_when_unreachable():
    session = _FakeSession([requests.ConnectionError("refused")])
    with pytest.raises(VlmError, match="Ollama"):
        vlm.check_vlm(session=session)


def test_check_vlm_passes_when_model_present():
    session = _FakeSession([_FakeResponse({"models": [{"name": VLM_MODEL}]})])
    vlm.check_vlm(session=session)


def test_check_vlm_raises_when_model_missing():
    session = _FakeSession([_FakeResponse({"models": [{"name": "bge-m3:latest"}]})])
    with pytest.raises(VlmError, match=VLM_MODEL.split(":")[0]):
        vlm.check_vlm(session=session)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vlm.py -k check_vlm -v`
Expected: FAIL — `AttributeError: module 'ingest.vlm' has no attribute 'check_vlm'`

- [ ] **Step 3: 実装を書く**

`ingest/vlm.py` の末尾に追加する。

```python
def check_vlm(session=None) -> None:
    """取り込み開始前の疎通確認。モデル未pullで460チャンクの処理が始まってから
    落ちるのを防ぐため、embedder.check_ollama() と同じ考え方で先に一度だけ確認する。
    """
    own_session = session is None
    session = session or requests.Session()
    try:
        try:
            response = session.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
            response.raise_for_status()
            names = [model["name"] for model in response.json().get("models", [])]
        except (requests.RequestException, KeyError, ValueError) as error:
            raise VlmError(
                f"Ollamaに接続できません（{OLLAMA_HOST}）。起動しているか確認してください: {error}"
            ) from error
        vlm_base = VLM_MODEL.split(":")[0]
        if not any(name.split(":")[0] == vlm_base for name in names):
            raise VlmError(
                f"VLMモデル {VLM_MODEL} がありません。`ollama pull {VLM_MODEL}` を実行してください。"
            )
    finally:
        if own_session:
            session.close()
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vlm.py -v`
Expected: PASS（8件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vlm.py tests/test_vlm.py
git commit -m "feat: add VLM preflight check"
```

---

### Task 3: `vlm` フラグを `ParsedUnit` → `Chunk` メタデータへ通す

**Files:**
- Modify: `ingest/models.py`
- Modify: `ingest/chunker.py`
- Test: `tests/test_chunker.py`

**Interfaces:**
- Consumes: なし
- Produces: `ParsedUnit(..., vlm: bool = False)`、Chunkメタデータの `"vlm"` キー、`chunker.RESERVED_METADATA_KEYS` に `"vlm"` を含む

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chunker.py` の `test_ocr_flag_is_carried_into_every_chunk`（既存）の直後に追加する。

```python
def test_vlm_flag_is_carried_into_every_chunk():
    unit = ParsedUnit(text="あ" * 2000, location_type="page", location=1, vlm=True)
    chunks = _chunk([unit])
    assert all(c.metadata["vlm"] is True for c in chunks)


def test_vlm_flag_defaults_to_false():
    chunks = _chunk([_unit("本文")])
    assert chunks[0].metadata["vlm"] is False
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_chunker.py -k vlm_flag -v`
Expected: FAIL — `TypeError: ParsedUnit.__init__() got an unexpected keyword argument 'vlm'`

- [ ] **Step 3: `ingest/models.py` を修正する**

`ParsedUnit` の `ocr: bool = False` の直後に1行追加する。

```python
    ocr: bool = False
    # PDF/PPTXに埋め込まれた図表・写真をVLMで説明文化し、本文へ追記したかどうか。
    vlm: bool = False
```

- [ ] **Step 4: `ingest/chunker.py` を修正する**

`RESERVED_METADATA_KEYS` に `"vlm"` を追加する。

```python
RESERVED_METADATA_KEYS = frozenset(
    {
        "source",
        "file_hash",
        "location_type",
        "location",
        "ocr",
        "vlm",
        "heading",
        "chunk_index",
        "indexed_at",
    }
)
```

`chunk_units()` 内のメタデータ辞書に `"ocr": unit.ocr,` の直後で1行追加する。

```python
                        "ocr": unit.ocr,
                        "vlm": unit.vlm,
```

- [ ] **Step 5: テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_chunker.py -v`
Expected: PASS（全件）

- [ ] **Step 6: コミット**

```bash
git add ingest/models.py ingest/chunker.py tests/test_chunker.py
git commit -m "feat: carry a vlm flag from ParsedUnit into chunk metadata"
```

---

### Task 4: `pdf_parser.py` — 埋め込み画像のキャプション化

**Files:**
- Modify: `ingest/parsers/pdf_parser.py`
- Test: `tests/test_parser_pdf.py`

**Interfaces:**
- Consumes: `ingest.vlm.VlmError`（Task 1）、`ParsedUnit(vlm=...)`（Task 3）
- Produces: `parse_pdf(path, ocr_page=None, caption_image=None) -> list[ParsedUnit]`（`caption_image` はTask 1の `caption_image(image_bytes: bytes) -> str` と同じ引数形）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_pdf.py` の先頭のimportに追加する。

```python
import io

from PIL import Image
```

同ファイルの `image_pdf` フィクスチャの直後に追加する。

```python
def _png_bytes(width, height, color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _make_pdf_with_image(tmp_path, text, image_bytes, filename="画像入り.pdf"):
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text, fontsize=14)
    page.insert_image(pymupdf.Rect(50, 200, 250, 400), stream=image_bytes)
    path = tmp_path / filename
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def pdf_with_large_image(tmp_path):
    return _make_pdf_with_image(
        tmp_path,
        "Chapter one has plenty of extractable text here.",
        _png_bytes(300, 300),
    )


@pytest.fixture
def pdf_with_small_image(tmp_path):
    return _make_pdf_with_image(
        tmp_path,
        "Chapter one has plenty of extractable text here.",
        _png_bytes(40, 40),
    )
```

ファイル末尾に追加する。

```python
def test_caption_image_not_called_when_not_provided(pdf_with_large_image):
    def _fail(_bytes):
        raise AssertionError("caption_imageが未指定なら呼ばれてはいけない")

    units = parse_pdf(pdf_with_large_image, ocr_page=_fail, caption_image=None)
    assert "[図の説明]" not in units[0].text
    assert units[0].vlm is False


def test_large_embedded_image_is_captioned(pdf_with_large_image):
    def _ocr_not_called(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    units = parse_pdf(
        pdf_with_large_image,
        ocr_page=_ocr_not_called,
        caption_image=lambda _bytes: "赤い正方形の図です。",
    )
    assert "Chapter one" in units[0].text
    assert "[図の説明] 赤い正方形の図です。" in units[0].text
    assert units[0].vlm is True


def test_small_embedded_image_is_not_captioned(pdf_with_small_image):
    def _fail(_bytes):
        raise AssertionError("閾値未満の画像でcaption_imageが呼ばれてはいけない")

    def _ocr_not_called(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    units = parse_pdf(pdf_with_small_image, ocr_page=_ocr_not_called, caption_image=_fail)
    assert "[図の説明]" not in units[0].text
    assert units[0].vlm is False


def test_caption_failure_is_skipped_with_a_warning(pdf_with_large_image, capsys):
    from ingest.vlm import VlmError

    def _ocr_not_called(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    def _raise(_bytes):
        raise VlmError("boom")

    units = parse_pdf(pdf_with_large_image, ocr_page=_ocr_not_called, caption_image=_raise)
    assert "[図の説明]" not in units[0].text
    assert units[0].vlm is False
    assert "boom" in capsys.readouterr().err
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_parser_pdf.py -v`
Expected: FAIL — `TypeError: parse_pdf() got an unexpected keyword argument 'caption_image'`

- [ ] **Step 3: `ingest/parsers/pdf_parser.py` を修正する**

ファイル冒頭のimportに `sys` を追加し、`ingest.vlm` から `VlmError` を取り込む。

```python
import sys
from pathlib import Path

import pymupdf

from ingest.models import PAGE, ParsedUnit
from ingest.vlm import VlmError

OCR_MIN_CHARS = 30

# ロゴ・アイコン等の装飾画像を除外するための閾値（px角）。実データでの実測は
# design docの5節を参照。未実測の仮値であり、後日調整する前提。
MIN_IMAGE_WIDTH = 150
MIN_IMAGE_HEIGHT = 150
```

`_describe_images` を新規に定義し、`parse_pdf` の直前に置く。

```python
def _describe_images(doc, page, page_number: int, source_name: str, caption_image) -> list[str]:
    """ページに埋め込まれた図・写真をVLMで説明文にする。1枚失敗しても残りは続ける。"""
    captions = []
    for xref, _smask, width, height, *_rest in page.get_images(full=True):
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            continue
        image_bytes = doc.extract_image(xref)["image"]
        try:
            captions.append(caption_image(image_bytes))
        except VlmError as error:
            print(
                f"警告: 画像の説明取得に失敗しました（{source_name} p.{page_number}）: {error}",
                file=sys.stderr,
            )
    return captions
```

`parse_pdf` を書き換える。

```python
def parse_pdf(path: Path, ocr_page=None, caption_image=None) -> list[ParsedUnit]:
    """PDFを1ページ1ユニットで読む。

    ocr_page/caption_image はテストで差し替えられるよう引数にしている。
    caption_image を省略した場合（既定）は画像の説明文化を一切行わない。
    """
    if ocr_page is None:
        from ingest.ocr import ocr_page as ocr_page_impl

        ocr_page = ocr_page_impl

    units = []
    doc = pymupdf.open(path)
    try:
        for number, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            used_ocr = False
            if len(text) < OCR_MIN_CHARS:
                text = ocr_page(page).strip()
                used_ocr = True

            used_vlm = False
            if caption_image is not None:
                for caption in _describe_images(doc, page, number, path.name, caption_image):
                    text = f"{text}\n\n[図の説明] {caption}".strip()
                    used_vlm = True

            if text:
                units.append(
                    ParsedUnit(
                        text=text,
                        location_type=PAGE,
                        location=number,
                        ocr=used_ocr,
                        vlm=used_vlm,
                    )
                )
    finally:
        doc.close()
    return units
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_parser_pdf.py -v`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/pdf_parser.py tests/test_parser_pdf.py
git commit -m "feat: caption embedded PDF images with a VLM"
```

---

### Task 5: `pptx_parser.py` — PICTUREシェイプのキャプション化

**Files:**
- Modify: `ingest/parsers/pptx_parser.py`
- Test: `tests/test_parsers_office.py`

**Interfaces:**
- Consumes: `ingest.vlm.VlmError`（Task 1）、`ParsedUnit(vlm=...)`（Task 3）
- Produces: `parse_pptx(path, caption_image=None) -> list[ParsedUnit]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parsers_office.py` の先頭のimportに追加する。

```python
import io

from PIL import Image
from pptx.enum.shapes import MSO_SHAPE_TYPE
```

`pptx_path` フィクスチャの直前に追加する。

```python
def _png_bytes(width, height, color="green"):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()
```

`rich_pptx_path` フィクスチャの直後に追加する。

```python
@pytest.fixture
def pptx_with_large_picture(tmp_path):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(4), Inches(1))
    box.text_frame.text = "タイトル"
    slide.shapes.add_picture(
        io.BytesIO(_png_bytes(800, 600)), Inches(1), Inches(2), Inches(4), Inches(3)
    )
    path = tmp_path / "図あり.pptx"
    prs.save(path)
    return path


@pytest.fixture
def pptx_with_small_picture(tmp_path):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(4), Inches(1))
    box.text_frame.text = "タイトル"
    slide.shapes.add_picture(
        io.BytesIO(_png_bytes(40, 40, "blue")), Inches(0.1), Inches(0.1), Inches(0.3), Inches(0.3)
    )
    path = tmp_path / "小さい画像.pptx"
    prs.save(path)
    return path
```

ファイル末尾に追加する。

```python
def test_caption_image_not_called_when_not_provided(pptx_with_large_picture):
    def _fail(_bytes):
        raise AssertionError("caption_imageが未指定なら呼ばれてはいけない")

    units = parse_pptx(pptx_with_large_picture, caption_image=None)
    assert all("[図の説明]" not in u.text for u in units)
    assert all(u.vlm is False for u in units)


def test_large_picture_is_captioned(pptx_with_large_picture):
    units = parse_pptx(
        pptx_with_large_picture, caption_image=lambda _bytes: "緑色の図表です。"
    )
    assert any("[図の説明] 緑色の図表です。" in u.text for u in units)
    assert any(u.vlm for u in units)


def test_small_picture_is_not_captioned(pptx_with_small_picture):
    def _fail(_bytes):
        raise AssertionError("閾値未満の画像でcaption_imageが呼ばれてはいけない")

    units = parse_pptx(pptx_with_small_picture, caption_image=_fail)
    assert all("[図の説明]" not in u.text for u in units)
    assert all(u.vlm is False for u in units)


def test_picture_caption_failure_is_skipped_with_a_warning(pptx_with_large_picture, capsys):
    from ingest.vlm import VlmError

    def _raise(_bytes):
        raise VlmError("boom")

    units = parse_pptx(pptx_with_large_picture, caption_image=_raise)
    assert all("[図の説明]" not in u.text for u in units)
    assert "boom" in capsys.readouterr().err
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_parsers_office.py -v`
Expected: FAIL — `TypeError: parse_pptx() got an unexpected keyword argument 'caption_image'`

- [ ] **Step 3: `ingest/parsers/pptx_parser.py` を修正する**

ファイル冒頭のimportを書き換える（`sys` と `Emu`、`ingest.vlm.VlmError` を追加）。

```python
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

from ingest.models import SLIDE, ParsedUnit
from ingest.vlm import VlmError
```

`GROUP_TARGET_CHARS = 200` の直後に閾値定数を追加する。

```python
# ロゴ・アイコン等の装飾画像を除外するための閾値（配置サイズ、インチ角）。
# PDFの画素サイズと違い、スライド上に配置された大きさで判定できる。実データでの
# 実測は design docの6節を参照。未実測の仮値であり、後日調整する前提。
MIN_PICTURE_INCHES = 1.0
```

`_position` 関数の直後に、装飾画像の判定関数とキャプション生成関数を追加する。

```python
def _is_captionable_picture(shape) -> bool:
    if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
        return False
    return (
        Emu(shape.width).inches >= MIN_PICTURE_INCHES
        and Emu(shape.height).inches >= MIN_PICTURE_INCHES
    )


def _picture_block(shape, slide_number: int, path_name: str, caption_image) -> str | None:
    try:
        caption = caption_image(shape.image.blob)
    except VlmError as error:
        print(
            f"警告: 画像の説明取得に失敗しました（{path_name} スライド{slide_number}）: {error}",
            file=sys.stderr,
        )
        return None
    return f"[図の説明] {caption}"
```

`_blocks` を書き換える（シグネチャに `path_name` と `caption_image` を追加）。

```python
def _blocks(slide, slide_number: int, path_name: str = "", caption_image=None) -> list[str]:
    """読み順に並べた、内容のあるシェイプのテキスト。"""
    content_shapes = [
        shape
        for shape in _walk(slide.shapes)
        if shape.has_text_frame
        or (caption_image is not None and _is_captionable_picture(shape))
    ]
    content_shapes.sort(key=_position)

    blocks = []
    for shape in content_shapes:
        if shape.has_text_frame:
            cleaned = _clean(shape.text_frame.text, slide_number)
            if cleaned:
                blocks.append(cleaned)
        else:
            block = _picture_block(shape, slide_number, path_name, caption_image)
            if block is not None:
                blocks.append(block)

    # ノート欄には本文に書かれていない補足や発表意図が入るため取り込む。
    # 位置情報を持たないので読み順の最後尾に置く。
    if slide.has_notes_slide:
        notes = _clean(slide.notes_slide.notes_text_frame.text, slide_number)
        if notes:
            blocks.append(notes)
    return blocks
```

`parse_pptx` を書き換える。

```python
def parse_pptx(path: Path, caption_image=None) -> list[ParsedUnit]:
    units: list[ParsedUnit] = []
    for number, slide in enumerate(Presentation(path).slides, start=1):
        blocks = _blocks(slide, number, path_name=path.name, caption_image=caption_image)
        if not blocks:
            continue
        title, _, remainder = blocks[0].partition("\n")
        body = ([remainder] if remainder else []) + blocks[1:]
        for group in _group(body) or [""]:
            text = f"{title}\n{group}" if group else title
            units.append(
                ParsedUnit(
                    text=text,
                    location_type=SLIDE,
                    location=number,
                    vlm="[図の説明] " in text,
                )
            )
    return units
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_parsers_office.py -v`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/pptx_parser.py tests/test_parsers_office.py
git commit -m "feat: caption PPTX picture shapes with a VLM"
```

---

### Task 6: `ingest/parsers/__init__.py` — `caption_image` の橋渡し

**Files:**
- Modify: `ingest/parsers/__init__.py`
- Test: `tests/test_parsers_office.py`

**Interfaces:**
- Consumes: Task 4/5の `parse_pdf(path, ocr_page=None, caption_image=None)` / `parse_pptx(path, caption_image=None)`
- Produces: `parse(path: Path, caption_image=None) -> list[ParsedUnit]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parsers_office.py` の `test_dispatch_routes_by_suffix` の直後に追加する。

```python
def test_dispatch_passes_caption_image_to_pptx_only(docx_path, pptx_with_large_picture):
    seen = []
    parse(pptx_with_large_picture, caption_image=lambda b: seen.append(b) or "説明")
    assert seen, "pptxにはcaption_imageが渡っているはず"

    # docxはcaption_imageを受け取らないシグネチャなので、渡してもエラーにならず無視される
    parse(docx_path, caption_image=lambda b: "説明")
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_parsers_office.py -k dispatch_passes -v`
Expected: FAIL — `TypeError: parse() got an unexpected keyword argument 'caption_image'`

- [ ] **Step 3: `ingest/parsers/__init__.py` を修正する**

```python
def parse(path: Path, caption_image=None) -> list[ParsedUnit]:
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    if path.suffix.lower() in (".pdf", ".pptx"):
        return parser(path, caption_image=caption_image)
    return parser(path)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_parsers_office.py tests/test_parser_pdf.py -v`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/parsers/__init__.py tests/test_parsers_office.py
git commit -m "feat: route caption_image to the pdf/pptx parsers only"
```

---

### Task 7: `scripts/ingest_source.py` — `--with-vlm` フラグ

**Files:**
- Modify: `scripts/ingest_source.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 2の `vlm.check_vlm()`、Task 1の `vlm.caption_image`、Task 6の `parse(path, caption_image=None)`
- Produces: `ingest_directory(source_dir, collection, session=None, on_progress=None, force=False, only_suffix=None, caption_image=None) -> IngestReport`、CLIフラグ `--with-vlm`

このタスクは既存の `--force` / `--only-suffix` と同じ配線パターンをなぞるだけで、
新しい分岐ロジックのテストは要らない（それらも単体テストされていない）。挙動は
Task 4/5/6で検証済みの `caption_image` パラメータをそのまま上流から渡すだけである。

- [ ] **Step 1: `ingest_directory()` のシグネチャと呼び出しを変更する**

`scripts/ingest_source.py` の先頭のimportを変更する。

```python
from ingest import embedder, store, vlm
```

`ingest_directory` のシグネチャに `caption_image=None` を追加する。

```python
def ingest_directory(
    source_dir: Path,
    collection,
    session=None,
    on_progress=None,
    force: bool = False,
    only_suffix: str | None = None,
    caption_image=None,
) -> IngestReport:
```

本文中の `units = parse(path)` を次のように変更する。

```python
                units = parse(path, caption_image=caption_image)
```

- [ ] **Step 2: `main()` にCLIフラグと事前確認を追加する**

`parser.add_argument("--only-suffix", ...)` の直後に追加する。

```python
    parser.add_argument(
        "--with-vlm",
        action="store_true",
        help="PDF/PPTX内の埋め込み画像をVLMで説明文化する（取り込みが大幅に遅くなる）",
    )
```

`embedder.check_ollama()` の疎通確認ブロックの直後、`collection = store.open_collection(...)` の前に追加する。

```python
    caption_image = None
    if args.with_vlm:
        try:
            vlm.check_vlm()
        except vlm.VlmError as error:
            print(error)
            return 1
        caption_image = vlm.caption_image
```

`ingest_directory(...)` の呼び出しに `caption_image=caption_image` を追加する。

```python
    report = ingest_directory(
        args.source_dir,
        collection,
        on_progress=print,
        force=args.force,
        only_suffix=args.only_suffix,
        caption_image=caption_image,
    )
```

- [ ] **Step 3: 既存テストが壊れていないことを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest -q`
Expected: PASS（全件。`ingest_directory` の呼び出し元は `caption_image` を省略できるため、既存テストは無変更で通る）

- [ ] **Step 4: READMEに使い方を追記する**

`README.md` の「## 使い方」内、取り込みコマンド一覧（`# チャットを起動する` の直前）に追加する。

```markdown
# PDF/PPTX内の図・写真もVLMで説明文化する（大幅に時間が伸びる。事前に
# ollama pull qwen2.5vl:7b が必要。ColabのL4に接続していればそちらで処理される）
.\myvenv313\Scripts\python.exe -m scripts.ingest_source --with-vlm
```

- [ ] **Step 5: コミット**

```bash
git add scripts/ingest_source.py README.md
git commit -m "feat: add --with-vlm flag to caption embedded images during ingest"
```

---

## Self-Review Notes

- **Spec coverage:** spec 4節→Task1/2、5節→Task4、6節→Task5、7節→Task6、8節→Task7、9節→Task3、11節（エラー処理）→Task4/5の`_describe_images`/`_picture_block`、13節（時間影響）→Task7のREADME注記でカバーしている。12節のテスト方針は各Taskのテストで満たしている。14節（今回やらないこと）・15節（残るリスク）は実装対象外のため対応するタスクはない（意図どおり）。
- **Placeholder scan:** 各ステップに実コードを記載済み。「TODO」「後で」等は無い。
- **Type consistency:** `caption_image` は全タスクを通じて `Callable[[bytes], str]`（`VlmError` を送出しうる）で統一。`ParsedUnit(vlm=...)` のキーワード名もTask 3で定義したとおり全パーサーで一致させた。
