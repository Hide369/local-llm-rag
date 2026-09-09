# ナビゲーション用スライドの除外 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 目次・章扉・締めのスライドを取り込み時に落とし、検索の上位を中身のある本文に明け渡す。

**Architecture:** 述語モジュール `ingest/navigation.py` を1つ足し、`scripts/ingest_source.py` がパースとチャンク化の間で呼ぶ。`ingest/chunker.py` と `ingest/retrieval.py` は変更しない。スキーマ変更なし、移行スクリプトなし。

**Tech Stack:** Python 3.13、pytest、SQLite + numpy のベクトルストア、Ollama（bge-m3）

**Spec:** `docs/superpowers/specs/2026-09-06-navigation-slides-design.md`（コミット `055ea9f`）

## Global Constraints

- **Python の起動は必ず `./myvenv313/Scripts/python.exe`。** システムの python には依存が入っていない。
- **スクリプトは `python -m scripts.X` で起動する。** `python scripts/X.py` は `ModuleNotFoundError: No module named 'ingest'` で落ちる。`sys.path` を足して回避しないこと。
- **テストは `./myvenv313/Scripts/python.exe -m pytest`。** 開始時点で 487 passed, 3 deselected（実測 efcd780）。
- **`git add -A` / `git add .` は禁止。** 触ったファイルを個別に指定する。作業ツリーには無関係の未追跡物（`.worktrees/generalize-coding-agent/`）がある。
- **`ingest/chunker.py` と `ingest/retrieval.py` は変更しない**（設計書3.2・8節）。
- **`chroma_db/` に書き込まない。** 旧アプリ `udemy3.py` がまだ使っている。
- コミットはコンベンショナルコミット形式、英語。
- 数字を書くときは実測するか、いつ・どの規模で測ったかを添える。測っていない数字を実測済みに見せない。

---

### Task 1: 述語モジュール `ingest/navigation.py`

**Files:**
- Create: `ingest/navigation.py`
- Test: `tests/test_navigation.py`

**Interfaces:**
- Consumes: なし
- Produces: `is_navigation(text: str) -> bool`

テストの中心は「捕まえるもの」ではなく「捕まえてはいけないもの」に置く。3つの規則が当たることの確認は容易で、価値があるのは境界のほうである（設計書6節）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_navigation.py` を新規作成する。文字列はすべて実コーパス（608出現、2026-09-06）から採ったものである。

```python
"""ナビゲーション用スライドの判定。

捕まえるものより、捕まえてはいけないものを重く見る。規則を緩めると
本文が消えるが、規則が当たらなくなっても消えるものは無いためである。
"""
from ingest.navigation import is_navigation


# --- 落とすもの（実コーパスから採取） ---

def test_a_section_divider_is_navigation():
    """回帰ケースで1位を取っていた章扉。"""
    assert is_navigation("3\n転移学習とファインチューニング")


def test_a_section_divider_wrapped_over_two_lines_is_navigation():
    """見出しが2行に折り返されていても章扉である。"""
    assert is_navigation("2\nローカルLLMを活用した\n検索精度を上げる仕組み")


def test_a_table_of_contents_is_navigation():
    """回帰ケースで3位を取っていた目次スライド。"""
    assert is_navigation("－ 目次 ー\nRAGの基礎知識\n1\nローカルLLMを活用した検索精度を上げる仕組み\n2")


def test_a_table_of_contents_with_a_different_dash_is_navigation():
    """資料によって末尾の記号が異なる（ー と －）。先頭行に含まれるかで見る。"""
    assert is_navigation("－ 目次 －\n1\nニューラルネットワークの基礎知識\n2")


def test_a_closing_slide_is_navigation():
    assert is_navigation("ご清聴ありがとうございました\nAIとともに、新しい働き方を始めよう")


# --- 落としてはいけないもの（規則の境界） ---

def test_a_cover_page_padded_with_blank_lines_is_not_navigation():
    """モデル就業規則.pdf の表紙。

    先頭が全角の「１」で str.isdigit() は真になる。章扉と分けているのは
    生の行数だけである（表紙19行、本物の章扉は2〜3行）。版数を尋ねる質問に
    必要なので落としてはならない。
    """
    cover = "１ \n \n \n \n \n \n \n \nモデル就業規則 \n \n \n \n \n \n \n \n \n令和７年12 月版 "
    assert not is_navigation(cover)


def test_a_run_of_page_numbers_is_not_navigation():
    """モデル就業規則.pdf 34ページ由来。数字だけの行が続く。

    3行に切り詰めてあるのは、生の行数ガード（4行以下）ではなく数字連続ガードが
    効いていることを確かめるため。原文の長さのままだと行数ガードだけで False に
    なり、数字連続ガードを消してもこのテストは通ってしまう（実行で確認）。
    """
    assert not is_navigation("17\n18\n19")


def test_body_text_that_mentions_a_table_of_contents_is_not_navigation():
    """Claude_Code_法人導入ガイド_スライド.pdf 13ページ由来の断片。

    787字が1行で、560文字目に「目次」が現れる。先頭行の長さで弾く。
    """
    body = "ける 日命名ルールが競ーされているか ロヘッダー・フツタ一・目次の除去 口文断が切れない位置て分割されているか"
    assert not is_navigation(body)


def test_a_short_body_fragment_is_not_navigation():
    """40字以下の本文断片は実在する。長さ単独では判定できない。"""
    assert not is_navigation("。 横展開：コア構成はそのまま")


def test_a_numbered_list_of_content_is_not_navigation():
    """先頭が数字でも、数字の行が続くものは章扉ではない。"""
    assert not is_navigation("1\n最初の項目\n2\n次の項目")


def test_empty_text_is_not_navigation():
    assert not is_navigation("")
    assert not is_navigation("   \n  \n ")
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_navigation.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.navigation'`

- [ ] **Step 3: 実装する**

`ingest/navigation.py` を新規作成する。

```python
"""検索の答えになる中身を持たないスライドを見分ける。

目次・章扉・締めのスライドは短くキーワード密度が高いため BM25 がこれを好むが、
中身が無いので上位に来ても質問に答えられない。取り込み時に落とす。

3つの述語はいずれも、想定外の入力に対しては「検出しない」側に倒れる。英語資料や
別テンプレートのスライドを入れても、規則が当たらなくなるだけで、本文を誤って
捨てる事故は起きない。

規則はすべて実コーパス608出現（2026-09-06、セミナー資料7本を含む44ファイル）に
当てて、誤検出ゼロ・取りこぼしゼロを確認している。内訳は章扉24・目次7・締め7。
"""

# 章扉の生の行数（空行を含む）の上限。
# モデル就業規則.pdf の表紙は先頭が全角の「１」で str.isdigit() が真になるが、
# タイトルが空行に挟まれて生の行数が19行ある。本物の章扉は2〜3行しかない。
# 「空行の詰め物があるものは章扉ではない」がこの上限の意味である。
_MAX_DIVIDER_LINES = 4

# 目次スライドの先頭行の長さの上限。「－ 目次 ー」は7字。
# 本文中で目次に言及しているだけのチャンク（Claude_Code_法人導入ガイド_スライド.pdf
# 13ページ、787字が1行で560文字目に「目次」）を弾く。
_MAX_TOC_HEADING_CHARS = 10

_CLOSING_PREFIX = "ご清聴"


def _content_lines(text: str) -> list[str]:
    return [line.strip() for line in text.strip().split("\n") if line.strip()]


def _is_section_divider(text: str) -> bool:
    """「3\\n転移学習とファインチューニング」のような章扉か。"""
    raw_lines = text.strip().split("\n")
    lines = _content_lines(text)
    if len(raw_lines) > _MAX_DIVIDER_LINES or len(lines) < 2:
        return False
    if not lines[0].isdigit():
        return False
    # ページ番号の羅列（モデル就業規則.pdf 34ページ）を弾く。章扉の2行目以降は
    # 見出しの文字列であり、数字だけの行にはならない。
    return not any(line.isdigit() for line in lines[1:])


def _is_table_of_contents(text: str) -> bool:
    lines = _content_lines(text)
    if not lines:
        return False
    return "目次" in lines[0] and len(lines[0]) <= _MAX_TOC_HEADING_CHARS


def _is_closing(text: str) -> bool:
    return text.strip().startswith(_CLOSING_PREFIX)


def is_navigation(text: str) -> bool:
    """検索の答えになる中身を持たないスライドか。"""
    return (
        _is_section_divider(text)
        or _is_table_of_contents(text)
        or _is_closing(text)
    )
```

- [ ] **Step 4: 通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_navigation.py -q`
Expected: PASS（11件）

- [ ] **Step 5: 規則を緩めるとテストが赤くなることを確かめる**

ガードが本当に働いているかを、実行して確認する。**このブランチの直前の作業で「修正前のコードでも通る恒真テスト」が3ラウンド出ている。**

`ingest/navigation.py` の `_MAX_DIVIDER_LINES` を一時的に `100` に書き換えて実行する。

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_navigation.py -q`
Expected: FAIL — `test_a_cover_page_padded_with_blank_lines_is_not_navigation`

次に `_MAX_TOC_HEADING_CHARS` を `1000` にして実行する。

Expected: FAIL — `test_body_text_that_mentions_a_table_of_contents_is_not_navigation`

**確認できたら両方とも元の値（4 と 10）に戻す。** 戻したことを `git diff` で確かめてから次へ進む。

- [ ] **Step 6: コミット**

```bash
git add ingest/navigation.py tests/test_navigation.py
git commit -m "feat: tell navigation slides from slides that answer questions

Section dividers, tables of contents, and closing slides are short and
keyword-dense, so BM25 ranks them highly, but they carry nothing that
answers a question.

The guards matter more than the rules. A full-width digit makes a PDF
cover page look like a section divider, and body text quoting the word
mokuji looks like a table of contents; both are pinned by tests, and
loosening either constant turns them red."
```

---

### Task 2: ユニットのふるい分け `drop_navigation()`

**Files:**
- Modify: `ingest/navigation.py`（Task 1 で作成）
- Test: `tests/test_navigation.py`（Task 1 で作成）

**Interfaces:**
- Consumes: `is_navigation(text: str) -> bool`（Task 1）
- Produces: `drop_navigation(units: list[ParsedUnit]) -> tuple[list[ParsedUnit], list[ParsedUnit]]` — 戻り値は `(残すもの, 落としたもの)` の順

落としたユニットを件数ではなく現物で返す。数だけでは、誤検出が起きたときに何が消えたのか追えない（設計書3.1）。

**全ユニットが落ちる場合の判断はここでは行わない。** 呼び出し側（Task 3）に任せる。ここで握り潰すと、資料が丸ごと消えたことに誰も気づけない。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_navigation.py` の末尾に足す。ファイル冒頭の import も書き換える。

```python
from ingest.models import SLIDE, ParsedUnit
from ingest.navigation import drop_navigation, is_navigation
```

```python
def _slide(text, location):
    return ParsedUnit(text=text, location_type=SLIDE, location=location)


def test_drop_navigation_separates_the_two_groups():
    units = [
        _slide("－ 目次 ー\nRAGの基礎知識\n1", 4),
        _slide("1\nRAGの基礎知識", 5),
        _slide("RAGは検索した文書を根拠にして回答を組み立てる仕組みである。", 6),
        _slide("ご清聴ありがとうございました\nAIとともに、新しい働き方を始めよう", 30),
    ]
    kept, dropped = drop_navigation(units)
    assert [unit.location for unit in kept] == [6]
    assert [unit.location for unit in dropped] == [4, 5, 30]


def test_drop_navigation_keeps_the_original_order():
    """出典の位置は location が持つが、並びが崩れると差分が読みにくくなる。"""
    units = [_slide(f"本文{n}", n) for n in (3, 1, 2)]
    kept, _ = drop_navigation(units)
    assert [unit.location for unit in kept] == [3, 1, 2]


def test_drop_navigation_returns_every_unit_when_none_is_navigation():
    units = [_slide("本文です。これは中身のあるスライドである。", 1)]
    kept, dropped = drop_navigation(units)
    assert kept == units
    assert dropped == []


def test_drop_navigation_does_not_decide_what_to_do_when_everything_drops():
    """全部落ちる場合の判断は呼び出し側に任せる。

    ここで握り潰すと、規則が誤爆して資料が丸ごと消えたことに誰も気づけない。
    scripts/ingest_source.py がこの場合に何も落とさず警告を出す。
    """
    units = [_slide("1\nRAGの基礎知識", 5), _slide("2\n導入手順", 9)]
    kept, dropped = drop_navigation(units)
    assert kept == []
    assert dropped == units
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_navigation.py -q`
Expected: FAIL — `ImportError: cannot import name 'drop_navigation'`

- [ ] **Step 3: 実装する**

`ingest/navigation.py` の冒頭に import を足す。

```python
from ingest.models import ParsedUnit
```

ファイル末尾に足す。

```python
def drop_navigation(
    units: list[ParsedUnit],
) -> tuple[list[ParsedUnit], list[ParsedUnit]]:
    """残すユニットと、落としたユニットを (残す, 落とす) の順で返す。

    落としたものを件数ではなく現物で返すのは、呼び出し側が「何を」落としたか
    報告できるようにするためである。件数だけでは、誤検出が起きたときに何が
    消えたのか追えない。

    全ユニットが落ちる場合の判断はここでは行わない。握り潰すと、資料が丸ごと
    DBから消えたことに誰も気づけない。scripts/ingest_source.py がこの場合に
    何も落とさず警告を出す。
    """
    kept: list[ParsedUnit] = []
    dropped: list[ParsedUnit] = []
    for unit in units:
        target = dropped if is_navigation(unit.text) else kept
        target.append(unit)
    return kept, dropped
```

- [ ] **Step 4: 通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_navigation.py -q`
Expected: PASS（15件）

- [ ] **Step 5: コミット**

```bash
git add ingest/navigation.py tests/test_navigation.py
git commit -m "feat: sift parsed units into kept and dropped

Returns the dropped units themselves rather than a count, so the caller
can report what disappeared. A count alone leaves a misfire untraceable.

Deciding what to do when every unit drops is left to the caller."
```

---

### Task 3: 取り込みへの組み込みと、全滅時の備え

**Files:**
- Modify: `scripts/ingest_source.py`（`IngestReport` は31-36行、取り込みループは110-125行付近）
- Test: `tests/test_ingest_source.py`

**Interfaces:**
- Consumes: `drop_navigation(units) -> (kept, dropped)`（Task 2）
- Produces: `IngestReport.dropped: dict[str, int]` — 資料キー → 除外件数。1件も落ちなかった資料はキーを持たない

**全ユニットがナビゲーションと判定されたら、何も落とさず警告を出す**（設計書5節）。そのまま落とすと `store.replace_source()` が空のチャンク列を受け取り、その資料がDBから丸ごと消える。規則が誤爆したときに最も起きてほしくない結果である。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ingest_source.py` の末尾に足す。既存の `source_dir` / `collection` / `_write_md` を使う。

Markdown パーサーの挙動は実行して確かめてある。`## ` で節に分かれ、各ユニットの
本文は `タイトル / 配列値 / 節見出し / 本体` を改行で繋いだものになる
（`ingest/parsers/md_parser.py:153-160`）。`# ` のタイトルを置くと全ユニットの
先頭に付いて章扉の判定を外すため、下のフィクスチャはタイトルを置かない。

実際に得られるユニットは次のとおり（実行で確認済み）。

```
mixed.md    → 2件: '1\n転移学習とファインチューニング'（章扉）
                   '本編\nRAGは検索した文書を根拠にして…'（本文）
nav_only.md → 1件: '1\n転移学習とファインチューニング'（章扉）
```

```python
_NAV_SECTION = "## 1\n\n転移学習とファインチューニング\n"


def test_ingest_drops_a_navigation_section_and_reports_how_many(
    source_dir, collection
):
    """章扉は取り込まれず、除外件数が報告に載る。本文の節は残る。"""
    _write_md(
        source_dir,
        "mixed.md",
        _NAV_SECTION
        + "\n## 本編\n\nRAGは検索した文書を根拠にして回答を組み立てる仕組みである。"
        "実務では社内文書を対象にする。\n",
    )

    report = ingest_directory(source_dir, collection, session=_FakeSession())

    assert report.dropped == {"mixed.md": 1}
    stored = collection.get()["documents"]
    assert "1\n転移学習とファインチューニング" not in stored
    assert any("RAGは検索した文書を根拠に" in text for text in stored)


def test_ingest_keeps_everything_when_every_unit_looks_like_navigation(
    source_dir, collection
):
    """全滅したら何も落とさない。

    落とすと store.replace_source() が空のチャンク列を受け取り、資料が
    DBから丸ごと消える。規則が誤爆したときに最も起きてほしくない結果である。
    """
    messages = []
    _write_md(source_dir, "nav_only.md", _NAV_SECTION)

    report = ingest_directory(
        source_dir,
        collection,
        session=_FakeSession(),
        on_progress=messages.append,
    )

    assert "nav_only.md" not in report.dropped
    assert report.indexed["nav_only.md"] == 1
    assert any("警告" in message and "nav_only.md" in message for message in messages)
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_ingest_source.py -q -k navigation`
Expected: FAIL — `AttributeError: 'IngestReport' object has no attribute 'dropped'`

- [ ] **Step 3: 実装する**

`scripts/ingest_source.py` の import に足す。

```python
from ingest import embedder, navigation, store, vlm
```

`IngestReport` にフィールドを足す。既定値があるので既存の呼び出しは影響を受けない。

```python
@dataclass
class IngestReport:
    indexed: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    removed: list[str] = field(default_factory=list)
    # 資料キー → ナビゲーション用スライドとして除外した件数。
    # 1件も落ちなかった資料はキーを持たない。
    dropped: dict[str, int] = field(default_factory=dict)
```

取り込みループの `units = parse(...)` から `notify(f"完了: ...")` までを次に置き換える。

```python
            notify(f"処理中: {source}")
            try:
                units = parse(path, caption_image=caption_image)
                kept, dropped = navigation.drop_navigation(units)
                if dropped and not kept:
                    # 規則が誤爆したときに資料が丸ごと消えるのを防ぐ。空のチャンク列を
                    # store.replace_source() に渡すと、その資料はDBから消える。
                    # 中身のある資料からノイズを取り除くのがこの機能の目的であり、
                    # 「中身が1つも無い資料」は規則の誤りである可能性のほうが高い。
                    notify(f"警告: {source} は全ユニットがナビゲーション判定。除外しません")
                    dropped = []
                else:
                    units = kept
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
            if dropped:
                report.dropped[source] = len(dropped)
                notify(
                    f"完了: {source}（{len(chunks)}チャンク、"
                    f"ナビゲーション{len(dropped)}件を除外）"
                )
            else:
                notify(f"完了: {source}（{len(chunks)}チャンク）")
```

- [ ] **Step 4: 通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_ingest_source.py -q`
Expected: PASS（既存分すべて + 新規2件）

- [ ] **Step 5: テストが恒真でないことを実行で確かめる**

`ingest/navigation.py` の `is_navigation` を一時的に `return False` に書き換える。

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_ingest_source.py -q -k navigation`
Expected: FAIL — 全滅時の警告テストが落ちる（警告が出ないため）

**確認できたら元に戻す。** `git diff ingest/navigation.py` が空であることを確かめる。

- [ ] **Step 6: コミット**

```bash
git add scripts/ingest_source.py tests/test_ingest_source.py
git commit -m "feat: drop navigation slides between parsing and chunking

A slide is the natural unit for this judgement, so the sieve runs on
ParsedUnits before chunk_units sees them. chunk_units keeps its calling
convention, so no existing test moves.

When every unit in a file looks like navigation, nothing is dropped and a
warning is printed instead. Dropping would hand replace_source an empty
chunk list and erase the document."
```

---

### Task 4: 除外件数を2つの要約に出す

**Files:**
- Modify: `ingest/prompting.py:85-94`（`format_report`、Streamlit のサイドバー用）
- Modify: `scripts/ingest_source.py:189-197`（CLI の要約）
- Test: `tests/test_prompting.py`

**Interfaces:**
- Consumes: `IngestReport.dropped: dict[str, int]`（Task 3）
- Produces: なし

要約は2箇所にある。片方だけ直すと、UIとCLIで見える内容が食い違う。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_prompting.py` の末尾に足す。

```python
def test_report_shows_how_many_navigation_slides_were_dropped():
    report = IngestReport(
        indexed={"a.pptx": 30, "b.pptx": 24},
        skipped=[],
        failed={},
        removed=[],
        dropped={"a.pptx": 4, "b.pptx": 3},
    )
    text = format_report(report)
    assert "ナビゲーション除外: 7件" in text
    assert "2ファイル" in text


def test_report_says_nothing_about_navigation_when_none_was_dropped():
    """何も落ちていないのに行が出ると、落ちたのかどうか読み取れない。"""
    report = IngestReport(indexed={"a.pdf": 3}, skipped=[], failed={}, removed=[])
    assert "ナビゲーション" not in format_report(report)
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_prompting.py -q -k navigation`
Expected: FAIL — `assert 'ナビゲーション除外: 7件' in text`

- [ ] **Step 3: 実装する**

`ingest/prompting.py` の `format_report` を書き換える。

```python
def format_report(report) -> str:
    lines = [
        f"取り込み: {sum(report.indexed.values())}チャンク / {len(report.indexed)}ファイル",
        f"スキップ: {len(report.skipped)}ファイル",
        f"削除: {len(report.removed)}ファイル",
    ]
    # 1件も落ちていないときは行を出さない。常に出すと、0件なのか
    # 機能が働いていないのか読み手が区別できない。
    if report.dropped:
        lines.append(
            f"ナビゲーション除外: {sum(report.dropped.values())}件"
            f" / {len(report.dropped)}ファイル"
        )
    for source, message in report.failed.items():
        lines.append(f"失敗 {source}: {message}")
    return "\n".join(lines)
```

`scripts/ingest_source.py` の要約（`print(f"削除: ...")` の直後）に足す。

```python
    print(f"削除: {len(report.removed)}ファイル")
    if report.dropped:
        print(
            f"ナビゲーション除外: {sum(report.dropped.values())}件"
            f" / {len(report.dropped)}ファイル"
        )
```

- [ ] **Step 4: 通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add ingest/prompting.py scripts/ingest_source.py tests/test_prompting.py
git commit -m "feat: report dropped navigation slides in both summaries

The sidebar and the CLI render the report separately; fixing one alone
would make the two disagree. The line is omitted when nothing dropped, so
a zero cannot be confused with the feature not running."
```

---

### Task 5: ドキュメント

**Files:**
- Modify: `README.md`
- Modify: `docs/処理箇所マップ.md`
- Modify: `docs/依存関係一覧.md`

**Interfaces:**
- Consumes: すべて
- Produces: なし

**行番号を書くときは必ず実ファイルを開いて照合すること。** 推測で書かない。この計画に書かれた行番号も、作業時点でずれている可能性がある。

- [ ] **Step 1: README に説明を足す**

取り込みの節に、何を落とすか・なぜ落とすか・件数の見方を書く。次の3点を必ず含める。

- 落とすのは章扉・目次・締めの3種で、判定は `ingest/navigation.py` にある
- 落とした件数は取り込みの要約に出る。見えないところで消えることはない
- 既存DBは差分取り込みでは変わらない。`python -m scripts.ingest_source --force --only-suffix .pptx` で入れ直す必要がある

**回帰ケースが直ったかどうかは、この時点では書かない。** Task 6 で実測してから書く。

- [ ] **Step 2: 処理箇所マップに `ingest/navigation.py` の節を足す**

`## 1. データをチャンクに分割している箇所` の中か直後に置く。パースとチャンク化の間に入る処理であることが読み取れる位置にする。

各エントリの行番号を実ファイルで照合する。次のコマンドで全参照を機械照合できる。

```bash
./myvenv313/Scripts/python.exe - <<'PY'
import io, re, os
s = io.open('docs/処理箇所マップ.md', encoding='utf-8').read()
pat = re.compile(r'\[([\w./]+\.py):(\d+)(?:-(\d+))?\]\((\.\./[^)#]*)#L(\d+)(?:-L(\d+))?\)')
cache, total, bad = {}, 0, 0
for mo in pat.finditer(s):
    total += 1
    label, a, b, href, ha, hb = mo.group(1), int(mo.group(2)), mo.group(3), mo.group(4), int(mo.group(5)), mo.group(6)
    t = os.path.normpath(os.path.join('docs', href)); pr = []
    if a != ha or (b or None) != (hb or None): pr.append('label/anchor mismatch')
    if not os.path.exists(t): pr.append('missing file')
    else:
        if t not in cache: cache[t] = io.open(t, encoding='utf-8').read().split('\n')
        L = cache[t]; end = int(b) if b else a
        if a < 1 or end > len(L): pr.append('out of range')
        elif not L[a-1].strip() or not L[end-1].strip(): pr.append('blank boundary')
    if pr: bad += 1; print(f'  !! {label}:{a}-{b}: {"; ".join(pr)}')
print(f'checked {total} references, {bad} problem(s)')
PY
```

Expected: `0 problem(s)`

**`scripts/ingest_source.py` の節も更新する。** Task 3 で取り込みループが伸びており、既存の参照がずれている。上のスクリプトは行の内容までは見ないので、`ingest_source.py` を指す参照は実際に開いて内容を確かめること。

- [ ] **Step 3: 依存関係一覧の取り込みの節を更新する**

`ingest/navigation.py` が増えたことと、それが何に依存するか（`ingest/models.py` のみ）を書く。

- [ ] **Step 4: コミット**

```bash
git add README.md "docs/処理箇所マップ.md" "docs/依存関係一覧.md"
git commit -m "docs: describe what gets dropped at ingest and how to see it"
```

---

### Task 6: 再取り込みと実測

**Files:**
- Modify: `README.md`（実測値の記録）
- Modify: `docs/superpowers/specs/2026-09-06-navigation-slides-design.md`（7節に実測を追記）

**Interfaces:**
- Consumes: すべて
- Produces: なし

**このタスクは Ollama を必要とする。** Colab の L4 が起動していることを確認してから始める。起動していない場合は、そこで止めて依頼者に伝えること。**測っていないものを測ったように書かない。**

- [ ] **Step 1: 現状を記録する**

```bash
./myvenv313/Scripts/python.exe -c "from ingest.store import open_store; c=open_store('vector_store.sqlite3'); print(c.count(), c.chunk_count(), c.integrity())"
```

Expected: `608 538 (0, 0)`

この値を控える。合わない場合は DB が計画の前提と違うので、そこで止めて依頼者に伝える。

- [ ] **Step 2: セミナー資料を入れ直す**

```bash
./myvenv313/Scripts/python.exe -m scripts.ingest_source --force --only-suffix .pptx
```

要約に「ナビゲーション除外」の行が出ることを確認する。

- [ ] **Step 3: 件数を検証する**

```bash
./myvenv313/Scripts/python.exe -c "from ingest.store import open_store; c=open_store('vector_store.sqlite3'); print(c.count(), c.chunk_count(), c.integrity())"
```

Expected: `570 512 (0, 0)`（設計書4節の予測値）

**合わない場合は、その数字をそのまま報告し、なぜ違うのかを調べる。** 予測に合わせて数字を書き換えない。締めスライドは7資料が共有しているため、7本すべてを入れ直さないと消えない点に注意する。

- [ ] **Step 4: 回帰ケースを測る**

```bash
./myvenv313/Scripts/python.exe -m scripts.check_retrieval
```

次の3つを記録する。

1. 「ファインチューニングについて教えてほしい」の上位3件（変更前は章扉・章扉・目次）
2. ゲートの距離（変更前は関連の最大 0.420 / 圏外の最小 0.522）
3. BM25 の絶対値（索引が538→512になり idf と平均文書長が変わる）

- [ ] **Step 5: 実測を書く**

README と設計書7節に、測った値をそのまま書く。**上位3件に中身のある本文が入らなかった場合は、NG のままだと書く。** 直ったことにしない。

前ブランチでは、畳み込みが主張どおりの効果を出した（10位→4位）にもかかわらず回帰ケースは NG のままだった。同じ誠実さで書く。

- [ ] **Step 6: 全テストを通す**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

- [ ] **Step 7: コミット**

```bash
git add README.md "docs/superpowers/specs/2026-09-06-navigation-slides-design.md"
git commit -m "docs: record what dropping navigation slides actually bought"
```
