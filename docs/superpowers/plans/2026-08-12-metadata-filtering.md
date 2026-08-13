# 数値メタデータによる絞り込み検索 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Markdownのフロントマターをベクトル検索の対象ではなくChromaDBのメタデータとして保持し、「条件で絞り込んで比較する」質問に `where` で正確に回答できるようにする。

**Architecture:** 質問からLLMが絞り込み条件をJSONで抽出し、条件が1つでも取れれば `collection.get(where=...)` で該当資料を全件取得して仕様表に整形し、その表だけを根拠にモデルへ回答させる。条件が取れなければ現行のベクトル検索経路をそのまま使う。分類器は置かず、条件が取れたかどうかで分岐する。

**Tech Stack:** Python 3.13 / 標準ライブラリのみ（新規依存なし）/ pytest / ChromaDB / Ollama (bge-m3, llama3.1:8b)

**設計書:** `docs/superpowers/specs/2026-08-12-metadata-filtering-design.md`

## Global Constraints

- Python 3.13.3、仮想環境は `myvenv313`。すべてのコマンドは `.\myvenv313\Scripts\python.exe` 経由で実行する
- `.exe` ランチャー（`pytest.exe` / `streamlit.exe`）は使わない。venvが移動済みで壊れているため、必ず `python.exe -m <module>` の形で起動する
- **新しい依存パッケージを追加しない。** JSONの解析は標準ライブラリの `json` で行う
- 外部サービスへの送信は一切行わない
- ChromaDBのコレクションは `local_docs_v2` のまま。教材が使う `local_docs` には一切触れない
- Ollamaの接続先は `ingest/embedder.py` の `DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"`。`localhost` は使用しない
- チャンクIDの形式は `{source}::{location_type}{location}::{chunk_index}` のまま変えない
- フロントマターを**埋め込みテキストに入れてはならない**。メタデータとしてのみ保持する
- ChromaDBのメタデータ値はスカラー（str / int / float / bool）のみ。リストや辞書は入らない
- **本番の `chroma_db` へ書き込む前に、他のプロセスがそれを開いていないことを必ず確認する**（同時アクセスによるHNSW破損の実績があるため）
- コミットメッセージはコンベンショナルコミット形式、英語で記述する
- 作業ブランチは `feat/metadata-filtering`

---

## File Structure

| ファイル | 責務 | 変更 |
|---|---|---|
| `ingest/models.py` | 共有データ構造 | `ParsedUnit.attributes` を追加 |
| `ingest/parsers/md_parser.py` | Markdownのテキスト抽出 | `_drop_frontmatter` → `_split_frontmatter` |
| `ingest/chunker.py` | ユニット→チャンク変換 | 属性をメタデータへ展開・予約キーを保護 |
| `ingest/conditions.py` | **新規** 質問→絞り込み条件（LLMに依存） | — |
| `ingest/catalog.py` | **新規** 条件→該当資料と仕様表（LLMに依存しない） | — |
| `ingest/prompting.py` | プロンプト組み立て | 仕様表用を追加・根拠ゼロ時の欠陥を修正 |
| `scripts/ingest_source.py` | 取り込みCLI | `--only-suffix` |
| `rag_chat_app.py` | Streamlit UI | 2経路の結線 |
| `README.md` | 利用者向け説明 | 絞り込み経路と再取り込み手順 |

`conditions.py`（LLMに依存）と `catalog.py`（純粋な計算）を分けるのは、後者をLLMなしでテストできるようにするためである。

---

## Task 1: フロントマターを属性として取り出す

**Files:**
- Modify: `ingest/models.py`
- Modify: `ingest/parsers/md_parser.py`
- Modify: `tests/test_parser_md.py`

**Interfaces:**
- Consumes: なし
- Produces: `ParsedUnit(text, location_type, location, ocr=False, heading="", attributes={})`。`md_parser._split_frontmatter(lines) -> tuple[dict, list[str]]`

- [ ] **Step 1: 作業ブランチにいることを確認する**

```bash
git branch --show-current
```
Expected: `feat/metadata-filtering`（違う場合は `git checkout feat/metadata-filtering`）

- [ ] **Step 2: `ParsedUnit` に `attributes` を足す**

`ingest/models.py` の `ParsedUnit` の `heading` の直後に追加する。

```python
    # Markdownのフロントマター由来の属性。埋め込みテキストには入れず、
    # メタデータとしてのみ運ぶ。ベクトルは「510以下」のような数値条件を
    # 表現できないため、絞り込みは where に任せる必要がある。
    attributes: dict = field(default_factory=dict)
```

- [ ] **Step 3: 失敗するテストを書く**

`tests/test_parser_md.py` の `SAMPLE` を以下で置き換える。フロントマターに属性を足すだけで、本文は変えない（既存テストはそのまま通る）。

```python
SAMPLE = """---
model_id: UD-0900i
price_tier: スタンダード
washing_capacity_kg: 9.0
noise_wash_db: 27
tags: [IoT, スマホ連携]
---

# UD-0900i IoTコンパクト

## 機種概要

打田電器のUD-0900iは、洗濯容量9キログラムのコンパクトなIoTモデルです。

## 設置情報

- 外形寸法：幅598ミリメートル × 奥行き700ミリメートル
- 本体質量：約73キログラム
"""
```

同じファイルの末尾に以下を追加する。

```python
def test_scalar_frontmatter_becomes_attributes(sample):
    """noise_wash_db は30製品中24製品で本文に一度も現れない。
    ここで拾わないと索引から永久に失われる。"""
    units = parse_md(sample)
    assert units[0].attributes["model_id"] == "UD-0900i"
    assert units[0].attributes["price_tier"] == "スタンダード"


def test_numeric_attributes_keep_numeric_types(sample):
    """文字列のままだと ChromaDB の $lte が働かず、絞り込みが静かに失敗する。"""
    attributes = parse_md(sample)[0].attributes
    assert attributes["noise_wash_db"] == 27
    assert isinstance(attributes["noise_wash_db"], int)
    assert attributes["washing_capacity_kg"] == 9.0
    assert isinstance(attributes["washing_capacity_kg"], float)


def test_array_attributes_are_skipped(sample):
    """ChromaDBのメタデータはスカラーしか持てず、where も部分一致を扱えない。"""
    assert "tags" not in parse_md(sample)[0].attributes


def test_every_unit_carries_the_same_attributes(sample):
    """どのセクションがヒットしても絞り込めるよう、全ユニットに乗せる。"""
    units = parse_md(sample)
    assert [u.attributes for u in units] == [units[0].attributes] * len(units)


def test_attributes_are_still_not_in_the_unit_text(sample):
    """メタデータとして持つようになっても、埋め込みテキストには入れない。"""
    assert all("model_id" not in u.text for u in parse_md(sample))
    assert all("noise_wash_db" not in u.text for u in parse_md(sample))


def test_nested_yaml_keys_are_skipped(tmp_path):
    """字下げされた行は入れ子の属性であり、平らなメタデータには載せられない。"""
    text = "---\nouter:\n  inner: 1\n---\n\n# タイトル\n\n## 節\n\n本文がここにあります。\n"
    assert "inner" not in parse_md(_write(tmp_path, text))[0].attributes


def test_file_without_frontmatter_has_no_attributes(tmp_path):
    path = _write(tmp_path, "# タイトル\n\n## 節\n\n本文がここにあります。\n")
    assert parse_md(path)[0].attributes == {}


def test_unclosed_frontmatter_yields_no_attributes(tmp_path):
    """閉じられていないなら本文とみなす既存の判断を、属性側でも守る。"""
    path = _write(tmp_path, "---\nmodel_id: X\n\n# タイトル\n\n本文がここにあります。\n")
    assert parse_md(path)[0].attributes == {}
```

- [ ] **Step 4: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_parser_md.py -v`
Expected: FAIL — `AttributeError: 'ParsedUnit' object has no attribute 'attributes'` または `KeyError: 'model_id'`

- [ ] **Step 5: パーサーを実装する**

`ingest/parsers/md_parser.py` の `_drop_frontmatter` を、以下の3つの関数で置き換える。

```python
def _scalar(value: str):
    """YAMLのスカラー値をPythonの型に直す。採用しない値には None を返す。

    数値に見えるものを int / float にするのは、ChromaDB の where が
    数値比較をするため。文字列のまま入れると $lte が黙って効かなくなる。
    """
    text = value.strip()
    if not text or text.startswith("["):
        return None  # 配列は where が部分一致を扱えず、実用にならない
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_attributes(lines: list[str]) -> dict:
    """`key: value` の平らな行だけを拾う。

    字下げされた行は入れ子の属性であり、平らなメタデータには載せられないので飛ばす。
    """
    attributes: dict = {}
    for line in lines:
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        scalar = _scalar(value)
        if key.strip() and scalar is not None:
            attributes[key.strip()] = scalar
    return attributes


def _split_frontmatter(lines: list[str]) -> tuple[dict, list[str]]:
    """先頭のYAMLフロントマターを属性として取り出し、本文と分けて返す。

    フロントマターを埋め込みテキストに入れない判断は当初から変えていない。
    YAMLの生テキストより散文のほうが日本語の質問との類似度が出るためである。
    変えたのは「捨てる」ことのほうで、noise_wash_db は30製品中24製品で本文に
    一度も現れず、捨てると索引から永久に失われることが実測で分かった。
    """
    if not lines or lines[0].strip() != "---":
        return {}, lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return _parse_attributes(lines[1:index]), lines[index + 1 :]
    return {}, lines  # 閉じられていないなら本文とみなす
```

- [ ] **Step 6: `parse_md` を属性を運ぶように直す**

`parse_md` の先頭の行を置き換える。

```python
def parse_md(path: Path) -> list[ParsedUnit]:
    attributes, body_lines = _split_frontmatter(_read_lines(path))
    title = ""
    sections: list[tuple[str, list[str]]] = []
    heading: str = ""
    body: list[str] = []
    in_fence = False

    for line in body_lines:
```

`ParsedUnit(...)` の生成に `attributes` を追加する。`heading=section_heading,` の直後に置く。

```python
                heading=section_heading,
                attributes=attributes,
```

- [ ] **Step 7: `_read_lines` のdocstringを直す**

`_drop_frontmatter` はもう存在しないため、docstring内の名前を更新する。

```python
    utf-8 ではなく utf-8-sig を使うのは、BOM付きファイルだとBOM文字（U+FEFF）が
    先頭行の '---' にくっつき、_split_frontmatter が先頭のフロントマター境界を
    認識できず、フロントマターの生のYAMLがそのまま索引されてしまうため。
```

- [ ] **Step 8: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件。既存の `test_frontmatter_is_not_indexed` も通ること）

- [ ] **Step 9: コミットする**

```bash
git add ingest/models.py ingest/parsers/md_parser.py tests/test_parser_md.py
git commit -F - <<'EOF'
feat: keep Markdown frontmatter as attributes instead of dropping it

Not embedding raw YAML was the right call and still holds; discarding it
was not. noise_wash_db appears in no prose at all for 24 of the 30 product
sheets, so dropping the frontmatter left the figure absent from the index
and every question about it unanswerable.

Numbers are parsed into int/float because ChromaDB compares metadata by
type, and a numeric string would make $lte silently match nothing. Lists
are skipped since where() cannot do partial matches on them.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 2: 属性をチャンクのメタデータへ展開する

**Files:**
- Modify: `ingest/chunker.py`
- Modify: `tests/test_chunker.py`

**Interfaces:**
- Consumes: `ingest.models.ParsedUnit.attributes`
- Produces: `ingest.chunker.RESERVED_METADATA_KEYS: frozenset[str]`。`chunk_units(...)` のメタデータに属性が加わる

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chunker.py` の先頭のimportを差し替える。

```python
from ingest.chunker import (
    CHUNK_SIZE,
    MIN_CHUNK_CHARS,
    RESERVED_METADATA_KEYS,
    chunk_units,
)
from ingest.models import ParsedUnit
```

同じファイルの末尾に以下を追加する。

```python
def test_attributes_are_added_to_metadata():
    unit = ParsedUnit(
        text="これは十分な長さのある本文です。",
        location_type="section",
        location=1,
        attributes={"noise_wash_db": 26, "model_id": "UD-1100iS"},
    )
    metadata = _chunk([unit])[0].metadata
    assert metadata["noise_wash_db"] == 26
    assert metadata["model_id"] == "UD-1100iS"


def test_attributes_are_carried_into_every_chunk():
    """分割されても全チャンクが属性を持たないと、絞り込みが断片を取りこぼす。"""
    unit = ParsedUnit(
        text="あ" * 2000,
        location_type="section",
        location=1,
        attributes={"noise_wash_db": 26},
    )
    chunks = _chunk([unit])
    assert len(chunks) > 1
    assert all(c.metadata["noise_wash_db"] == 26 for c in chunks)


def test_reserved_keys_in_attributes_are_ignored():
    """属性が source を上書きすると、出典表示と差分取り込みが同時に壊れる。"""
    unit = ParsedUnit(
        text="これは十分な長さのある本文です。",
        location_type="section",
        location=1,
        attributes={"source": "偽物.md", "heading": "偽の見出し", "noise_wash_db": 26},
    )
    metadata = _chunk([unit])[0].metadata
    assert metadata["source"] == "a.pdf"
    assert metadata["heading"] == ""
    assert metadata["noise_wash_db"] == 26


def test_metadata_is_unchanged_for_units_without_attributes():
    """PDF・PPTX・DOCX由来のチャンクは今までどおりのキーだけを持つ。"""
    metadata = _chunk([_unit("これは十分な長さのある本文です。")])[0].metadata
    assert set(metadata) == RESERVED_METADATA_KEYS
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_chunker.py -v`
Expected: FAIL — `ImportError: cannot import name 'RESERVED_METADATA_KEYS' from 'ingest.chunker'`

- [ ] **Step 3: 予約キーを定義する**

`ingest/chunker.py` の `_SEPARATORS` の定義の直前に追加する。

```python
# チャンク自身が使うメタデータのキー。フロントマター由来の属性がこれらと
# 同名だった場合は採用しない。source を上書きされると出典表示と差分取り込みの
# ハッシュ判定が同時に壊れ、しかも例外が出ないため気づけない。
RESERVED_METADATA_KEYS = frozenset(
    {
        "source",
        "file_hash",
        "location_type",
        "location",
        "ocr",
        "heading",
        "chunk_index",
        "indexed_at",
    }
)
```

- [ ] **Step 4: メタデータに展開する**

`chunk_units` のメタデータ辞書の `"indexed_at": indexed_at,` の直後に追加する。

```python
                        "indexed_at": indexed_at,
                        **{
                            key: value
                            for key, value in unit.attributes.items()
                            if key not in RESERVED_METADATA_KEYS
                        },
```

- [ ] **Step 5: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 6: コミットする**

```bash
git add ingest/chunker.py tests/test_chunker.py
git commit -F - <<'EOF'
feat: carry unit attributes into chunk metadata

Every chunk of a product sheet gets the same attributes, so a hit on any
section can still be filtered on. Attributes that collide with a reserved
key are dropped rather than allowed to overwrite it: a frontmatter
"source" would break both the citation and the hash-based skip, and
neither failure raises.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 3: 拡張子を絞った再取り込みと実データへの反映

**Files:**
- Modify: `scripts/ingest_source.py`
- Modify: `tests/test_ingest_source.py`

**Interfaces:**
- Consumes: `ingest.parsers.SUPPORTED_SUFFIXES`
- Produces: `_target_files(source_dir, only_suffix=None)`、`ingest_directory(..., only_suffix=None)`、CLIの `--only-suffix`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ingest_source.py` の末尾（`test_main_forwards_force_flag_to_ingest_directory` の前）に以下を追加する。既存の `_write_docx` / `_write_md` / `_FakeSession` をそのまま使う。

```python
def test_only_suffix_limits_the_files(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    _write_md(source_dir, "仕様.md", "# 製品\n\n## 節\n\n本文がここにあります。\n")
    report = ingest_directory(
        source_dir, collection, session=_FakeSession(), only_suffix=".md"
    )
    assert set(report.indexed) == {"仕様.md"}


def test_only_suffix_accepts_a_bare_extension(source_dir, collection):
    """--only-suffix md と .md を同じに扱う。書き分けを覚える理由がない。"""
    _write_md(source_dir, "仕様.md", "# 製品\n\n## 節\n\n本文がここにあります。\n")
    report = ingest_directory(
        source_dir, collection, session=_FakeSession(), only_suffix="md"
    )
    assert set(report.indexed) == {"仕様.md"}


def test_only_suffix_skips_orphan_pruning(source_dir, collection):
    """ここを飛ばさないと、対象外の拡張子の資料が全部孤児として消える。"""
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    _write_md(source_dir, "仕様.md", "# 製品\n\n## 節\n\n本文がここにあります。\n")
    ingest_directory(source_dir, collection, session=_FakeSession())
    report = ingest_directory(
        source_dir, collection, session=_FakeSession(), force=True, only_suffix=".md"
    )
    assert report.removed == []
    assert stored_file_hash(collection, "議事録.docx") is not None


def test_full_run_still_prunes_orphans(source_dir, collection):
    """部分取り込みの分岐を入れても、通常の取り込みの孤児削除は残っていること。"""
    path = _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    path.unlink()
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == ["議事録.docx"]


def test_main_forwards_only_suffix_to_ingest_directory(monkeypatch, tmp_path):
    captured = {}

    def fake_ingest_directory(source_dir, collection, on_progress=None, **kwargs):
        captured.update(kwargs)
        return ingest_source.IngestReport()

    monkeypatch.setattr(ingest_source, "ingest_directory", fake_ingest_directory)
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(
        ingest_source.store, "open_collection", lambda _client: _FakeCollection()
    )
    monkeypatch.setattr(ingest_source.chromadb, "PersistentClient", lambda path: None)
    monkeypatch.setattr(
        sys, "argv", ["ingest_source", "--source-dir", str(tmp_path), "--only-suffix", "md"]
    )
    ingest_source.main()
    assert captured["only_suffix"] == "md"
```

`_FakeCollection` が既存テストに無い場合は、同じファイルの `_FakeSession` の直後に追加する。

```python
class _FakeCollection:
    """main() の最後に呼ばれる count() だけを満たす最小の代役。"""

    def count(self):
        return 0
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_ingest_source.py -v`
Expected: FAIL — `TypeError: ingest_directory() got an unexpected keyword argument 'only_suffix'`

- [ ] **Step 3: 走査を実装する**

`scripts/ingest_source.py` の `_target_files` を以下で置き換える。

```python
def _normalise_suffix(suffix: str) -> str:
    """先頭のドットの有無を問わない。--only-suffix md と .md を同じに扱う。"""
    lowered = suffix.strip().lower()
    return lowered if lowered.startswith(".") else f".{lowered}"


def _target_files(source_dir: Path, only_suffix: str | None = None) -> list[Path]:
    """サブフォルダも含めて対象ファイルを集める。

    資料を分類して置けるようにするため再帰する。対象外の拡張子はここで落とすので、
    source/ に雑多なファイルが増えてもパーサーには渡らない。
    ~$ で始まるファイルはOfficeが編集中に作る一時ファイル（ロックファイル）なので、
    対応拡張子でも除外する。含めるとPermissionErrorで取り込みが失敗扱いになる。
    only_suffix を渡すとさらにその拡張子だけへ絞る。フロントマターの追加のように
    Markdownだけを取り直したいとき、OCRを含む全量再処理（約24分）を避けるため。
    """
    wanted = _normalise_suffix(only_suffix) if only_suffix else None
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and not path.name.startswith("~$")
        and (wanted is None or path.suffix.lower() == wanted)
    )
```

- [ ] **Step 4: `ingest_directory` に引数を通す**

シグネチャに追加する。

```python
def ingest_directory(
    source_dir: Path,
    collection,
    session=None,
    on_progress=None,
    force: bool = False,
    only_suffix: str | None = None,
) -> IngestReport:
```

`files = _target_files(source_dir)` を置き換える。

```python
        files = _target_files(source_dir, only_suffix)
```

孤児削除を条件付きにする。既存の3行を以下で置き換える。

```python
        # source/ を唯一の入力とするため、消えた資料はDBからも消す。
        # ただし部分取り込みのときは行わない。対象外の拡張子のファイルが
        # すべて孤児と判定され、他形式のチャンクが丸ごと消えるため。
        if only_suffix is None:
            report.removed = store.delete_orphans(
                collection, {_source_key(path, source_dir) for path in files}
            )
            for source in report.removed:
                notify(f"削除（source/にありません）: {source}")
```

- [ ] **Step 5: CLIに引数を足す**

`main()` の `--force` の直後に追加する。

```python
    parser.add_argument(
        "--only-suffix",
        help="この拡張子のファイルだけを対象にする（例 .md）。指定時は孤児削除を行わない",
    )
```

`ingest_directory` の呼び出しを置き換える。

```python
    report = ingest_directory(
        args.source_dir,
        collection,
        on_progress=print,
        force=args.force,
        only_suffix=args.only_suffix,
    )
```

- [ ] **Step 6: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 7: `chroma_db` を開くプロセスが無いことを確認する**

Run:
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CommandLine | Format-List
```
Expected: `streamlit` を含むコマンドラインが1つも無いこと。**あれば必ず停止してから次へ進む。** 同時アクセスでHNSWインデックスが壊れた実績がある。

- [ ] **Step 8: 取り込み前の状態を記録する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; c=chromadb.PersistentClient(path=r'.\chroma_db'); print([(x.name, c.get_collection(x.name).count()) for x in c.list_collections()])"
```
Expected: `local_docs_v2` が460、`local_docs` が21。この数字を控える

- [ ] **Step 9: Markdownだけを再取り込みする**

Run: `.\myvenv313\Scripts\python.exe -m scripts.ingest_source --force --only-suffix .md`

Expected: `家電製品/*.md` 30ファイルが再取り込みされ、削除0件、`DB内の総チャンク数` が460のまま。OCRが走らないため数十秒で終わる

**総チャンク数が460から変わった場合は止めること。** チャンクの分割規則は変えていないため、数が変わるのは想定外である。

- [ ] **Step 10: 属性が入ったことを実データで確認する**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; from ingest import store; c=store.open_collection(chromadb.PersistentClient(path=r'.\chroma_db')); r=c.get(where={'noise_wash_db': {'$lte': 26}}, include=['metadatas']); print(sorted({m['source'] for m in r['metadatas']}))"
```
Expected: 10製品のファイル名が並ぶこと（UD-1000X / UD-1100i / UD-1100iE / UD-1100iP / UD-1100iS / UD-1200X / UD-1200XA / UD-1200XL / UD-1200XP / UD-1400X）

- [ ] **Step 11: コミットする**

```bash
git add scripts/ingest_source.py tests/test_ingest_source.py
git commit -F - <<'EOF'
feat: allow ingestion to be limited to one file extension

Adding metadata to existing chunks means re-ingesting, but a full --force
run reprocesses 23 OCR pages and takes about 24 minutes. Limiting the run
to .md re-indexes the 30 product sheets in seconds.

Orphan pruning is skipped whenever the filter is active: with the other
extensions filtered out of the file list, every one of their sources would
otherwise be judged an orphan and deleted.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 4: 質問から絞り込み条件を抽出する

**Files:**
- Create: `ingest/conditions.py`
- Create: `tests/test_conditions.py`

**Interfaces:**
- Consumes: `ingest.chunker.RESERVED_METADATA_KEYS`
- Produces: `Extraction(conditions: dict, failed: bool)`、`available_keys(collection) -> dict[str, str]`、`extract(question: str, schema: dict, ask) -> Extraction`。`ask` は `str -> str` の呼び出し可能オブジェクトで、LLMにプロンプトを渡してJSON文字列を返す

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_conditions.py` を新規作成する。

```python
import json

import pytest

from ingest.conditions import available_keys, extract
from ingest.embedder import EMBED_DIM
from ingest.store import open_collection
from tests.conftest import ephemeral_client

SCHEMA = {
    "noise_wash_db": "number",
    "installation_depth_min_mm": "number",
    "price_tier": "string",
}


@pytest.fixture
def collection():
    client = ephemeral_client()
    yield open_collection(client)
    client.clear_system_cache()


def _answer(payload):
    """LLMの代役。渡された文字列をそのまま返す。"""
    return lambda _prompt: payload


def _add(collection, chunk_id, metadata):
    collection.add(
        ids=[chunk_id],
        documents=["本文"],
        metadatas=[metadata],
        embeddings=[[1.0] + [0.0] * (EMBED_DIM - 1)],
    )


def test_extracts_a_numeric_condition():
    result = extract("26dB以下は", SCHEMA, _answer('{"noise_wash_db": {"$lte": 26}}'))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}
    assert result.failed is False


def test_extracts_two_conditions():
    payload = '{"noise_wash_db": {"$lte": 26}, "installation_depth_min_mm": {"$lte": 510}}'
    result = extract("26dBで510mm", SCHEMA, _answer(payload))
    assert result.conditions == {
        "noise_wash_db": {"$lte": 26},
        "installation_depth_min_mm": {"$lte": 510},
    }


def test_no_conditions_is_not_a_failure():
    """通常の質問と、抽出できなかったことは区別する。前者は黙って検索に回す。"""
    result = extract("乾燥方式は", SCHEMA, _answer("{}"))
    assert result.conditions == {}
    assert result.failed is False


def test_broken_json_is_a_failure():
    result = extract("26dB以下は", SCHEMA, _answer("これはJSONではありません"))
    assert result.conditions == {}
    assert result.failed is True


def test_failing_ask_is_a_failure():
    def explode(_prompt):
        raise RuntimeError("Ollamaが落ちた")

    result = extract("26dB以下は", SCHEMA, explode)
    assert result.conditions == {}
    assert result.failed is True


def test_unknown_key_is_dropped():
    result = extract("重さは", SCHEMA, _answer('{"weight_kg": {"$lte": 80}}'))
    assert result.conditions == {}


def test_unknown_operator_is_dropped():
    result = extract("26dBより下", SCHEMA, _answer('{"noise_wash_db": {"$lt": 26}}'))
    assert result.conditions == {}


def test_non_numeric_value_for_comparison_is_dropped():
    result = extract("26dB以下", SCHEMA, _answer('{"noise_wash_db": {"$lte": "26"}}'))
    assert result.conditions == {}


def test_string_equality_is_kept():
    """price_tier のような文字列属性は一致で絞れる必要がある。"""
    result = extract(
        "ハイグレードは", SCHEMA, _answer('{"price_tier": {"$eq": "ハイグレード"}}')
    )
    assert result.conditions == {"price_tier": {"$eq": "ハイグレード"}}


def test_one_broken_condition_does_not_discard_the_other():
    """片方が壊れていても、残った条件で絞り込めるほうが利用者に有益である。"""
    payload = '{"noise_wash_db": {"$lte": 26}, "weight_kg": {"$lte": 80}}'
    result = extract("26dBで80kg以下", SCHEMA, _answer(payload))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}
    assert result.failed is False


def test_empty_schema_does_not_call_the_llm():
    """属性が1つも無いコーパスでLLMを呼ぶのは無駄でしかない。"""
    calls = []

    def record(prompt):
        calls.append(prompt)
        return "{}"

    assert extract("26dB以下は", {}, record).conditions == {}
    assert calls == []


def test_available_keys_reports_types(collection):
    _add(
        collection,
        "a.md::section1::0",
        {"source": "a.md", "noise_wash_db": 26, "washing_capacity_kg": 11.0,
         "price_tier": "ハイグレード"},
    )
    assert available_keys(collection) == {
        "noise_wash_db": "number",
        "washing_capacity_kg": "number",
        "price_tier": "string",
    }


def test_available_keys_excludes_reserved_keys(collection):
    _add(collection, "a.md::section1::0", {"source": "a.md", "heading": "設置情報"})
    assert available_keys(collection) == {}


def test_available_keys_is_empty_for_an_empty_collection(collection):
    assert available_keys(collection) == {}


def test_the_prompt_lists_the_available_keys():
    """スキーマを渡さなければ、モデルはどのキー名を返せばよいか分からない。"""
    seen = []

    def record(prompt):
        seen.append(prompt)
        return "{}"

    extract("26dB以下は", SCHEMA, record)
    assert "noise_wash_db" in seen[0]
    assert "26dB以下は" in seen[0]
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_conditions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.conditions'`

- [ ] **Step 3: 実装する**

`ingest/conditions.py` を新規作成する。

```python
"""質問から絞り込み条件を取り出す。

ベクトルは「510以下」のような数値条件を表現できない。実測では、防水パン510mmを
問う質問で設置不可のUD-1400X（545mm必要）が上位に入り、上位20件の距離が
0.375〜0.421に密集して製品を区別しなかった。距離ではなく where で絞るために、
質問を機械が扱える条件へ変換する。

LLMの呼び出しは ask として外から渡す。ここをモジュール内でOpenAIクライアントに
束縛すると、変換規則のテストに実機のOllamaが要るようになるため。
"""
import json
from dataclasses import dataclass, field

from ingest.chunker import RESERVED_METADATA_KEYS

# ChromaDBの where がそのまま受け取れる演算子だけを許す。変換層を挟まずに済む。
COMPARISONS = ("$lte", "$gte")
EQUALITY = "$eq"


@dataclass(frozen=True)
class Extraction:
    """抽出の結果。

    conditions が空であることと failed は別物である。前者は「条件のない通常の
    質問」であり黙ってベクトル検索へ回してよいが、後者は利用者に伝える必要がある。
    """

    conditions: dict = field(default_factory=dict)
    failed: bool = False


def available_keys(collection) -> dict[str, str]:
    """メタデータに実在する属性キーと、その型（number / string）を集める。

    キー一覧をコードに固定しない。資料を入れ替えてもコードを直さずに追従させるため。
    件数を絞らず全件読むのは、ChromaDBの取得順が資料の並びを保証せず、属性を
    持たないPDF由来のチャンクばかりを引いてスキーマが空になり得るため。
    460件でも数十ミリ秒であり、起動時の1回だけ呼ぶ。
    """
    if collection.count() == 0:
        return {}
    schema: dict[str, str] = {}
    for metadata in collection.get(include=["metadatas"]).get("metadatas") or []:
        for key, value in metadata.items():
            if key in RESERVED_METADATA_KEYS or key in schema:
                continue
            # bool は int の派生なので、数値より先に落とす。
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                schema[key] = "number"
            elif isinstance(value, str):
                schema[key] = "string"
    return schema


def _prompt(question: str, schema: dict[str, str]) -> str:
    keys = "\n".join(f"- {key}（{kind}）" for key, kind in sorted(schema.items()))
    return (
        "次の質問から、資料を絞り込む条件だけを抜き出してJSONで答えてください。\n"
        "使ってよい属性は以下だけです。\n\n"
        f"{keys}\n\n"
        "演算子は $lte（以下）、$gte（以上）、$eq（一致）の3つだけを使ってください。\n"
        '形式: {"属性名": {"演算子": 値}}\n'
        "条件が読み取れない質問には {} と答えてください。\n"
        "説明は書かず、JSONだけを返してください。\n\n"
        f"質問: {question}"
    )


def _valid(operator: str, value) -> bool:
    if isinstance(value, bool):  # True は 1 として比較できてしまうため弾く
        return False
    if operator in COMPARISONS:
        return isinstance(value, (int, float))
    return operator == EQUALITY and isinstance(value, (int, float, str))


def _sanitise(loaded: dict, schema: dict[str, str]) -> dict:
    """スキーマに無いキー・許可外の演算子・型の合わない値を1件ずつ捨てる。

    1つでも壊れていたら全部捨てる作りにはしない。2条件のうち片方だけが壊れて
    いる場合、残った条件で絞り込めるほうが利用者にとって有益なためである。
    """
    conditions: dict = {}
    for key, condition in loaded.items():
        if key not in schema or not isinstance(condition, dict):
            continue
        for operator, value in condition.items():
            if _valid(operator, value):
                conditions[key] = {operator: value}
                break
    return conditions


def extract(question: str, schema: dict[str, str], ask) -> Extraction:
    """質問を絞り込み条件へ変換する。失敗しても例外は投げない。"""
    if not schema:
        return Extraction()
    try:
        raw = ask(_prompt(question, schema))
    except Exception:  # LLM側の事情で回答生成まで巻き添えにしない
        return Extraction(failed=True)
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return Extraction(failed=True)
    if not isinstance(loaded, dict):
        return Extraction(failed=True)
    return Extraction(conditions=_sanitise(loaded, schema))
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 5: コミットする**

```bash
git add ingest/conditions.py tests/test_conditions.py
git commit -F - <<'EOF'
feat: extract numeric filter conditions from a question

An embedding cannot represent "at most 510": the measured ranking for a
510mm question put UD-1400X, which needs 545mm, above most models that
actually fit, with all twenty top hits inside 0.375-0.421. Conditions have
to reach ChromaDB as a where clause instead.

The LLM call is injected so the conversion rules can be tested without a
running Ollama. A malformed condition is dropped on its own rather than
discarding its siblings, and a failed extraction is reported separately
from a question that simply has no conditions.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 5: 条件で絞り込んで仕様表を作る

**Files:**
- Create: `ingest/catalog.py`
- Create: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `ingest.chunker.RESERVED_METADATA_KEYS`、`ingest.conditions.Extraction.conditions` の形の辞書
- Produces: `Product(source: str, attributes: dict)`、`select(collection, conditions) -> list[Product]`、`relaxations(collection, conditions) -> list[tuple[str, list[Product]]]`、`format_table(conditions, matched, relaxed) -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_catalog.py` を新規作成する。

```python
import pytest

from ingest.catalog import Product, format_table, relaxations, select
from ingest.embedder import EMBED_DIM
from ingest.store import open_collection
from tests.conftest import ephemeral_client

QUIET_AND_SLIM = {"noise_wash_db": {"$lte": 26}, "installation_depth_min_mm": {"$lte": 510}}


@pytest.fixture
def collection():
    client = ephemeral_client()
    yield open_collection(client)
    client.clear_system_cache()


def _add_product(collection, model, noise, depth, sections=1):
    """1製品を sections 個のチャンクとして入れる。属性は全チャンクに同じ値が乗る。"""
    source = f"家電製品/{model}.md"
    for index in range(sections):
        collection.add(
            ids=[f"{source}::section{index}::0"],
            documents=[f"{model}の本文"],
            metadatas=[
                {
                    "source": source,
                    "heading": f"節{index}",
                    "noise_wash_db": noise,
                    "installation_depth_min_mm": depth,
                    "model_id": model,
                }
            ],
            embeddings=[[1.0] + [0.0] * (EMBED_DIM - 1)],
        )
    return source


def _catalogue(collection):
    _add_product(collection, "UD-1100iS", 26, 510, sections=3)
    _add_product(collection, "UD-1100i", 26, 540)
    _add_product(collection, "UD-1100iE", 26, 540)
    _add_product(collection, "UD-1000S", 28, 510)


def test_select_returns_every_match(collection):
    _catalogue(collection)
    assert [p.source for p in select(collection, QUIET_AND_SLIM)] == [
        "家電製品/UD-1100iS.md"
    ]


def test_select_folds_the_chunks_of_one_source_into_one_product(collection):
    """3チャンクある製品が3行になると、件数の質問に誤って答えることになる。"""
    _catalogue(collection)
    assert len(select(collection, {"noise_wash_db": {"$lte": 26}})) == 3


def test_select_drops_reserved_keys_from_attributes(collection):
    _catalogue(collection)
    attributes = select(collection, QUIET_AND_SLIM)[0].attributes
    assert "source" not in attributes
    assert "heading" not in attributes
    assert attributes["model_id"] == "UD-1100iS"


def test_select_returns_nothing_without_conditions(collection):
    _catalogue(collection)
    assert select(collection, {}) == []


def test_select_returns_nothing_when_no_product_matches(collection):
    _catalogue(collection)
    assert select(collection, {"noise_wash_db": {"$lte": 20}}) == []


def test_relaxations_report_products_that_miss_exactly_one_condition(collection):
    """「同じ26dBでも設置できない機種はどれか」に答えるために要る。"""
    _catalogue(collection)
    relaxed = relaxations(collection, QUIET_AND_SLIM)
    assert [key for key, _ in relaxed] == ["installation_depth_min_mm"]
    assert [p.source for _, products in relaxed for p in products] == [
        "家電製品/UD-1100i.md",
        "家電製品/UD-1100iE.md",
    ]


def test_relaxations_exclude_products_that_already_matched(collection):
    _catalogue(collection)
    relaxed = relaxations(collection, QUIET_AND_SLIM)
    assert all(
        p.source != "家電製品/UD-1100iS.md" for _, products in relaxed for p in products
    )


def test_relaxations_are_empty_for_a_single_condition(collection):
    """条件が1つしかなければ、外した先は「条件なし」で全件になり意味がない。"""
    _catalogue(collection)
    assert relaxations(collection, {"noise_wash_db": {"$lte": 26}}) == []


def test_format_table_shows_conditions_and_rows():
    product = Product(source="家電製品/UD-1100iS.md", attributes={"noise_wash_db": 26})
    table = format_table({"noise_wash_db": {"$lte": 26}}, [product], [])
    assert "noise_wash_db 26以下" in table
    assert "家電製品/UD-1100iS.md" in table
    assert "noise_wash_db=26" in table
    assert "1件" in table


def test_format_table_labels_the_relaxed_group():
    product = Product(source="家電製品/UD-1100i.md", attributes={"noise_wash_db": 26})
    table = format_table(QUIET_AND_SLIM, [], [("installation_depth_min_mm", [product])])
    assert "installation_depth_min_mm" in table
    assert "家電製品/UD-1100i.md" in table


def test_format_table_says_none_when_nothing_matches():
    """空の表を渡すと、モデルは根拠が無いことに気づかず作り話を始める。"""
    assert "該当なし" in format_table({"noise_wash_db": {"$lte": 20}}, [], [])
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.catalog'`

- [ ] **Step 3: 実装する**

`ingest/catalog.py` を新規作成する。

```python
"""条件に合う資料を集めて、モデルが読める表に整える。

ベクトル検索と違い where は取りこぼさない。条件に合うものは必ず全件そろうので、
「該当する型番をすべて」という質問に構造的に答えられる。

LLMには一切依存しない。ここを純粋な計算に保つことで、絞り込みと表組みの規則を
実機のOllamaなしでテストできる。
"""
from dataclasses import dataclass

from ingest.chunker import RESERVED_METADATA_KEYS

_OPERATOR_LABELS = {"$lte": "以下", "$gte": "以上", "$eq": "＝"}


@dataclass(frozen=True)
class Product:
    """1つの資料（＝1製品）とその属性。"""

    source: str
    attributes: dict


def _where(conditions: dict) -> dict:
    """ChromaDBは条件が2つ以上のとき $and で包む必要がある。"""
    clauses = [{key: condition} for key, condition in conditions.items()]
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def select(collection, conditions: dict) -> list[Product]:
    """条件に合う資料を、1資料1件にまとめて返す。

    同じ製品の6セクションは同じ属性を持つ。畳まずに返すと件数を尋ねる質問に
    誤って答えることになるため、source ごとに1つにする。
    """
    if not conditions:
        return []
    found = collection.get(where=_where(conditions), include=["metadatas"])
    products: dict[str, dict] = {}
    for metadata in found.get("metadatas") or []:
        source = metadata.get("source")
        if source and source not in products:
            products[source] = {
                key: value
                for key, value in metadata.items()
                if key not in RESERVED_METADATA_KEYS
            }
    return [Product(source=source, attributes=products[source]) for source in sorted(products)]


def relaxations(collection, conditions: dict) -> list[tuple[str, list[Product]]]:
    """条件を1つずつ外して、惜しくも外れた資料を返す。

    「同じ26dBでも設置できない機種がある場合、その型番と理由も」という問いに
    答えるために要る。条件が1つのときは外した先が全件になり意味がないので何もしない。
    get は埋め込み計算を伴わないため、条件の数だけ引いても追加コストはほぼない。
    """
    if len(conditions) < 2:
        return []
    matched = {product.source for product in select(collection, conditions)}
    results: list[tuple[str, list[Product]]] = []
    for dropped in conditions:
        remaining = {key: value for key, value in conditions.items() if key != dropped}
        extra = [p for p in select(collection, remaining) if p.source not in matched]
        if extra:
            results.append((dropped, extra))
    return results


def _describe(conditions: dict) -> str:
    parts = []
    for key, condition in conditions.items():
        for operator, value in condition.items():
            parts.append(f"{key} {value}{_OPERATOR_LABELS.get(operator, operator)}")
    return " / ".join(parts)


def _row(product: Product) -> str:
    attributes = " | ".join(
        f"{key}={value}" for key, value in sorted(product.attributes.items())
    )
    return f"{product.source} | {attributes}"


def format_table(conditions: dict, matched: list[Product], relaxed: list) -> str:
    """モデルに渡す一覧を組み立てる。

    各行の先頭に出典（ファイル名）を置く。散文チャンクを渡していたときと同じ形で
    出典を示せるようにするためである。
    """
    lines = [f"条件: {_describe(conditions)}", "", f"■ 全条件に合致（{len(matched)}件）"]
    if matched:
        lines.extend(_row(product) for product in matched)
    else:
        lines.append("該当なし")
    for dropped, products in relaxed:
        lines.append("")
        lines.append(f"■ 「{dropped}」の条件を外すと合致（{len(products)}件）")
        lines.extend(_row(product) for product in products)
    return "\n".join(lines)
```

- [ ] **Step 4: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 5: コミットする**

```bash
git add ingest/catalog.py tests/test_catalog.py
git commit -F - <<'EOF'
feat: select products by condition and lay them out as a table

where() cannot miss what matches, so "list every model that fits" becomes
answerable in a way top-k retrieval never was. Chunks are folded per
source because a product split across six sections would otherwise be
counted six times.

Relaxing each condition in turn answers the second half of the measured
question - which models share the noise rating but still cannot be
installed - and costs nothing, since get() runs no embedding.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 6: プロンプトを整える

**Files:**
- Modify: `ingest/prompting.py`
- Modify: `tests/test_prompting.py`

**Interfaces:**
- Consumes: `ingest.catalog.format_table` の戻り値
- Produces: `build_catalog_prompt(question: str, table: str) -> str`。`build_prompt` は根拠ゼロのとき質問をそのまま返さなくなる

- [ ] **Step 1: 矛盾する既存テストを差し替える**

`tests/test_prompting.py` の `test_prompt_without_hits_is_the_bare_question` を**削除する**。

```python
def test_prompt_without_hits_is_the_bare_question():
    assert build_prompt("経費の上限は", []) == "経費の上限は"
```

このテストは「根拠ゼロなら質問をそのまま返す」という現行の振る舞いを固定しており、
本タスクが直そうとしている欠陥そのものをロックしている。次のStepで書く2件が
置き換えとなる。

- [ ] **Step 2: 失敗するテストを書く**

`tests/test_prompting.py` の末尾に追加する。

```python
def test_prompt_without_hits_tells_the_model_not_to_guess():
    """根拠ゼロは最もハルシネーションが起きやすい場面である。ここで指示が
    外れると、残るのは『あなたは有能なアシスタントです』だけになる。"""
    prompt = build_prompt("今日の天気は", [])
    assert prompt != "今日の天気は"
    assert "社内文書" in prompt


def test_prompt_without_hits_still_contains_the_question():
    assert "今日の天気は" in build_prompt("今日の天気は", [])


def test_catalog_prompt_contains_the_table_and_the_question():
    prompt = build_catalog_prompt("26dB以下は", "■ 全条件に合致（1件）\nUD-1100iS.md")
    assert "UD-1100iS.md" in prompt
    assert "26dB以下は" in prompt


def test_catalog_prompt_forbids_inventing_values():
    """表に無い数値を補われると、絞り込みで正確にした意味が消える。"""
    prompt = build_catalog_prompt("26dB以下は", "表")
    assert "推測" in prompt
```

`tests/test_prompting.py` の先頭のimportに `build_catalog_prompt` を足す。

```python
from ingest.prompting import build_catalog_prompt, build_prompt, format_report
```

- [ ] **Step 3: テストが失敗することを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/test_prompting.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_catalog_prompt' from 'ingest.prompting'`

- [ ] **Step 4: 根拠ゼロのプロンプトを実装する**

`ingest/prompting.py` の `build_prompt` の `if not hits:` の分岐を置き換える。

```python
    if not hits:
        # ここで質問をそのまま返すと、system prompt の「あなたは有能な
        # アシスタントです」だけが残り、モデルは知識で答えにいく。根拠が
        # 1件も無いときこそ歯止めが要る。
        return (
            "社内文書を検索しましたが、この質問に関連する記述は見つかりませんでした。"
            "推測で答えず、社内文書からは回答できない旨を伝えてください。\n\n"
            f"ユーザーの質問: {question}"
        )
```

- [ ] **Step 5: 仕様表用のプロンプトを実装する**

`ingest/prompting.py` の `build_prompt` の直後に追加する。

```python
def build_catalog_prompt(question: str, table: str) -> str:
    """絞り込んだ一覧だけを根拠に答えさせる。

    この表は where で引いており、条件に合うものは全件そろっている。裏を返せば
    表に無いものは条件に合わないということなので、補完の余地は一切ない。
    実測では、表を渡さずに散文チャンクだけを渡したとき、モデルは型番から
    容量を推測して誤った数値を答えた。
    """
    return (
        "以下は社内の資料を条件で絞り込んだ一覧です。"
        "この一覧に載っている事実だけを使って回答してください。"
        "一覧に無い型番や数値を推測して補ってはいけません。"
        "回答の根拠にした行の出典（各行の先頭のファイル名）を示してください。\n\n"
        f"{table}\n\nユーザーの質問: {question}"
    )
```

- [ ] **Step 6: テストが通ることを確認する**

Run: `.\myvenv313\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（全件）

- [ ] **Step 7: コミットする**

```bash
git add ingest/prompting.py tests/test_prompting.py
git commit -F - <<'EOF'
fix: keep the no-guessing instruction when there is no evidence at all

build_prompt returned the bare question whenever retrieval found nothing,
which dropped the "answer only from the documents" instruction in exactly
the case that needs it most and left the helpful-assistant system prompt
as the model's only guidance.

The catalogue prompt states that the list is complete for the conditions
given, so there is nothing for the model to fill in.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 7: UIを結線して実データで確認する

**Files:**
- Modify: `rag_chat_app.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1〜6 のすべて
- Produces: 2経路が動くUI

- [ ] **Step 1: importとスキーマの取得を足す**

`rag_chat_app.py` のimport群を置き換える。

```python
from ingest import catalog, conditions, embedder, store
from ingest.prompting import build_catalog_prompt, build_prompt, format_report
from ingest.retrieval import RELEVANCE_THRESHOLD, search
from scripts.ingest_source import DEFAULT_SOURCE_DIR, ingest_directory
```

`get_collection` の直後に追加する。

```python
@st.cache_resource
def get_schema(_collection):
    """絞り込みに使える属性の一覧。起動時に1回だけ集める。

    先頭のアンダースコアは、Streamlitにこの引数をハッシュさせないための目印。
    ChromaDBのコレクションはハッシュ化できない。
    """
    return conditions.available_keys(_collection)
```

- [ ] **Step 2: 表示関数を足す**

`render_hits` の直後に追加する。

```python
def render_evidence(message):
    """根拠の表示。絞り込み経路は表を、検索経路はチャンクを見せる。"""
    if message.get("table"):
        with st.expander("絞り込んだ一覧"):
            st.code(message["table"])
    render_hits(message.get("hits"))
```

履歴の描画（`for message in st.session_state.messages:` のループ内）で `render_hits(message.get("hits"))` を置き換える。

```python
        render_evidence(message)
```

- [ ] **Step 3: 条件抽出の呼び出しを足す**

`client = OpenAI(...)` の直後に追加する。

```python
schema = get_schema(collection)


def ask_json(prompt: str) -> str:
    """条件抽出用にJSONだけを返させる。

    temperature=0 なのは、同じ質問で条件が揺れると再現性のない誤りになるため。
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content
```

- [ ] **Step 4: 2経路の分岐を書く**

`if question:` の中の `hits = search(collection, question)` から `history` の組み立てまでを置き換える。

```python
    extraction = conditions.extract(question, schema, ask_json)
    if extraction.failed:
        st.warning("条件を解釈できませんでした。通常の検索で回答します。")

    table = None
    hits = []
    if extraction.conditions:
        matched = catalog.select(collection, extraction.conditions)
        relaxed = catalog.relaxations(collection, extraction.conditions)
        table = catalog.format_table(extraction.conditions, matched, relaxed)
        user_content = build_catalog_prompt(question, table)
    else:
        hits = search(collection, question)
        user_content = build_prompt(question, hits)

    history = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]
        + [{"role": "user", "content": user_content}]
    )
```

`render_hits(hits)` を置き換える。

```python
            render_evidence({"hits": hits, "table": table})
```

履歴への追加を置き換える。

```python
    if answer is not None:
        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "hits": hits, "table": table}
        )
```

- [ ] **Step 5: 全テストを実行する**

Run: `.\myvenv313\Scripts\python.exe -m pytest -v`
Expected: PASS（全件）

- [ ] **Step 6: 抽出が動くかを実機で確かめる**

Run:
```powershell
.\myvenv313\Scripts\python.exe -c "
from openai import OpenAI
from ingest import conditions, embedder, store
import chromadb
c = store.open_collection(chromadb.PersistentClient(path=r'.\chroma_db'))
schema = conditions.available_keys(c)
print('schema:', schema)
client = OpenAI(api_key='ollama', base_url=f'{embedder.OLLAMA_HOST}/v1')
ask = lambda p: client.chat.completions.create(model='llama3.1:8b', messages=[{'role':'user','content':p}], temperature=0, response_format={'type':'json_object'}).choices[0].message.content
for q in ['運転音（洗い）が26dB以下で、かつ防水パン奥行き510mmに設置できる機種をすべて教えてください', 'UD-0900iの乾燥方式は何ですか']:
    print(q, '->', conditions.extract(q, schema, ask))
"
```
Expected: 1つ目で `noise_wash_db` と `installation_depth_min_mm` の条件が取れ、2つ目は条件が空で `failed=False` になること

**1つ目で条件が取れない、または不等号が逆になる場合は、設計書 第13節のリスクが現実になっている。** 作業を止めて報告すること。プロンプトの調整で改善するかを先に試し、駄目なら正規表現による補助を検討する。

- [ ] **Step 7: UIで2件の質問を確認する**

Run: `.\myvenv313\Scripts\python.exe -m streamlit run rag_chat_app.py`

以下を確認したら停止する。

1. 「運転音（洗い）が26dB以下で、かつ防水パン奥行き510mmに設置できる機種をすべて教えてください。また同じ26dBでも設置できない機種がある場合、その型番と理由も答えてください」
   → **UD-1100iS のみ**が該当し、UD-1100i / UD-1100iE / UD-1100iP が防水パン540mm以上のため設置不可として挙がること
2. 「部活動の子が3人いる5人家族で毎日大量の洗濯をします。できるだけ大容量の機種がほしいのですが、洗濯機置き場の防水パン内寸奥行きが510mmしかありません。設置できる機種の中で最大の洗濯容量は何kgで、該当する型番をすべて教えてください」
   → **最大11kg、UD-1100S と UD-1100iS** が挙がること
3. 「UD-0900iの乾燥方式は何ですか」→ 従来どおりベクトル検索で回答でき、出典が表示されること
4. 「こんにちは」→ 社内文書から回答できない旨が返ること

- [ ] **Step 8: READMEを更新する**

`README.md` に次を反映する。

1. 冒頭の説明に、条件による絞り込みに対応したことを1文加える
2. 「使い方」に、拡張子を絞った再取り込みの例を加える

```markdown
# Markdownだけを取り直す（フロントマターを直したときなど。OCRを伴わないため数十秒）
.\myvenv313\Scripts\python.exe -m scripts.ingest_source --force --only-suffix .md
```

3. 「構成」の表に `ingest/conditions.py` と `ingest/catalog.py` を加える
4. 「既知の制約」に、絞り込みの限界を1項目加える。次の3点を必ず含める
   - 絞り込みはフロントマターを持つMarkdownにしか効かない（PDF/PPTX/DOCXは対象外）
   - 条件抽出は `llama3.1:8b` に依存し、不等号を取り違える可能性がある
   - 配列属性（`tags` / `target_users`）では絞り込めない
5. 「設計資料」に今回の設計書と実装計画へのリンクを加える

- [ ] **Step 9: 全テストを実行する**

Run: `.\myvenv313\Scripts\python.exe -m pytest -v`
Expected: PASS（全件）

- [ ] **Step 10: コミットする**

```bash
git add rag_chat_app.py README.md
git commit -F - <<'EOF'
feat: route constraint questions through metadata filtering

A question that carries numeric conditions is answered from a where()
filtered table; everything else takes the existing vector path unchanged.
The two measured hallucinations are now answered correctly: 11kg from
UD-1100S and UD-1100iS, and UD-1100iS alone at 26dB.

A failed extraction is surfaced rather than silently degrading, so a
fallback to vector search is visible to the reader.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Self-Review 結果

**1. 設計書のカバレッジ**

| 設計書のセクション | 対応タスク |
|---|---|
| 2. 現状なぜ答えられないのか（実測） | 根拠として各所のコメントに反映（Task 4 docstring、Task 6 Step 4） |
| 4. 採用する方針（メタデータ化） | Task 1、Task 2 |
| 5.1 フロントマターの採用規則（スカラーのみ・型変換） | Task 1 Step 3 のテスト3件、Step 5 の `_scalar` |
| 5.2 予約キーとの衝突 | Task 2（`RESERVED_METADATA_KEYS` と `test_reserved_keys_in_attributes_are_ignored`） |
| 5.3 データ構造の変更 | Task 1 Step 2、Task 2 Step 4 |
| 6. 問い合わせの流れ（条件で分岐・分類器を置かない） | Task 7 Step 4 |
| 6.1 抽出に渡すスキーマ（全件収集・予約キー除外・キャッシュ） | Task 4（`available_keys`）、Task 7 Step 1（`get_schema`） |
| 6.2 抽出の出力形式（演算子3種・個別に捨てる・失敗と空の区別） | Task 4（`_valid` / `_sanitise` / `Extraction.failed`） |
| 6.3 「条件を1つ外すと合致」 | Task 5（`relaxations`） |
| 6.4 仕様表の形（出典を各行の先頭に） | Task 5（`format_table` / `_row`） |
| 7. モジュール構成 | File Structure の表と各タスクの Files |
| 8. 既存チャンクへの反映（`--only-suffix`・孤児削除の抑止） | Task 3 |
| 9. エラー処理（抽出失敗・0件） | Task 4（失敗の扱い）、Task 5（`該当なし`）、Task 7 Step 4（`st.warning`） |
| 9.1 根拠ゼロ時の欠陥修正 | Task 6 |
| 10. テスト方針 | Task 1〜6 の各テスト、Task 7 Step 6〜7 の受け入れ確認 |
| 11. 想定される影響（チャンク数不変） | Task 3 Step 9 の確認 |
| 12. 今回やらないこと | 該当タスクなし（意図どおり） |
| 13. 残るリスク（抽出の不安定さ） | Task 7 Step 6 で測定し、駄目なら止める手順を明記 |

**2. プレースホルダ**: なし。Task 7 Step 8 のREADMEは書き換える項目と必ず含める3点を明示している。

**3. 型の一貫性**

- `ParsedUnit.attributes: dict` は Task 1 で定義し、Task 2 が `unit.attributes` として読む
- `RESERVED_METADATA_KEYS: frozenset[str]` は Task 2 で定義し、Task 4（`available_keys`）と Task 5（`select`）が使う
- `Extraction(conditions: dict, failed: bool)` は Task 4 で定義し、Task 7 Step 4 が `.conditions` / `.failed` を読む
- `Product(source: str, attributes: dict)` は Task 5 で定義し、同タスクの `format_table` と Task 7 が使う
- `select` / `relaxations` / `format_table` の呼び出し順と引数は Task 5 の定義と Task 7 Step 4 の呼び出しで一致している
- `build_catalog_prompt(question, table)` は Task 6 で定義し、Task 7 Step 4 が同じ順で呼ぶ
- `ingest_directory(..., only_suffix=None)` は Task 3 Step 4 で定義し、同 Step 5 のCLIが同じキーワードで渡す

**4. 既存テストへの影響**

- Task 1 は `tests/test_parser_md.py` の `SAMPLE` にフロントマターの行を足すが、本文は変えないため既存15件は不変
- Task 2 は `tests/test_chunker.py` のimportを1行広げるのみ。既存の `_unit` は `attributes` を渡さず既定値の空辞書で動く
- Task 3 は `tests/test_ingest_source.py` へ追記のみ。`_target_files` の第2引数は既定値ありのため既存の呼び出しは不変
- Task 6 は既存の `test_prompt_without_hits_is_the_bare_question` を削除する（現行の欠陥をロックしているため）。同ファイルの他の6件は不変で、importを1行広げるのみ
