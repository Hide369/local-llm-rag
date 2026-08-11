# 非構造化データ取り込み機能 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PDF・PowerPoint・Word を完全ローカルでベクトルDBに取り込み、ページ番号付きの出典を示せるRAGチャットにする。

**Architecture:** 取り込みパイプラインを Streamlit から完全に分離し、`ingest/` 以下の純粋な関数群として実装する。各パーサーは形式の違いを `ParsedUnit`（テキスト + 出典位置）という共通の中間表現に吸収するため、チャンク分割・埋め込み・保存の各段は元の形式を一切知らない。差分取り込みの判定情報は ChromaDB のメタデータ自身に持たせ、状態の二重管理を避ける。

**Tech Stack:** PyMuPDF / python-pptx / python-docx / RapidOCR (onnxruntime) / langchain-text-splitters / Ollama (bge-m3) / ChromaDB / Streamlit / pytest

**設計書:** `docs/superpowers/specs/2026-08-11-document-ingestion-design.md`

## Global Constraints

- Python 3.13.3、仮想環境は `myvenv313`。すべてのコマンドは `.\myvenv313\Scripts\python.exe` 経由で実行する
- 外部サービスへの送信は一切行わない。埋め込み・生成・OCR はすべてローカル
- Ollama の接続先は既定 `http://127.0.0.1:12000`。**`localhost` は使用しない**（Windows環境で1リクエストあたり約2.1秒を浪費するため）。環境変数 `OLLAMA_HOST` で上書き可能とする
- 埋め込みモデルは `bge-m3`、次元数 1024、バッチサイズ **8**（32は1件あたり遅い）
- ChromaDB のコレクション名は `local_docs_v2`、距離空間は `cosine`。既存の `local_docs` には一切触れない（`udemy3.py` を動作させ続けるため）
- チャンクサイズ 800文字、オーバーラップ 100文字。800文字以下の単位は分割しない
- PDFのOCR判定境界は **30文字未満**、OCRのレンダリング解像度は **200dpi**
- チャンクIDの形式は `{source}::{location_type}{location}::{chunk_index}`
- コミットメッセージはコンベンショナルコミット形式、英語で記述する
- 作業ブランチは `feat/document-ingestion`

---

## File Structure

| ファイル | 責務 |
|---|---|
| `ingest/models.py` | `ParsedUnit` / `Chunk` のデータ構造定義。他モジュールが共有する語彙 |
| `ingest/chunker.py` | `ParsedUnit` を `Chunk` に変換。800字超のみ再分割、IDとメタデータを生成 |
| `ingest/ocr.py` | RapidOCR の遅延初期化ラッパー。PDFページ画像 → テキスト |
| `ingest/parsers/__init__.py` | 拡張子によるパーサーのディスパッチ |
| `ingest/parsers/pdf_parser.py` | PyMuPDF。テキストなしページをOCRへ委譲 |
| `ingest/parsers/pptx_parser.py` | python-pptx。スライド単位、ノート欄も取得 |
| `ingest/parsers/docx_parser.py` | python-docx。文書全体で1単位 |
| `ingest/embedder.py` | Ollama `/api/embed` 呼び出し。バッチ・接続再利用・リトライ |
| `ingest/store.py` | ChromaDB操作。ハッシュ差分判定、source単位の置換、孤児削除 |
| `scripts/ingest_source.py` | CLI。`source/` の走査と全体オーケストレーション |
| `scripts/check_retrieval.py` | 関連度しきい値を決めるための距離実測 |
| `rag_chat_app.py` | Streamlit UI。チャットと差分取り込みボタン |

---

## Task 1: 依存関係とデータ構造の基盤

**Files:**
- Create: `ingest/__init__.py`
- Create: `ingest/models.py`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`
- Create: `pytest.ini`

**Interfaces:**
- Consumes: なし（最初のタスク）
- Produces: `ParsedUnit(text: str, location_type: str, location: int, ocr: bool = False)`、`Chunk(id: str, text: str, metadata: dict)`、`ParsedUnit.label` プロパティ（`"p.48"` / `"スライド12"` / `""` を返す）

- [ ] **Step 1: 依存パッケージを導入する**

```powershell
.\myvenv313\Scripts\python.exe -m pip install pymupdf python-pptx rapidocr langchain-text-splitters pytest
```

`onnxruntime` 1.28.0、`python-docx` 1.2.0、`chromadb` 1.0.16、`requests` 2.32.3、`streamlit` 1.61.1 は導入済みのため対象外。

- [ ] **Step 2: 導入結果を確認する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import pymupdf, pptx, docx, rapidocr, langchain_text_splitters, pytest, chromadb; print('all ok')"
```
Expected: `all ok`

- [ ] **Step 3: pytest の設定ファイルを作る**

`pytest.ini`:
```ini
[pytest]
testpaths = tests
markers =
    integration: 実機のOCRモデルやOllamaを必要とする低速なテスト（既定では実行しない）
addopts = -m "not integration"
```

- [ ] **Step 4: 失敗するテストを書く**

`tests/__init__.py` は空ファイルとして作成する。

`tests/test_models.py`:
```python
from ingest.models import Chunk, ParsedUnit


def test_page_unit_label():
    unit = ParsedUnit(text="本文", location_type="page", location=48)
    assert unit.label == "p.48"


def test_slide_unit_label():
    unit = ParsedUnit(text="本文", location_type="slide", location=12)
    assert unit.label == "スライド12"


def test_document_unit_has_no_label():
    """docxのようにページ概念を持たない形式では位置ラベルを出さない。"""
    unit = ParsedUnit(text="本文", location_type="document", location=0)
    assert unit.label == ""


def test_unit_is_not_ocr_by_default():
    assert ParsedUnit(text="本文", location_type="page", location=1).ocr is False


def test_chunk_holds_id_text_and_metadata():
    chunk = Chunk(id="a.pdf::page1::0", text="本文", metadata={"source": "a.pdf"})
    assert chunk.id == "a.pdf::page1::0"
    assert chunk.metadata["source"] == "a.pdf"
```

- [ ] **Step 5: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest'`

- [ ] **Step 6: 最小限の実装を書く**

`ingest/__init__.py` は空ファイルとして作成する。

`ingest/models.py`:
```python
"""取り込みパイプライン全体で共有するデータ構造。

各パーサーはPDF・PPTX・DOCXの違いをすべて ParsedUnit に吸収する。
これにより後続のチャンク分割・埋め込み・保存は元の形式を知る必要がない。
"""
from dataclasses import dataclass, field

# 出典位置の種別。docxのようにページ概念を持たない形式は "document" を使う。
PAGE = "page"
SLIDE = "slide"
DOCUMENT = "document"

_LABEL_FORMATS = {PAGE: "p.{}", SLIDE: "スライド{}"}


@dataclass(frozen=True)
class ParsedUnit:
    """パーサーが返す最小単位。1ページ、1スライド、または文書全体。"""

    text: str
    location_type: str
    location: int
    ocr: bool = False

    @property
    def label(self) -> str:
        """出典表示に使う位置ラベル。位置概念がない形式では空文字を返す。"""
        fmt = _LABEL_FORMATS.get(self.location_type)
        return fmt.format(self.location) if fmt else ""


@dataclass(frozen=True)
class Chunk:
    """ベクトルDBに保存する単位。"""

    id: str
    text: str
    metadata: dict = field(default_factory=dict)
```

- [ ] **Step 7: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: PASS（5件）

- [ ] **Step 8: コミットする**

```bash
git add ingest/ tests/ pytest.ini
git commit -m "feat: add shared data structures for the ingestion pipeline

ParsedUnit is the common intermediate representation that lets every
parser hide its format from the rest of the pipeline.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: チャンク分割

**Files:**
- Create: `ingest/chunker.py`
- Create: `tests/test_chunker.py`

**Interfaces:**
- Consumes: `ingest.models.ParsedUnit`, `ingest.models.Chunk`
- Produces: `chunk_units(units: list[ParsedUnit], source: str, file_hash: str, indexed_at: str) -> list[Chunk]`、定数 `CHUNK_SIZE = 800`, `CHUNK_OVERLAP = 100`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chunker.py`:
```python
from ingest.chunker import CHUNK_SIZE, chunk_units
from ingest.models import ParsedUnit


def _unit(text, location=1, location_type="page", ocr=False):
    return ParsedUnit(text=text, location_type=location_type, location=location, ocr=ocr)


def _chunk(units):
    return chunk_units(units, source="a.pdf", file_hash="abc123", indexed_at="2026-08-11")


def test_short_unit_becomes_exactly_one_chunk():
    """議事録のような800字未満の文書は分割せず1つの文脈として保つ。"""
    chunks = _chunk([_unit("短い本文")])
    assert len(chunks) == 1
    assert chunks[0].text == "短い本文"


def test_long_unit_is_split():
    chunks = _chunk([_unit("あ" * 2000)])
    assert len(chunks) > 1
    assert all(len(c.text) <= CHUNK_SIZE for c in chunks)


def test_empty_unit_produces_no_chunk():
    assert _chunk([_unit("   ")]) == []


def test_id_is_deterministic():
    """同じ資料を再取り込みしても同じIDになり、重複登録が起きない。"""
    first = _chunk([_unit("本文", location=48)])
    second = _chunk([_unit("本文", location=48)])
    assert first[0].id == second[0].id == "a.pdf::page48::0"


def test_split_chunks_get_sequential_indexes():
    chunks = _chunk([_unit("あ" * 2000, location=3)])
    assert [c.metadata["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert chunks[0].id == "a.pdf::page3::0"
    assert chunks[1].id == "a.pdf::page3::1"


def test_location_is_carried_into_every_chunk():
    """出典表示のため、分割後の全チャンクがページ番号を保持する必要がある。"""
    chunks = _chunk([_unit("あ" * 2000, location=48)])
    assert all(c.metadata["location"] == 48 for c in chunks)
    assert all(c.metadata["location_type"] == "page" for c in chunks)


def test_ocr_flag_is_carried_into_every_chunk():
    chunks = _chunk([_unit("あ" * 2000, ocr=True)])
    assert all(c.metadata["ocr"] is True for c in chunks)


def test_metadata_contains_source_hash_and_date():
    chunk = _chunk([_unit("本文")])[0]
    assert chunk.metadata["source"] == "a.pdf"
    assert chunk.metadata["file_hash"] == "abc123"
    assert chunk.metadata["indexed_at"] == "2026-08-11"


def test_units_are_processed_independently():
    """ページをまたいで結合しない。混ざるとページ番号が特定できなくなる。"""
    chunks = _chunk([_unit("一ページ目", location=1), _unit("二ページ目", location=2)])
    assert len(chunks) == 2
    assert chunks[0].metadata["location"] == 1
    assert chunks[1].metadata["location"] == 2
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_chunker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.chunker'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/chunker.py`:
```python
"""ParsedUnit を ベクトルDB に入れる Chunk へ変換する。

1ページ・1スライドを基本単位とし、長すぎるものだけを再分割する。
実測では就業規則841字/ページ、PPTX304字/スライド、画像PDF約1,673字/ページであり、
議事録(551〜615字)は分割されず1件1チャンクに収まる。
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingest.models import Chunk, ParsedUnit

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 日本語は空白で語が区切られないため、句読点を区切り候補に含める。
# これがないと文の途中で不自然に切れて検索精度が落ちる。
_SEPARATORS = ["\n\n", "\n", "。", "、", " ", ""]

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=_SEPARATORS,
)


def _split(text: str) -> list[str]:
    """800字以下はそのまま返す。分割器を通すと余計な境界調整が入るため。"""
    if len(text) <= CHUNK_SIZE:
        return [text]
    return [part for part in _splitter.split_text(text) if part.strip()]


def chunk_units(
    units: list[ParsedUnit], source: str, file_hash: str, indexed_at: str
) -> list[Chunk]:
    """各ユニットを独立にチャンク化する。

    ユニットをまたいで結合しない。結合するとチャンクがページ境界を越え、
    「何ページ目の記述か」を一意に示せなくなる。
    """
    chunks: list[Chunk] = []
    for unit in units:
        text = unit.text.strip()
        if not text:
            continue
        for index, part in enumerate(_split(text)):
            chunks.append(
                Chunk(
                    id=f"{source}::{unit.location_type}{unit.location}::{index}",
                    text=part,
                    metadata={
                        "source": source,
                        "file_hash": file_hash,
                        "location_type": unit.location_type,
                        "location": unit.location,
                        "ocr": unit.ocr,
                        "chunk_index": index,
                        "indexed_at": indexed_at,
                    },
                )
            )
    return chunks
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_chunker.py -v`
Expected: PASS（9件）

- [ ] **Step 5: コミットする**

```bash
git add ingest/chunker.py tests/test_chunker.py
git commit -m "feat: split parsed units into chunks with source metadata

Units are chunked independently so every chunk keeps an unambiguous page
or slide number for citation. Units at or below 800 characters pass
through whole, which keeps each meeting minute in one piece.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: DOCX / PPTX パーサー

**Files:**
- Create: `ingest/parsers/__init__.py`（この時点ではdocxとpptxのみ登録）
- Create: `ingest/parsers/docx_parser.py`
- Create: `ingest/parsers/pptx_parser.py`
- Create: `tests/test_parsers_office.py`

**Interfaces:**
- Consumes: `ingest.models.ParsedUnit`, `ingest.models.DOCUMENT`, `ingest.models.SLIDE`
- Produces: `parse_docx(path: Path) -> list[ParsedUnit]`、`parse_pptx(path: Path) -> list[ParsedUnit]`、`ingest.parsers.parse(path: Path) -> list[ParsedUnit]`、`ingest.parsers.SUPPORTED_SUFFIXES: set[str]`、例外 `UnsupportedFormatError`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parsers_office.py`:
```python
import pytest
from docx import Document
from pptx import Presentation
from pptx.util import Inches

from ingest.parsers import UnsupportedFormatError, parse
from ingest.parsers.docx_parser import parse_docx
from ingest.parsers.pptx_parser import parse_pptx


@pytest.fixture
def docx_path(tmp_path):
    """テスト用のdocxをその場で生成する（バイナリをリポジトリに置かないため）。"""
    doc = Document()
    doc.add_paragraph("会議名：キックオフ")
    doc.add_paragraph("")  # 空段落は無視されること
    doc.add_paragraph("決定事項：RAGを導入する")
    path = tmp_path / "議事録.docx"
    doc.save(path)
    return path


@pytest.fixture
def pptx_path(tmp_path):
    prs = Presentation()
    blank = prs.slide_layouts[6]

    slide1 = prs.slides.add_slide(blank)
    box = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    box.text_frame.text = "一枚目のタイトル"

    slide2 = prs.slides.add_slide(blank)
    box2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    box2.text_frame.text = "二枚目の本文"
    slide2.notes_slide.notes_text_frame.text = "発表者ノート"

    path = tmp_path / "資料.pptx"
    prs.save(path)
    return path


def test_docx_becomes_a_single_document_unit(docx_path):
    units = parse_docx(docx_path)
    assert len(units) == 1
    assert units[0].location_type == "document"
    assert units[0].location == 0


def test_docx_joins_paragraphs_and_drops_empty_ones(docx_path):
    text = parse_docx(docx_path)[0].text
    assert "会議名：キックオフ" in text
    assert "決定事項：RAGを導入する" in text
    assert "\n\n" not in text


def test_pptx_produces_one_unit_per_slide(pptx_path):
    units = parse_pptx(pptx_path)
    assert len(units) == 2
    assert [u.location for u in units] == [1, 2]
    assert all(u.location_type == "slide" for u in units)


def test_pptx_includes_speaker_notes(pptx_path):
    """ノート欄には本文に書かれない補足が入るため取り込み対象にする。"""
    assert "発表者ノート" in parse_pptx(pptx_path)[1].text


def test_pptx_slide_text_is_captured(pptx_path):
    assert "一枚目のタイトル" in parse_pptx(pptx_path)[0].text


def test_office_parsers_are_not_marked_as_ocr(docx_path, pptx_path):
    assert parse_docx(docx_path)[0].ocr is False
    assert all(u.ocr is False for u in parse_pptx(pptx_path))


def test_dispatch_routes_by_suffix(docx_path, pptx_path):
    assert parse(docx_path)[0].location_type == "document"
    assert parse(pptx_path)[0].location_type == "slide"


def test_dispatch_rejects_unsupported_suffix(tmp_path):
    other = tmp_path / "memo.txt"
    other.write_text("本文", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError):
        parse(other)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_parsers_office.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.parsers'`

- [ ] **Step 3: docxパーサーを実装する**

`ingest/parsers/docx_parser.py`:
```python
"""Word文書のテキスト抽出。

docxにはページの概念が（レンダリングするまで）存在しないため、
文書全体を1つのユニットとして扱う。
"""
from pathlib import Path

from docx import Document

from ingest.models import DOCUMENT, ParsedUnit


def parse_docx(path: Path) -> list[ParsedUnit]:
    text = "\n".join(p.text for p in Document(path).paragraphs if p.text.strip())
    if not text.strip():
        return []
    return [ParsedUnit(text=text, location_type=DOCUMENT, location=0)]
```

- [ ] **Step 4: pptxパーサーを実装する**

`ingest/parsers/pptx_parser.py`:
```python
"""PowerPointのテキスト抽出。

スライドは話題の区切りそのものなので、1スライド=1ユニットとする。
"""
from pathlib import Path

from pptx import Presentation

from ingest.models import SLIDE, ParsedUnit


def _slide_text(slide) -> str:
    parts = [
        shape.text_frame.text for shape in slide.shapes if shape.has_text_frame
    ]
    # ノート欄には本文に書かれていない補足や発表意図が入るため取り込む。
    if slide.has_notes_slide:
        parts.append(slide.notes_slide.notes_text_frame.text)
    return "\n".join(part for part in parts if part.strip())


def parse_pptx(path: Path) -> list[ParsedUnit]:
    units = []
    for number, slide in enumerate(Presentation(path).slides, start=1):
        text = _slide_text(slide)
        if text.strip():
            units.append(ParsedUnit(text=text, location_type=SLIDE, location=number))
    return units
```

- [ ] **Step 5: ディスパッチを実装する**

`ingest/parsers/__init__.py`:
```python
"""拡張子に応じて適切なパーサーへ振り分ける。

新しい形式に対応するときは、パーサーを1つ書いて _PARSERS に登録するだけでよい。
"""
from pathlib import Path

from ingest.models import ParsedUnit
from ingest.parsers.docx_parser import parse_docx
from ingest.parsers.pptx_parser import parse_pptx


class UnsupportedFormatError(Exception):
    """取り込み対象外の拡張子を渡された。"""


_PARSERS = {".docx": parse_docx, ".pptx": parse_pptx}

SUPPORTED_SUFFIXES = set(_PARSERS)


def parse(path: Path) -> list[ParsedUnit]:
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    return parser(path)
```

- [ ] **Step 6: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_parsers_office.py -v`
Expected: PASS（8件）

- [ ] **Step 7: コミットする**

```bash
git add ingest/parsers/ tests/test_parsers_office.py
git commit -m "feat: add DOCX and PPTX parsers with suffix dispatch

Slides become one unit each since a slide is already a topic boundary,
and speaker notes are included because they carry context the slide body
does not.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: OCRラッパー

**Files:**
- Create: `ingest/ocr.py`
- Create: `tests/test_ocr.py`

**Interfaces:**
- Consumes: なし
- Produces: `ocr_page(page) -> str`（`page` は `pymupdf.Page`）、`reset_engine() -> None`、定数 `OCR_DPI = 200`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ocr.py`:
```python
import pymupdf
import pytest

import ingest.ocr as ocr_module
from ingest.ocr import OCR_DPI, ocr_page, reset_engine


class _FakeResult:
    def __init__(self, txts):
        self.txts = txts


@pytest.fixture(autouse=True)
def _clean_engine():
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def blank_page():
    doc = pymupdf.open()
    doc.new_page()
    yield doc[0]
    doc.close()


def test_engine_is_not_created_until_first_use():
    """エンジン生成に実測4.8秒かかるため、画像ページに遭遇するまで作らない。"""
    assert ocr_module._engine is None


def test_recognized_texts_are_joined(blank_page, monkeypatch):
    monkeypatch.setattr(
        ocr_module, "_build_engine", lambda: (lambda _img: _FakeResult(["社内", "ナレッジ"]))
    )
    assert ocr_page(blank_page) == "社内 ナレッジ"


def test_engine_is_built_only_once(blank_page, monkeypatch):
    calls = []

    def _build():
        calls.append(1)
        return lambda _img: _FakeResult(["文字"])

    monkeypatch.setattr(ocr_module, "_build_engine", _build)
    ocr_page(blank_page)
    ocr_page(blank_page)
    assert len(calls) == 1


def test_no_recognized_text_returns_empty_string(blank_page, monkeypatch):
    monkeypatch.setattr(
        ocr_module, "_build_engine", lambda: (lambda _img: _FakeResult(None))
    )
    assert ocr_page(blank_page) == ""


def test_dpi_is_200():
    """150/200/300dpiで精度も速度も変わらなかったため、上げる意味がない。"""
    assert OCR_DPI == 200


@pytest.mark.integration
def test_real_engine_reads_japanese_from_the_source_pdf():
    """実機確認。初回はモデルのダウンロードが走る。"""
    from pathlib import Path

    pdf = Path("source/Claude_Code_法人導入ガイド_スライド.pdf")
    if not pdf.exists():
        pytest.skip("source PDFがありません")
    doc = pymupdf.open(pdf)
    text = ocr_page(doc[0])
    doc.close()
    assert "本コース" in text
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_ocr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.ocr'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/ocr.py`:
```python
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


def ocr_page(page) -> str:
    """PyMuPDFのページを画像化してOCRし、認識文字列を連結して返す。"""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    result = _engine(page.get_pixmap(dpi=OCR_DPI).tobytes("png"))
    return " ".join(result.txts) if result.txts else ""
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_ocr.py -v`
Expected: PASS（5件）。`integration` マークのテストは `pytest.ini` の設定により実行されない

- [ ] **Step 5: 実機テストを1回だけ実行して確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_ocr.py -v -m integration`
Expected: PASS（1件）。初回はモデルのダウンロードが走るため数分かかる場合がある

- [ ] **Step 6: コミットする**

```bash
git add ingest/ocr.py tests/test_ocr.py
git commit -m "feat: add lazily initialised Japanese OCR wrapper

Building the RapidOCR engine costs ~4.8s and keeps models resident, so it
is deferred until an image page is actually encountered. Rendering is
fixed at 200dpi because 150/200/300 measured the same.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: PDFパーサーとOCRフォールバック

**Files:**
- Create: `ingest/parsers/pdf_parser.py`
- Modify: `ingest/parsers/__init__.py`（`.pdf` を `_PARSERS` に追加）
- Create: `tests/test_parser_pdf.py`

**Interfaces:**
- Consumes: `ingest.models.ParsedUnit`, `ingest.models.PAGE`, `ingest.ocr.ocr_page`
- Produces: `parse_pdf(path: Path, ocr_page=None) -> list[ParsedUnit]`、定数 `OCR_MIN_CHARS = 30`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_pdf.py`:
```python
import pymupdf
import pytest

from ingest.parsers import parse
from ingest.parsers.pdf_parser import OCR_MIN_CHARS, parse_pdf


def _make_pdf(tmp_path, page_texts):
    """指定した文字列を各ページに書いたPDFを生成する。空文字なら白紙ページ。"""
    doc = pymupdf.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text, fontsize=14)
    path = tmp_path / "test.pdf"
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def text_pdf(tmp_path):
    return _make_pdf(tmp_path, ["Chapter one has plenty of extractable text here."])


@pytest.fixture
def image_pdf(tmp_path):
    """テキストを持たない白紙ページ = 画像PDFと同じ扱いになる。"""
    return _make_pdf(tmp_path, [""])


def test_text_page_is_extracted_without_ocr(text_pdf):
    def _fail(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    units = parse_pdf(text_pdf, ocr_page=_fail)
    assert len(units) == 1
    assert "Chapter one" in units[0].text
    assert units[0].ocr is False


def test_page_without_text_falls_back_to_ocr(image_pdf):
    units = parse_pdf(image_pdf, ocr_page=lambda _page: "OCRで読んだ文字")
    assert len(units) == 1
    assert units[0].text == "OCRで読んだ文字"
    assert units[0].ocr is True


def test_pages_are_numbered_from_one(tmp_path):
    path = _make_pdf(tmp_path, ["First page with enough text to skip OCR entirely.",
                                "Second page with enough text to skip OCR entirely."])
    units = parse_pdf(path, ocr_page=lambda _page: "")
    assert [u.location for u in units] == [1, 2]
    assert all(u.location_type == "page" for u in units)


def test_page_is_skipped_when_ocr_also_finds_nothing(image_pdf):
    """白紙ページで空チャンクを作らない。"""
    assert parse_pdf(image_pdf, ocr_page=lambda _page: "") == []


def test_ocr_threshold_is_30_characters():
    """就業規則PDFの最少ページが66字、画像PDFが0字。この境界で完全に分離できる。"""
    assert OCR_MIN_CHARS == 30


def test_dispatch_handles_pdf(text_pdf):
    assert parse(text_pdf)[0].location_type == "page"
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_parser_pdf.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.parsers.pdf_parser'`

- [ ] **Step 3: PDFパーサーを実装する**

`ingest/parsers/pdf_parser.py`:
```python
"""PDFのテキスト抽出。画像ページはOCRへ回す。

source/ の実測では、テキストPDF(モデル就業規則)は最少ページでも66文字、
画像PDF(Claude_Code_法人導入ガイド)は全23ページが0文字だった。
30文字を境界にすれば実データ上は完全に分離できる。
"""
from pathlib import Path

import pymupdf

from ingest.models import PAGE, ParsedUnit

OCR_MIN_CHARS = 30


def parse_pdf(path: Path, ocr_page=None) -> list[ParsedUnit]:
    """PDFを1ページ1ユニットで読む。

    ocr_page はテストで差し替えられるよう引数にしている。省略時は実際のOCRを使う。
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
            if text:
                units.append(
                    ParsedUnit(
                        text=text, location_type=PAGE, location=number, ocr=used_ocr
                    )
                )
    finally:
        doc.close()
    return units
```

- [ ] **Step 4: ディスパッチにPDFを登録する**

`ingest/parsers/__init__.py` を以下のように変更する。

インポート行に追加:
```python
from ingest.parsers.pdf_parser import parse_pdf
```

`_PARSERS` を差し替え:
```python
_PARSERS = {".pdf": parse_pdf, ".docx": parse_docx, ".pptx": parse_pptx}
```

- [ ] **Step 5: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全28件。既存タスクのテストも壊れていないこと）

- [ ] **Step 6: コミットする**

```bash
git add ingest/parsers/ tests/test_parser_pdf.py
git commit -m "feat: add PDF parser with OCR fallback for image-only pages

Pages yielding fewer than 30 characters are rendered and OCR'd. The
threshold separates the real corpus cleanly: the text PDF's thinnest page
holds 66 characters and the image PDF's pages hold none.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: 埋め込みクライアント

**Files:**
- Create: `ingest/embedder.py`
- Create: `tests/test_embedder.py`

**Interfaces:**
- Consumes: なし
- Produces: `embed_texts(texts: list[str], session=None) -> list[list[float]]`、`embed_query(text: str, session=None) -> list[float]`、`check_ollama(session=None) -> None`、`new_session() -> requests.Session`、例外 `EmbeddingError`、定数 `OLLAMA_HOST`, `EMBED_MODEL = "bge-m3"`, `EMBED_BATCH_SIZE = 8`, `EMBED_DIM = 1024`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_embedder.py`:
```python
import pytest
import requests

import ingest.embedder as embedder
from ingest.embedder import (
    EMBED_BATCH_SIZE,
    EMBED_DIM,
    EMBED_MODEL,
    OLLAMA_HOST,
    EmbeddingError,
    check_ollama,
    embed_query,
    embed_texts,
)


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


def _vectors(count):
    return _FakeResponse({"embeddings": [[0.1] * EMBED_DIM for _ in range(count)]})


def test_host_never_uses_localhost():
    """Windowsでは localhost 解決に約2.1秒かかる。127.0.0.1 なら約80ms。"""
    assert "localhost" not in OLLAMA_HOST
    assert "127.0.0.1" in OLLAMA_HOST


def test_uses_bge_m3(monkeypatch):
    session = _FakeSession([_vectors(1)])
    embed_texts(["本文"], session=session)
    assert session.payloads[0]["model"] == EMBED_MODEL == "bge-m3"


def test_batches_are_capped_at_eight():
    """batch=32は1件あたり1,417ms、batch=8は1,197ms。大きすぎるバッチは不利。"""
    assert EMBED_BATCH_SIZE == 8
    session = _FakeSession([_vectors(8), _vectors(8), _vectors(4)])
    result = embed_texts([f"本文{i}" for i in range(20)], session=session)
    assert [len(p["input"]) for p in session.payloads] == [8, 8, 4]
    assert len(result) == 20


def test_empty_input_makes_no_request():
    session = _FakeSession([])
    assert embed_texts([], session=session) == []
    assert session.payloads == []


def test_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(embedder.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("boom"), _vectors(1)])
    assert len(embed_texts(["本文"], session=session)) == 1


def test_backoff_is_exponential(monkeypatch):
    waits = []
    monkeypatch.setattr(embedder.time, "sleep", waits.append)
    session = _FakeSession(
        [requests.ConnectionError("x"), requests.ConnectionError("x"), _vectors(1)]
    )
    embed_texts(["本文"], session=session)
    assert waits == [1, 2]


def test_gives_up_after_all_attempts(monkeypatch):
    monkeypatch.setattr(embedder.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("x")] * 4)
    with pytest.raises(EmbeddingError):
        embed_texts(["本文"], session=session)


def test_wrong_dimension_is_rejected():
    """モデルを取り違えると次元が変わり、DBに入れてから壊れていることに気付く。"""
    session = _FakeSession([_FakeResponse({"embeddings": [[0.1] * 768]})])
    with pytest.raises(EmbeddingError):
        embed_texts(["本文"], session=session)


def test_embed_query_returns_a_single_vector():
    session = _FakeSession([_vectors(1)])
    assert len(embed_query("質問", session=session)) == EMBED_DIM


def test_check_ollama_raises_when_unreachable():
    session = _FakeSession([requests.ConnectionError("refused")])
    with pytest.raises(EmbeddingError, match="Ollama"):
        check_ollama(session=session)


def test_check_ollama_passes_when_model_present():
    session = _FakeSession([_FakeResponse({"models": [{"name": "bge-m3:latest"}]})])
    check_ollama(session=session)


def test_check_ollama_raises_when_model_missing():
    session = _FakeSession([_FakeResponse({"models": [{"name": "llama3.1:8b"}]})])
    with pytest.raises(EmbeddingError, match="bge-m3"):
        check_ollama(session=session)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_embedder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.embedder'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/embedder.py`:
```python
"""Ollama の埋め込みAPIを叩く。

接続先に localhost を使ってはならない。Windowsでは localhost が先にIPv6の ::1 に
解決され、OllamaがIPv4でしか待ち受けていないためタイムアウト待ちが発生する。
実測: localhost + 毎回新規接続 2,151ms / 127.0.0.1 79ms / Session再利用 77ms。
Ollama自身の処理時間はいずれも約80msである。
"""
import os
import time

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:12000")
EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024

# batch=8で1,197ms/件、batch=32で1,417ms/件。16GBのメモリでは大きなバッチが不利。
EMBED_BATCH_SIZE = 8

_MAX_ATTEMPTS = 4  # 初回 + 3回の再試行（1秒 → 2秒 → 4秒）
_TIMEOUT = 600


class EmbeddingError(Exception):
    """埋め込みの取得に失敗した。"""


def new_session() -> requests.Session:
    """接続を再利用するセッションを作る。使い回すことで1リクエストあたり約2秒を節約できる。"""
    return requests.Session()


def _post_batch(session, texts: list[str]) -> list[list[float]]:
    url = f"{OLLAMA_HOST}/api/embed"
    payload = {"model": EMBED_MODEL, "input": texts, "keep_alive": "30m"}
    last_error = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = session.post(url, json=payload, timeout=_TIMEOUT)
            response.raise_for_status()
            vectors = response.json()["embeddings"]
        except (requests.RequestException, KeyError, ValueError) as error:
            last_error = error
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(2**attempt)
            continue
        # モデルを取り違えると次元が変わる。DBに書き込む前にここで止める。
        if any(len(vector) != EMBED_DIM for vector in vectors):
            raise EmbeddingError(
                f"埋め込みの次元が想定と違います（期待 {EMBED_DIM}）。"
                f"モデル {EMBED_MODEL} が正しいか確認してください。"
            )
        return vectors
    raise EmbeddingError(
        f"{OLLAMA_HOST} への埋め込みリクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
    )


def embed_texts(texts: list[str], session=None) -> list[list[float]]:
    """テキスト列をバッチに分けて埋め込む。"""
    if not texts:
        return []
    own_session = session is None
    session = session or new_session()
    try:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            vectors.extend(_post_batch(session, texts[start : start + EMBED_BATCH_SIZE]))
        return vectors
    finally:
        if own_session:
            session.close()


def embed_query(text: str, session=None) -> list[float]:
    return embed_texts([text], session=session)[0]


def check_ollama(session=None) -> None:
    """取り込み開始前の疎通確認。

    260チャンクの処理を始めてから落ちるのを防ぐため、先に一度だけ確認する。
    """
    own_session = session is None
    session = session or new_session()
    try:
        try:
            response = session.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
            response.raise_for_status()
            names = [model["name"] for model in response.json().get("models", [])]
        except (requests.RequestException, KeyError, ValueError) as error:
            raise EmbeddingError(
                f"Ollamaに接続できません（{OLLAMA_HOST}）。"
                f"起動しているか確認してください: {error}"
            ) from error
        if not any(name.split(":")[0] == EMBED_MODEL for name in names):
            raise EmbeddingError(
                f"埋め込みモデル {EMBED_MODEL} がありません。"
                f"`ollama pull {EMBED_MODEL}` を実行してください。"
            )
    finally:
        if own_session:
            session.close()
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_embedder.py -v`
Expected: PASS（12件）

- [ ] **Step 5: 実機で疎通を確認する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "from ingest.embedder import check_ollama, embed_query; check_ollama(); print('dim:', len(embed_query('経費精算の上限は')))"
```
Expected: `dim: 1024`

- [ ] **Step 6: コミットする**

```bash
git add ingest/embedder.py tests/test_embedder.py
git commit -m "feat: add batched bge-m3 embedding client over a reused session

Binds to 127.0.0.1 rather than localhost: on Windows the latter resolves
to ::1 first and costs ~2.1s per request against Ollama's ~80ms of actual
work. Batches are capped at 8, which measured faster per item than 32.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: ChromaDBストア

**Files:**
- Create: `ingest/store.py`
- Create: `tests/test_store.py`

**Interfaces:**
- Consumes: `ingest.models.Chunk`, `ingest.embedder.EMBED_DIM`
- Produces: `open_collection(client)`、`stored_file_hash(collection, source) -> str | None`、`replace_source(collection, source, chunks, embeddings) -> None`、`indexed_sources(collection) -> set[str]`、`delete_orphans(collection, known_sources) -> list[str]`、定数 `COLLECTION_NAME = "local_docs_v2"`, `DISTANCE_SPACE = "cosine"`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_store.py`:
```python
import chromadb
import pytest

from ingest.embedder import EMBED_DIM
from ingest.models import Chunk
from ingest.store import (
    COLLECTION_NAME,
    DISTANCE_SPACE,
    delete_orphans,
    indexed_sources,
    open_collection,
    replace_source,
    stored_file_hash,
)


@pytest.fixture
def collection():
    """ディスクに触れないインメモリのChromaを使う。"""
    return open_collection(chromadb.EphemeralClient())


def _chunks(source, file_hash, count=2):
    return [
        Chunk(
            id=f"{source}::page{i}::0",
            text=f"{source}の{i}ページ目",
            metadata={
                "source": source,
                "file_hash": file_hash,
                "location_type": "page",
                "location": i,
                "ocr": False,
                "chunk_index": 0,
                "indexed_at": "2026-08-11",
            },
        )
        for i in range(1, count + 1)
    ]


def _vectors(count):
    return [[0.1] * EMBED_DIM for _ in range(count)]


def _add(collection, source, file_hash, count=2):
    chunks = _chunks(source, file_hash, count)
    replace_source(collection, source, chunks, _vectors(len(chunks)))
    return chunks


def test_collection_name_does_not_collide_with_the_course_collection():
    """local_docs は udemy3.py が768次元で使い続けるため触らない。"""
    assert COLLECTION_NAME == "local_docs_v2"


def test_collection_uses_cosine(collection):
    config = getattr(collection, "configuration_json", None) or {}
    assert (config.get("hnsw") or {}).get("space") == DISTANCE_SPACE == "cosine"


def test_stored_hash_is_none_for_unknown_source(collection):
    assert stored_file_hash(collection, "未登録.pdf") is None


def test_stored_hash_is_returned_after_adding(collection):
    _add(collection, "a.pdf", "hash1")
    assert stored_file_hash(collection, "a.pdf") == "hash1"


def test_replacing_a_source_removes_its_old_chunks(collection):
    _add(collection, "a.pdf", "hash1", count=5)
    _add(collection, "a.pdf", "hash2", count=2)
    assert collection.count() == 2
    assert stored_file_hash(collection, "a.pdf") == "hash2"


def test_replacing_a_source_leaves_other_sources_intact(collection):
    _add(collection, "a.pdf", "hash1", count=3)
    _add(collection, "b.pptx", "hash2", count=2)
    _add(collection, "a.pdf", "hash3", count=1)
    assert collection.count() == 3
    assert stored_file_hash(collection, "b.pptx") == "hash2"


def test_indexed_sources_lists_every_source(collection):
    _add(collection, "a.pdf", "hash1")
    _add(collection, "b.pptx", "hash2")
    assert indexed_sources(collection) == {"a.pdf", "b.pptx"}


def test_orphans_are_deleted(collection):
    """source/ から資料を消したら、DB側も追従しないと幽霊の出典が出る。"""
    _add(collection, "a.pdf", "hash1")
    _add(collection, "消した.pptx", "hash2")
    removed = delete_orphans(collection, known_sources={"a.pdf"})
    assert removed == ["消した.pptx"]
    assert indexed_sources(collection) == {"a.pdf"}


def test_nothing_is_deleted_when_all_sources_are_known(collection):
    _add(collection, "a.pdf", "hash1")
    assert delete_orphans(collection, known_sources={"a.pdf"}) == []
    assert collection.count() == 2


def test_metadata_survives_a_round_trip(collection):
    _add(collection, "a.pdf", "hash1", count=1)
    stored = collection.get(include=["metadatas"])["metadatas"][0]
    assert stored["location"] == 1
    assert stored["location_type"] == "page"
    assert stored["ocr"] is False
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.store'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/store.py`:
```python
"""ChromaDBへの保存と差分管理。

差分判定に使う file_hash は各チャンクのメタデータに持たせる。別途マニフェスト
ファイルを置くとDBとファイルで状態が二重管理になり、必ず食い違うため。
信頼できる情報源は常にDBひとつにする。
"""
from ingest.models import Chunk

# udemy3.py が使う local_docs (nomic-embed-text / 768次元) とは別に作る。
# 同じコレクションを使い回すと次元不一致で既存の教材が動かなくなる。
COLLECTION_NAME = "local_docs_v2"
DISTANCE_SPACE = "cosine"


def open_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": DISTANCE_SPACE}
    )


def stored_file_hash(collection, source: str) -> str | None:
    """登録済みならそのファイルのハッシュを返す。未登録ならNone。"""
    found = collection.get(where={"source": source}, limit=1, include=["metadatas"])
    metadatas = found.get("metadatas") or []
    return metadatas[0].get("file_hash") if metadatas else None


def replace_source(collection, source: str, chunks: list[Chunk], embeddings) -> None:
    """1つの資料のチャンクを丸ごと入れ替える。

    先に古いチャンクを消してから入れる。ページ数が減った資料を再取り込みしたとき、
    上書きだけでは末尾の古いページが残ってしまうため。
    """
    collection.delete(where={"source": source})
    if not chunks:
        return
    collection.add(
        ids=[chunk.id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[chunk.metadata for chunk in chunks],
        embeddings=list(embeddings),
    )


def indexed_sources(collection) -> set[str]:
    if collection.count() == 0:
        return set()
    metadatas = collection.get(include=["metadatas"]).get("metadatas") or []
    return {meta["source"] for meta in metadatas if "source" in meta}


def delete_orphans(collection, known_sources: set[str]) -> list[str]:
    """source/ に存在しなくなった資料のチャンクを削除し、削除した資料名を返す。"""
    orphans = sorted(indexed_sources(collection) - set(known_sources))
    for source in orphans:
        collection.delete(where={"source": source})
    return orphans
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: PASS（10件）

- [ ] **Step 5: 既存コレクションが無傷であることを確認する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; c=chromadb.PersistentClient(path=r'.\chroma_db'); print([(x.name, c.get_collection(x.name).count()) for x in c.list_collections()])"
```
Expected: `[('local_docs', 21)]` — 教材のコレクションが21チャンクのまま残っていること

- [ ] **Step 6: コミットする**

```bash
git add ingest/store.py tests/test_store.py
git commit -m "feat: add Chroma store with hash-based incremental re-ingest

The file hash lives in chunk metadata rather than a side manifest, so the
database stays the single source of truth. Sources are replaced whole and
sources missing from disk are pruned to avoid stale citations.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: 取り込みCLIと初回実行

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/ingest_source.py`
- Create: `tests/test_ingest_source.py`

**Interfaces:**
- Consumes: `ingest.parsers.parse`, `ingest.chunker.chunk_units`, `ingest.embedder`, `ingest.store`
- Produces: `file_hash(path: Path) -> str`、`ingest_directory(source_dir, collection, session=None, on_progress=None, force=False) -> IngestReport`、`IngestReport(indexed: dict[str, int], skipped: list[str], failed: dict[str, str], removed: list[str])`、定数 `DEFAULT_SOURCE_DIR = Path("source")`, `DB_DIR`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ingest_source.py`:
```python
import chromadb
import pytest
from docx import Document

from ingest.embedder import EMBED_DIM
from ingest.store import open_collection, stored_file_hash
from scripts.ingest_source import file_hash, ingest_directory


@pytest.fixture
def collection():
    return open_collection(chromadb.EphemeralClient())


@pytest.fixture
def source_dir(tmp_path):
    directory = tmp_path / "source"
    directory.mkdir()
    return directory


def _write_docx(directory, name, body):
    doc = Document()
    doc.add_paragraph(body)
    doc.save(directory / name)
    return directory / name


class _FakeSession:
    """埋め込みAPIの代わりに固定長のベクトルを返す。"""

    def __init__(self):
        self.calls = 0

    def post(self, url, json, timeout):
        self.calls += 1
        count = len(json["input"])
        return _FakeResponse({"embeddings": [[0.1] * EMBED_DIM for _ in range(count)]})

    def close(self):
        pass


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_hash_changes_with_content(source_dir):
    first = _write_docx(source_dir, "a.docx", "内容A")
    before = file_hash(first)
    _write_docx(source_dir, "a.docx", "内容Bで違う長さの本文")
    assert file_hash(first) != before


def test_hash_is_stable_for_unchanged_file(source_dir):
    path = _write_docx(source_dir, "a.docx", "内容A")
    assert file_hash(path) == file_hash(path)


def test_documents_are_indexed(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入する")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"議事録.docx": 1}
    assert collection.count() == 1


def test_unchanged_file_is_skipped_on_second_run(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入する")
    session = _FakeSession()
    ingest_directory(source_dir, collection, session=session)
    calls_after_first = session.calls

    report = ingest_directory(source_dir, collection, session=session)
    assert report.skipped == ["議事録.docx"]
    assert report.indexed == {}
    assert session.calls == calls_after_first, "スキップ時に埋め込みを呼んではいけない"


def test_changed_file_is_reindexed(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "初版の本文")
    ingest_directory(source_dir, collection, session=_FakeSession())
    _write_docx(source_dir, "議事録.docx", "改訂された本文")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"議事録.docx": 1}
    assert stored_file_hash(collection, "議事録.docx") == file_hash(
        source_dir / "議事録.docx"
    )


def test_force_reindexes_even_when_unchanged(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "本文")
    ingest_directory(source_dir, collection, session=_FakeSession())
    report = ingest_directory(source_dir, collection, session=_FakeSession(), force=True)
    assert report.indexed == {"議事録.docx": 1}
    assert report.skipped == []


def test_deleted_file_is_pruned(source_dir, collection):
    _write_docx(source_dir, "残す.docx", "本文")
    path = _write_docx(source_dir, "消す.docx", "本文")
    ingest_directory(source_dir, collection, session=_FakeSession())
    path.unlink()
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == ["消す.docx"]


def test_unsupported_files_are_ignored(source_dir, collection):
    (source_dir / "memo.txt").write_text("本文", encoding="utf-8")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {}
    assert report.failed == {}


def test_one_broken_file_does_not_stop_the_others(source_dir, collection):
    _write_docx(source_dir, "正常.docx", "読める本文")
    (source_dir / "壊れた.docx").write_bytes(b"this is not a docx")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"正常.docx": 1}
    assert "壊れた.docx" in report.failed


def test_progress_is_reported_per_file(source_dir, collection):
    _write_docx(source_dir, "a.docx", "本文")
    _write_docx(source_dir, "b.docx", "本文")
    messages = []
    ingest_directory(
        source_dir, collection, session=_FakeSession(), on_progress=messages.append
    )
    assert any("a.docx" in m for m in messages)
    assert any("b.docx" in m for m in messages)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_ingest_source.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts'`

- [ ] **Step 3: 最小限の実装を書く**

`scripts/__init__.py` は空ファイルとして作成する。

`scripts/ingest_source.py`:
```python
"""source/ 配下の資料をベクトルDBへ取り込むCLI。

初回はOCR23ページと埋め込み260件でおよそ13分かかる。Streamlitのボタンで
13分ブロックするのは現実的でないため、初回はこのCLIから実行する。

1ファイル処理するごとにDBへ書き込む。全ファイル分をまとめて書き込むと、
12分経過時点の失敗ですべてを失う。ファイル単位で保存しておけば、再実行時に
ハッシュ判定で成功済みのファイルがスキップされ、失敗分だけをやり直せる。
"""
import argparse
import hashlib
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import chromadb

from ingest import embedder, store
from ingest.chunker import chunk_units
from ingest.parsers import SUPPORTED_SUFFIXES, parse

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent.parent / "source"
DB_DIR = Path(__file__).resolve().parent.parent / "chroma_db"


@dataclass
class IngestReport:
    indexed: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    removed: list[str] = field(default_factory=list)


def file_hash(path: Path) -> str:
    """内容が1バイトでも変われば変わる識別子。先頭16桁で十分に衝突しない。"""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:16]


def _target_files(source_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def ingest_directory(
    source_dir: Path,
    collection,
    session=None,
    on_progress=None,
    force: bool = False,
) -> IngestReport:
    """source_dir を走査し、変更のあった資料だけを取り込む。"""
    report = IngestReport()
    notify = on_progress or (lambda _message: None)
    own_session = session is None
    session = session or embedder.new_session()
    today = date.today().isoformat()

    try:
        files = _target_files(source_dir)
        for path in files:
            source = path.name
            current_hash = file_hash(path)

            if not force and store.stored_file_hash(collection, source) == current_hash:
                report.skipped.append(source)
                notify(f"スキップ（変更なし）: {source}")
                continue

            notify(f"処理中: {source}")
            try:
                units = parse(path)
                chunks = chunk_units(units, source, current_hash, today)
                vectors = embedder.embed_texts(
                    [chunk.text for chunk in chunks], session=session
                )
                store.replace_source(collection, source, chunks, vectors)
            except Exception as error:  # 1ファイルの失敗で全体を止めない
                report.failed[source] = str(error)
                notify(f"失敗: {source} — {error}")
                continue

            report.indexed[source] = len(chunks)
            notify(f"完了: {source}（{len(chunks)}チャンク）")

        # source/ を唯一の入力とするため、消えた資料はDBからも消す。
        report.removed = store.delete_orphans(
            collection, {path.name for path in files}
        )
        for source in report.removed:
            notify(f"削除（source/にありません）: {source}")
    finally:
        if own_session:
            session.close()

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="source/ の資料をベクトルDBへ取り込む")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument(
        "--force", action="store_true", help="変更がなくても再取り込みする"
    )
    args = parser.parse_args()

    if not args.source_dir.is_dir():
        print(f"ディレクトリがありません: {args.source_dir}")
        return 1

    try:
        # 260チャンクの処理を始めてから落ちないよう、先に疎通を確認する。
        embedder.check_ollama()
    except embedder.EmbeddingError as error:
        print(error)
        return 1

    collection = store.open_collection(chromadb.PersistentClient(path=str(DB_DIR)))
    report = ingest_directory(args.source_dir, collection, on_progress=print)

    print("\n--- 結果 ---")
    print(f"取り込み: {sum(report.indexed.values())}チャンク / {len(report.indexed)}ファイル")
    print(f"スキップ: {len(report.skipped)}ファイル")
    print(f"削除: {len(report.removed)}ファイル")
    if report.failed:
        print(f"失敗: {len(report.failed)}ファイル")
        for source, message in report.failed.items():
            print(f"  {source}: {message}")
    print(f"DB内の総チャンク数: {collection.count()}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全50件）

- [ ] **Step 5: コミットする**

```bash
git add scripts/ tests/test_ingest_source.py
git commit -m "feat: add source directory ingestion CLI

Commits to the database per file so a failure twelve minutes into the
initial run does not discard completed work; re-running skips what already
succeeded. A broken file is recorded and the remaining files continue.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: 実データで初回取り込みを実行する**

Run: `.\myvenv313\Scripts\python.exe -m scripts.ingest_source`
Expected: 約13分かかる。8ファイルすべてが「完了」となり、最終行の総チャンク数が **260前後** になること。失敗が0件であること

- [ ] **Step 7: 差分取り込みが機能することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m scripts.ingest_source`
Expected: 8ファイルすべてが「スキップ（変更なし）」となり、**数秒で終了**すること。総チャンク数が変わらないこと

---

## Task 9: 関連度しきい値の実測と確定

**Files:**
- Create: `scripts/check_retrieval.py`
- Create: `ingest/retrieval.py`
- Create: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `ingest.embedder.embed_query`, `ingest.store`
- Produces: `search(collection, query, session=None, threshold=None, n_results=4) -> list[Hit]`、`Hit(text: str, distance: float, metadata: dict)`、`Hit.citation -> str`、定数 `RELEVANCE_THRESHOLD`（Step 5で実測値に確定）, `SEARCH_RESULT_COUNT = 4`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_retrieval.py`:
```python
import pytest

from ingest.retrieval import Hit, search


class _FakeCollection:
    def __init__(self, documents, distances, metadatas):
        self._payload = {
            "documents": [documents],
            "distances": [distances],
            "metadatas": [metadatas],
        }

    def count(self):
        return len(self._payload["documents"][0])

    def query(self, query_embeddings, n_results):
        return self._payload


def _meta(source="a.pdf", location_type="page", location=48, ocr=False):
    return {
        "source": source,
        "location_type": location_type,
        "location": location,
        "ocr": ocr,
    }


@pytest.fixture(autouse=True)
def _no_real_embedding(monkeypatch):
    monkeypatch.setattr("ingest.retrieval.embed_query", lambda _q, session=None: [0.1])


def test_page_citation():
    hit = Hit(text="本文", distance=0.1, metadata=_meta())
    assert hit.citation == "a.pdf p.48"


def test_slide_citation():
    hit = Hit(text="本文", distance=0.1, metadata=_meta(location_type="slide", location=12))
    assert hit.citation == "a.pdf スライド12"


def test_document_citation_has_no_position():
    hit = Hit(text="本文", distance=0.1, metadata=_meta(location_type="document", location=0))
    assert hit.citation == "a.pdf"


def test_ocr_hits_are_marked():
    """OCR由来は小書き仮名が崩れることがあるため、根拠として示すときに明示する。"""
    hit = Hit(text="本文", distance=0.1, metadata=_meta(ocr=True))
    assert hit.citation == "a.pdf p.48（OCR）"


def test_far_results_are_dropped():
    collection = _FakeCollection(["近い", "遠い"], [0.10, 0.90], [_meta(), _meta()])
    hits = search(collection, "質問", threshold=0.5)
    assert [h.text for h in hits] == ["近い"]


def test_empty_collection_returns_nothing():
    assert search(_FakeCollection([], [], []), "質問", threshold=0.5) == []


def test_hits_keep_their_distance():
    collection = _FakeCollection(["本文"], [0.25], [_meta()])
    assert search(collection, "質問", threshold=0.5)[0].distance == 0.25
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_retrieval.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.retrieval'`

- [ ] **Step 3: 検索モジュールを実装する**

`ingest/retrieval.py`:
```python
"""ベクトル検索と出典の組み立て。

足切りをしないと、挨拶のような検索対象外の入力でも必ず最近傍が1件返ってきて、
無関係な文書がコンテキストに紛れ込む。
"""
from dataclasses import dataclass

from ingest.embedder import embed_query

SEARCH_RESULT_COUNT = 4

# scripts/check_retrieval.py の実測に基づく暫定値。Step 5 で確定値に置き換える。
RELEVANCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class Hit:
    text: str
    distance: float
    metadata: dict

    @property
    def citation(self) -> str:
        """「ファイル名 p.48（OCR）」の形式で出典を組み立てる。"""
        source = self.metadata.get("source", "")
        location_type = self.metadata.get("location_type")
        location = self.metadata.get("location")
        if location_type == "page":
            source = f"{source} p.{location}"
        elif location_type == "slide":
            source = f"{source} スライド{location}"
        if self.metadata.get("ocr"):
            source = f"{source}（OCR）"
        return source


def search(collection, query, session=None, threshold=None, n_results=SEARCH_RESULT_COUNT):
    if collection.count() == 0:
        return []
    limit = threshold if threshold is not None else RELEVANCE_THRESHOLD
    results = collection.query(
        query_embeddings=[embed_query(query, session=session)], n_results=n_results
    )
    hits = zip(
        results["documents"][0], results["distances"][0], results["metadatas"][0]
    )
    return [
        Hit(text=text, distance=distance, metadata=metadata)
        for text, distance, metadata in hits
        if text and distance <= limit
    ]
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_retrieval.py -v`
Expected: PASS（7件）

- [ ] **Step 5: しきい値の実測スクリプトを書いて実行する**

`scripts/check_retrieval.py`:
```python
"""関連度しきい値を決めるために距離を実測する。

関連する質問の最大距離 < 無関係な質問の最小距離 が成り立てば足切りが機能する。
成り立たない場合はチャンクサイズか埋め込みモデルの見直しが必要。
"""
import chromadb

from ingest import embedder, store
from ingest.retrieval import search
from scripts.ingest_source import DB_DIR

# 取り込んだ資料に確実に答えがある質問
RELEVANT = [
    "懲戒解雇となるのはどのような場合ですか",
    "裁判員になったとき休暇はもらえますか",
    "育児休業は誰が取得できますか",
    "コンテキスト使用率の危険ラインは何％ですか",
    "本コースで選んだRAGの手法は何ですか",
    "セミナーの講師は誰ですか",
    "AI活用プロジェクトの初期スコープは何ですか",
]

# 取り込んだ資料のどこにも答えがない質問
IRRELEVANT = [
    "今日の東京の天気を教えてください",
    "おすすめのラーメン屋はどこですか",
    "こんにちは",
    "1たす1はいくつですか",
]


def main() -> int:
    embedder.check_ollama()
    collection = store.open_collection(chromadb.PersistentClient(path=str(DB_DIR)))
    print(f"総チャンク数: {collection.count()}\n")

    session = embedder.new_session()
    try:
        relevant_max = 0.0
        print("=== 関連する質問（最も近いチャンクとの距離） ===")
        for question in RELEVANT:
            hits = search(collection, question, session=session, threshold=99.0, n_results=1)
            distance = hits[0].distance
            relevant_max = max(relevant_max, distance)
            print(f"  {distance:.3f}  {question}  → {hits[0].citation}")

        irrelevant_min = 99.0
        print("\n=== 無関係な質問（最も近いチャンクとの距離） ===")
        for question in IRRELEVANT:
            hits = search(collection, question, session=session, threshold=99.0, n_results=1)
            distance = hits[0].distance
            irrelevant_min = min(irrelevant_min, distance)
            print(f"  {distance:.3f}  {question}  → {hits[0].citation}")
    finally:
        session.close()

    print(f"\n関連の最大: {relevant_max:.3f}")
    print(f"無関係の最小: {irrelevant_min:.3f}")
    if relevant_max < irrelevant_min:
        print(f"分離できています。推奨しきい値: {(relevant_max + irrelevant_min) / 2:.3f}")
        return 0
    print("分離できていません。チャンクサイズか埋め込みモデルの見直しが必要です。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `.\myvenv313\Scripts\python.exe -m scripts.check_retrieval`
Expected: 「分離できています。推奨しきい値: X.XXX」が表示されること

- [ ] **Step 6: 実測値を `ingest/retrieval.py` に反映する**

`RELEVANCE_THRESHOLD` の行を、Step 5 で表示された推奨しきい値に置き換える。コメントには実測した2つの値を必ず残す（後から資料を入れ替えた人が再調整できるようにするため）。書式は以下に従う。

```python
# 検索結果を採用するcosine距離のしきい値（0に近いほど類似）。
# scripts/check_retrieval.py の実測（bge-m3 / 260チャンク）:
#   関連する質問の最大距離 = 0.XXX、無関係な質問の最小距離 = 0.YYY
# この2つの間を取っている。扱う資料を入れ替えたら再度実測して調整すること。
RELEVANCE_THRESHOLD = 0.ZZZ
```

- [ ] **Step 7: しきい値が機能することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全57件）

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; from ingest import store; from ingest.retrieval import search; c=store.open_collection(chromadb.PersistentClient(path=r'.\chroma_db')); print('関連:', [h.citation for h in search(c, '懲戒解雇となるのはどのような場合ですか')]); print('無関係:', [h.citation for h in search(c, '今日の天気は')])"
```
Expected: 関連の質問では出典が1件以上返り、無関係な質問では `[]` が返ること

- [ ] **Step 8: コミットする**

```bash
git add ingest/retrieval.py scripts/check_retrieval.py tests/test_retrieval.py
git commit -m "feat: add retrieval with citations and a calibrated threshold

The cutoff is measured rather than guessed: check_retrieval.py reports the
farthest relevant hit and the nearest irrelevant one, and the threshold
sits between them. Both figures are recorded in the code comment so the
next person can recalibrate after swapping documents.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: Streamlit UI

**Files:**
- Create: `ingest/prompting.py`
- Create: `rag_chat_app.py`
- Create: `tests/test_prompting.py`

**Interfaces:**
- Consumes: `ingest.retrieval.search`, `ingest.retrieval.Hit`, `ingest.store`, `ingest.embedder`, `scripts.ingest_source.ingest_directory`
- Produces: `ingest.prompting.build_prompt(question: str, hits: list[Hit]) -> str`、`ingest.prompting.format_report(report) -> str`

**重要:** `build_prompt` と `format_report` は `rag_chat_app.py` ではなく `ingest/prompting.py` に置く。Streamlitスクリプトはトップレベルに処理を並べるため、テストからインポートするとスクリプト全体が実行され、本番の `chroma_db` を開いてしまう。テスト対象のロジックはUIファイルの外に出す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_prompting.py`:
```python
from ingest.prompting import build_prompt, format_report
from ingest.retrieval import Hit
from scripts.ingest_source import IngestReport


def _hit(text="本文", source="a.pdf", location=48):
    return Hit(
        text=text,
        distance=0.2,
        metadata={
            "source": source,
            "location_type": "page",
            "location": location,
            "ocr": False,
        },
    )


def test_prompt_without_hits_is_the_bare_question():
    assert build_prompt("経費の上限は", []) == "経費の上限は"


def test_prompt_includes_retrieved_text():
    prompt = build_prompt("経費の上限は", [_hit(text="上限は1万円です")])
    assert "上限は1万円です" in prompt
    assert "経費の上限は" in prompt


def test_prompt_includes_citations_so_the_model_can_cite_them():
    prompt = build_prompt("経費の上限は", [_hit()])
    assert "a.pdf p.48" in prompt


def test_report_counts_chunks_files_and_skips_separately():
    report = IngestReport(
        indexed={"a.pdf": 10, "b.pdf": 7}, skipped=["c.pptx"], failed={}, removed=["d.docx"]
    )
    text = format_report(report)
    assert "17チャンク" in text
    assert "2ファイル" in text
    assert "スキップ: 1ファイル" in text
    assert "削除: 1ファイル" in text


def test_report_lists_failures():
    report = IngestReport(indexed={}, skipped=[], failed={"壊れた.pdf": "読めません"}, removed=[])
    text = format_report(report)
    assert "壊れた.pdf" in text
    assert "読めません" in text
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_prompting.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.prompting'`

- [ ] **Step 3: ヘルパーモジュールを実装する**

`ingest/prompting.py`:
```python
"""プロンプト組み立てと取り込み結果の要約。

UIから呼ばれるがUIには依存しない。Streamlitスクリプトに置くと、テストが
インポートしただけでスクリプト全体が走り本番DBを開いてしまうため、ここに分離する。
"""


def build_prompt(question: str, hits) -> str:
    """検索結果を今回の質問にだけ添える。

    履歴には生の質問を残す。ここで作った文字列を履歴に入れると、
    次のターン以降に古いコンテキストが混ざる。
    """
    if not hits:
        return question
    context = "\n\n".join(f"[{hit.citation}]\n{hit.text}" for hit in hits)
    return (
        "以下の社内文書を参考に回答してください。"
        "回答の根拠にした箇所は [ ] 内の出典を示してください。\n\n"
        f"{context}\n\nユーザーの質問: {question}"
    )


def format_report(report) -> str:
    lines = [
        f"取り込み: {sum(report.indexed.values())}チャンク / {len(report.indexed)}ファイル",
        f"スキップ: {len(report.skipped)}ファイル",
        f"削除: {len(report.removed)}ファイル",
    ]
    for source, message in report.failed.items():
        lines.append(f"失敗 {source}: {message}")
    return "\n".join(lines)
```

- [ ] **Step 4: ヘルパーのテストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_prompting.py -v`
Expected: PASS（5件）

- [ ] **Step 5: UIを実装する**

`rag_chat_app.py`:
```python
"""ローカル文書RAGチャット。

取り込み処理は ingest/ 側にあり、このファイルは表示と入出力だけを担当する。
初回の取り込みは13分かかるため、CLI (python -m scripts.ingest_source) で行う。
このUIのボタンは差分取り込み（通常は数秒）を想定している。
"""
from datetime import datetime
from pathlib import Path

import chromadb
import streamlit as st
from openai import OpenAI

from ingest import embedder, store
from ingest.prompting import build_prompt, format_report
from ingest.retrieval import RELEVANCE_THRESHOLD, search
from scripts.ingest_source import DEFAULT_SOURCE_DIR, ingest_directory

DB_DIR = str(Path(__file__).parent / "chroma_db")


@st.cache_resource
def get_collection(db_dir):
    return store.open_collection(chromadb.PersistentClient(path=db_dir))


def render_hits(hits):
    if not hits:
        return
    with st.expander(f"参考にした情報（{len(hits)}件）"):
        for hit in hits:
            st.caption(f"{hit.citation} ／ cosine距離 {hit.distance:.3f}（しきい値 {RELEVANCE_THRESHOLD}）")
            st.write(hit.text)


st.set_page_config(page_title="社内文書RAGチャット")
st.sidebar.title("設定")

model = st.sidebar.text_input("モデル名", value="llama3.1:8b")
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
system_prompt = st.sidebar.text_area(
    "System Prompt",
    f"あなたは有能なアシスタントです。今日の日付は{datetime.today():%Y年%m月%d日}です。"
    "日本語で回答して下さい。",
)

collection = get_collection(DB_DIR)
st.sidebar.metric("インデックス済みチャンク", collection.count())

st.sidebar.divider()
st.sidebar.caption(f"取り込み元: {DEFAULT_SOURCE_DIR.name}/")
if st.sidebar.button("差分を取り込む"):
    try:
        embedder.check_ollama()
    except embedder.EmbeddingError as error:
        st.sidebar.error(str(error))
    else:
        with st.spinner("取り込み中…"):
            report = ingest_directory(DEFAULT_SOURCE_DIR, collection)
        st.sidebar.success(format_report(report))
        st.rerun()

if st.sidebar.button("会話履歴をリセット"):
    st.session_state.messages = []
    st.rerun()

st.title("社内文書RAGチャット")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        render_hits(message.get("hits"))

client = OpenAI(api_key="ollama", base_url=f"{embedder.OLLAMA_HOST}/v1")

question = st.chat_input("メッセージを入力")

if question:
    with st.chat_message("user"):
        st.write(question)
    st.session_state.messages.append({"role": "user", "content": question})

    hits = search(collection, question)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ] + [{"role": "user", "content": build_prompt(question, hits)}]

    if system_prompt.strip():
        history = [{"role": "system", "content": system_prompt}] + history

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model, messages=history, temperature=temperature, stream=True
        )

        def tokens():
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        answer = st.write_stream(tokens())
        render_hits(hits)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "hits": hits}
    )
```

- [ ] **Step 6: 全テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全62件）

- [ ] **Step 7: アプリを起動して動作を確認する**

Run: `.\myvenv313\Scripts\streamlit.exe run rag_chat_app.py`

以下をブラウザで確認する。
1. サイドバーの「インデックス済みチャンク」が260前後を示すこと
2. 「懲戒解雇となるのはどのような場合ですか」と質問し、回答に加えて `モデル就業規則.pdf p.XX` 形式の出典が折りたたみに出ること
3. 「本コースで選んだRAGの手法は何ですか」と質問し、`Claude_Code_法人導入ガイド_スライド.pdf p.XX（OCR）` の出典が出ること
4. 「今日の天気は」と質問し、参考情報が表示されないこと
5. 「差分を取り込む」を押し、数秒で「スキップ: 8ファイル」と表示されること

- [ ] **Step 8: コミットする**

```bash
git add ingest/prompting.py rag_chat_app.py tests/test_prompting.py
git commit -m "feat: add RAG chat UI with document citations

Retrieved passages carry their file and page into the prompt so the model
can cite them, and the expander shows the same citation with its distance.
The sidebar button handles incremental ingestion only; the initial 13
minute run belongs on the CLI.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 11: 教材ファイルの共存確認とドキュメント

**Files:**
- Create: `README.md`
- Verify: `udemy3.py`（変更しない）

**Interfaces:**
- Consumes: すべてのタスクの成果物
- Produces: なし

- [ ] **Step 1: 既存の教材が壊れていないことを確認する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; c=chromadb.PersistentClient(path=r'.\chroma_db'); print([(x.name, c.get_collection(x.name).count()) for x in c.list_collections()])"
```
Expected: `local_docs` が21チャンク、`local_docs_v2` が260前後。**2つが共存していること**

- [ ] **Step 2: udemy3.py が今も起動することを確認する**

Run: `.\myvenv313\Scripts\streamlit.exe run udemy3.py`

議事録に関する質問（「AI活用プロジェクトの初期スコープは」）に回答できることを確認したら停止する。

- [ ] **Step 3: READMEを書く**

`README.md`:
```markdown
# ローカル文書RAGチャット

PDF・PowerPoint・Word を完全ローカルでベクトルDBに取り込み、出典付きで回答するRAGチャット。
外部サービスへの送信は一切行わない。

## 必要なもの

- Python 3.13（`myvenv313`）
- Ollama（`http://127.0.0.1:12000` で待ち受け）
- モデル: `ollama pull bge-m3` と `ollama pull llama3.1:8b`

## セットアップ

```powershell
.\myvenv313\Scripts\python.exe -m pip install pymupdf python-pptx python-docx rapidocr onnxruntime langchain-text-splitters chromadb streamlit openai requests pytest
```

## 使い方

取り込みたい資料を `source/` に置く（`.pdf` / `.pptx` / `.docx`）。

```powershell
# 初回の取り込み（実測 約13分。OCR 23ページと埋め込み260件を処理する）
.\myvenv313\Scripts\python.exe -m scripts.ingest_source

# チャットを起動する
.\myvenv313\Scripts\streamlit.exe run rag_chat_app.py
```

2回目以降はファイルのハッシュを見て変更分だけを処理するため数秒で終わる。
UIサイドバーの「差分を取り込む」も同じ処理を呼ぶ。

## 構成

| パス | 役割 |
|---|---|
| `ingest/` | 取り込みパイプライン（UIに依存しない） |
| `scripts/ingest_source.py` | 取り込みCLI |
| `scripts/check_retrieval.py` | 関連度しきい値を決めるための距離実測 |
| `rag_chat_app.py` | Streamlit UI |
| `udemy1.py` 〜 `udemy3.py` | 教材の各段階。`local_docs` コレクションを使い続ける |

## テスト

```powershell
.\myvenv313\Scripts\python.exe -m pytest            # 通常のテスト
.\myvenv313\Scripts\python.exe -m pytest -m integration  # 実機のOCRを使う低速なテスト
```

## 既知の制約

- OCRテキストは小書き仮名が崩れることがある（`ナレッジ` → `ナレツヅ`）。ベクトル検索では吸収できるが完全一致検索には使えない
- このPCはGPUを使えないため、OCRを連続実行すると熱により約2.5倍遅くなる
- 資料を入れ替えたら `scripts/check_retrieval.py` でしきい値を再調整すること

## 設計資料

- 設計書: `docs/superpowers/specs/2026-08-11-document-ingestion-design.md`
- 実装計画: `docs/superpowers/plans/2026-08-11-document-ingestion.md`
```

- [ ] **Step 4: 全テストを実行する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全62件）

- [ ] **Step 5: コミットする**

```bash
git add README.md
git commit -m "docs: add README covering setup, ingestion, and known limits

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review 結果

**1. 設計書のカバレッジ**

| 設計書のセクション | 対応タスク |
|---|---|
| 4. 技術スタック | Task 1（依存導入） |
| 5. アーキテクチャ / ParsedUnit | Task 1 |
| 5. OCRの遅延初期化 | Task 4 |
| 5. コレクションの新設 | Task 7、Task 11（共存確認） |
| 6. データフロー / 差分取り込み | Task 8 |
| 6. 削除されたファイルの扱い | Task 7（`delete_orphans`）、Task 8 |
| 6. OCRフォールバック判定（30字） | Task 5 |
| 6. チャンク分割（800字） | Task 2 |
| 7. メタデータ設計 | Task 2（生成）、Task 7（往復）、Task 9（出典組み立て） |
| 8. localhost の2秒問題 | Task 6 |
| 8. 埋め込み性能 / バッチ8 | Task 6 |
| 9. 長時間処理時の設計上の要請 | Task 8（ファイル単位コミット・進捗出力・CLI優先） |
| 10. エラー処理 | Task 6（疎通確認・リトライ）、Task 8（破損ファイル・未対応拡張子） |
| 11. テスト方針 | 各タスク、`pytest.ini` の integration マーカー |
| 12. しきい値の再調整 | Task 9 |
| 13. 事前準備 | Task 1、README |
| 14. 熱スロットリング | README の既知の制約 |
| 15. 既知の制約 | README |

**2. プレースホルダ**: なし。Task 9 Step 6 のしきい値のみ実測後に確定するが、確定手順と書式を明示している。

**3. 型の一貫性**: `ParsedUnit(text, location_type, location, ocr)` は Task 1 で定義し Task 3・5 で生成、Task 2 で消費。`Chunk(id, text, metadata)` は Task 2 で生成し Task 7 で消費。`Hit(text, distance, metadata)` は Task 9 で定義し Task 10 で消費。`IngestReport(indexed, skipped, failed, removed)` は Task 8 で定義し Task 10 の `format_report` で消費。すべて一致を確認。
