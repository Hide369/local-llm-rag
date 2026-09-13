# 雛形からの文書生成（Cowork相当）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 利用者が登録した雛形の `{{印}}` を、検索結果（社内資料／技術ドキュメント）と添付ファイルから埋めて、ダウンロードできるファイルとして返す。Mermaid の値は図として埋め込む。

**Architecture:** 新しいパッケージ `docgen/` を作る。`ingest/parsers/` と同じく「拡張子ごとに1ファイル＋振り分け役の `__init__.py`」の形にし、形式ごとの違いを `*_template.py` の中だけに閉じる。印の記法は `docgen/marks.py` 1箇所に置く。値の決定（`filling.py`）は形式を知らず、`ask` を引数で受け取るため実機のOllamaなしでテストできる。`rag_chat_app.py` には画面だけを足す。

**Tech Stack:** Python 3.13 / python-docx 1.2.0 / openpyxl 3.1.5 / python-pptx 1.0.2 / streamlit 1.61.1 / pytest 9.1.1。**依存の追加はない。**

**Spec:** `docs/superpowers/specs/2026-09-13-document-generation-design.md`

## Global Constraints

- 対応する拡張子は `.docx` / `.xlsx` / `.pptx` / `.md` の4つだけ。PDF・drawio・画像は対象外。
- 印の記法は `{{名前}}`。名前は利用者が読む日本語。
- 埋まらなかった印は `{{名前}}` の文字列をそのまま残す。空にしない。
- 添付ファイルはDBに入れない。その回の生成にだけ使う。
- 雛形の原本は `templates/` にファイルとして残す（埋めるのに原本が要る）。
- `ingest/chat.py` の `NUM_CTX = 8192` は変更しない。`ask_json` に `num_ctx` 引数を足し、既定値を `NUM_CTX` にする。既存の呼び出しは1つも変えない。
- Cowork の生成に使う `num_ctx` は **32768**、プロンプトの上限は **`MAX_PROMPT_CHARS = 28000`**。
- Cowork が引く資料は利用者がその回ごとに選ぶ。既定は社内資料（`vector_store.sqlite3`）だけで、技術ドキュメント（`docs_store.sqlite3`）は選んだときだけ引く。
- 技術ドキュメントを引くときだけ、指示文を英訳し（`query_translation.translate_query`）、`search(..., rerank_floor=DOCS_RERANK_FLOOR)` を渡す。社内資料側にはどちらも渡さない。
- ```` ```mermaid ```` で始まる値は、docx/pptx/xlsx では PNG にして貼り、md ではコードブロックのまま入れる。
- 図にできなかったときは黙って落とさない。Mermaid のテキストをそのまま入れ、画面で伝える。
- 図の描画は `mermaid-cli`（`mmdc`）を手元で呼ぶ。`mermaid.ink` や `kroki.io` などの外部サービスへは送らない（AGENTS.md）。
- テストは実機のOllamaにもネットワークにも触れない。
- コメントは「なぜ」を書く。「何を」はコードで表す。
- コミットメッセージは英語、コンベンショナルコミット形式。

## ファイル構成

| ファイル | 責務 |
|---|---|
| `docgen/marks.py` | 印の記法。名前の抽出と文字列置換。**記法を知る唯一の場所** |
| `docgen/__init__.py` | 拡張子で `*_template.py` へ振り分ける |
| `docgen/md_template.py` | `.md` の印の抽出と差し込み |
| `docgen/docx_template.py` | `.docx` の印の抽出と差し込み |
| `docgen/pptx_template.py` | `.pptx` の印の抽出と差し込み |
| `docgen/xlsx_template.py` | `.xlsx` の印の抽出と差し込み |
| `docgen/templates.py` | 雛形の保管・一覧・削除 |
| `docgen/filling.py` | 検索結果と添付から印の値を決める |
| `docgen/mermaid.py` | Mermaid のテキストを PNG にする（`mmdc` を呼ぶ） |
| `rag_chat_app.py` | 画面（トグル・雛形選択・添付・生成・ダウンロード） |

`marks.py` を別ファイルにするのは、4つの `*_template.py` すべてが記法を必要とするためである。`__init__.py` に置くと、`__init__.py` が各 `*_template.py` を import する一方で各 `*_template.py` が `__init__.py` を import することになり、循環する。

---

### Task 1: 印の記法（`docgen/marks.py`）

**Files:**
- Create: `docgen/__init__.py`（空でよい。Task 2 で中身を入れる）
- Create: `docgen/marks.py`
- Test: `tests/test_docgen_marks.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - `docgen.marks.names(text: str) -> list[str]` — 出現順、重複を除いた印の名前
  - `docgen.marks.replace(text: str, values: dict[str, str]) -> str` — 値のある印だけ置換する

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_marks.py
"""印の記法。

記法を知る場所をここ1つに閉じている。4つの形式すべてが同じ規則で動く必要が
あり、形式ごとに正規表現を書くと、片方だけ直した状態が例外を出さずに成立する。
"""
from docgen import marks


def test_names_are_returned_in_the_order_they_appear():
    text = "会議名：{{会議名}}\n日時：{{開催日}}"
    assert marks.names(text) == ["会議名", "開催日"]


def test_a_name_that_appears_twice_is_listed_once():
    """同じ印を2箇所に置く雛形がある（表紙とヘッダーなど）。

    2回数えると、画面の「埋まらなかった欄」も二重に出る。
    """
    text = "{{会議名}}\n\n---\n\n{{会議名}} 議事録"
    assert marks.names(text) == ["会議名"]


def test_text_without_any_mark_has_no_names():
    assert marks.names("ただの本文です。") == []


def test_replace_fills_only_the_marks_that_have_a_value():
    """値の無い印は残す。空にすると、もともと空欄なのか埋め損ねたのか分からない。"""
    text = "会議名：{{会議名}}\n決定事項：{{決定事項}}"
    filled = marks.replace(text, {"会議名": "第5回"})
    assert filled == "会議名：第5回\n決定事項：{{決定事項}}"


def test_replace_ignores_a_value_whose_name_is_not_in_the_text():
    assert marks.replace("{{会議名}}", {"会議名": "第5回", "余計": "x"}) == "第5回"


def test_replace_fills_every_occurrence_of_the_same_name():
    assert marks.replace("{{名}}と{{名}}", {"名": "A"}) == "AとA"


def test_a_multi_line_value_is_inserted_as_is():
    """件数が変わる中身は1つの印に複数行で入れる（設計書5節）。"""
    assert marks.replace("{{決定事項}}", {"決定事項": "・A\n・B"}) == "・A\n・B"


def test_a_mark_containing_braces_is_not_matched():
    """入れ子の { } は印ではない。コード例を載せた雛形を壊さない。"""
    assert marks.names("{{ {x} }}") == []
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_docgen_marks.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'docgen'`）

- [ ] **Step 3: 実装する**

```python
# docgen/__init__.py
```

（Task 1 では空のファイルを置くだけ。Task 2 で振り分けを入れる）

```python
# docgen/marks.py
"""雛形の印（プレースホルダ）の記法。

記法を知る場所をここ1つに閉じる。4つの形式（docx/xlsx/pptx/md）すべてが同じ
規則で動く必要があり、形式ごとに正規表現を書くと、片方だけ直した状態が例外を
出さずに成立する。

名前は利用者が読む日本語をそのまま使う（`{{決定事項}}`）。画面の「埋まらな
かった欄」とLLMへの指示の両方にこの文字列が出るため、読めない記号にしない。
"""
import re

# 中に { } を含まないものだけを印とみなす。コード例を載せた雛形で、入れ子の
# 波括弧を印と取り違えないため。
_MARK = re.compile(r"\{\{([^{}]+)\}\}")


def names(text: str) -> list[str]:
    """出現順に、重複を除いた印の名前を返す。

    重複を除くのは、同じ印を表紙とヘッダーの2箇所に置く雛形があるためである。
    2回数えると画面の「埋まらなかった欄」も二重に出る。
    """
    found: list[str] = []
    for match in _MARK.finditer(text):
        name = match.group(1).strip()
        if name and name not in found:
            found.append(name)
    return found


def replace(text: str, values: dict[str, str]) -> str:
    """値のある印だけを置き換える。

    値の無い印は `{{名前}}` のまま残す。空にすると、利用者はもともと空欄の
    書式なのか埋め損ねたのかを見分けられない（scripts/code_references.py が
    解決できなかった :::code を元の行のまま残すのと同じ判断）。
    """

    def _one(match: re.Match) -> str:
        name = match.group(1).strip()
        value = values.get(name)
        return match.group(0) if value is None else value

    return _MARK.sub(_one, text)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_marks.py -v`
Expected: PASS（8件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/__init__.py docgen/marks.py tests/test_docgen_marks.py
git commit -m "feat: add the placeholder notation for document templates"
```

---

### Task 2: Markdown の雛形と振り分け（`docgen/md_template.py` / `docgen/__init__.py`）

**Files:**
- Create: `docgen/md_template.py`
- Modify: `docgen/__init__.py`
- Test: `tests/test_docgen_md_template.py`

**Interfaces:**
- Consumes: `docgen.marks.names()` / `docgen.marks.replace()`
- Produces:
  - `docgen.md_template.placeholders(path: Path) -> list[str]`
  - `docgen.md_template.fill(path: Path, values: dict[str, str]) -> bytes`
  - `docgen.SUPPORTED_SUFFIXES: set[str]`
  - `docgen.UnsupportedTemplateError`
  - `docgen.placeholders(path: Path) -> list[str]`
  - `docgen.fill(path: Path, values: dict[str, str]) -> bytes`

`fill()` が `bytes` を返すのは、`st.download_button` がバイト列を受け取るためである。中間ファイルを作らずに済む。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_md_template.py
"""Markdown の雛形と、拡張子による振り分け。

4形式のうち最も単純なものでディスパッチャの形を確立する。ingest/parsers/ が
「拡張子ごとに1ファイル＋振り分け役の __init__.py」でうまく動いているので、
書く側も同じ形にする。
"""
import pytest

import docgen


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_placeholders_are_found_in_a_markdown_template(tmp_path):
    path = _write(tmp_path, "議事録.md", "# {{会議名}}\n\n日時：{{開催日}}\n")
    assert docgen.placeholders(path) == ["会議名", "開催日"]


def test_fill_returns_the_filled_bytes(tmp_path):
    path = _write(tmp_path, "議事録.md", "# {{会議名}}\n")
    assert docgen.fill(path, {"会議名": "第5回"}).decode("utf-8") == "# 第5回\n"


def test_an_unfilled_mark_is_left_in_place(tmp_path):
    path = _write(tmp_path, "議事録.md", "# {{会議名}}\n{{決定事項}}\n")
    filled = docgen.fill(path, {"会議名": "第5回"}).decode("utf-8")
    assert filled == "# 第5回\n{{決定事項}}\n"


def test_an_unsupported_suffix_is_refused(tmp_path):
    """PDF は対象外である（設計書2節）。黙って空を返すと、印が0個の雛形と
    区別がつかない。"""
    path = _write(tmp_path, "議事録.pdf", "{{会議名}}")
    with pytest.raises(docgen.UnsupportedTemplateError, match="議事録.pdf"):
        docgen.placeholders(path)


def test_the_supported_suffixes_are_the_four_agreed_formats():
    assert docgen.SUPPORTED_SUFFIXES == {".docx", ".xlsx", ".pptx", ".md"}
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_docgen_md_template.py -v`
Expected: FAIL（`AttributeError: module 'docgen' has no attribute 'placeholders'`）

- [ ] **Step 3: 実装する**

```python
# docgen/md_template.py
"""Markdown の雛形。

書式を保つ必要がないため、本文全体に対する文字列置換で済む。
"""
from pathlib import Path

from docgen import marks


def placeholders(path: Path) -> list[str]:
    return marks.names(path.read_text(encoding="utf-8"))


def fill(path: Path, values: dict[str, str]) -> bytes:
    text = marks.replace(path.read_text(encoding="utf-8"), values)
    return text.encode("utf-8")
```

```python
# docgen/__init__.py
"""雛形の印を見つけて、値で埋める。

拡張子に応じて適切なモジュールへ振り分ける。形式を増やすときはモジュールを
1つ書いて _TEMPLATES に登録するだけでよい。そのために全モジュールの署名を
揃えてある（ingest/parsers/__init__.py と同じ方針）。

対象は docx / xlsx / pptx / md の4つだけである。PDF を入れていないのは、PDFが
文字を「位置」で持つ形式で、印より長い文字列を入れると溢れて重なるためである
（設計書2節に実測あり）。
"""
from pathlib import Path

from docgen.md_template import fill as _fill_md
from docgen.md_template import placeholders as _placeholders_md


class UnsupportedTemplateError(Exception):
    """雛形として扱えない拡張子を渡された。"""


_TEMPLATES = {
    ".md": (_placeholders_md, _fill_md),
}

SUPPORTED_SUFFIXES = {".docx", ".xlsx", ".pptx", ".md"}


def _module(path: Path):
    found = _TEMPLATES.get(path.suffix.lower())
    if found is None:
        raise UnsupportedTemplateError(f"雛形として使えない形式です: {path.name}")
    return found


def placeholders(path: Path) -> list[str]:
    """雛形に含まれる印の名前を、出現順・重複なしで返す。"""
    return _module(path)[0](path)


def fill(path: Path, values: dict[str, str]) -> bytes:
    """印を値で埋めた結果をバイト列で返す。

    バイト列を返すのは st.download_button がそれを受け取るためで、中間ファイルを
    作らずに済む。
    """
    return _module(path)[1](path, values)
```

`SUPPORTED_SUFFIXES` が `_TEMPLATES` より多いのは、この時点で残り3形式が未実装だからである。Task 3〜5 で `_TEMPLATES` に足していき、Task 5 の完了時点で一致する。

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_md_template.py -v`
Expected: PASS（5件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/__init__.py docgen/md_template.py tests/test_docgen_md_template.py
git commit -m "feat: fill markdown templates and dispatch by suffix"
```

---

### Task 3: Word の雛形（`docgen/docx_template.py`）

**Files:**
- Create: `docgen/docx_template.py`
- Modify: `docgen/__init__.py`
- Test: `tests/test_docgen_docx_template.py`

**Interfaces:**
- Consumes: `docgen.marks`
- Produces: `docgen.docx_template.placeholders(path) -> list[str]` / `docgen.docx_template.fill(path, values) -> bytes`

**この課題の要点**: 実測（2026-09-13）で、人が編集した docx は1つの段落が複数の run に割れていることを確認した。

```
段落: text='会議名：{{会議名}}'
      runs=['会議名：{{会議', '名}}']
```

`run.text` を1つずつ見て置換すると**印が見つからない**。段落単位で扱うこと。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_docx_template.py
"""Word の雛形。

実測 2026-09-13: 人が編集した docx は1つの段落が複数の run に割れている。
`['会議名：{{会議', '名}}']` のようになるため、run 単位で置換すると印が
見つからない。このファイルのテストはその形を必ず含める。
"""
import io

import docx
import pytest

import docgen


def _save(tmp_path, document, name="雛形.docx"):
    path = tmp_path / name
    document.save(path)
    return path


def _text_of(data: bytes) -> str:
    return "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)


def test_a_placeholder_split_across_runs_is_found(tmp_path):
    """これがこの形式で最も起きやすい壊れ方である。"""
    document = docx.Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("会議名：{{会議")
    paragraph.add_run("名}}")
    path = _save(tmp_path, document)
    assert docgen.placeholders(path) == ["会議名"]


def test_a_placeholder_split_across_runs_is_filled(tmp_path):
    document = docx.Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("会議名：{{会議")
    paragraph.add_run("名}}")
    path = _save(tmp_path, document)
    assert _text_of(docgen.fill(path, {"会議名": "第5回"})) == "会議名：第5回"


def test_a_placeholder_in_a_table_cell_is_found_and_filled(tmp_path):
    document = docx.Document()
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "出席者"
    table.cell(0, 1).text = "{{出席者}}"
    path = _save(tmp_path, document)
    assert docgen.placeholders(path) == ["出席者"]
    filled = docx.Document(io.BytesIO(docgen.fill(path, {"出席者": "田中、佐藤"})))
    assert filled.tables[0].cell(0, 1).text == "田中、佐藤"


def test_a_placeholder_in_the_header_is_found_and_filled(tmp_path):
    """会議名をヘッダーに入れる雛形がある。本文だけ見ていると取りこぼす。"""
    document = docx.Document()
    document.sections[0].header.paragraphs[0].text = "{{会議名}}"
    path = _save(tmp_path, document)
    assert docgen.placeholders(path) == ["会議名"]
    filled = docx.Document(io.BytesIO(docgen.fill(path, {"会議名": "第5回"})))
    assert filled.sections[0].header.paragraphs[0].text == "第5回"


def test_a_multi_line_value_becomes_line_breaks(tmp_path):
    """実測 2026-09-13: run.text に \\n を入れると <w:br/> になる。

    件数が変わる中身は1つの印に複数行で入れる（設計書5節）ので、ここが効く。
    """
    document = docx.Document()
    document.add_paragraph("{{決定事項}}")
    path = _save(tmp_path, document)
    data = docgen.fill(path, {"決定事項": "・A\n・B\n・C"})
    paragraph = docx.Document(io.BytesIO(data)).paragraphs[0]
    assert paragraph.text == "・A\n・B\n・C"
    assert paragraph.runs[0]._element.xml.count("<w:br/>") == 2


def test_an_unfilled_mark_is_left_in_place(tmp_path):
    document = docx.Document()
    document.add_paragraph("会議名：{{会議名}}")
    document.add_paragraph("決定事項：{{決定事項}}")
    path = _save(tmp_path, document)
    assert _text_of(docgen.fill(path, {"会議名": "第5回"})) == (
        "会議名：第5回\n決定事項：{{決定事項}}"
    )


def test_a_paragraph_without_any_mark_is_untouched(tmp_path):
    """印の無い段落に触ると、書式が先頭 run のものに潰れる副作用が出る。"""
    document = docx.Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("前半")
    paragraph.add_run("後半").bold = True
    path = _save(tmp_path, document)
    filled = docx.Document(io.BytesIO(docgen.fill(path, {})))
    assert [r.text for r in filled.paragraphs[0].runs] == ["前半", "後半"]


def test_a_template_without_marks_has_no_placeholders(tmp_path):
    document = docx.Document()
    document.add_paragraph("ただの本文")
    assert docgen.placeholders(_save(tmp_path, document)) == []
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_docgen_docx_template.py -v`
Expected: FAIL（`docgen.UnsupportedTemplateError: 雛形として使えない形式です: 雛形.docx`）

- [ ] **Step 3: 実装する**

```python
# docgen/docx_template.py
"""Word の雛形。

印は段落単位で扱う。実測 2026-09-13 では、人が編集した docx は1つの段落が
複数の run に割れており、`{{会議名}}` が `['会議名：{{会議', '名}}']` の
2つになっていた。run を1つずつ見て置換すると印が見つからない。

差し込みは、段落のテキストを組み立てて置換し、先頭の run に書き戻して残りの
run を空にする。書式は先頭 run のものになる。印を含まない段落には触らない。
触ると、書式の違う run が先頭のものに潰れる。
"""
import io
from pathlib import Path

import docx

from docgen import marks


def _paragraphs(document):
    """本文・表・ヘッダー・フッターの全段落を返す。

    ヘッダーまで見るのは、会議名をヘッダーに入れる雛形があるためである。
    本文だけ見ていると取りこぼし、しかも「印が無い雛形」と同じ見え方になる。
    """
    yield from document.paragraphs
    for table in document.tables:
        yield from _table_paragraphs(table)
    for section in document.sections:
        for part in (section.header, section.footer):
            yield from part.paragraphs
            for table in part.tables:
                yield from _table_paragraphs(table)


def _table_paragraphs(table):
    """表のセルの段落。セルの中に表が入ることがあるので再帰する。"""
    for row in table.rows:
        for cell in row.cells:
            yield from cell.paragraphs
            for nested in cell.tables:
                yield from _table_paragraphs(nested)


def placeholders(path: Path) -> list[str]:
    document = docx.Document(path)
    found: list[str] = []
    for paragraph in _paragraphs(document):
        for name in marks.names(paragraph.text):
            if name not in found:
                found.append(name)
    return found


def fill(path: Path, values: dict[str, str]) -> bytes:
    document = docx.Document(path)
    for paragraph in _paragraphs(document):
        _fill_paragraph(paragraph, values)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _fill_paragraph(paragraph, values: dict[str, str]) -> None:
    if not paragraph.runs:
        return
    original = "".join(run.text for run in paragraph.runs)
    replaced = marks.replace(original, values)
    if replaced == original:
        # 印が無い、あるいは値が1つも当たらなかった段落。触らない。
        # 触ると、書式の違う run が先頭 run のものに潰れる。
        return
    # 改行は run.text の setter が <w:br/> に変換する（実測 2026-09-13）。
    # タブも同じで、run.text は w:tab を \t として往復する。
    paragraph.runs[0].text = replaced
    for run in paragraph.runs[1:]:
        # 文字を持たない run は触らない。run.text の setter（CT_R.clear_content）は
        # w:rPr 以外の子を全部消すため、段落の中に差し込まれたロゴ（w:drawing）が
        # 一緒に消える。文字が無い run は original にも現れておらず、消す必要もない。
        if run.text:
            run.text = ""
```

`docgen/__init__.py` の `_TEMPLATES` に登録する。

```python
from docgen.docx_template import fill as _fill_docx
from docgen.docx_template import placeholders as _placeholders_docx

_TEMPLATES = {
    ".md": (_placeholders_md, _fill_md),
    ".docx": (_placeholders_docx, _fill_docx),
}
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_docx_template.py -v`
Expected: PASS（8件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/docx_template.py docgen/__init__.py tests/test_docgen_docx_template.py
git commit -m "feat: fill word templates per paragraph, not per run"
```

---

### Task 4: PowerPoint の雛形（`docgen/pptx_template.py`）

**Files:**
- Create: `docgen/pptx_template.py`
- Modify: `docgen/__init__.py`
- Test: `tests/test_docgen_pptx_template.py`

**Interfaces:**
- Consumes: `docgen.marks`
- Produces: `docgen.pptx_template.placeholders(path) -> list[str]` / `docgen.pptx_template.fill(path, values) -> bytes`

**この課題の要点**: pptx も docx と同じく run が割れる（実測 2026-09-13 で確認済み）。加えて、図形はグループにまとめられることがあるため再帰が要る。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_pptx_template.py
"""PowerPoint の雛形。

実測 2026-09-13: pptx も docx と同じく、段落が複数の run に割れる
（`['会議名：{{会議', '名}}']`）。段落単位で扱う。
"""
import io

import pytest
from pptx import Presentation
from pptx.util import Inches

import docgen


def _blank(tmp_path, name="雛形.pptx"):
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    return presentation, slide, tmp_path / name


def _textbox(slide, text):
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(1))
    box.text_frame.paragraphs[0].add_run().text = text
    return box


def _all_text(data: bytes) -> str:
    presentation = Presentation(io.BytesIO(data))
    parts = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
    return "\n".join(parts)


def test_a_placeholder_split_across_runs_is_found_and_filled(tmp_path):
    presentation, slide, path = _blank(tmp_path)
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(1))
    paragraph = box.text_frame.paragraphs[0]
    paragraph.add_run().text = "会議名：{{会議"
    paragraph.add_run().text = "名}}"
    presentation.save(path)

    assert docgen.placeholders(path) == ["会議名"]
    assert _all_text(docgen.fill(path, {"会議名": "第5回"})) == "会議名：第5回"


def test_a_placeholder_in_a_table_cell_is_found_and_filled(tmp_path):
    presentation, slide, path = _blank(tmp_path)
    shape = slide.shapes.add_table(1, 2, Inches(1), Inches(1), Inches(6), Inches(1))
    shape.table.cell(0, 0).text = "出席者"
    shape.table.cell(0, 1).text = "{{出席者}}"
    presentation.save(path)

    assert docgen.placeholders(path) == ["出席者"]
    filled = Presentation(io.BytesIO(docgen.fill(path, {"出席者": "田中"})))
    assert filled.slides[0].shapes[0].table.cell(0, 1).text == "田中"


def test_a_placeholder_inside_a_grouped_shape_is_found(tmp_path):
    """図形はグループにまとめられる。グループの中を見ないと取りこぼす。"""
    presentation, slide, path = _blank(tmp_path)
    first = _textbox(slide, "{{会議名}}")
    second = _textbox(slide, "{{開催日}}")
    slide.shapes.add_group_shape([first, second])
    presentation.save(path)

    assert docgen.placeholders(path) == ["会議名", "開催日"]


def test_an_unfilled_mark_is_left_in_place(tmp_path):
    presentation, slide, path = _blank(tmp_path)
    _textbox(slide, "{{会議名}} / {{決定事項}}")
    presentation.save(path)

    assert _all_text(docgen.fill(path, {"会議名": "第5回"})) == "第5回 / {{決定事項}}"


def test_a_template_without_marks_has_no_placeholders(tmp_path):
    presentation, slide, path = _blank(tmp_path)
    _textbox(slide, "ただの本文")
    presentation.save(path)
    assert docgen.placeholders(path) == []
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_docgen_pptx_template.py -v`
Expected: FAIL（`docgen.UnsupportedTemplateError: 雛形として使えない形式です: 雛形.pptx`）

- [ ] **Step 3: 実装する**

```python
# docgen/pptx_template.py
"""PowerPoint の雛形。

docx と同じく段落単位で扱う。実測 2026-09-13 では pptx でも
`{{会議名}}` が `['会議名：{{会議', '名}}']` の2つの run に割れていた。

図形はグループにまとめられるため、図形の走査は再帰する。グループの中を
見ないと印を取りこぼし、しかも「印が無い雛形」と同じ見え方になる。
"""
import io
from pathlib import Path

from pptx import Presentation

from docgen import marks


def _paragraphs(presentation):
    for slide in presentation.slides:
        yield from _shape_paragraphs(slide.shapes)


def _shape_paragraphs(shapes):
    for shape in shapes:
        if shape.has_text_frame:
            yield from shape.text_frame.paragraphs
        if shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    yield from cell.text_frame.paragraphs
        # グループ図形は .shapes を持つ。中の図形も同じ扱いにする。
        if hasattr(shape, "shapes"):
            yield from _shape_paragraphs(shape.shapes)


def placeholders(path: Path) -> list[str]:
    found: list[str] = []
    for paragraph in _paragraphs(Presentation(path)):
        text = "".join(run.text for run in paragraph.runs)
        for name in marks.names(text):
            if name not in found:
                found.append(name)
    return found


def fill(path: Path, values: dict[str, str]) -> bytes:
    presentation = Presentation(path)
    for paragraph in _paragraphs(presentation):
        _fill_paragraph(paragraph, values)
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def _fill_paragraph(paragraph, values: dict[str, str]) -> None:
    if not paragraph.runs:
        return
    original = "".join(run.text for run in paragraph.runs)
    replaced = marks.replace(original, values)
    if replaced == original:
        # 印が無い段落には触らない。触ると書式が先頭 run のものに潰れる。
        return
    paragraph.runs[0].text = replaced
    for run in paragraph.runs[1:]:
        run.text = ""
```

`docgen/__init__.py` の `_TEMPLATES` に `".pptx": (_placeholders_pptx, _fill_pptx)` を足し、import も追加する。

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_pptx_template.py -v`
Expected: PASS（5件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/pptx_template.py docgen/__init__.py tests/test_docgen_pptx_template.py
git commit -m "feat: fill powerpoint templates, including grouped shapes"
```

---

### Task 5: Excel の雛形（`docgen/xlsx_template.py`）

**Files:**
- Create: `docgen/xlsx_template.py`
- Modify: `docgen/__init__.py`
- Test: `tests/test_docgen_xlsx_template.py`

**Interfaces:**
- Consumes: `docgen.marks`
- Produces: `docgen.xlsx_template.placeholders(path) -> list[str]` / `docgen.xlsx_template.fill(path, values) -> bytes`

**この課題の要点**: セルの値は文字列1つなので run の分割は起きない。代わりに、複数行の値を入れるときは折り返し（`wrap_text`）を立てないと画面に1行としか出ない。実測 2026-09-13 で `copy(cell.alignment)` してから `wrap_text = True` を立てる形が動くことを確認済み。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_xlsx_template.py
"""Excel の雛形。

セルの値は文字列1つなので、docx/pptx のような run の分割は起きない。
代わりに、複数行の値は折り返しを立てないと1行にしか見えない。
"""
import io

import openpyxl

import docgen


def _save(tmp_path, book, name="雛形.xlsx"):
    path = tmp_path / name
    book.save(path)
    return path


def _loaded(data: bytes):
    return openpyxl.load_workbook(io.BytesIO(data))


def test_placeholders_are_found_across_sheets(tmp_path):
    book = openpyxl.Workbook()
    book.active["A1"] = "{{会議名}}"
    second = book.create_sheet("明細")
    second["B2"] = "{{決定事項}}"
    path = _save(tmp_path, book)
    assert docgen.placeholders(path) == ["会議名", "決定事項"]


def test_a_cell_is_filled(tmp_path):
    book = openpyxl.Workbook()
    book.active["A1"] = "会議名：{{会議名}}"
    path = _save(tmp_path, book)
    assert _loaded(docgen.fill(path, {"会議名": "第5回"})).active["A1"].value == "会議名：第5回"


def test_a_multi_line_value_turns_on_wrapping(tmp_path):
    """折り返しを立てないと、改行を入れても画面には1行としか出ない。"""
    book = openpyxl.Workbook()
    book.active["A1"] = "{{決定事項}}"
    path = _save(tmp_path, book)
    filled = _loaded(docgen.fill(path, {"決定事項": "・A\n・B"}))
    assert filled.active["A1"].value == "・A\n・B"
    assert filled.active["A1"].alignment.wrap_text is True


def test_a_single_line_value_does_not_change_the_alignment(tmp_path):
    """折り返しを常に立てると、雛形が決めた見た目を勝手に変えることになる。"""
    book = openpyxl.Workbook()
    book.active["A1"] = "{{会議名}}"
    path = _save(tmp_path, book)
    filled = _loaded(docgen.fill(path, {"会議名": "第5回"}))
    assert not filled.active["A1"].alignment.wrap_text


def test_an_unfilled_mark_is_left_in_place(tmp_path):
    book = openpyxl.Workbook()
    book.active["A1"] = "{{決定事項}}"
    path = _save(tmp_path, book)
    assert _loaded(docgen.fill(path, {})).active["A1"].value == "{{決定事項}}"


def test_a_numeric_cell_is_left_alone(tmp_path):
    """数値セルに文字列置換をかけると型が変わる。印は文字列にしか現れない。"""
    book = openpyxl.Workbook()
    book.active["A1"] = 26
    path = _save(tmp_path, book)
    assert docgen.placeholders(path) == []
    assert _loaded(docgen.fill(path, {})).active["A1"].value == 26
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_docgen_xlsx_template.py -v`
Expected: FAIL（`docgen.UnsupportedTemplateError: 雛形として使えない形式です: 雛形.xlsx`）

- [ ] **Step 3: 実装する**

```python
# docgen/xlsx_template.py
"""Excel の雛形。

セルの値は文字列1つなので、docx/pptx のような run の分割は起きない。

複数行の値を入れるときだけ折り返しを立てる。常に立てると、雛形が決めた
見た目を勝手に変えることになる。実測 2026-09-13: copy(cell.alignment) して
から wrap_text を立てる形で保存後も保たれる。
"""
import io
from copy import copy
from pathlib import Path

import openpyxl

from docgen import marks


def _cells(book):
    for sheet in book.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                # 印は文字列にしか現れない。数値セルに置換をかけると型が変わる。
                if isinstance(cell.value, str):
                    yield cell


def placeholders(path: Path) -> list[str]:
    found: list[str] = []
    for cell in _cells(openpyxl.load_workbook(path)):
        for name in marks.names(cell.value):
            if name not in found:
                found.append(name)
    return found


def fill(path: Path, values: dict[str, str]) -> bytes:
    book = openpyxl.load_workbook(path)
    for cell in _cells(book):
        replaced = marks.replace(cell.value, values)
        if replaced == cell.value:
            continue
        cell.value = replaced
        if "\n" in replaced:
            alignment = copy(cell.alignment)
            alignment.wrap_text = True
            cell.alignment = alignment
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()
```

`docgen/__init__.py` の `_TEMPLATES` に `".xlsx": (_placeholders_xlsx, _fill_xlsx)` を足し、import も追加する。

- [ ] **Step 4: 4形式そろったことを確認する**

`docgen/__init__.py` に次のテストを足して、登録漏れを機械的に防ぐ。

```python
# tests/test_docgen_md_template.py に追記
def test_every_supported_suffix_has_a_module():
    """SUPPORTED_SUFFIXES だけ足して _TEMPLATES への登録を忘れると、
    画面では選べるのに使うと例外になる。"""
    from docgen import _TEMPLATES

    assert set(_TEMPLATES) == docgen.SUPPORTED_SUFFIXES
```

Run: `pytest tests/test_docgen_xlsx_template.py tests/test_docgen_md_template.py -v`
Expected: PASS（6件 + 6件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/xlsx_template.py docgen/__init__.py tests/test_docgen_xlsx_template.py tests/test_docgen_md_template.py
git commit -m "feat: fill excel templates and complete the four formats"
```

---

### Task 6: 雛形の保管（`docgen/templates.py`）

**Files:**
- Create: `docgen/templates.py`
- Modify: `.gitignore`
- Test: `tests/test_docgen_templates.py`

**Interfaces:**
- Consumes: `docgen.SUPPORTED_SUFFIXES` / `docgen.UnsupportedTemplateError`
- Produces:
  - `docgen.templates.TEMPLATE_DIR: Path`
  - `docgen.templates.register(source: Path, directory: Path | None = None) -> Path`
  - `docgen.templates.templates(directory: Path | None = None) -> list[Path]`
  - `docgen.templates.remove(name: str, directory: Path | None = None) -> None`

`directory` を引数に持つのは、テストが本番の `templates/` を汚さないためである（既定値は `TEMPLATE_DIR`）。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_templates.py
"""雛形の保管。

既存のアップロード（scripts/ingest_source.py）は「原本を残さず、DBのチャンク
だけ残す」という設計判断を採っている。雛形はこれと異なる。埋めるために原本
そのものが要るため、ファイルとして残す。
"""
import pytest

import docgen
from docgen import templates as templates_module


def _template(tmp_path, name="議事録.docx"):
    import docx

    path = tmp_path / name
    document = docx.Document()
    document.add_paragraph("{{会議名}}")
    document.save(path)
    return path


def test_a_registered_template_is_listed(tmp_path):
    store = tmp_path / "templates"
    templates_module.register(_template(tmp_path), directory=store)
    assert [p.name for p in templates_module.templates(directory=store)] == ["議事録.docx"]


def test_templates_are_listed_in_name_order(tmp_path):
    store = tmp_path / "templates"
    for name in ("報告書.docx", "議事録.docx", "台帳.xlsx"):
        templates_module.register(_template(tmp_path, name), directory=store)
    listed = [p.name for p in templates_module.templates(directory=store)]
    assert listed == sorted(listed)


def test_registering_the_same_name_replaces_it(tmp_path):
    """利用者にとっては差し替えである。版管理の仕組みは作らない。"""
    store = tmp_path / "templates"
    first = tmp_path / "議事録.docx"
    import docx

    document = docx.Document()
    document.add_paragraph("{{会議名}}")
    document.save(first)
    templates_module.register(first, directory=store)

    document = docx.Document()
    document.add_paragraph("{{会議名}}\n{{決定事項}}")
    document.save(first)
    templates_module.register(first, directory=store)

    assert len(templates_module.templates(directory=store)) == 1
    stored = templates_module.templates(directory=store)[0]
    assert docgen.placeholders(stored) == ["会議名", "決定事項"]


def test_an_unsupported_suffix_is_refused(tmp_path):
    """PDF を登録できてしまうと、選べるのに生成できない雛形が一覧に並ぶ。"""
    store = tmp_path / "templates"
    path = tmp_path / "議事録.pdf"
    path.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(docgen.UnsupportedTemplateError, match="議事録.pdf"):
        templates_module.register(path, directory=store)


def test_removing_a_template_takes_it_off_the_list(tmp_path):
    store = tmp_path / "templates"
    templates_module.register(_template(tmp_path), directory=store)
    templates_module.remove("議事録.docx", directory=store)
    assert templates_module.templates(directory=store) == []


def test_removing_a_name_that_is_not_there_is_not_an_error(tmp_path):
    """2つの画面から同時に消したときに例外を出さない。結果は同じである。"""
    store = tmp_path / "templates"
    templates_module.remove("無い.docx", directory=store)


def test_listing_an_empty_store_returns_nothing(tmp_path):
    """まだ1つも登録していないのは通常の状態であり、例外ではない。"""
    assert templates_module.templates(directory=tmp_path / "templates") == []


def test_a_name_with_a_path_separator_is_refused(tmp_path):
    """名前はファイル名であってパスではない。templates/ の外へ書かせない。"""
    store = tmp_path / "templates"
    with pytest.raises(ValueError, match="ファイル名"):
        templates_module.remove("../vector_store.sqlite3", directory=store)
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_docgen_templates.py -v`
Expected: FAIL（`ImportError: cannot import name 'templates' from 'docgen'`）

- [ ] **Step 3: 実装する**

```python
# docgen/templates.py
"""雛形の保管。

原本をファイルとして残す。既存のアップロード（scripts/ingest_source.py の
ingest_uploads）は「原本を残さず、DBのチャンクだけ残す」という設計判断を
採っているが、雛形はこれと異なる。埋めるために原本そのものが要る。

名前はファイル名そのものである（`議事録.docx`）。別名を付ける仕組みは作らない。
同名を登録したら上書きする。利用者にとっては差し替えであり、版管理は作らない。
"""
import shutil
from pathlib import Path

import docgen

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _checked(name: str) -> str:
    """名前がファイル名であることを確かめる。

    パス区切りを含む名前を受け取ると templates/ の外へ書いたり消したりできる。
    雛形の名前は画面の一覧から来るが、利用者が触れる値を信じる形にはしない
    （ingest/parsers/md_parser.py の _resolve が同じ理由で .. を拒んでいる）。
    """
    if name != Path(name).name or name in ("", ".", ".."):
        raise ValueError(f"雛形の名前はファイル名でなければなりません: {name}")
    return name


def register(source: Path, directory: Path | None = None) -> Path:
    """雛形を保存し、置いた場所を返す。"""
    if source.suffix.lower() not in docgen.SUPPORTED_SUFFIXES:
        raise docgen.UnsupportedTemplateError(
            f"雛形として使えない形式です: {source.name}"
        )
    directory = directory or TEMPLATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / _checked(source.name)
    shutil.copyfile(source, destination)
    return destination


def templates(directory: Path | None = None) -> list[Path]:
    """登録済みの雛形をファイル名の昇順で返す。

    並びを決めるのは、画面のプルダウンの順序が実行のたびに変わらないように
    するためである。
    """
    directory = directory or TEMPLATE_DIR
    if not directory.is_dir():
        # まだ1つも登録していない状態は通常であり、例外ではない。
        return []
    return sorted(
        (path for path in directory.iterdir()
         if path.is_file() and path.suffix.lower() in docgen.SUPPORTED_SUFFIXES),
        key=lambda path: path.name,
    )


def remove(name: str, directory: Path | None = None) -> None:
    """雛形を消す。無ければ何もしない。

    2つの画面から同時に消したときに例外を出さない。結果は同じである。
    """
    directory = directory or TEMPLATE_DIR
    (directory / _checked(name)).unlink(missing_ok=True)
```

`.gitignore` に追記する。

```
# 利用者が登録した雛形。原本はそのマシンのものであり、配布対象ではない
# （source/ と同じ理由）
templates/
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_templates.py -v`
Expected: PASS（8件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/templates.py .gitignore tests/test_docgen_templates.py
git commit -m "feat: keep the registered templates on disk"
```

---

### Task 7: `ask_json` に `num_ctx` を足す（`ingest/chat.py`）

**Files:**
- Modify: `ingest/chat.py`
- Test: `tests/test_chat.py`

**Interfaces:**
- Produces: `ingest.chat.ask_json(model: str, prompt: str, session=None, num_ctx: int = NUM_CTX) -> str`

**この課題の要点**: 既定値を現行の `NUM_CTX`（8192）にすることで、既存の呼び出しは1つも変わらない。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chat.py` が無ければ新規に作る。既にあれば追記する。

```python
# tests/test_chat.py
"""生成リクエストの組み立て。

ネットワークへは出ない。セッションを差し替えて、送られたペイロードを見る。
"""
import json

from ingest import chat


class _FakeResponse:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": json.dumps({"query": "ok"})}}


class _FakeSession:
    def __init__(self):
        self.payloads = []

    def post(self, url, json=None, timeout=None):
        self.payloads.append(json)
        return _FakeResponse()

    def close(self):
        pass


def test_ask_json_uses_the_default_context_size():
    """既存の呼び出しが1つも変わらないこと。既定値は現行の NUM_CTX である。"""
    session = _FakeSession()
    chat.ask_json("gpt-oss:20b", "質問", session=session)
    assert session.payloads[0]["options"]["num_ctx"] == chat.NUM_CTX


def test_ask_json_accepts_a_larger_context_size():
    """Cowork は添付ファイルを丸ごと渡すため 8192 では足りない（設計書7節）。"""
    session = _FakeSession()
    chat.ask_json("gpt-oss:20b", "質問", session=session, num_ctx=32768)
    assert session.payloads[0]["options"]["num_ctx"] == 32768
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_chat.py -v`
Expected: 1件目は PASS、2件目は FAIL（`TypeError: ask_json() got an unexpected keyword argument 'num_ctx'`）

- [ ] **Step 3: 実装する**

`ingest/chat.py:37` の署名と `options` を変える。

```python
def ask_json(model: str, prompt: str, session=None, num_ctx: int = NUM_CTX) -> str:
    """JSONオブジェクト1個だけを返させる。条件抽出用。temperature=0固定。

    temperature=0固定の理由はingest/conditions.pyと同じ: 同じ質問で条件が
    揺れると再現性のない誤りになるため。

    num_ctx の既定は NUM_CTX（8192）で、条件抽出とクエリ翻訳はこれで足りる。
    雛形の生成（docgen/filling.py）だけは添付ファイルを丸ごと渡すため大きい値を
    渡す。既定値を上げないのは、短いプロンプトにも大きな文脈を割り当てると
    VRAMの余裕を使い切るためである（この定数のコメントを参照）。
    """
```

`payload` の `options` を次にする。

```python
            "options": {"temperature": 0, "num_ctx": num_ctx},
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_chat.py -v`
Expected: PASS（2件）

- [ ] **Step 5: 既存のテストが1つも壊れていないことを確認してコミットする**

Run: `pytest -q`
Expected: 全件 PASS、失敗ゼロ

```bash
git add ingest/chat.py tests/test_chat.py
git commit -m "feat: let the caller choose the context size for ask_json"
```

---

### Task 8: 印の値を決める（`docgen/filling.py`）

**Files:**
- Create: `docgen/filling.py`
- Test: `tests/test_docgen_filling.py`

**Interfaces:**
- Consumes: `ingest.retrieval.Hit`（`.text` と `.citation` を使う）
- Produces:
  - `docgen.filling.GENERATION_NUM_CTX: int`（= 32768）
  - `docgen.filling.MAX_PROMPT_CHARS: int`（= 28000）
  - `docgen.filling.PromptTooLongError`
  - `docgen.filling.build_prompt(placeholders: list[str], question: str, sources: list[tuple[str, list]], attachments: list[tuple[str, str]]) -> str`
  - `docgen.filling.fill_values(placeholders: list[str], question: str, sources: list[tuple[str, list]], attachments: list[tuple[str, str]], ask) -> dict[str, str]`

`sources` は `(資料の種類の名前, ヒットの並び)` の並びで、`[("社内資料", hits), ("技術ドキュメント", docs_hits)]` のように渡す。`attachments` は `(ファイル名, 本文)` の並びである。`ask` は `str -> str` の呼び出し可能オブジェクトで、`ingest/conditions.py` と同じく外から渡す。

**`filling.py` はどのコーパスが存在するかを知らない。** 見出しの文字列とヒットを受け取るだけにするのは、検索対象が増えてもこのモジュールを直さずに済ませるためである。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_filling.py
"""印の値を決める。

ask を引数で受け取るため、実機のOllamaに触れずにテストできる
（ingest/conditions.py と同じ方針）。
"""
import json

import pytest

from docgen import filling
from ingest.retrieval import Hit


def _hit(text, source="議事録.docx"):
    return Hit(text=text, distance=0.3, occurrences=[{"source": source}])


def _answering(payload):
    def ask(prompt):
        return json.dumps(payload, ensure_ascii=False)

    return ask


def test_the_values_come_back_keyed_by_placeholder_name():
    values = filling.fill_values(
        ["会議名", "決定事項"],
        "第5回会議の議事録を作って",
        [("社内資料", [_hit("第5回 AI活用検討会を開催した。")])],
        [],
        _answering({"会議名": "第5回 AI活用検討会", "決定事項": "・継続"}),
    )
    assert values == {"会議名": "第5回 AI活用検討会", "決定事項": "・継続"}


def test_a_key_that_is_not_a_placeholder_is_dropped():
    """雛形に無い欄を返してくることがある。そのまま通すと、置換されない値が
    黙って捨てられたのか、そもそも印が無かったのかが分からなくなる。"""
    values = filling.fill_values(
        ["会議名"], "質問", [], [], _answering({"会議名": "第5回", "余計": "x"})
    )
    assert values == {"会議名": "第5回"}


def test_a_value_that_is_not_a_string_is_dropped():
    """数値や配列を返してくることがある。置換は文字列にしかできない。"""
    values = filling.fill_values(
        ["会議名", "出席者"],
        "質問",
        [],
        [],
        _answering({"会議名": "第5回", "出席者": ["田中", "佐藤"]}),
    )
    assert values == {"会議名": "第5回"}


def test_an_empty_value_is_dropped():
    """空文字は「埋まった」ではない。印を残したほうが利用者は気づける。"""
    values = filling.fill_values(
        ["会議名", "決定事項"], "質問", [], [], _answering({"会議名": "第5回", "決定事項": ""})
    )
    assert values == {"会議名": "第5回"}


def test_broken_json_yields_no_values_instead_of_raising():
    """壊れて返ることがある。止めると、雛形すら受け取れない。
    全欄が埋まらなかった扱いになり、印の残った雛形が出る（設計書6節）。"""
    assert filling.fill_values(["会議名"], "質問", [], [], lambda prompt: "not json") == {}


def test_a_json_array_yields_no_values():
    assert filling.fill_values(["会議名"], "質問", [], [], lambda prompt: "[1, 2]") == {}


def test_an_llm_failure_is_not_swallowed():
    """LLMが落ちたことは利用者に伝える。黙って空の雛形を返さない。"""

    def broken(prompt):
        raise RuntimeError("模擬失敗")

    with pytest.raises(RuntimeError, match="模擬失敗"):
        filling.fill_values(["会議名"], "質問", [], [], broken)


def test_the_prompt_contains_the_placeholder_names_and_the_question():
    prompt = filling.build_prompt(["会議名"], "第5回会議の議事録", [], [])
    assert "会議名" in prompt
    assert "第5回会議の議事録" in prompt


def test_the_prompt_contains_the_search_results_with_their_citations():
    prompt = filling.build_prompt(
        ["会議名"],
        "質問",
        [("社内資料", [_hit("第5回を開催した。", source="第5回議事録.docx")])],
        [],
    )
    assert "第5回を開催した。" in prompt
    assert "第5回議事録.docx" in prompt


def test_each_kind_of_source_gets_its_own_section():
    """混ぜて並べると、どれが社内の決定事項でどれが外部ライブラリの説明なのかを
    モデルが区別できない。"""
    prompt = filling.build_prompt(
        ["図"],
        "質問",
        [
            ("社内資料", [_hit("社内の決定事項。")]),
            ("技術ドキュメント", [_hit("sequenceDiagram syntax", source="mermaid.md")]),
        ],
        [],
    )
    assert prompt.index("社内資料") < prompt.index("技術ドキュメント")
    assert "sequenceDiagram syntax" in prompt


def test_the_prompt_says_a_diagram_may_be_returned():
    """この1文が無いと、モデルは図の欄にも散文を返す。記法を覚える役目は
    利用者ではなくプロンプトが引き受ける（設計書7節）。"""
    prompt = filling.build_prompt(["シーケンス図"], "質問", [], [])
    assert "mermaid" in prompt


def test_the_prompt_contains_the_attachments_with_their_names():
    prompt = filling.build_prompt(["会議名"], "質問", [], [("録音.txt", "本日の会議を始めます")])
    assert "録音.txt" in prompt
    assert "本日の会議を始めます" in prompt


def test_a_prompt_over_the_limit_is_refused():
    """切り詰めると、議事録の後半が抜けたことに利用者が気づけない（設計書7節）。"""
    long_text = "あ" * (filling.MAX_PROMPT_CHARS + 1)
    with pytest.raises(filling.PromptTooLongError, match="長すぎ"):
        filling.fill_values(["会議名"], "質問", [], [("長い.txt", long_text)], _answering({}))
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_docgen_filling.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'docgen.filling'`）

- [ ] **Step 3: 実装する**

```python
# docgen/filling.py
"""雛形の印に入れる値を決める。

検索を1回、LLM呼び出しを1回で全部の印を決める。印ごとに検索してLLMを呼ぶ案も
検討したが、議事録の雛形で印が8個あればLLM呼び出しが8回になり、1回30〜60秒として
数分かかる。さらに印どうしの整合が保証されず、「会議名は第5回なのに決定事項は
第4回」という食い違いが構造的に起こりうる（設計書6節）。

ask を引数で受け取るのは ingest/conditions.py と同じ理由である。ここを
モジュール内でOllamaクライアントに束縛すると、値を決める規則のテストに実機の
Ollamaが要るようになる。
"""
import json

# 生成に使う文脈の大きさ。coding_agent/connection.py が使う 32768／65536 の
# 小さいほうに合わせる。ingest/chat.py の NUM_CTX（8192）は条件抽出とクエリ翻訳の
# ための値であり、添付ファイルを丸ごと渡すこの経路には足りない。
GENERATION_NUM_CTX = 32768

# プロンプトの上限。日本語は1文字が1トークン以上になることがあるため
# 「1文字 = 1トークン」とみなす安全側の見積もりを採り、32,768 から回答用に
# 約4,000を残した値である。トークナイザを持ち込んで正確に数えることはしない。
# 判定に使うだけの目的に対して依存が重く、生成モデルを替えるたびに数え方が
# 変わる。この値は上限の目安であって、超えたら止めるという一点にしか使わない。
MAX_PROMPT_CHARS = 28000


class PromptTooLongError(Exception):
    """添付と検索結果が文脈に収まらない。"""


def build_prompt(placeholders, question, sources, attachments) -> str:
    """印の一覧・検索結果・添付を1つのプロンプトにまとめる。

    sources は (資料の種類の名前, ヒットの並び) の並びである。種類ごとに節を
    分けるのは、混ぜて並べるとどれが社内の決定事項でどれが外部ライブラリの
    説明なのかをモデルが区別できないためである。
    """
    found = "\n\n".join(
        f"## {kind}の検索結果\n"
        + ("\n\n".join(f"【{hit.citation}】\n{hit.text}" for hit in hits)
           or f"（{kind}の検索結果はありません）")
        for kind, hits in sources
    ) or "## 検索結果\n（検索していません）"
    attached = "\n\n".join(
        f"【添付 {name}】\n{text}" for name, text in attachments
    ) or "（添付ファイルはありません）"
    names = "\n".join(f"- {name}" for name in placeholders)
    return (
        "あなたは社内文書を作成する担当者です。\n"
        "次の資料をもとに、雛形の各欄に入れる文章を決めてください。\n\n"
        "資料に書かれていないことは書かないでください。"
        "根拠が見つからない欄は、その欄を含めずに返してください。"
        "推測で埋めるより、空欄のまま人が書き足せるほうが安全です。\n\n"
        f"## 依頼\n{question}\n\n"
        f"{found}\n\n"
        f"## 添付ファイル\n{attached}\n\n"
        f"## 埋める欄\n{names}\n\n"
        "欄の名前をキー、入れる文章を値とするJSONオブジェクトだけを返してください。"
        "説明や前置きは書かないでください。\n"
        "箇条書きなど複数行になる場合は、値の中で改行してください。\n"
        # 印の名前から図かどうかを当てる仕組み（「図」で終わる名前を探す等）は
        # 作らない。名前の付け方は雛形を書く人の自由であり、規則を決めると
        # 雛形の書き方に制約が生まれる。
        "図で表すほうがよい欄は、```mermaid で始まるコードブロックだけを"
        "値にしてください。説明文と図を同じ欄に混ぜないでください。\n"
    )


def fill_values(placeholders, question, sources, attachments, ask) -> dict[str, str]:
    """印の名前から値への対応を返す。決まらなかった印は含めない。

    JSONが壊れて返っても例外は投げない。止めると雛形すら受け取れないため、
    全欄が「埋まらなかった」扱いになり、印の残った雛形が出る
    （ingest/query_translation.py が翻訳の失敗で原文に落とすのと同じ考え方）。

    LLM そのものが落ちた場合は投げ直す。こちらは利用者に伝えるべき失敗であり、
    黙って空の雛形を返してはいけない。
    """
    prompt = build_prompt(placeholders, question, sources, attachments)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise PromptTooLongError(
            f"添付と検索結果が長すぎます（{len(prompt):,}文字 / 上限 "
            f"{MAX_PROMPT_CHARS:,}文字）。添付を減らすか、短いものに分けてください"
        )
    raw = ask(prompt)
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    wanted = set(placeholders)
    return {
        name: value
        for name, value in loaded.items()
        # 雛形に無いキー、文字列でない値、空文字はいずれも「埋まらなかった」と
        # 同じ扱いにする。空文字を通すと、印が消えて空欄になり、埋め損ねたことに
        # 利用者が気づけない。
        if name in wanted and isinstance(value, str) and value.strip()
    }
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_filling.py -v`
Expected: PASS（13件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/filling.py tests/test_docgen_filling.py
git commit -m "feat: decide the placeholder values from search results and attachments"
```

---

### Task 9: Mermaid を PNG にする（`docgen/mermaid.py`）

**Files:**
- Create: `docgen/mermaid.py`
- Test: `tests/test_docgen_mermaid.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - `docgen.mermaid.MermaidError`
  - `docgen.mermaid.RENDER_TIMEOUT: int`（= 30）
  - `docgen.mermaid.is_diagram(value: str) -> bool`
  - `docgen.mermaid.diagram_source(value: str) -> str`
  - `docgen.mermaid.render(source: str) -> bytes` — PNG のバイト列
  - `docgen.mermaid.rendered(values: dict[str, str], on_diagram_error=None) -> tuple[dict[str, str], dict[str, bytes]]`

`on_diagram_error` は `(印の名前, 理由) -> None` である。`ingest/parsers/md_parser.py` の `on_missing_image` と同じ形にする。読めなかったものを黙って捨てず、呼び出し元が利用者へ伝えられるようにするためである。

**この課題の要点**: `mmdc` は呼ばない。実際に描けることは実測（設計書7節）で確かめてある。テストのたびに Chromium を起動すると遅く、`mmdc` の無い環境では必ず落ちる。ここで測るのは「失敗を黙って飲み込まないこと」である。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_mermaid.py
"""Mermaid のテキストを PNG にする。

mmdc は呼ばない。描けることは実測（設計書7節）で確かめてあり、テストのたびに
Chromium を起動すると遅く、mmdc の無い環境では必ず落ちる。ここで確かめるのは
「描けなかったことが呼び出し元に伝わる」という一点である。
"""
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from docgen import mermaid

DIAGRAM = "```mermaid\nsequenceDiagram\n  利用者->>画面: 生成を頼む\n```"
SOURCE = "sequenceDiagram\n  利用者->>画面: 生成を頼む"
PNG = b"\x89PNG\r\n\x1a\n"


def test_a_mermaid_block_is_a_diagram():
    assert mermaid.is_diagram(DIAGRAM)


def test_plain_text_is_not_a_diagram():
    assert not mermaid.is_diagram("第5回 定例会議")


def test_a_code_block_of_another_language_is_not_a_diagram():
    assert not mermaid.is_diagram("```python\nprint(1)\n```")


def test_text_after_the_block_is_not_a_diagram():
    """図とその説明が混ざった値は、図にせず文字列として扱う。

    一部だけ図にすると説明文が消える。図にしなければ Mermaid の記法が
    そのまま見えるだけで、利用者は何が起きたか分かる。
    """
    assert not mermaid.is_diagram(DIAGRAM + "\n\n上の図のとおりです。")


def test_the_source_comes_back_without_the_fence():
    assert mermaid.diagram_source(DIAGRAM) == SOURCE


def test_render_returns_what_the_tool_wrote():
    def fake_run(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_bytes(PNG)
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch("docgen.mermaid.shutil.which", return_value="mmdc.cmd"):
        with patch("docgen.mermaid.subprocess.run", side_effect=fake_run):
            assert mermaid.render(SOURCE) == PNG


def test_render_raises_when_the_tool_is_not_installed():
    with patch("docgen.mermaid.shutil.which", return_value=None):
        with pytest.raises(mermaid.MermaidError):
            mermaid.render(SOURCE)


def test_render_raises_when_the_tool_fails():
    failed = subprocess.CompletedProcess([], 1, "", "Parse error on line 2")
    with patch("docgen.mermaid.shutil.which", return_value="mmdc.cmd"):
        with patch("docgen.mermaid.subprocess.run", return_value=failed):
            with pytest.raises(mermaid.MermaidError, match="Parse error"):
                mermaid.render(SOURCE)


def test_render_raises_when_the_tool_does_not_return():
    timeout = subprocess.TimeoutExpired("mmdc", mermaid.RENDER_TIMEOUT)
    with patch("docgen.mermaid.shutil.which", return_value="mmdc.cmd"):
        with patch("docgen.mermaid.subprocess.run", side_effect=timeout):
            with pytest.raises(mermaid.MermaidError):
                mermaid.render(SOURCE)


def test_rendered_keeps_plain_values_as_text():
    texts, images = mermaid.rendered({"会議名": "第5回 定例会議"})
    assert texts == {"会議名": "第5回 定例会議"}
    assert images == {}


def test_rendered_turns_a_diagram_into_bytes():
    with patch("docgen.mermaid.render", return_value=PNG):
        texts, images = mermaid.rendered({"シーケンス図": DIAGRAM})
    assert texts == {}
    assert images == {"シーケンス図": PNG}


def test_a_diagram_that_cannot_be_drawn_stays_as_text_and_is_reported():
    """黙って落とさない。利用者は成果物を開くまで気づけない。"""
    reported = []
    with patch("docgen.mermaid.render", side_effect=mermaid.MermaidError("mmdc が見つかりません")):
        texts, images = mermaid.rendered(
            {"シーケンス図": DIAGRAM}, lambda name, reason: reported.append((name, reason))
        )
    assert texts == {"シーケンス図": DIAGRAM}
    assert images == {}
    assert reported == [("シーケンス図", "mmdc が見つかりません")]
```

- [ ] **Step 2: 失敗することを確認する**

Run: `pytest tests/test_docgen_mermaid.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'docgen.mermaid'`

- [ ] **Step 3: 実装する**

```python
# docgen/mermaid.py
"""Mermaid のテキストを PNG にする。

外部サービスへは投げない。mermaid.ink や kroki.io に送れば依存は増えないが、
社内設計書の図をそのまま社外へ出すことになる（AGENTS.md）。mermaid-cli は
手元の Chromium で描くため、図の内容はマシンの外へ出ない。
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# 描画を待つ上限（秒）。実測 2026-09-13 は3.5秒だった。Chromium の起動が
# 刺さったまま返らないと、画面が「生成中」のまま戻らなくなる。
RENDER_TIMEOUT = 30

# 値の全体が1つの ```mermaid ブロックであることを求める。ブロックの前後に
# 説明文が付いた値を「図の部分だけ」描くと説明文が消える。図にしなければ
# Mermaid の記法がそのまま見えるだけで、利用者は何が起きたか分かる。
_FENCE = re.compile(r"\A\s*```mermaid[ \t]*\r?\n(?P<source>.*?)\r?\n?```\s*\Z", re.DOTALL)


class MermaidError(Exception):
    """図にできなかった。呼び出し元は Mermaid のテキストをそのまま入れる。"""


def is_diagram(value: str) -> bool:
    return _FENCE.match(value) is not None


def diagram_source(value: str) -> str:
    match = _FENCE.match(value)
    if match is None:
        raise MermaidError("Mermaid のコードブロックではありません")
    return match.group("source")


def render(source: str) -> bytes:
    # Windows での実体は mmdc.cmd である。subprocess へ "mmdc" をそのまま渡すと
    # PATHEXT を見ないため FileNotFoundError になる。shutil.which は見る。
    executable = shutil.which("mmdc")
    if executable is None:
        raise MermaidError("mmdc が見つかりません")
    # mmdc は標準入出力を扱わず、入力も出力もファイルで指定する作りである。
    with tempfile.TemporaryDirectory() as directory:
        input_path = Path(directory) / "diagram.mmd"
        output_path = Path(directory) / "diagram.png"
        input_path.write_text(source, encoding="utf-8")
        try:
            completed = subprocess.run(
                [executable, "-i", str(input_path), "-o", str(output_path)],
                capture_output=True,
                text=True,
                timeout=RENDER_TIMEOUT,
            )
        except subprocess.TimeoutExpired as error:
            raise MermaidError(f"{RENDER_TIMEOUT}秒で描き終わりませんでした") from error
        if completed.returncode != 0:
            raise MermaidError(completed.stderr.strip() or "mmdc が失敗しました")
        if not output_path.is_file():
            raise MermaidError("mmdc が画像を書きませんでした")
        return output_path.read_bytes()


def rendered(values: dict[str, str], on_diagram_error=None):
    """値を「文字列として入れるもの」と「画像として入れるもの」に分ける。

    描けなかった値は文字列の側へ戻す。印が消えるのでも空になるのでもなく、
    Mermaid のテキストがそのまま成果物に残る。そのうえで on_diagram_error に
    知らせ、画面が利用者へ伝えられるようにする。
    """
    texts: dict[str, str] = {}
    images: dict[str, bytes] = {}
    for name, value in values.items():
        if not is_diagram(value):
            texts[name] = value
            continue
        try:
            images[name] = render(diagram_source(value))
        except MermaidError as error:
            texts[name] = value
            if on_diagram_error is not None:
                on_diagram_error(name, str(error))
    return texts, images
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_mermaid.py -v`
Expected: PASS（12件）

- [ ] **Step 5: コミットする**

```bash
git add docgen/mermaid.py tests/test_docgen_mermaid.py
git commit -m "feat: draw mermaid diagrams locally with mermaid-cli"
```

---

### Task 10: 図を差し込む（4つの `*_template.py`）

**Files:**
- Modify: `docgen/md_template.py`
- Modify: `docgen/docx_template.py`
- Modify: `docgen/pptx_template.py`
- Modify: `docgen/xlsx_template.py`
- Modify: `docgen/__init__.py`
- Test: `tests/test_docgen_diagrams.py`

**Interfaces:**
- Consumes: `docgen.mermaid.rendered()` / `docgen.mermaid.MermaidError`
- Produces:
  - `docgen.md_template.fill(path, values, on_diagram_error=None) -> bytes`
  - `docgen.docx_template.fill(path, values, on_diagram_error=None) -> bytes`
  - `docgen.pptx_template.fill(path, values, on_diagram_error=None) -> bytes`
  - `docgen.xlsx_template.fill(path, values, on_diagram_error=None) -> bytes`
  - `docgen.fill(path, values, on_diagram_error=None) -> bytes`
  - `docgen.docx_template.DIAGRAM_WIDTH`（= `Inches(6.0)`）

`on_diagram_error` の既定は `None` である。Task 2〜5 で書いた `fill(path, values)` の呼び出しとテストは1つも変えなくてよい。

**この課題の要点**: `.md` は図にしない。コードブロックのままで GitHub・VS Code・画面のプレビューが図として表示する。残り3形式だけが PNG を貼る。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_docgen_diagrams.py
"""Mermaid の値が図として入ること。

mmdc は呼ばない。docgen.mermaid.render を差し替えて PNG を返させる。
確かめるのは「画像が1つ増えること」と「描けなかったときに Mermaid の
テキストがそのまま残り、そのことが呼び出し元へ伝わること」である。
"""
import base64
import inspect
import io
import zipfile
from unittest.mock import patch

import docx
import openpyxl
import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

import docgen
from docgen import mermaid

DIAGRAM = "```mermaid\nsequenceDiagram\n  利用者->>画面: 生成を頼む\n```"

# 1x1 の PNG。python-docx も openpyxl も Pillow で実際に開くため、
# でたらめなバイト列では差し込めない。
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def drawn():
    with patch("docgen.mermaid.render", return_value=PNG) as render:
        yield render


@pytest.fixture
def undrawable():
    error = mermaid.MermaidError("mmdc が見つかりません")
    with patch("docgen.mermaid.render", side_effect=error):
        yield


def _word(tmp_path, text):
    path = tmp_path / "設計書.docx"
    document = docx.Document()
    document.add_paragraph(text)
    document.save(path)
    return path


def _slide_with(tmp_path, shapes_of):
    path = tmp_path / "設計書.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    box = shapes_of(slide).add_textbox(Inches(1), Inches(2), Inches(4), Inches(1))
    box.text_frame.text = "{{シーケンス図}}"
    presentation.save(path)
    return path


def _all_text(shapes) -> str:
    found = []
    for shape in shapes:
        if shape.has_text_frame:
            found.append(shape.text_frame.text)
        if hasattr(shape, "shapes"):
            found.append(_all_text(shape.shapes))
    return "\n".join(found)


def test_word_gets_a_picture_instead_of_the_mark(tmp_path, drawn):
    path = _word(tmp_path, "{{シーケンス図}}")
    filled = docx.Document(io.BytesIO(docgen.fill(path, {"シーケンス図": DIAGRAM})))
    assert len(filled.inline_shapes) == 1
    assert "mermaid" not in filled.paragraphs[0].text
    assert "{{" not in filled.paragraphs[0].text


def test_word_keeps_the_mermaid_text_when_it_cannot_be_drawn(tmp_path, undrawable):
    """黙って図が消えるのが最悪である。利用者は成果物を開くまで気づけない。"""
    path = _word(tmp_path, "{{シーケンス図}}")
    reported = []
    result = docgen.fill(
        path, {"シーケンス図": DIAGRAM}, lambda name, reason: reported.append(name)
    )
    filled = docx.Document(io.BytesIO(result))
    assert len(filled.inline_shapes) == 0
    assert "sequenceDiagram" in filled.paragraphs[0].text
    assert reported == ["シーケンス図"]


def test_powerpoint_puts_the_picture_where_the_shape_was(tmp_path, drawn):
    path = _slide_with(tmp_path, lambda slide: slide.shapes)
    filled = Presentation(io.BytesIO(docgen.fill(path, {"シーケンス図": DIAGRAM})))
    shapes = filled.slides[0].shapes
    pictures = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pictures) == 1
    assert (pictures[0].left, pictures[0].top) == (Inches(1), Inches(2))
    assert "{{シーケンス図}}" not in _all_text(shapes)


def test_powerpoint_reports_a_mark_inside_a_group(tmp_path, drawn):
    """グループの中の left/top はグループからの相対値で、スライドへ貼ると
    見当違いの場所に出る。ずれた場所に置くより、置けないことを伝える。"""
    path = _slide_with(tmp_path, lambda slide: slide.shapes.add_group_shape().shapes)
    reported = []
    result = docgen.fill(
        path, {"シーケンス図": DIAGRAM}, lambda name, reason: reported.append(name)
    )
    shapes = Presentation(io.BytesIO(result)).slides[0].shapes
    assert [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE] == []
    assert reported == ["シーケンス図"]
    assert "sequenceDiagram" in _all_text(shapes)


def test_excel_anchors_the_picture_to_the_marked_cell(tmp_path, drawn):
    """保存した中身で確かめる。openpyxl で読み直したときの画像の扱いは版に
    依存するため、xlsx の中に画像の部品があることを直接見る。"""
    path = tmp_path / "設計書.xlsx"
    book = openpyxl.Workbook()
    book.active["B3"] = "{{シーケンス図}}"
    book.save(path)

    result = docgen.fill(path, {"シーケンス図": DIAGRAM})
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        assert [name for name in archive.namelist() if name.startswith("xl/media/")]
    assert openpyxl.load_workbook(io.BytesIO(result)).active["B3"].value in (None, "")


def test_markdown_keeps_the_code_block(tmp_path, drawn):
    """.md は描かない。コードブロックのままで図として表示される。"""
    path = tmp_path / "設計書.md"
    path.write_text("# 設計書\n\n{{シーケンス図}}\n", encoding="utf-8")
    filled = docgen.fill(path, {"シーケンス図": DIAGRAM}).decode("utf-8")
    assert "```mermaid" in filled
    assert not drawn.called


def test_every_filler_accepts_the_callback():
    """1つでも受け取り損ねると、その形式の雛形を選んだときだけ TypeError に
    なる。画面からは4形式を同じ呼び方で呼ぶ。"""
    from docgen import _TEMPLATES

    for suffix, (_, filler) in _TEMPLATES.items():
        assert "on_diagram_error" in inspect.signature(filler).parameters, suffix
```

- [ ] **Step 2: 失敗することを確認する**

Run: `pytest tests/test_docgen_diagrams.py -v`
Expected: FAIL with `TypeError: fill() takes 2 positional arguments but 3 were given`

- [ ] **Step 3: 実装する**

`docgen/md_template.py` — 引数を受け取るだけで使わない。

```python
def fill(path: Path, values: dict[str, str], on_diagram_error=None) -> bytes:
    # .md は Mermaid をコードブロックのまま入れる。GitHub・VS Code・画面の
    # プレビューが図として表示するため、PNG にする理由が無い。引数を受け取る
    # のは、振り分け役が形式ごとに呼び分けなくて済むようにするためである。
    text = path.read_text(encoding="utf-8")
    return marks.replace(text, values).encode("utf-8")
```

`docgen/docx_template.py` — 印を消して、同じ段落に画像を足す。

```python
import io

from docx.shared import Inches

from docgen import marks, mermaid

# mmdc の既定の PNG は幅800px（約8.3インチ）で、A4縦の段幅（約6.5インチ）より
# 広い。そのまま入れると右へはみ出すので、幅を決めて高さは比で追従させる。
DIAGRAM_WIDTH = Inches(6.0)


def fill(path: Path, values: dict[str, str], on_diagram_error=None) -> bytes:
    texts, images = mermaid.rendered(values, on_diagram_error)
    document = docx.Document(path)
    for paragraph in _paragraphs(document):
        _fill_paragraph(paragraph, texts, images)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _fill_paragraph(paragraph, values: dict[str, str], images=None) -> None:
    if not paragraph.runs:
        return
    images = images or {}
    original = "".join(run.text for run in paragraph.runs)
    here = [name for name in marks.names(original) if name in images]
    # 図にする印はいったん空文字にしてから画像を足す。消さないと、画像の脇に
    # {{シーケンス図}} の文字が残る。
    replaced = marks.replace(original, {**values, **{name: "" for name in here}})
    if replaced == original:
        # 印が無い、あるいは値が1つも当たらなかった段落。触らない。
        # 触ると、書式の違う run が先頭 run のものに潰れる。
        return
    paragraph.runs[0].text = replaced
    for run in paragraph.runs[1:]:
        # 文字を持たない run は触らない（Task 3 と同じ理由。ロゴが消える）。
        if run.text:
            run.text = ""
    for name in here:
        paragraph.runs[0].add_picture(io.BytesIO(images[name]), width=DIAGRAM_WIDTH)
```

`docgen/pptx_template.py` — 印を持つ図形の位置に置く。

```python
from docgen import marks, mermaid


def fill(path: Path, values: dict[str, str], on_diagram_error=None) -> bytes:
    texts, images = mermaid.rendered(values, on_diagram_error)
    presentation = Presentation(path)
    placed: set[str] = set()
    for slide in presentation.slides:
        placed |= _place_diagrams(slide, images)
    for name in images:
        if name in placed:
            continue
        # 貼る先が決まらなかった図は、Mermaid のテキストとして入れる。印が
        # 空のまま残ると、利用者は図が消えたことに気づけない。
        texts[name] = values[name]
        if on_diagram_error is not None:
            on_diagram_error(name, "グループ図形の中の印は図にできません")
    for slide in presentation.slides:
        for paragraph in _shape_paragraphs(slide.shapes):
            _fill_paragraph(paragraph, texts)
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def _place_diagrams(slide, images: dict[str, bytes]) -> set[str]:
    """図の印を持つ図形の位置に画像を置き、印の文字を消す。置けた印を返す。

    ここだけグループの中へ入らない。グループの中の図形の left/top はグループ
    からの相対値であり、slide.shapes.add_picture にそのまま渡すと見当違いの
    場所へ貼られる。黙ってずれるより、置かずに呼び出し元へ返す。
    """
    placed: set[str] = set()
    # 走査の途中で図形が増えるため、先に並びを固定する。
    for shape in list(slide.shapes):
        if not shape.has_text_frame:
            continue
        here = [name for name in marks.names(shape.text_frame.text) if name in images]
        if not here:
            continue
        for name in here:
            # 幅は図形に合わせ、高さは比を保って python-pptx に決めさせる。
            slide.shapes.add_picture(
                io.BytesIO(images[name]), shape.left, shape.top, width=shape.width
            )
            placed.add(name)
        for paragraph in shape.text_frame.paragraphs:
            _fill_paragraph(paragraph, {name: "" for name in here})
    return placed
```

`docgen/xlsx_template.py` — `_cells` がシートも返すようにして、セルを錨にする。

```python
from openpyxl.drawing.image import Image

from docgen import marks, mermaid


def _cells(book):
    for sheet in book.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                # 印は文字列にしか現れない。数値セルに置換をかけると型が変わる。
                if isinstance(cell.value, str):
                    # 画像はセルではなくシートに足すため、シートも一緒に返す。
                    yield sheet, cell


def placeholders(path: Path) -> list[str]:
    found: list[str] = []
    for _, cell in _cells(openpyxl.load_workbook(path)):
        for name in marks.names(cell.value):
            if name not in found:
                found.append(name)
    return found


def fill(path: Path, values: dict[str, str], on_diagram_error=None) -> bytes:
    texts, images = mermaid.rendered(values, on_diagram_error)
    book = openpyxl.load_workbook(path)
    for sheet, cell in _cells(book):
        here = [name for name in marks.names(cell.value) if name in images]
        replaced = marks.replace(cell.value, {**texts, **{name: "" for name in here}})
        if replaced == cell.value:
            continue
        cell.value = replaced
        if "\n" in replaced:
            alignment = copy(cell.alignment)
            alignment.wrap_text = True
            cell.alignment = alignment
        for name in here:
            # 画像はセルの中に入らない。セルを左上の錨にして上へ浮かせる。
            image = Image(io.BytesIO(images[name]))
            image.anchor = cell.coordinate
            sheet.add_image(image)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()
```

`docgen/__init__.py` — 受け取った合図をそのまま渡す。

```python
def fill(path: Path, values: dict[str, str], on_diagram_error=None) -> bytes:
    _, filler = _template_for(path)
    return filler(path, values, on_diagram_error)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_docgen_diagrams.py tests/test_docgen_md_template.py tests/test_docgen_docx_template.py tests/test_docgen_pptx_template.py tests/test_docgen_xlsx_template.py -v`
Expected: PASS（7件 + Task 2〜5 で書いた分が全部通ったまま）

- [ ] **Step 5: コミットする**

```bash
git add docgen/ tests/test_docgen_diagrams.py
git commit -m "feat: embed mermaid diagrams as pictures in word, powerpoint and excel"
```

---

### Task 11: 画面（`rag_chat_app.py`）

**Files:**
- Modify: `rag_chat_app.py`
- Test: `tests/test_rag_chat_app_cowork.py`

**Interfaces:**
- Consumes: `docgen.placeholders()` / `docgen.fill()` / `docgen.templates` / `docgen.filling` / `ingest.retrieval.search()` / `ingest.parsers.parse()`
- Produces: なし（画面が終端）

**この課題の要点**: `st.chat_input` の中にウィジェットは置けない。トグルは入力欄のすぐ上に置く。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_rag_chat_app_cowork.py
"""Cowork タブ（雛形からの文書生成）。

実機のOllamaにもネットワークにも触れない。AppTest は rag_chat_app.py を同じ
プロセスで実行するため、本番のストアと本番の templates/ を開かせない。
"""
import json
from pathlib import Path
from unittest.mock import patch

import docx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import ingest.retrieval as retrieval
from docgen import templates as templates_module
from ingest import chat
from ingest import reranker as reranker_module
from ingest import store as store_module
from ingest import vlm as vlm_module
from ingest.vector_store import open_store as open_real_store

APP_PATH = Path(__file__).resolve().parent.parent / "rag_chat_app.py"


@pytest.fixture
def app():
    st.cache_resource.clear()
    return AppTest.from_file(str(APP_PATH), default_timeout=60)


@pytest.fixture(autouse=True)
def _no_network():
    with (
        patch.object(reranker_module, "check_reranker", lambda: None),
        patch.object(reranker_module, "rerank", lambda query, texts: [9.0] * len(texts)),
        patch.object(vlm_module, "check_vlm", lambda *a, **k: None),
    ):
        yield


def _stub_store():
    def factory(*args, **kwargs):
        collection = open_real_store(":memory:")
        collection.add(
            ids=["chunk-1"],
            documents=["第5回 AI活用検討会を開催した。"],
            embeddings=[[0.1, 0.2]],
            metadatas=[{"source": "議事録.docx", "location_type": "section", "location": 1}],
        )
        return collection

    return factory


def _register(directory, name="議事録.docx"):
    directory.mkdir(parents=True, exist_ok=True)
    document = docx.Document()
    document.add_paragraph("{{会議名}}")
    document.add_paragraph("{{決定事項}}")
    document.save(directory / name)


def test_the_mode_toggle_offers_both_modes(app, tmp_path):
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
    ):
        app.run()
    assert not app.exception
    assert "Cowork" in str(app)


def test_cowork_without_any_template_tells_the_user_to_register_one(app, tmp_path):
    """雛形が0件のまま生成ボタンだけ出すと、押しても何も起きない。"""
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()

    assert not app.exception
    assert any("雛形" in warning.value for warning in app.warning)


def test_cowork_generates_a_file_and_offers_it_for_download(app, tmp_path):
    store = tmp_path / "templates"
    _register(store)
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {"会議名": "第5回 AI活用検討会", "決定事項": "・継続"}, ensure_ascii=False
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert app.download_button


def test_cowork_lists_the_marks_it_could_not_fill(app, tmp_path):
    """埋まらなかった欄を出さないと、利用者は雛形を開くまで気づけない。"""
    store = tmp_path / "templates"
    _register(store)
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {"会議名": "第5回 AI活用検討会"}, ensure_ascii=False
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert any("決定事項" in warning.value for warning in app.warning)


def test_cowork_uses_a_larger_context_size(app, tmp_path):
    """8192 のままだと、文字起こしを添付した瞬間に文脈からこぼれる。"""
    store = tmp_path / "templates"
    _register(store)
    seen = []

    def ask_json(model, prompt, session=None, num_ctx=None):
        seen.append(num_ctx)
        return json.dumps({"会議名": "第5回"}, ensure_ascii=False)

    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "ask_json", ask_json),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("議事録を作って").run()

    from docgen import filling

    assert seen == [filling.GENERATION_NUM_CTX]


def test_cowork_does_not_search_the_documentation_unless_it_is_asked(app, tmp_path):
    """既定で技術ドキュメントまで引くと、1回の生成ごとに英訳のLLM呼び出しが
    1回と検索が1本、要らないまま増える（30〜60秒）。"""
    store = tmp_path / "templates"
    _register(store)
    opened = []
    collection = _stub_store()

    def factory(db_path, *args, **kwargs):
        opened.append(str(db_path))
        return collection(db_path)

    with (
        patch.object(store_module, "open_store", factory),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {"会議名": "第5回"}, ensure_ascii=False
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert not any("docs_store" in path for path in opened)


def test_cowork_tells_the_user_when_a_diagram_could_not_be_drawn(app, tmp_path):
    """黙って Mermaid のテキストが入っていると、利用者は成果物を開くまで
    気づけない。"""
    store = tmp_path / "templates"
    _register(store)
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            mermaid, "render", side_effect=mermaid.MermaidError("mmdc が見つかりません")
        ),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {
                    "会議名": "```mermaid\nsequenceDiagram\n  利用者->>画面: 生成\n```",
                    "決定事項": "・継続",
                },
                ensure_ascii=False,
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("設計書を作って").run()

    assert not app.exception
    assert any("図にできなかった" in warning.value for warning in app.warning)
```

テストの import に `from docgen import mermaid` を足す。

- [ ] **Step 2: テストが失敗することを確認する**

Run: `pytest tests/test_rag_chat_app_cowork.py -v`
Expected: FAIL（`IndexError`。`app.segmented_control` が空）

- [ ] **Step 3: 実装する**

`rag_chat_app.py` に次を足す。

import に追加する。

```python
import docgen
from docgen import filling as docgen_filling
from docgen import templates as docgen_templates
```

`MODE_CHAT` / `MODE_COWORK` の定数を `CORPUS_INTERNAL` の近くに置く。

```python
MODE_CHAT = "チャット"
MODE_COWORK = "Cowork"
```

雛形の登録・削除ダイアログを `upload_dialog` の隣に置く。画面の作り方を2通りにしない。

```python
@st.dialog("雛形を登録・削除する")
def template_dialog():
    st.caption(
        "雛形の空欄は {{会議名}} のように書いてください。"
        "登録した雛形はこのマシンの templates/ に残ります。"
    )
    uploaded = st.file_uploader(
        "雛形のファイル",
        type=sorted(suffix.lstrip(".") for suffix in docgen.SUPPORTED_SUFFIXES),
        accept_multiple_files=True,
        key="template_files",
    )
    if st.button("登録する", key="run_template_register"):
        if not uploaded:
            st.warning("先にファイルを選んでください。")
        else:
            with tempfile.TemporaryDirectory() as workspace:
                for file in uploaded:
                    path = Path(workspace) / file.name
                    path.write_bytes(file.getvalue())
                    docgen_templates.register(path)
            st.success(f"{len(uploaded)}件を登録しました。")

    if st.button("閉じる", key="close_template_dialog"):
        st.session_state.template_dialog_open = False
        st.rerun()

    for path in docgen_templates.templates():
        left, right = st.columns([4, 1])
        # 印を添えるのは、登録した雛形に印が1つも無いことをこの場で気づける
        # ようにするため。生成してから空の結果を見るより早い。
        names = docgen.placeholders(path)
        left.write(f"{path.name} — 印 {len(names)}個: {'、'.join(names) or 'なし'}")
        if right.button("削除", key=f"remove_{path.name}"):
            docgen_templates.remove(path.name)
            st.rerun()
```

チャット入力の直前にトグルと Cowork 用の入力を置く。

```python
# st.chat_input の中にウィジェットは置けないため、トグルは入力欄のすぐ上に置く。
mode = st.segmented_control(
    "モード",
    [MODE_CHAT, MODE_COWORK],
    default=MODE_CHAT,
    key="mode",
    label_visibility="collapsed",
    disabled=st.session_state.generating,
)

template_path = None
attachments = []
# 既定は社内資料だけ。議事録や報告書はそれで足りる。
use_internal, use_docs = True, False
if mode == MODE_COWORK:
    available = docgen_templates.templates()
    if not available:
        st.warning(
            "雛形が登録されていません。下のボタンから登録してください。"
            "空欄は {{会議名}} のように書きます。"
        )
    else:
        left, right = st.columns([3, 1])
        template_path = left.selectbox(
            "雛形", available, format_func=lambda path: path.name, key="template"
        )
        if right.button("雛形を登録・削除"):
            st.session_state.template_dialog_open = True
        # どの資料を引くかは雛形と依頼で決まるので、利用者に選ばせる。
        # 技術ドキュメントを入れると英訳のLLM呼び出しが1回と検索が1本増え、
        # 生成が30〜60秒遅くなる。要らない回に払う理由がない。
        corpora = st.columns(2)
        use_internal = corpora[0].checkbox(
            "社内資料を参照", value=True, key="cowork_internal"
        )
        use_docs = corpora[1].checkbox(
            "技術ドキュメントを参照", value=False, key="cowork_docs"
        )
        attached = st.file_uploader(
            "添付（この回だけ使い、DBには入れません）",
            type=sorted(suffix.lstrip(".") for suffix in SUPPORTED_SUFFIXES),
            accept_multiple_files=True,
            key="cowork_files",
        )
        attachments = attached or []

if st.session_state.get("template_dialog_open"):
    template_dialog()
```

生成の処理は、既存の `if st.session_state.generating:` の中で `mode` により分岐させる。

```python
    if mode == MODE_COWORK and template_path is not None:
        names = docgen.placeholders(template_path)
        if not names:
            st.error(
                f"{template_path.name} に {{{{印}}}} がありません。"
                "埋める欄が無いため生成しません。"
            )
        elif not use_internal and not use_docs and not attachments:
            # 両方外して添付も無ければ、根拠が1つも無い。呼んでも全欄が
            # 埋まらないので、LLMを呼ぶ前に止める。
            st.error("参照する資料も添付ファイルもありません。根拠が無いため生成しません。")
        else:
            _generate_document(
                template_path, names, question, attachments, use_internal, use_docs
            )
```

生成の本体は関数に切り出す。`rag_chat_app.py` は665行あり、この処理をチャットの分岐の中に直接書くと読めなくなる。

**実測 2026-09-13（実装中に判明）**: 下のコードは `st.error` / `st.download_button` をその場で呼ぶ形だが、**このままでは画面に何も出ない**。生成の分岐の末尾には `generating` を戻すための `st.rerun()` があり（チャットの入力欄を再び使えるようにするため）、同じ実行での描画ごと消える。結果は `st.session_state.cowork_result` に積み、次の実行で描くこと。既存の `ingest_report`（取り込みの結果を `st.session_state` 経由で次の実行に描き直している箇所）と同じ形にする。下のコードの `st.*` の呼び出しは、**その `render_cowork_result` の中に置く**と読み替えること。

```python
def _generate_document(template_path, names, question, attachments, use_internal, use_docs):
    """雛形を埋めてダウンロードボタンまで出す。

    どのコーパスを引くかは画面が決め、filling.py へは (種類の名前, ヒット) の
    並びで渡す。filling.py にコーパスの知識を持たせない（設計書6節）。
    """

    def ask(prompt):
        return chat.ask_json(
            model, prompt, num_ctx=docgen_filling.GENERATION_NUM_CTX
        )

    sources = []
    try:
        if use_internal:
            internal = get_collection(DB_PATH)
            sources.append((
                "社内資料",
                search(
                    internal,
                    question,
                    index=get_index(internal, DB_PATH, internal.revision()),
                    rerank=rerank_callable,
                ),
            ))
        if use_docs:
            documents = get_collection(DOCS_DB_PATH)
            if documents.count() == 0:
                # 取り込み前でも生成は止めない。社内資料と添付だけで埋める。
                st.info("技術ドキュメントが取り込まれていません。この検索は飛ばしました。")
            else:
                # 英語のコーパスなので日本語のままでは当たらず、採否も距離では
                # 決まらない（PR #41）。チャット側の経路と同じ2つを渡す。
                english = query_translation.translate_query(question, ask_json)
                sources.append((
                    "技術ドキュメント",
                    search(
                        documents,
                        english,
                        index=get_index(documents, DOCS_DB_PATH, documents.revision()),
                        rerank=rerank_callable,
                        rerank_floor=DOCS_RERANK_FLOOR,
                    ),
                ))
    except embedder.EmbeddingError as error:
        st.error(str(error))
        return
    except chat.ChatError as error:
        # 英訳もLLMである。落ちたら伝えて止める。
        st.error(str(error))
        return

    texts = []
    with tempfile.TemporaryDirectory() as workspace:
        for file in attachments:
            path = Path(workspace) / file.name
            path.write_bytes(file.getvalue())
            # 添付はDBに入れない。取り出した本文をその場で使うだけである。
            units = parse(path)
            texts.append((file.name, "\n".join(unit.text for unit in units)))

    try:
        values = docgen_filling.fill_values(names, question, sources, texts, ask)
    except docgen_filling.PromptTooLongError as error:
        st.error(str(error))
        return
    except chat.ChatError as error:
        st.error(str(error))
        return

    undrawn = []
    data = docgen.fill(
        template_path, values, lambda name, reason: undrawn.append((name, reason))
    )
    missing = [name for name in names if name not in values]
    if missing:
        st.warning(f"埋まらなかった欄: {'、'.join(missing)}（雛形の {{{{印}}}} が残ります）")
    if undrawn:
        # 図にできなかったことは開く前に伝える。黙って Mermaid のテキストが
        # 入っていると、利用者は成果物を開くまで気づけない。
        st.warning(
            "図にできなかった欄: "
            + "、".join(f"{name}（{reason}）" for name, reason in undrawn)
        )
    for name, hits in sources:
        if not hits:
            st.info(f"{name}の検索は0件でした。")
    stem = template_path.stem
    st.download_button(
        "ダウンロード",
        data=data,
        file_name=f"{stem}_{date.today().isoformat()}{template_path.suffix}",
    )
    for _, hits in sources:
        if hits:
            render_hits(hits)
```

`from ingest.parsers import parse` と `from datetime import date` の import を足す。`query_translation` / `DOCS_DB_PATH` / `DOCS_RERANK_FLOOR` は既にチャット側の経路が使っており、追加の import は要らない。

- [ ] **Step 4: テストが通ることを確認する**

Run: `pytest tests/test_rag_chat_app_cowork.py -v`
Expected: PASS（7件）

- [ ] **Step 5: 既存のテストが1つも壊れていないことを確認してコミットする**

Run: `pytest -q`
Expected: 全件 PASS、失敗ゼロ

```bash
git add rag_chat_app.py tests/test_rag_chat_app_cowork.py
git commit -m "feat: add the cowork mode that fills a template and offers the file"
```

---

### Task 12: ドキュメントを更新する

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/処理箇所マップ.md`
- Modify: `README.md`

**Interfaces:** なし

**この課題の要点**: 新しい外部通信の経路は増えないが、**添付ファイルの本文が `OLLAMA_HOST` に乗る**。DBに残らないことと、外へ出ないことは別である。あわせて、Python の外の依存（`mermaid-cli`）の入れ方を README に書く。`requirements.txt` では管理できない。

- [ ] **Step 1: `AGENTS.md` の4本目の説明に追記する**

`AGENTS.md` の「4本目は `OLLAMA_HOST` である」の段落の末尾に足す。

```markdown
  雛形からの文書生成（`docgen/`）もこの経路を使う。新しい宛先は増えないが、
  画面で添付したファイルの本文が `ingest/chat.py` の `ask_json` に渡り、この
  経路へ乗る。添付はDBに入れない（`docs/superpowers/specs/2026-09-13-document-generation-design.md`）
  が、DBに残らないことと外へ出ないことは別である。オフラインの資料を扱うときは
  `OLLAMA_HOST` がローカルを指していることを確かめること。
```

- [ ] **Step 2: `docs/処理箇所マップ.md` に節を足す**

末尾に次の節を足す。

```markdown
## 雛形からの文書生成

| 箇所 | 内容 |
|---|---|
| [docgen/marks.py](../docgen/marks.py) | 印の記法 `{{名前}}`。記法を知る唯一の場所 |
| [docgen/__init__.py](../docgen/__init__.py) | 拡張子で振り分ける。対応は docx/xlsx/pptx/md の4つ |
| [docgen/docx_template.py](../docgen/docx_template.py) | 段落単位で置換する。run に割れた印（実測 `['会議名：{{会議', '名}}']`）を拾うため |
| [docgen/templates.py](../docgen/templates.py) | 雛形の保管。原本を `templates/` に残す（埋めるのに原本が要る） |
| [docgen/filling.py](../docgen/filling.py) | 検索＋LLM1回で全部の印を決める。`GENERATION_NUM_CTX = 32768` |
| [docgen/mermaid.py](../docgen/mermaid.py) | ```` ```mermaid ```` の値を `mmdc` で PNG にする。外部サービスへは送らない |
| [rag_chat_app.py](../rag_chat_app.py) | チャット／Cowork のトグルと生成の画面 |

PDF は対象外である。PDFは文字を「位置」で持つ形式で、印より長い文字列を入れると
溢れて重なる（設計書2節に実測あり）。
```

- [ ] **Step 3: `README.md` に使い方を足す**

「ColabのL4 GPUに接続する」の節の後に足す。

```markdown
## 雛形からファイルを作る（Cowork）

1. 雛形の Word / Excel / PowerPoint / Markdown を用意し、埋めたい場所を
   `{{会議名}}` のように書く
2. 画面下のトグルで「Cowork」を選ぶ
3. 「雛形を登録・削除」から雛形を登録する
4. 雛形を選び、必要なら文字起こしなどを添付して、「第5回会議の議事録を作って」
   のように頼む
5. できたファイルをダウンロードする

検索結果と添付ファイルの両方から埋める。引く資料は「社内資料」「技術ドキュメント」の
チェックで選ぶ（既定は社内資料だけ）。根拠が見つからなかった欄は `{{会議名}}` のまま
残り、画面にも一覧が出る。添付ファイルはDBに入らない。

PDF は対象外である。

### 図（Mermaid）を入れる

`{{シーケンス図}}` のような欄には、Mermaid の図が入る。記法を覚える必要はない。
Word・Excel・PowerPoint には PNG として貼られ、Markdown ではコードブロックのまま
入る（GitHub や VS Code が図として表示する）。

図を描くには `mermaid-cli` が要る。

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc --version
```

入っていなければ、その欄には Mermaid のテキストがそのまま入り、画面に
「図にできなかった欄」として出る。生成そのものは止まらない。描画は手元の
Chromium で行い、図の内容は外へ出ない。
```

- [ ] **Step 4: テストが1つも壊れていないことを確認する**

Run: `pytest -q`
Expected: 全件 PASS、失敗ゼロ

- [ ] **Step 5: コミットする**

```bash
git add AGENTS.md docs/処理箇所マップ.md README.md
git commit -m "docs: describe the template-filling document generation"
```

---

## 完了の確認

すべての課題が終わったら次を確かめる。

- [ ] `pytest -q` が全件 PASS、失敗ゼロ
- [ ] `templates/` が `.gitignore` に入っている
- [ ] `ingest/chat.py` の `NUM_CTX = 8192` が変わっていない
- [ ] `docgen/` の外に印の正規表現が書かれていない（`grep -rn "{{" --include=*.py` で確認）
- [ ] 画面から実際に docx の雛形を登録し、生成してダウンロードできる
- [ ] `{{シーケンス図}}` を含む docx で、図が画像として入っている（`mmdc` を入れた状態）
- [ ] `mmdc` を PATH から外した状態で生成し、止まらずに「図にできなかった欄」が出る
- [ ] `grep -rn "mermaid.ink\|kroki" --include=*.py` が0件（図を外部へ送っていない）
