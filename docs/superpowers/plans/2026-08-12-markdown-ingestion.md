# Markdown取り込みとサブフォルダ対応 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `source/家電製品/` の30件のMarkdown製品仕様書を、サブフォルダ対応の再帰走査とともに既存のRAGチャットから検索・引用できるようにする。

**Architecture:** `##` 見出しを話題の境界とみなし、PPTXの「1スライド=1ユニット」と同じく1見出し=1 `ParsedUnit` とする。各ユニットの先頭にH1（製品名）を前置し、単独のセクションチャンクでも機種を特定できるようにする。`source` 識別子を `source/` からの相対パスに変えることでサブフォルダを許容しつつ、直下のファイルは識別子が変わらないため既存279チャンクの再取り込みを回避する。

**Tech Stack:** Python 3.13 / 標準ライブラリのみ（新規依存なし）/ pytest / ChromaDB / Ollama (bge-m3)

**設計書:** `docs/superpowers/specs/2026-08-12-markdown-ingestion-design.md`

## Global Constraints

- Python 3.13.3、仮想環境は `myvenv313`。すべてのコマンドは `.\myvenv313\Scripts\python.exe` 経由で実行する
- `.exe` ランチャー（`pytest.exe` / `streamlit.exe`）は使わない。venvが移動済みで壊れているため、必ず `python.exe -m <module>` の形で起動する
- **新しい依存パッケージを追加しない。** Markdownの解析は標準ライブラリだけで行う（YAMLパーサーを入れない）
- 外部サービスへの送信は一切行わない
- ChromaDBのコレクションは `local_docs_v2` のまま。教材が使う `local_docs` には一切触れない
- Ollamaの接続先は `ingest/embedder.py` の `DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"`。`localhost` は使用しない
- チャンクIDの形式は `{source}::{location_type}{location}::{chunk_index}` のまま変えない
- **既存の279チャンクを再取り込みさせない。** 直下のファイルの `source` 識別子は現行と同一でなければならない
- コミットメッセージはコンベンショナルコミット形式、英語で記述する
- 作業ブランチは `feat/markdown-ingestion`

---

## File Structure

| ファイル | 責務 | 変更 |
|---|---|---|
| `ingest/models.py` | `ParsedUnit` / `Chunk` の定義 | `SECTION` と `heading` を追加、未使用の `label` を削除 |
| `ingest/chunker.py` | ユニット→チャンク変換 | メタデータに `heading` を追加 |
| `ingest/parsers/md_parser.py` | Markdownのテキスト抽出 | 新規作成 |
| `ingest/parsers/__init__.py` | 拡張子によるディスパッチ | `.md` を登録 |
| `ingest/retrieval.py` | 検索と出典組み立て | `Hit.citation` に section を追加 |
| `scripts/ingest_source.py` | 取り込みCLI | 再帰走査と相対パス識別子 |
| `scripts/check_retrieval.py` | しきい値の実測 | 製品への質問を追加 |
| `README.md` | 利用者向け説明 | 対応形式・チャンク数・定数表を更新 |

---

## Task 1: データモデルに section と heading を導入する

**Files:**
- Modify: `ingest/models.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Consumes: なし
- Produces: 定数 `SECTION = "section"`、`ParsedUnit(text: str, location_type: str, location: int, ocr: bool = False, heading: str = "")`。`ParsedUnit.label` は削除される

- [ ] **Step 1: 作業ブランチを作る**

```bash
git checkout -b feat/markdown-ingestion
```

- [ ] **Step 2: 失敗するテストを書く**

`tests/test_models.py` の内容を以下で**全面的に置き換える**。`label` の3テストは削除する。`label` は本番コードから一度も呼ばれておらず、出典整形の実体は `ingest/retrieval.py` の `Hit.citation` である。同じ責務が2箇所にあると位置種別を追加するたびに両方を直すことになるため、使われていない側を消す。

```python
from ingest.models import SECTION, Chunk, ParsedUnit


def test_unit_is_not_ocr_by_default():
    assert ParsedUnit(text="本文", location_type="page", location=1).ocr is False


def test_unit_has_no_heading_by_default():
    """ページやスライド由来のユニットは見出しを持たない。"""
    assert ParsedUnit(text="本文", location_type="page", location=1).heading == ""


def test_section_unit_keeps_its_heading():
    """Markdownの見出しは出典表示に使うため、ユニットが運ぶ必要がある。"""
    unit = ParsedUnit(
        text="本文", location_type=SECTION, location=3, heading="設置情報"
    )
    assert unit.heading == "設置情報"


def test_section_location_type_is_section():
    assert SECTION == "section"


def test_chunk_holds_id_text_and_metadata():
    chunk = Chunk(id="a.pdf::page1::0", text="本文", metadata={"source": "a.pdf"})
    assert chunk.id == "a.pdf::page1::0"
    assert chunk.metadata["source"] == "a.pdf"
```

- [ ] **Step 3: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'SECTION' from 'ingest.models'`

- [ ] **Step 4: 実装する**

`ingest/models.py` を以下で全面的に置き換える。

```python
"""取り込みパイプライン全体で共有するデータ構造。

各パーサーはPDF・PPTX・DOCX・Markdownの違いをすべて ParsedUnit に吸収する。
これにより後続のチャンク分割・埋め込み・保存は元の形式を知る必要がない。
"""
from dataclasses import dataclass, field

# 出典位置の種別。docxのようにページ概念を持たない形式は "document" を使う。
PAGE = "page"
SLIDE = "slide"
DOCUMENT = "document"
SECTION = "section"


@dataclass(frozen=True)
class ParsedUnit:
    """パーサーが返す最小単位。1ページ、1スライド、1見出し、または文書全体。"""

    text: str
    location_type: str
    location: int
    ocr: bool = False
    # Markdownの見出し文字列。出典を「ファイル名 ＞ 設置情報」と表示するために運ぶ。
    # 位置の一意性は location（通し番号）が持ち、heading は表示専用である。
    heading: str = ""


@dataclass(frozen=True)
class Chunk:
    """ベクトルDBに保存する単位。"""

    id: str
    text: str
    metadata: dict = field(default_factory=dict)
```

- [ ] **Step 5: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（既存テストも含めて全件。`label` を参照するコードは残っていないこと）

- [ ] **Step 6: コミットする**

```bash
git add ingest/models.py tests/test_models.py
git commit -m "refactor: give parsed units a heading and drop the unused label

Markdown sections need their heading carried to the citation, and the
position stays numeric so chunk IDs cannot collide on repeated headings.
ParsedUnit.label was never called outside its own tests and duplicated the
citation formatting that Hit.citation already owns.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: チャンクのメタデータに heading を載せる

**Files:**
- Modify: `ingest/chunker.py`
- Modify: `tests/test_chunker.py`

**Interfaces:**
- Consumes: `ingest.models.ParsedUnit`（`heading` を持つ）
- Produces: `chunk_units(...)` が生成するメタデータに `"heading": str` が加わる

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chunker.py` の末尾に以下を追加する。既存の `_unit` / `_chunk` ヘルパーをそのまま使う。

```python
def test_heading_is_empty_for_units_without_one():
    """ページ由来のチャンクでもキー自体は存在させ、読み手が分岐を書かずに済むようにする。"""
    chunks = _chunk([_unit("これは十分な長さのある本文です。")])
    assert chunks[0].metadata["heading"] == ""


def test_heading_is_carried_into_every_chunk():
    """出典表示に使うため、分割されても全チャンクが見出しを保持する必要がある。"""
    unit = ParsedUnit(
        text="あ" * 2000, location_type="section", location=1, heading="設置情報"
    )
    chunks = _chunk([unit])
    assert len(chunks) > 1
    assert all(c.metadata["heading"] == "設置情報" for c in chunks)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_chunker.py -v`
Expected: FAIL — `KeyError: 'heading'`

- [ ] **Step 3: 実装する**

`ingest/chunker.py` の `chunk_units` 内のメタデータ辞書に1行追加する。`"ocr": unit.ocr,` の直後に置く。

```python
                        "ocr": unit.ocr,
                        "heading": unit.heading,
                        "chunk_index": index,
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 5: コミットする**

```bash
git add ingest/chunker.py tests/test_chunker.py
git commit -m "feat: carry the unit heading into chunk metadata

Every chunk of a split section keeps the heading so the citation can name
the section regardless of which fragment matched.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Markdownパーサー

**Files:**
- Create: `ingest/parsers/md_parser.py`
- Modify: `ingest/parsers/__init__.py`
- Create: `tests/test_parser_md.py`

**Interfaces:**
- Consumes: `ingest.models.SECTION`, `ingest.models.ParsedUnit`
- Produces: `parse_md(path: Path) -> list[ParsedUnit]`。`ingest.parsers.SUPPORTED_SUFFIXES` に `.md` が加わる

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parser_md.py` を新規作成する。外側のコードフェンスが4つのバッククォートになっている点に注意すること（テスト本文が3つのバッククォートを含むため）。

````python
import pytest

from ingest.parsers import parse
from ingest.parsers.md_parser import parse_md

SAMPLE = """---
model_id: UD-0900i
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
````

さらに、コードフェンス内の `##` で誤分割しないことを確認するテストを同じファイルの末尾に追加する。3つのバッククォートを直接書くとテストファイル自体が読みにくくなるため、変数で組み立てる。

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_parser_md.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.parsers.md_parser'`

- [ ] **Step 3: パーサーを実装する**

`ingest/parsers/md_parser.py` を新規作成する。

```python
"""Markdownのテキスト抽出。

`##` 見出しは書き手が引いた話題の境界そのものなので、PPTXのスライドと同じく
1見出し=1ユニットとする。source/家電製品/ の30件を実測したところ、セクションは
最小76字・中央値157字・最大448字であり、CHUNK_SIZE(800)を超えないため
再分割は一度も起きない。

各ユニットの先頭にはH1（例 'UD-0900i IoTコンパクト'）を1行付ける。
'## 設置情報' だけを検索で引いたときに、どの製品の設置情報なのか分からなく
なるのを防ぐためで、これがこの形式を扱ううえでの要になる。
"""
from pathlib import Path

from ingest.models import SECTION, ParsedUnit

_FENCE = "```"


def _read_lines(path: Path) -> list[str]:
    """CRLFを正規化して行に分ける。

    実データ30件はすべてCRLFであり、そのままだと見出し文字列の末尾に \r が残って
    出典が「＞ 設置情報\r」のように壊れる。encoding を省略しないのは、Windowsの
    既定が CP932 で日本語の読み込みに必ず失敗するため。
    """
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _drop_frontmatter(lines: list[str]) -> list[str]:
    """先頭のYAMLフロントマターを取り除く。

    model_id と product_name はH1前置で全ユニットに行き渡り、その他の属性は
    本文の散文が保持している。YAMLの生テキストを埋め込むより散文のほうが
    日本語の質問との類似度が出るため、索引には入れない。
    """
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1 :]
    return lines  # 閉じられていないなら本文とみなす


def parse_md(path: Path) -> list[ParsedUnit]:
    title = ""
    sections: list[tuple[str, list[str]]] = []
    heading: str = ""
    body: list[str] = []
    in_fence = False

    for line in _drop_frontmatter(_read_lines(path)):
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
        body.append(line)
    sections.append((heading, body))

    units: list[ParsedUnit] = []
    for section_heading, section_body in sections:
        text = "\n".join(section_body).strip()
        if not text:
            continue
        units.append(
            ParsedUnit(
                text="\n".join(part for part in (title, section_heading, text) if part),
                location_type=SECTION,
                # 見出し文字列ではなく通し番号を位置にする。同じ見出しが2つある文書で
                # チャンクIDが衝突するのを防ぐため、IDの一意性を文書構造に依存させない。
                location=len(units) + 1,
                heading=section_heading,
            )
        )
    return units
```

- [ ] **Step 4: ディスパッチに `.md` を登録する**

`ingest/parsers/__init__.py` のインポート行に追加する。

```python
from ingest.parsers.md_parser import parse_md
```

`_PARSERS` を差し替える。

```python
_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".pptx": parse_pptx,
    ".md": parse_md,
}
```

- [ ] **Step 5: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 6: 実データで確認する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "from pathlib import Path; from ingest.parsers.md_parser import parse_md; u=parse_md(Path('source/家電製品/UD-0900i_spec_step3.md')); print(len(u), '件'); print([x.heading for x in u]); print(max(len(x.text) for x in u), '字（最大）'); print(u[2].text[:80])"
```
Expected: 6件、見出しは `['機種概要', '基本スペック', '設置情報', '主な機能', '年間使用コスト目安', 'こんなお客様に最適']`、最大文字数は800未満、本文の先頭が `UD-0900i IoTコンパクト` で始まること

- [ ] **Step 7: コミットする**

```bash
git add ingest/parsers/md_parser.py ingest/parsers/__init__.py tests/test_parser_md.py
git commit -m "feat: add Markdown parser that splits on level-two headings

A heading is already a topic boundary, so each becomes one unit the way a
slide does; measured sections top out at 448 characters and never hit the
800-character split. Every unit is prefixed with the document's H1 so a
lone spec section still identifies its product, and YAML frontmatter is
skipped because the prose carries the same facts in searchable Japanese.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: 出典表示に section を追加する

**Files:**
- Modify: `ingest/retrieval.py`
- Modify: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: チャンクメタデータの `location_type` と `heading`
- Produces: `Hit.citation` が section 由来のヒットに対して `"家電製品/UD-0900i_spec_step3.md ＞ 設置情報"` を返す

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_retrieval.py` の `_meta` ヘルパーに `heading` を追加する。既存のテストは既定値の空文字で動く。

```python
def _meta(source="a.pdf", location_type="page", location=48, ocr=False, heading=""):
    return {
        "source": source,
        "location_type": location_type,
        "location": location,
        "ocr": ocr,
        "heading": heading,
    }
```

同じファイルの `test_document_citation_has_no_position` の直後に以下の2件を追加する。

```python
def test_section_citation_shows_the_heading():
    hit = Hit(
        text="本文",
        distance=0.1,
        metadata=_meta(
            source="家電製品/UD-0900i_spec_step3.md",
            location_type="section",
            location=3,
            heading="設置情報",
        ),
    )
    assert hit.citation == "家電製品/UD-0900i_spec_step3.md ＞ 設置情報"


def test_section_without_a_heading_shows_only_the_file():
    """見出しのないMarkdownでは、空の『＞』を出さない。"""
    hit = Hit(
        text="本文",
        distance=0.1,
        metadata=_meta(location_type="section", location=1, heading=""),
    )
    assert hit.citation == "a.pdf"
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_retrieval.py -v`
Expected: FAIL — `assert 'a.pdf' == '家電製品/UD-0900i_spec_step3.md ＞ 設置情報'`（section の分岐がないため位置が付かない）

- [ ] **Step 3: 実装する**

`ingest/retrieval.py` の `Hit.citation` を以下で置き換える。

```python
    @property
    def citation(self) -> str:
        """「ファイル名 p.48（OCR）」の形式で出典を組み立てる。

        出典整形はここが唯一の置き場所である。位置種別を増やすときはこのメソッドだけを直す。
        """
        source = self.metadata.get("source", "")
        location_type = self.metadata.get("location_type")
        location = self.metadata.get("location")
        if location_type == "page":
            source = f"{source} p.{location}"
        elif location_type == "slide":
            source = f"{source} スライド{location}"
        elif location_type == "section":
            # 見出し文字列で示す。通し番号（location）は利用者にとって意味がない。
            heading = self.metadata.get("heading")
            if heading:
                source = f"{source} ＞ {heading}"
        if self.metadata.get("ocr"):
            source = f"{source}（OCR）"
        return source
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 5: コミットする**

```bash
git add ingest/retrieval.py tests/test_retrieval.py
git commit -m "feat: cite Markdown hits by their heading

The section number means nothing to a reader, so the citation names the
heading instead and falls back to the file alone when a document has none.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: サブフォルダの再帰走査と相対パス識別子

**Files:**
- Modify: `scripts/ingest_source.py`
- Modify: `tests/test_ingest_source.py`

**Interfaces:**
- Consumes: `ingest.parsers.SUPPORTED_SUFFIXES`
- Produces: `_source_key(path: Path, source_dir: Path) -> str`。`ingest_directory` が返す `IngestReport.indexed` / `skipped` / `removed` のキーが相対パス（`家電製品/仕様.docx`）になる

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ingest_source.py` の末尾（`test_main_forwards_force_flag_to_ingest_directory` の前）に以下の4件を追加する。

```python
def test_files_in_subdirectories_are_indexed(source_dir, collection):
    """資料を分類して置けるようにする。iterdir のままでは中身に到達しない。"""
    sub = source_dir / "家電製品"
    sub.mkdir()
    _write_docx(sub, "仕様.docx", "この製品の仕様書の本文がここにあります。")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"家電製品/仕様.docx": 1}


def test_top_level_identifier_stays_the_bare_filename(source_dir, collection):
    """既存279チャンクを再取り込みさせないための保証。

    相対パスは直下のファイルではファイル名と一致するため、識別子は変わらない。
    """
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"議事録.docx": 1}
    assert stored_file_hash(collection, "議事録.docx") is not None


def test_subdirectory_files_are_not_pruned_as_orphans(source_dir, collection):
    """孤児判定を相対パスに揃え忘れると、毎回削除と再取り込みを繰り返す。"""
    sub = source_dir / "家電製品"
    sub.mkdir()
    _write_docx(sub, "仕様.docx", "この製品の仕様書の本文がここにあります。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == []
    assert report.skipped == ["家電製品/仕様.docx"]


def test_same_filename_in_two_folders_does_not_collide(source_dir, collection):
    """ファイル名だけを識別子にすると、片方がもう片方を上書きしてしまう。"""
    for folder in ("A", "B"):
        directory = source_dir / folder
        directory.mkdir()
        _write_docx(directory, "仕様.docx", f"{folder}フォルダの仕様書の本文です。")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert set(report.indexed) == {"A/仕様.docx", "B/仕様.docx"}
    assert collection.count() == 2
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_ingest_source.py -v`
Expected: FAIL — `test_files_in_subdirectories_are_indexed` が `assert {} == {'家電製品/仕様.docx': 1}` で落ちる

- [ ] **Step 3: 走査と識別子を実装する**

`scripts/ingest_source.py` の `_target_files` を以下で置き換える。

```python
def _target_files(source_dir: Path) -> list[Path]:
    """サブフォルダも含めて対象ファイルを集める。

    資料を分類して置けるようにするため再帰する。対象外の拡張子はここで落とすので、
    source/ に雑多なファイルが増えてもパーサーには渡らない。
    """
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _source_key(path: Path, source_dir: Path) -> str:
    """source/ からの相対パスを資料の識別子にする。

    区切りはスラッシュに統一する。WindowsのバックスラッシュがそのままチャンクIDと
    メタデータに入ると、環境をまたいだときに一致しなくなるため。
    直下のファイルは相対パスがファイル名と一致するので、既存のチャンクの識別子は
    変わらず、再取り込みは発生しない。
    """
    return path.relative_to(source_dir).as_posix()
```

- [ ] **Step 4: `ingest_directory` を相対パスに揃える**

`ingest_directory` の中の2箇所を変更する。

`source = path.name` を以下に変える。

```python
            source = _source_key(path, source_dir)
```

`delete_orphans` の呼び出しを以下に変える。ここを変え忘れると、サブフォルダの資料が毎回孤児と判定されて削除される。

```python
        report.removed = store.delete_orphans(
            collection, {_source_key(path, source_dir) for path in files}
        )
```

- [ ] **Step 5: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 6: コミットする**

```bash
git add scripts/ingest_source.py tests/test_ingest_source.py
git commit -m "feat: walk source subdirectories and key chunks by relative path

Documents can now be filed into folders. The identifier is the path
relative to source/ with forward slashes, which keeps top-level files on
their existing key — so the 279 chunks already indexed are untouched — and
stops same-named files in different folders from overwriting each other.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: 実データの取り込みとしきい値の再測定

**Files:**
- Modify: `scripts/check_retrieval.py`
- Modify: `ingest/retrieval.py`（`RELEVANCE_THRESHOLD` の値とコメント）
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1〜5 のすべて
- Produces: 実測に基づく `RELEVANCE_THRESHOLD` の値と、更新されたREADME

- [ ] **Step 1: Ollamaの疎通を確認する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "from ingest.embedder import OLLAMA_HOST, check_ollama; check_ollama(); print('ok', OLLAMA_HOST)"
```
Expected: `ok http://127.0.0.1:11434`

失敗する場合はOllamaが起動していないか、標準以外のポートで待ち受けている。`ollama list` で確認する。

- [ ] **Step 2: 取り込み前の状態を記録する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; c=chromadb.PersistentClient(path=r'.\chroma_db'); print([(x.name, c.get_collection(x.name).count()) for x in c.list_collections()])"
```
Expected: `local_docs_v2` が279、`local_docs` が21。この数字を控えておく

- [ ] **Step 3: 実データを取り込む**

Run: `.\myvenv313\Scripts\python.exe -m scripts.ingest_source`

Expected: 既存8ファイルが「スキップ（変更なし）」となり、`家電製品/*.md` 30ファイルが新たに取り込まれる。削除は0件。OCRが走らないため数分で終わる。`DB内の総チャンク数` が約460になる

**既存8ファイルがスキップされずに再取り込みされた場合は、`_source_key` が直下のファイルでファイル名と一致していない。** Task 5 に戻ること。

- [ ] **Step 4: 実測した所要時間とチャンク数を記録する**

Step 3 の出力から、取り込みチャンク数と総チャンク数を控える。所要時間も控える。README に書く。

- [ ] **Step 5: しきい値の測定用に製品への質問を追加する**

`scripts/check_retrieval.py` の `RELEVANT` リストの末尾（閉じ括弧の直前）に以下を追加する。特定機種の照会と条件による絞り込みの両方を含める。設計の想定用途がその2つだからである。

```python
    # 家電製品の仕様書（source/家電製品/）。特定機種の照会と条件による絞り込みの両方を測る。
    "UD-0900iの設置に必要な防水パンの奥行きは何ミリですか",
    "UD-0900iの乾燥方式は何ですか",
    "スマートフォンから遠隔操作できる洗濯機はどれですか",
    "一人暮らし向けのコンパクトな洗濯機を教えてください",
```

- [ ] **Step 6: 距離を実測する**

Run: `.\myvenv313\Scripts\python.exe -m scripts.check_retrieval`

Expected: `分離できています。推奨しきい値: X.XXX` と表示される。「関連の最大」と「圏外の最小」の値を控える

**「分離できていません」と表示された場合はしきい値を動かしてはならない。** 設計書 第9節のとおり、チャンク設計の見直しが必要である。その場合は作業を止めて報告すること。

- [ ] **Step 7: しきい値を確定する**

`ingest/retrieval.py` の `RELEVANCE_THRESHOLD` のコメントを、Step 6 で得た実測値に書き換える。値は「関連の最大」と「圏外の最小」の間に置く。現行のコメント（279チャンク時点の 0.459 / 0.549）は新しい実測値で置き換える。コメントには次を必ず含める。

- 測定したコーパスの規模（約460チャンク、うち家電製品181）
- 関連する質問の最大距離
- 圏外の質問の最小距離
- 挨拶が距離では分離できないという既知の事実（現行の記述を維持する）

推奨しきい値が現行の 0.50 と変わらない場合も、コメントの実測条件は更新すること。

- [ ] **Step 8: 全テストを実行する**

Run: `.\myvenv313\Scripts\python.exe -m pytest -v`
Expected: PASS（全件）

- [ ] **Step 9: UIで実際に質問して確認する**

Run: `.\myvenv313\Scripts\python.exe -m streamlit run rag_chat_app.py`

以下を確認したら停止する。

1. サイドバーの「インデックス済みチャンク」が約460になっている
2. 「UD-0900iの設置に必要な防水パンの奥行きは」と質問し、出典に `家電製品/UD-0900i_spec_step3.md ＞ 設置情報` が表示される
3. 「AI活用プロジェクトの初期スコープは」と質問し、既存の議事録から回答できる（既存資料が壊れていないこと）

- [ ] **Step 10: READMEを更新する**

`README.md` の以下を書き換える。

1. 冒頭の説明文: 対応形式に Markdown を加える（`PDF・PowerPoint・Word・Markdown`）
2. 「使い方」: 取り込み対象の説明を「`source/` に置く（`.pdf` / `.pptx` / `.docx` / `.md`）。**サブフォルダに分類して置いてもよい**」に変える。初回取り込みの実測時間も Step 4 の値で更新する
3. 「構成」の表: 変更なし
4. 現在のチャンク数の記述（`source/` の8ファイルから279チャンク）を、Step 3 で得た実際の数字に更新する
5. 「設計定数」の表: 変更があれば `RELEVANCE_THRESHOLD` の値を更新する
6. 「既知の制約」: しきい値に関する記述を Step 6 の実測値に更新する
7. 「設計資料」: 今回の設計書と実装計画へのリンクを追加する

- [ ] **Step 11: コミットする**

```bash
git add scripts/check_retrieval.py ingest/retrieval.py README.md
git commit -m "feat: index the product spec sheets and recalibrate the threshold

The corpus grew from 279 to roughly 460 chunks and now mixes internal
documents with a product catalogue, so the relevance threshold was
re-measured against questions of both kinds rather than carried over.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review 結果

**1. 設計書のカバレッジ**

| 設計書のセクション | 対応タスク |
|---|---|
| 2. 現状なぜ取り込めないのか（再帰・拡張子） | Task 5、Task 3 Step 4 |
| 4. 対象データの実測 | Task 3（パーサーのdocstringに記録）、Task 3 Step 6（実データ確認） |
| 5. 採用する方針（`##` 単位） | Task 3 |
| 6. ユニットのテキスト構成（H1→見出し→本文、記号除去） | Task 3 Step 1 のテスト3件、Step 3 |
| 6. H1の前置 | Task 3（`test_every_unit_carries_the_product_title`） |
| 6. フロントマターの扱い | Task 3（`test_frontmatter_is_not_indexed`） |
| 6. CRLFの正規化 | Task 3（`test_crlf_does_not_leak_into_headings`） |
| 6. コードフェンスのガード | Task 3（`test_heading_inside_a_code_fence_does_not_split`） |
| 6. 退化ケース（4種） | Task 3（`test_file_without_any_heading_becomes_one_unit` / `test_section_without_a_body_is_dropped` / `test_frontmatter_only_file_produces_nothing` / `test_empty_file_produces_nothing`） |
| 7. 再帰走査 | Task 5 Step 3 |
| 7. 相対パス識別子・既存チャンク不変 | Task 5（`test_top_level_identifier_stays_the_bare_filename`）、Task 6 Step 3 の確認 |
| 7. 孤児削除への影響 | Task 5（`test_subdirectory_files_are_not_pruned_as_orphans`） |
| 8. `SECTION` と `heading` の追加 | Task 1 |
| 8. `location` は通し番号 | Task 1（コメント）、Task 3（`test_units_are_numbered_from_one`） |
| 8. メタデータへの `heading` 追加 | Task 2 |
| 8. 出典表示 | Task 4 |
| 8. `ParsedUnit.label` の削除 | Task 1 |
| 9. しきい値の再測定 | Task 6 Step 5〜7 |
| 10. エラー処理（既存のファイル単位try/except、encoding指定） | Task 3 Step 3（`_read_lines` のencoding指定とコメント）。既存の `ingest_directory` の例外処理は変更しないため新規タスクなし |
| 11. テスト方針 | Task 1〜5 の各テスト |
| 12. 想定される影響（チャンク数・時間・README） | Task 6 Step 4、Step 10 |
| 13. 今回やらないこと | 該当タスクなし（意図どおり） |

**2. プレースホルダ**: なし。Task 6 Step 7 のしきい値のみ実測後に確定するが、確定手順・記載すべき内容・分離できない場合の対応をすべて明示している。

**3. 型の一貫性**: `ParsedUnit(text, location_type, location, ocr, heading)` は Task 1 で定義し、Task 2（`unit.heading` を読む）・Task 3（生成）が使う。定数 `SECTION` は Task 1 で定義し Task 3 が使う。`_source_key(path, source_dir) -> str` は Task 5 Step 3 で定義し同 Step 4 の2箇所が使う。メタデータキー `heading` は Task 2 で書き込み Task 4 が読む。すべて名称と型の一致を確認した。

**4. 既存テストへの影響**: Task 1 で `tests/test_models.py` の `label` 3件を削除し4件を追加（5件→5件）。Task 4 で `tests/test_retrieval.py` の `_meta` にキーを1つ足すが既定値があるため既存7件は不変。他のテストファイルは追記のみ。
