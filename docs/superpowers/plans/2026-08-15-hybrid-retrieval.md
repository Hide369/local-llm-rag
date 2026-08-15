# ハイブリッド検索とPPTXチャンク分割 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 固有の専門用語で質問したとき、その語を実際に含む資料が検索結果に入るようにする。

**Architecture:** ベクトル検索（Chroma / bge-m3）とBM25（文字bigram・自前実装・メモリ常駐）を並行実行し、RRFで融合する。足切りは各アームの生の指標によるOR条件で行う。あわせてPPTXのチャンクをテキストボックス（シェイプ）単位に分割し、1スライドに複数話題が同居することによるベクトルの希釈を緩和する。

**Tech Stack:** Python 3.13（`myvenv313`）、ChromaDB、python-pptx 1.0.2、pytest。**追加の依存パッケージは無い。**

**Spec:** `docs/superpowers/specs/2026-08-15-hybrid-retrieval-design.md`

## Global Constraints

- 依存パッケージを追加しない。BM25も日本語の語分割も自前で実装する（spec 5.1）
- BM25インデックスをディスクへ永続化しない。起動時にChromaDBから構築する（spec 5.5）
- `ingest/lexical.py` は純粋な計算モジュールとする。ChromaDBにもOllamaにも依存させない（spec 11）
- しきい値は推測せず実測で決める。`RELEVANCE_THRESHOLD = 0.50` は据え置き、`BM25_FLOOR` はTask 6で実測して確定する（spec 9）
- BM25パラメータは `BM25_K1 = 1.2` / `BM25_B = 0.75`、RRF定数は `RRF_K = 60`、各アームの候補数は `CANDIDATE_COUNT = 30`（spec 5.3, 6.1）
- PPTXのグルーピング目標は `GROUP_TARGET_CHARS = 200`、行の丸め幅は `ROW_TOLERANCE = 228600`（0.25インチをEMUで表した値）（spec 7.2, 7.5）
- テストは `.\myvenv313\Scripts\python.exe -m pytest` で実行する。着手時点で212件成功・1件deselected（integration）
- コメントは「なぜ」を書く。実測値を根拠として残す（既存コードの作法）
- コミットメッセージは英語のコンベンショナルコミット。末尾に `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- 作業ブランチは `feat/hybrid-retrieval`（作成済み）

## 前提となる実測値

計画中のテストと検証はこの値を根拠にしている。

| 事実 | 値 |
|---|---|
| 現在のDB総チャンク数 | 460 |
| 「ファインチューニング」を含むチャンク | 2件のみ（セミナー スライド11・スライド40） |
| 「ファインチューニングについて教えてほしい」でのスライド11 | 4位 / 距離 0.514（しきい値0.50で足切り） |
| 「ファインチューニング」単体でのベクトル最良 | 0.523（全滅する） |
| 既存の関連質問の最大距離 / 圏外質問の最小距離 | 0.459 / 0.549 |
| PPTX `slide.shapes.title` が取れる枚数 | 0 / 43 |
| `©` 行を持つスライド / ページ番号行を持つスライド | 43 / 43、38 / 43 |
| 新パーサー試作の出力 | 43スライド → 80ユニット（min 11 / max 547 / avg 156字） |

---

### Task 1: 文字bigramトークナイザ

**Files:**
- Create: `ingest/lexical.py`
- Test: `tests/test_lexical.py`

**Interfaces:**
- Consumes: なし
- Produces: `tokenize(text: str) -> list[str]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_lexical.py` を新規作成する。

```python
"""BM25の語分割とスコア計算。

形態素解析器を使わない理由は spec 5.1 を参照。辞書に無い語（型番・新しい
専門用語）で分割が揺れないことが、この検索の存在意義そのものである。
"""
from ingest import lexical


def test_japanese_text_becomes_character_bigrams():
    assert lexical.tokenize("ファイン") == ["ファ", "ァイ", "イン"]


def test_a_single_character_segment_survives_as_one_token():
    """1文字ではbigramが作れない。落とすとその語で引けなくなる。"""
    assert lexical.tokenize("犬") == ["犬"]


def test_width_and_case_are_normalised():
    """全角で書かれた「ＲＡＧ」と半角の「rag」は同じ語である。"""
    assert lexical.tokenize("ＲＡＧ") == lexical.tokenize("rag")


def test_punctuation_separates_segments():
    """型番のハイフンは境界。クエリと本文で同じ分かれ方をすれば一致する。"""
    assert lexical.tokenize("UD-0900i") == lexical.tokenize("ud 0900i")


def test_bigrams_do_not_cross_a_boundary():
    """区切りを跨いだbigramを作ると、実在しない語で一致してしまう。"""
    assert "犬猫" not in lexical.tokenize("犬 猫")


def test_empty_text_produces_no_tokens():
    assert lexical.tokenize("") == []


def test_whitespace_only_text_produces_no_tokens():
    assert lexical.tokenize("  \n  ") == []
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_lexical.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.lexical'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/lexical.py` を新規作成する。

```python
"""全文検索(BM25)のための語分割とスコア計算。

形態素解析器を使わないのは、辞書に無い語で分割位置が変わるためである。
「UD-0900i」のような型番や新しい専門用語こそ、この検索が救おうとしている
対象であり、そこで分割が揺れては意味がない。文字bigramは辞書を持たない。

このモジュールはChromaDBにもOllamaにも依存しない純粋な計算である。
"""
import re
import unicodedata

# Unicode対応の \W で区切る。漢字・かなは語構成文字として残り、空白と約物
# だけが境界になる。区切りを跨いだbigramは作らない（実在しない語で一致するため）。
_BOUNDARY = re.compile(r"\W+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """NFKC正規化して小文字化し、文字bigramへ分割する。

    正規化は全角/半角と大文字/小文字の揺れを吸収する。実データには全角の
    「ＲＡＧ」と半角の「RAG」が混在する。

    1文字のセグメントはbigramが作れず消滅してしまうため、そのまま1トークンとする。
    """
    normalised = unicodedata.normalize("NFKC", text).lower()
    tokens: list[str] = []
    for segment in _BOUNDARY.split(normalised):
        if not segment:
            continue
        if len(segment) == 1:
            tokens.append(segment)
            continue
        tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens
```

- [ ] **Step 4: テストを実行して成功を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_lexical.py -v
```

Expected: PASS（7件）

- [ ] **Step 5: コミット**

```bash
git add ingest/lexical.py tests/test_lexical.py
git commit -m "feat: tokenize Japanese text into character bigrams for BM25

A morphological analyser splits unknown words differently depending on its
dictionary, and unknown words - model numbers, new jargon - are exactly what
this search exists to rescue. Character bigrams carry no dictionary.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: BM25インデックスと検索

**Files:**
- Modify: `ingest/lexical.py`
- Test: `tests/test_lexical.py`

**Interfaces:**
- Consumes: `lexical.tokenize(text) -> list[str]`（Task 1）
- Produces:
  - `lexical.BM25Index`（frozen dataclass。`ids: list[str]`, `postings: dict[str, dict[int, int]]`, `lengths: list[int]`, `average_length: float`, プロパティ `document_count: int`）
  - `lexical.build(ids: list[str], texts: list[str]) -> BM25Index`
  - `lexical.search(index: BM25Index, query: str, limit: int) -> list[tuple[str, float]]`
  - 定数 `BM25_K1 = 1.2`, `BM25_B = 0.75`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_lexical.py` の末尾に追記する。

```python
def _index():
    """語が一切重ならない3文書。順位の判定を明確にするため。"""
    return lexical.build(
        ["a", "b", "c"],
        ["ファインチューニング", "有給休暇", "洗濯容量"],
    )


def test_the_document_containing_the_term_is_returned():
    assert [doc for doc, _ in lexical.search(_index(), "ファインチューニング", limit=3)] == ["a"]


def test_documents_sharing_no_token_score_nothing():
    """スコア0の文書を返すと、無関係な文書がRRFの順位に紛れ込む。"""
    assert lexical.search(_index(), "天気", limit=3) == []


def test_empty_index_returns_nothing():
    assert lexical.search(lexical.build([], []), "何か", limit=3) == []


def test_a_rare_term_outscores_a_common_one():
    """IDF。全文書に出る語は識別力を持たない。文字bigramの部分一致による
    ノイズを押さえているのもこの項である。"""
    index = lexical.build(["a", "b", "c"], ["共通語 希少語", "共通語", "共通語"])
    rare = dict(lexical.search(index, "希少語", limit=3))["a"]
    common = dict(lexical.search(index, "共通語", limit=3))["a"]
    assert rare > common


def test_a_shorter_document_outscores_a_longer_one():
    """文書長による正規化。同じ1回の出現でも、短い文書のほうが主題である。"""
    index = lexical.build(["short", "long"], ["希少語", "希少語 " + "詰め物 " * 30])
    assert lexical.search(index, "希少語", limit=2)[0][0] == "short"


def test_more_occurrences_score_higher():
    index = lexical.build(["once", "twice"], ["希少語 詰め物", "希少語 希少語"])
    assert lexical.search(index, "希少語", limit=2)[0][0] == "twice"


def test_limit_caps_the_number_of_results():
    index = lexical.build(["a", "b", "c"], ["希少語", "希少語", "希少語"])
    assert len(lexical.search(index, "希少語", limit=2)) == 2


def test_results_are_ordered_deterministically():
    """同点の文書はID順にする。順位が揺れるとRRFの結果が再現しなくなる。"""
    index = lexical.build(["c", "a", "b"], ["希少語", "希少語", "希少語"])
    assert [doc for doc, _ in lexical.search(index, "希少語", limit=3)] == ["a", "b", "c"]
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_lexical.py -v
```

Expected: FAIL — `AttributeError: module 'ingest.lexical' has no attribute 'build'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/lexical.py` の import 行を次に差し替える。

```python
import math
import re
import unicodedata
from dataclasses import dataclass
```

ファイル末尾（`tokenize` の後）に追記する。

```python
# Okapi BM25の標準的な値。実データで調整が要るのは BM25_FLOOR のほうであり、
# ここは動かさない。
BM25_K1 = 1.2
BM25_B = 0.75


@dataclass(frozen=True)
class BM25Index:
    """転置索引。ids[i] が i 番目の文書のチャンクIDにあたる。

    ディスクへ永続化しない。DBとファイルで状態が二重管理になると、差分取り込みの
    たびに食い違い、しかも例外が出ないため「検索結果が静かに古くなる」。
    信頼できる情報源は常にDBひとつにする（ingest/store.py と同じ方針）。
    """

    ids: list[str]
    postings: dict[str, dict[int, int]]  # トークン → {文書番号: 出現回数}
    lengths: list[int]
    average_length: float

    @property
    def document_count(self) -> int:
        return len(self.ids)


def build(ids: list[str], texts: list[str]) -> BM25Index:
    postings: dict[str, dict[int, int]] = {}
    lengths: list[int] = []
    for number, text in enumerate(texts):
        tokens = tokenize(text)
        lengths.append(len(tokens))
        for token in tokens:
            counts = postings.setdefault(token, {})
            counts[number] = counts.get(number, 0) + 1
    return BM25Index(
        ids=list(ids),
        postings=postings,
        lengths=lengths,
        # 空のインデックスで0除算しないための1.0。search が先に空を返すため
        # この値が実際に使われることはない。
        average_length=(sum(lengths) / len(lengths)) if lengths else 1.0,
    )


def _idf(index: BM25Index, token: str) -> float:
    frequency = len(index.postings.get(token, {}))
    if frequency == 0:
        return 0.0
    return math.log(
        1 + (index.document_count - frequency + 0.5) / (frequency + 0.5)
    )


def search(index: BM25Index, query: str, limit: int) -> list[tuple[str, float]]:
    """スコアの高い順に (チャンクID, スコア) を返す。

    スコア0の文書は含めない。含めるとRRFの順位に無関係な文書が紛れ込む。
    同点はID順にして並びを決定的にする。順位が揺れるとRRFの結果が再現しない。
    """
    if index.document_count == 0:
        return []
    scores: dict[int, float] = {}
    for token in tokenize(query):
        idf = _idf(index, token)
        if idf == 0.0:
            continue
        for number, frequency in index.postings[token].items():
            length_ratio = index.lengths[number] / index.average_length
            denominator = frequency + BM25_K1 * (1 - BM25_B + BM25_B * length_ratio)
            scores[number] = scores.get(number, 0.0) + (
                idf * frequency * (BM25_K1 + 1) / denominator
            )
    ranked = sorted(scores.items(), key=lambda item: (-item[1], index.ids[item[0]]))
    return [(index.ids[number], score) for number, score in ranked[:limit]]
```

- [ ] **Step 4: テストを実行して成功を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_lexical.py -v
```

Expected: PASS（15件）

- [ ] **Step 5: コミット**

```bash
git add ingest/lexical.py tests/test_lexical.py
git commit -m "feat: score documents with Okapi BM25 over an in-memory index

The index is never written to disk. Keeping a file beside the DB means the
two drift apart on every incremental ingest, and nothing raises - the search
just goes quietly stale.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: チャンクIDの衝突を直す

同一 `(location_type, location)` に複数のユニットが来たとき、現行の実装は
いずれも `index=0` を生成する。ChromaDBの `add` は同一IDを上書きするため、
**例外を出さずにチャンクが消える。** Task 4でPPTXが1スライド複数ユニットに
なる前に直しておく必要がある。

**Files:**
- Modify: `ingest/chunker.py:70-97`
- Test: `tests/test_chunker.py`

**Interfaces:**
- Consumes: なし
- Produces: `chunk_units` の `chunk_index` が `(location_type, location)` ごとの通し番号になる。関数シグネチャは不変

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chunker.py` の末尾に追記する。

```python
def test_units_sharing_a_location_get_distinct_ids():
    """PPTXは1スライドが複数ユニットになる（spec 7.5）。IDが衝突すると
    ChromaDBが黙って上書きし、チャンクが消える。例外は出ない。"""
    units = [
        _unit("スライドの前半について述べた文章です。", location=11, location_type="slide"),
        _unit("スライドの後半について述べた文章です。", location=11, location_type="slide"),
    ]
    chunks = _chunk(units)
    assert len(chunks) == 2
    assert len({chunk.id for chunk in chunks}) == 2
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == [0, 1]


def test_each_location_numbers_its_chunks_from_zero():
    """ロケーションが違えば0から振り直す。既存形式のIDを変えないための境界。"""
    units = [
        _unit("1ページ目の文章です。ここに本文が入ります。", location=1),
        _unit("2ページ目の文章です。ここに本文が入ります。", location=2),
    ]
    assert [chunk.metadata["chunk_index"] for chunk in _chunk(units)] == [0, 0]
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_chunker.py -v
```

Expected: `test_units_sharing_a_location_get_distinct_ids` が FAIL
（`assert 1 == 2` — IDが重複して集合が1件になる）。
`test_each_location_numbers_its_chunks_from_zero` は既に PASS。

- [ ] **Step 3: 最小限の実装を書く**

`ingest/chunker.py` の先頭に import を追加する。

```python
from collections import Counter
```

`chunk_units` の本体を次に差し替える。

```python
def chunk_units(
    units: list[ParsedUnit], source: str, file_hash: str, indexed_at: str
) -> list[Chunk]:
    """各ユニットを独立にチャンク化する。

    ユニットをまたいで結合しない。結合するとチャンクがページ境界を越え、
    「何ページ目の記述か」を一意に示せなくなる。

    チャンク番号はユニット内ではなく (location_type, location) ごとの通し番号に
    する。PPTXは1スライドが複数ユニットになるため（spec 7.5）、ユニット内で
    0から振り直すとIDが衝突し、ChromaDBが例外を出さずに上書きしてチャンクを失う。
    1ロケーション1ユニットの他形式では 0,1,2… の並びが従来と変わらないため、
    既存チャンクのIDは1件も変化しない。
    """
    chunks: list[Chunk] = []
    numbers: Counter = Counter()
    for unit in units:
        text = unit.text.strip()
        if not text:
            continue
        location_key = (unit.location_type, unit.location)
        for part in _split(text):
            index = numbers[location_key]
            numbers[location_key] += 1
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
                        "heading": unit.heading,
                        "chunk_index": index,
                        "indexed_at": indexed_at,
                        **{
                            key: value
                            for key, value in unit.attributes.items()
                            if key not in RESERVED_METADATA_KEYS
                        },
                    },
                )
            )
    return chunks
```

- [ ] **Step 4: テストを実行して成功を確認する**

チャンカーだけでなく全体を回す。既存形式のIDが変わっていないことを確かめるため。

```powershell
.\myvenv313\Scripts\python.exe -m pytest -q
```

Expected: PASS（229件 = 着手時212 + Task 1の7 + Task 2の8 + 本タスクの2）。失敗ゼロ。

- [ ] **Step 5: コミット**

```bash
git add ingest/chunker.py tests/test_chunker.py
git commit -m "fix: number chunks per location so ids cannot collide

Two units at the same location both produced index 0, and Chroma's add
overwrites a duplicate id without raising. No format hits this today; the
pptx split in the next commit does.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: PPTXをシェイプ単位で分割する

**Files:**
- Modify: `ingest/parsers/pptx_parser.py`（全面置き換え）
- Test: `tests/test_parsers_office.py`

**Interfaces:**
- Consumes: `ingest.models.SLIDE`, `ingest.models.ParsedUnit`
- Produces: `parse_pptx(path: Path) -> list[ParsedUnit]`（シグネチャ不変。1スライドが複数ユニットを返すようになる）。モジュール定数 `ROW_TOLERANCE = 228600`, `GROUP_TARGET_CHARS = 200`

**注意:** 既存テスト4件（`test_pptx_produces_one_unit_per_slide` / `test_pptx_includes_speaker_notes` / `test_pptx_slide_text_is_captured` / `test_office_parsers_are_not_marked_as_ocr`）は**変更せずに通す**。spec 7.6 がその理由である。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_parsers_office.py` に fixture とテストを追記する。ファイル先頭の import に `MSO_SHAPE_TYPE` は不要（グループはAPIで作る）。

```python
@pytest.fixture
def rich_pptx_path(tmp_path):
    """実データのスライド11を模した1枚。

    読み順・ノイズ除去・タイトル複写・分割をまとめて確かめる。シェイプは
    わざとXML順と視覚順がずれるように置く（実データも同じ形だった）。
    """
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    def box(text, top_inches):
        shape = slide.shapes.add_textbox(
            Inches(1), Inches(top_inches), Inches(6), Inches(1)
        )
        shape.text_frame.text = text
        return shape

    box("©2026 OpenUp Next Engineer Inc.", 6.0)
    box("1", 5.5)
    box("あ" * 150, 2.0)
    box("1-6. 生成AI活用のポイント", 0.5)
    box("い" * 120, 3.0)

    path = tmp_path / "セミナー.pptx"
    prs.save(path)
    return path


def test_shapes_are_read_in_visual_order_not_xml_order(rich_pptx_path):
    """XML順ではタイトルが4番目に来る。読み順に直さないとタイトルを取り違える。"""
    units = parse_pptx(rich_pptx_path)
    assert units[0].text.startswith("1-6. 生成AI活用のポイント")


def test_the_slide_is_split_into_several_units(rich_pptx_path):
    """150字と120字は合わせて目標200字を超えるので別グループになる。"""
    units = parse_pptx(rich_pptx_path)
    assert len(units) == 2
    assert "あ" in units[0].text and "い" not in units[0].text
    assert "い" in units[1].text and "あ" not in units[1].text


def test_the_title_is_copied_into_every_unit(rich_pptx_path):
    """分割後のチャンクが単独で何の話か分かるようにする。"""
    units = parse_pptx(rich_pptx_path)
    assert all(u.text.startswith("1-6. 生成AI活用のポイント\n") for u in units)


def test_a_shape_is_never_split_across_units(rich_pptx_path):
    """シェイプは作成者が区切った意味のまとまり。跨いで切ると文脈が壊れる。"""
    units = parse_pptx(rich_pptx_path)
    assert units[0].text.count("あ") == 150
    assert units[1].text.count("い") == 120


def test_copyright_and_page_number_lines_are_dropped(rich_pptx_path):
    """全43枚に同じフッタが入っており、ベクトルを一様に濁らせる。"""
    joined = "\n".join(u.text for u in parse_pptx(rich_pptx_path))
    assert "©" not in joined
    assert "OpenUp" not in joined
    assert "\n1\n" not in joined and not joined.endswith("\n1")


def test_every_unit_of_a_slide_keeps_the_slide_number(rich_pptx_path):
    """出典が「スライド11」であることは分割後も変わらない。"""
    units = parse_pptx(rich_pptx_path)
    assert all(u.location == 1 and u.location_type == "slide" for u in units)


def test_a_shape_larger_than_the_target_becomes_its_own_unit(tmp_path):
    """実データには538字のシェイプがある。200字は目標であって上限ではない。"""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    for text, top in (("見出しの行", 0.5), ("う" * 500, 2.0)):
        shape = slide.shapes.add_textbox(Inches(1), Inches(top), Inches(6), Inches(1))
        shape.text_frame.text = text
    path = tmp_path / "長い.pptx"
    prs.save(path)

    units = parse_pptx(path)
    assert len(units) == 1
    assert units[0].text.count("う") == 500


def test_text_inside_grouped_shapes_is_captured(tmp_path):
    """グループ内のテキストは現行の実装が無言で捨てていた（spec 7.7）。"""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    title = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(6), Inches(1))
    title.text_frame.text = "手順の説明"
    group = slide.shapes.add_group_shape()
    inner = group.shapes.add_textbox(Inches(1), Inches(2), Inches(3), Inches(1))
    inner.text_frame.text = "Step 1 レビュー依頼"
    path = tmp_path / "グループ.pptx"
    prs.save(path)

    assert "Step 1 レビュー依頼" in parse_pptx(path)[0].text


def test_a_slide_with_only_a_title_still_produces_a_unit(tmp_path):
    """本文が空でもユニットを落とさない（spec 7.6）。"""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    box.text_frame.text = "章の扉ページ"
    path = tmp_path / "扉.pptx"
    prs.save(path)

    units = parse_pptx(path)
    assert len(units) == 1
    assert units[0].text == "章の扉ページ"


def test_remaining_lines_of_the_title_shape_are_kept_as_body(tmp_path):
    """タイトルと副題が同じテキストボックスに入っている場合、副題を捨てない。"""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(6), Inches(2))
    box.text_frame.text = "生成AI活用セミナー\nAIエージェントとAI駆動開発を学ぼう"
    path = tmp_path / "扉2.pptx"
    prs.save(path)

    units = parse_pptx(path)
    assert len(units) == 1
    assert units[0].text == "生成AI活用セミナー\nAIエージェントとAI駆動開発を学ぼう"
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_parsers_office.py -v
```

Expected: 新規10件のうち少なくとも
`test_the_slide_is_split_into_several_units`（`assert 1 == 2`）、
`test_the_title_is_copied_into_every_unit`、
`test_copyright_and_page_number_lines_are_dropped`、
`test_text_inside_grouped_shapes_is_captured` が FAIL。既存4件は PASS。

- [ ] **Step 3: 最小限の実装を書く**

`ingest/parsers/pptx_parser.py` を全面的に次へ置き換える。

```python
"""PowerPointのテキスト抽出。

スライドは話題の単位としては粗すぎる。実測では1スライドに7つの話題が同居し、
チャンクのベクトルがスライド全体の平均に薄まって、その中の1話題を指す質問で
順位を落としていた。同じチャンクが、スライドの表題そのままの質問には距離0.303で
1位、その中の1話題を指す質問には0.514で4位になる（spec 2.4）。

テキストボックスは作成者が視覚的に区切った意味のまとまりなので、これを分割の
単位にする。実測では43スライドが80ユニット（min 11 / max 547 / avg 156字）になる。
"""
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from ingest.models import SLIDE, ParsedUnit

# 同じ行に並ぶ図表の要素を左から右へ並べるための丸め幅。0.25インチをEMUで表した値。
ROW_TOLERANCE = 228600

# ブロックを積んでいく目標文字数。上限ではない。単独でこれを超えるシェイプ
# （実データの最大は538字）は、それ1つで1グループになる。
GROUP_TARGET_CHARS = 200


def _walk(shapes):
    """グループ化されたシェイプの中まで辿る。

    トップレベルだけを見ると、グループ内のテキストが例外も警告もなく捨てられる。
    実データではスライド26の「Step 1」〜「Step 4」が該当した。
    """
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _walk(shape.shapes)
        else:
            yield shape


def _position(shape):
    """読み順（行優先）で並べるための整列キー。

    XML上の並び順は視覚的な読み順と一致しない。実データではタイトルの次に
    ページ番号が来る。top を丸めて行にまとめ、その中を left で並べる。
    """
    return (round((shape.top or 0) / ROW_TOLERANCE), shape.left or 0)


def _clean(text: str, slide_number: int) -> str:
    """内容を持たない行を落とす。

    実データでは全43枚にコピーライトのフッタが、38枚にページ番号だけの行が
    入っていた。全スライドに同じ文字列が入るとベクトルが一様に濁る。BM25側は
    IDFが押さえるが、ベクトル側には効かないため取り込み時に落とす。
    ページ番号は location メタデータが持っているので失われない。
    """
    lines = [
        line
        for line in (raw.strip() for raw in text.split("\n"))
        if line and not line.startswith("©") and line != str(slide_number)
    ]
    return "\n".join(lines)


def _blocks(slide, slide_number: int) -> list[str]:
    """読み順に並べた、内容のあるシェイプのテキスト。"""
    shapes = sorted(
        (shape for shape in _walk(slide.shapes) if shape.has_text_frame),
        key=_position,
    )
    blocks = [
        cleaned
        for cleaned in (_clean(shape.text_frame.text, slide_number) for shape in shapes)
        if cleaned
    ]
    # ノート欄には本文に書かれていない補足や発表意図が入るため取り込む。
    # 位置情報を持たないので読み順の最後尾に置く。
    if slide.has_notes_slide:
        notes = _clean(slide.notes_slide.notes_text_frame.text, slide_number)
        if notes:
            blocks.append(notes)
    return blocks


def _group(blocks: list[str]) -> list[str]:
    """目標文字数を目安にブロックをまとめる。シェイプは分割しない。"""
    groups: list[str] = []
    current: list[str] = []
    length = 0
    for block in blocks:
        # 足すと目標を超えるなら、足す前に閉じる。ただし空のときは閉じない。
        # 単独で目標を超えるシェイプが、それ1つで1グループになるようにするため。
        if current and length + len(block) > GROUP_TARGET_CHARS:
            groups.append("\n".join(current))
            current, length = [], 0
        current.append(block)
        length += len(block)
    if current:
        groups.append("\n".join(current))
    return groups


def parse_pptx(path: Path) -> list[ParsedUnit]:
    units: list[ParsedUnit] = []
    for number, slide in enumerate(Presentation(path).slides, start=1):
        blocks = _blocks(slide, number)
        if not blocks:
            continue
        # 先頭シェイプの1行目をタイトルとする。この資料では slide.shapes.title が
        # 43枚すべて None だった（タイトルプレースホルダを使っていない）。
        # 残りの行は捨てず、最初の本文ブロックとして扱う。
        title, _, remainder = blocks[0].partition("\n")
        body = ([remainder] if remainder else []) + blocks[1:]
        # タイトルを全ユニットへ複写する。分割後のチャンクが単独で何の話か
        # 分かるようにするため。「事前学習済モデルに追加学習させ、LLMを再生成する」
        # だけを見ても、何の定義か分からない。
        # 本文が空のスライド（章の扉）はタイトルだけで1ユニットにする。
        for group in _group(body) or [""]:
            units.append(
                ParsedUnit(
                    text=f"{title}\n{group}" if group else title,
                    location_type=SLIDE,
                    location=number,
                )
            )
    return units
```

- [ ] **Step 4: テストを実行して成功を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest -q
```

Expected: PASS（239件 = 229 + 本タスクの10）。既存4件のPPTXテストを含めて失敗ゼロ。

- [ ] **Step 5: 実データでの出力を確認する**

DBには触らず、パース結果だけを見る。

```powershell
.\myvenv313\Scripts\python.exe -c "from ingest.parsers.pptx_parser import parse_pptx; from pathlib import Path; u = parse_pptx(Path('source/生成AI活用セミナー.pptx')); print('units', len(u)); L=[len(x.text) for x in u]; print('min',min(L),'max',max(L),'avg',sum(L)//len(L)); print([x.text[:40] for x in u if x.location==11])"
```

Expected:
- `units 80`
- `min 11 max 547 avg 156`
- スライド11が2件に分かれ、1件目が `1-6. 生成AI活用のポイント\nプロンプト（指示文）の質が…` で始まる

数が大きく違う場合は先へ進まず、読み順かノイズ除去の条件を見直す。

- [ ] **Step 6: コミット**

```bash
git add ingest/parsers/pptx_parser.py tests/test_parsers_office.py
git commit -m "feat: split pptx slides by shape instead of one chunk per slide

A slide held up to seven topics in 364 characters, so its vector settled on
the slide's average and lost to chunks that never mention the term. Text
boxes are where the author already drew the topic boundaries.

Also recurses into grouped shapes, whose text was being dropped silently.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: PPTXを再取り込みする（運用）

コードは書かない。DBを新しいチャンク分割へ揃える。

**Files:** なし（`chroma_db/` の内容が変わる）

**Interfaces:**
- Consumes: Task 3・Task 4の成果
- Produces: DB総チャンク数 496（460 − 44 + 80）

- [ ] **Step 1: Streamlitが起動していないことを確認する**

同時アクセスでHNSWインデックスを破損させた実績がある（README「既知の制約」）。

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*streamlit*" -or $_.ProcessName -eq "python" } | Select-Object Id, ProcessName, StartTime
```

Expected: `rag_chat_app.py` を実行中のプロセスが無いこと。あれば停止してから進む。

- [ ] **Step 2: 取り込み前の状態を記録する**

```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; from ingest import store; from scripts.ingest_source import DB_DIR; c=store.open_collection(chromadb.PersistentClient(path=str(DB_DIR))); print('before', c.count())"
```

Expected: `before 460`

- [ ] **Step 3: PPTXだけを再取り込みする**

`--only-suffix` を付けているので孤児削除は走らず、他形式のチャンクは消えない。
OCRを伴わないため数秒で終わる。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.ingest_source --force --only-suffix .pptx
```

Expected: `取り込み: 80チャンク / 1ファイル`、`失敗: 0`、`DB内の総チャンク数: 496`

- [ ] **Step 4: スライド11が2チャンクに分かれたことを確認する**

```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; from ingest import store; from scripts.ingest_source import DB_DIR; c=store.open_collection(chromadb.PersistentClient(path=str(DB_DIR))); g=c.get(where={'source':'生成AI活用セミナー.pptx'}, include=['documents','metadatas']); print('pptx chunks', len(g['ids'])); print([d[:30] for d,m in zip(g['documents'],g['metadatas']) if m['location']==11])"
```

Expected: `pptx chunks 80` と、スライド11の2件がいずれも `1-6. 生成AI活用のポイント` で始まること

- [ ] **Step 5: コミットは不要**

`chroma_db/` は `.gitignore` の対象か確認する。追跡されていればコミットしない
（生成物であり、再実行で復元できる）。

```bash
git status --short
```

Expected: 変更なし、または `chroma_db/` が無視されている

---

### Task 6: BM25_FLOOR を実測して決める

**Files:**
- Modify: `ingest/store.py`
- Modify: `ingest/retrieval.py`（`build_index` の追加のみ。RRFはTask 7）
- Modify: `scripts/check_retrieval.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `lexical.build`, `lexical.search`（Task 2）
- Produces:
  - `store.all_documents(collection) -> tuple[list[str], list[str]]`（IDの並びと本文の並び）
  - `retrieval.build_index(collection) -> lexical.BM25Index`
  - 確定した `BM25_FLOOR` の数値（Task 7で定数に入れる）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_store.py` の末尾に追記する。既存ファイルの作法（`ephemeral_client`）に合わせる。

```python
def test_all_documents_returns_ids_and_texts_in_the_same_order():
    """BM25インデックスはIDと本文の並びが一致していることに依存する。"""
    collection = store.open_collection(ephemeral_client())
    collection.add(
        ids=["x", "y"],
        documents=["本文エックス", "本文ワイ"],
        embeddings=[[0.1], [0.2]],
        metadatas=[{"source": "a.pptx"}, {"source": "b.pptx"}],
    )
    ids, documents = store.all_documents(collection)
    assert dict(zip(ids, documents)) == {"x": "本文エックス", "y": "本文ワイ"}


def test_all_documents_on_an_empty_collection_returns_two_empty_lists():
    assert store.all_documents(store.open_collection(ephemeral_client())) == ([], [])
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_store.py -v
```

Expected: FAIL — `AttributeError: module 'ingest.store' has no attribute 'all_documents'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/store.py` の末尾に追記する。

```python
def all_documents(collection) -> tuple[list[str], list[str]]:
    """全チャンクのIDと本文を、並びを揃えて返す。

    BM25インデックスをディスクに持たず起動時に組み直すため、その入力を
    ここから供給する。DBを唯一の情報源に保つための経路である。
    """
    if collection.count() == 0:
        return [], []
    found = collection.get(include=["documents"])
    return found["ids"], found["documents"]
```

`ingest/retrieval.py` の import に追加する。

```python
from ingest import lexical, store
```

`ingest/retrieval.py` の末尾に追記する。

```python
def build_index(collection):
    """DBの全チャンクからBM25インデックスを組む。

    永続化しないのは、DBとファイルで状態が二重管理になると差分取り込みの
    たびに食い違い、例外も出ないまま検索結果が古くなるためである。
    """
    return lexical.build(*store.all_documents(collection))
```

- [ ] **Step 4: テストを実行して成功を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest -q
```

Expected: PASS（241件 = 239 + 本タスクの2）

- [ ] **Step 5: check_retrieval.py を両アーム表示へ拡張する**

`RELEVANT` の末尾に回帰ケースを追加する。

```python
    # ハイブリッド検索の回帰ケース（spec 1）。いずれも
    # 「生成AI活用セミナー.pptx スライド11」が出典として期待される。
    # 前者はベクトル4位・距離0.514で足切りされ、後者はベクトル最良が0.523で全滅していた。
    "ファインチューニングについて教えてほしい",
    "ファインチューニング",
```

`main()` の中身を次に差し替える。

```python
def _vector_best(collection, question, session):
    """ベクトル側の最良ヒット。距離と出典を返す。"""
    results = collection.query(
        query_embeddings=[embedder.embed_query(question, session=session)],
        n_results=1,
    )
    hit = Hit(
        text=results["documents"][0][0],
        distance=results["distances"][0][0],
        metadata=results["metadatas"][0][0],
    )
    return hit.distance, hit.citation


def _lexical_best(collection, index, question):
    """BM25側の最良ヒット。スコアと出典を返す。該当なしは (0.0, "—")。"""
    ranked = lexical.search(index, question, limit=1)
    if not ranked:
        return 0.0, "—"
    chunk_id, score = ranked[0]
    found = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    hit = Hit(
        text=found["documents"][0], distance=None, metadata=found["metadatas"][0]
    )
    return score, hit.citation


def _report(collection, index, session, title, questions):
    """1グループ分を表示し、(距離, BM25スコア) の並びを返す。"""
    print(f"\n=== {title} ===")
    measured = []
    for question in questions:
        distance, vector_citation = _vector_best(collection, question, session)
        score, lexical_citation = _lexical_best(collection, index, question)
        measured.append((distance, score))
        print(f"  {question}")
        print(f"      ベクトル {distance:.3f}  → {vector_citation}")
        print(f"      BM25     {score:6.2f}  → {lexical_citation}")
    return measured


def main() -> int:
    embedder.check_ollama()
    collection = store.open_collection(chromadb.PersistentClient(path=str(DB_DIR)))
    print(f"総チャンク数: {collection.count()}")
    index = build_index(collection)
    print(f"BM25インデックス: {index.document_count}文書 / {len(index.postings)}トークン")

    session = embedder.new_session()
    try:
        relevant = _report(collection, index, session, "関連する質問", RELEVANT)
        out_of_domain = _report(collection, index, session, "圏外の質問", OUT_OF_DOMAIN)
        _report(
            collection,
            index,
            session,
            "挨拶（参考値。距離では分離できないため合否判定には使わない）",
            GREETINGS,
        )
        print(
            "  意味的に空な入力はコーパスの重心付近に埋め込まれるため、際どい関連質問"
            "より近傍にヒットすることがある。ingest/prompting.py の「根拠がなければ"
            "答えない」プロンプトがこの入力を受け持つ。"
        )
    finally:
        session.close()

    relevant_max_distance = max(distance for distance, _ in relevant)
    out_of_domain_min_distance = min(distance for distance, _ in out_of_domain)
    out_of_domain_max_bm25 = max(score for _, score in out_of_domain)
    # ベクトル側の足切りを通らない関連質問は、BM25側が拾わなければ救えない。
    rescued = [score for distance, score in relevant if distance > RELEVANCE_THRESHOLD]

    print(f"\n関連の最大距離: {relevant_max_distance:.3f}")
    print(f"圏外の最小距離: {out_of_domain_min_distance:.3f}")
    print(f"圏外の最大BM25: {out_of_domain_max_bm25:.2f}")
    if rescued:
        print(f"BM25で救う必要がある関連質問の最小BM25: {min(rescued):.2f}")

    if not rescued:
        print("ベクトル側だけで全件通っています。BM25_FLOOR は現状の値のままで構いません。")
        return 0
    if out_of_domain_max_bm25 < min(rescued):
        print(f"分離できています。推奨 BM25_FLOOR: {(out_of_domain_max_bm25 + min(rescued)) / 2:.2f}")
        return 0
    print(
        "BM25では分離できていません。spec 16 の縮退構成"
        "（ベクトル側を圏内判定のゲートに使う）へ切り替えてください。"
    )
    return 1
```

import は最終的に次の形になる。`search` はもう使わないので**外す**
（融合済みの検索ではなく、各アームを個別に測るスクリプトになったため）。

```python
from ingest import embedder, lexical, store
from ingest.retrieval import RELEVANCE_THRESHOLD, Hit, build_index
```

- [ ] **Step 6: 実測を走らせて BM25_FLOOR を決める**

Ollamaが起動している必要がある。Streamlitは停止したままにする。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.check_retrieval
```

Expected:
- `総チャンク数: 496`
- 「ファインチューニングについて教えてほしい」のBM25側の出典が
  `生成AI活用セミナー.pptx スライド11`
- 末尾に `推奨 BM25_FLOOR: <値>` が出て、終了コード 0

**この推奨値を控える。Task 7 で定数に入れる。**
`BM25では分離できていません` と出た場合は Task 7 へ進まず、spec 16 の縮退構成を
採るかどうかを人間に確認する。

- [ ] **Step 7: コミット**

```bash
git add ingest/store.py ingest/retrieval.py scripts/check_retrieval.py tests/test_store.py
git commit -m "feat: measure both retrieval arms to pick a BM25 floor

BM25 scores are not normalised - they depend on the corpus IDF - so the floor
has to be measured the same way the distance threshold was, and re-measured
whenever the corpus changes.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: RRF融合とOR足切り

**Files:**
- Modify: `ingest/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `lexical.search`（Task 2）、`retrieval.build_index`（Task 6）、Task 6で確定した `BM25_FLOOR` の値
- Produces:
  - `Hit(text: str, distance: float | None, metadata: dict, bm25_score: float | None = None, rrf_score: float = 0.0)`
  - `search(collection, query, index=None, session=None, threshold=None, bm25_floor=None, n_results=SEARCH_RESULT_COUNT) -> list[Hit]`
  - 定数 `CANDIDATE_COUNT = 30`, `RRF_K = 60`, `BM25_FLOOR`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_retrieval.py` の `_FakeCollection` を差し替える。ChromaDBの `query` は
`ids` も返すため、フェイクもそれに揃える。`get` はBM25のみのヒットの本文取得に使う。

```python
class _FakeCollection:
    def __init__(self, documents, distances, metadatas, ids=None):
        self._ids = ids or [f"id-{n}" for n in range(len(documents))]
        self._documents = documents
        self._metadatas = metadatas
        self._payload = {
            "ids": [self._ids],
            "documents": [documents],
            "distances": [distances],
            "metadatas": [metadatas],
        }

    def count(self):
        return len(self._documents)

    def query(self, query_embeddings, n_results):
        return self._payload

    def get(self, ids=None, include=None):
        # ids 省略は全件。store.all_documents がこの形で呼ぶ。
        rows = (
            list(range(len(self._ids)))
            if ids is None
            else [self._ids.index(chunk_id) for chunk_id in ids]
        )
        return {
            "ids": [self._ids[row] for row in rows],
            "documents": [self._documents[row] for row in rows],
            "metadatas": [self._metadatas[row] for row in rows],
        }
```

既存の `test_far_results_are_dropped` / `test_empty_collection_returns_nothing` /
`test_hits_keep_their_distance` は `index` を渡さない呼び出しなので、
**そのまま後方互換のテストとして機能する**。重複する新テストは足さない。

末尾に追記する。

```python
from ingest import lexical
from ingest.retrieval import BM25_FLOOR, build_index


def _index_over(collection, texts):
    return lexical.build(collection._ids, texts)


def test_a_bm25_hit_is_admitted_even_when_the_vector_arm_cuts_it():
    """今回の症状そのもの。「ファインチューニング」を含むチャンクはDB中2件しか
    無いのに、ベクトル距離は0.523で全滅していた（spec 6.3）。"""
    collection = _FakeCollection(
        ["ファインチューニングとは追加学習である", "無関係な文章"],
        [0.60, 0.62],
        [_meta(), _meta()],
    )
    index = _index_over(collection, ["ファインチューニングとは追加学習である", "無関係な文章"])
    hits = search(
        collection, "ファインチューニング", index=index, threshold=0.5, bm25_floor=0.1
    )
    assert [h.text for h in hits] == ["ファインチューニングとは追加学習である"]
    assert hits[0].distance == 0.60
    assert hits[0].bm25_score > 0


def test_a_vector_hit_is_admitted_even_with_no_lexical_match():
    """言い換えの質問はBM25では引けない。ベクトル側だけで通ること。"""
    collection = _FakeCollection(["近い", "遠い"], [0.10, 0.90], [_meta(), _meta()])
    index = _index_over(collection, ["近い", "遠い"])
    hits = search(collection, "まったく別の語", index=index, threshold=0.5, bm25_floor=0.1)
    assert [h.text for h in hits] == ["近い"]
    assert hits[0].bm25_score is None


def test_a_document_failing_both_arms_is_dropped():
    """圏外の質問。距離が遠く、語も一致しないものは採用しない。"""
    collection = _FakeCollection(["遠い文章"], [0.90], [_meta()])
    index = _index_over(collection, ["遠い文章"])
    assert search(collection, "天気", index=index, threshold=0.5, bm25_floor=0.1) == []


def test_a_weak_bm25_match_below_the_floor_is_dropped():
    """文字bigramは部分一致するため、床を置かないとノイズが素通りする。"""
    collection = _FakeCollection(["遠い文章"], [0.90], [_meta()])
    index = _index_over(collection, ["遠い文章"])
    assert search(collection, "文章", index=index, threshold=0.5, bm25_floor=99.0) == []


def test_results_are_ordered_by_rrf_not_by_distance():
    """両アームで1位のものが、ベクトル単独で1位のものより上に来る。"""
    documents = ["ファインチューニングの解説", "やや近いだけの文章"]
    collection = _FakeCollection(documents, [0.30, 0.20], [_meta(), _meta()])
    index = _index_over(collection, documents)
    hits = search(
        collection, "ファインチューニング", index=index, threshold=0.5, bm25_floor=0.1
    )
    assert hits[0].text == "ファインチューニングの解説"


def test_hits_carry_both_scores():
    documents = ["ファインチューニングの解説"]
    collection = _FakeCollection(documents, [0.30], [_meta()])
    hits = search(
        collection,
        "ファインチューニング",
        index=_index_over(collection, documents),
        threshold=0.5,
        bm25_floor=0.1,
    )
    assert hits[0].distance == 0.30
    assert hits[0].bm25_score > 0
    assert hits[0].rrf_score > 0


def test_n_results_caps_the_output():
    documents = ["ファインチューニング一", "ファインチューニング二", "ファインチューニング三"]
    collection = _FakeCollection(documents, [0.10, 0.11, 0.12], [_meta()] * 3)
    hits = search(
        collection,
        "ファインチューニング",
        index=_index_over(collection, documents),
        threshold=0.5,
        bm25_floor=0.1,
        n_results=2,
    )
    assert len(hits) == 2


def test_the_measured_floor_is_positive():
    """実測で決めた定数が入っていること（Task 6）。"""
    assert BM25_FLOOR > 0


def test_build_index_over_an_empty_collection_is_safe():
    assert build_index(_FakeCollection([], [], [])).document_count == 0
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_retrieval.py -v
```

Expected: FAIL — `ImportError: cannot import name 'BM25_FLOOR' from 'ingest.retrieval'`

- [ ] **Step 3: 最小限の実装を書く**

`ingest/retrieval.py` の定数部に追記する。`<測定値>` はTask 6 Step 6の推奨値に置き換える。

```python
# 各アームから取る候補数。融合してから足切りするため、しきい値付近の
# チャンクが片方のアームで圏外に落ちないよう、採用件数より十分に大きく取る。
CANDIDATE_COUNT = 30

# RRFの定数。順位の逆数を足し合わせるときに上位の影響を和らげる。60は慣用値。
RRF_K = 60

# BM25側の足切り。scripts/check_retrieval.py の実測で決めた（spec 9）。
#   圏外質問の最大BM25 = <測定値>、BM25で救う必要がある関連質問の最小 = <測定値>
# BM25スコアはコーパスのIDFに依存する量で、正規化されていない。
# 資料を入れ替えたら RELEVANCE_THRESHOLD と同様に必ず再実測すること。
BM25_FLOOR = <測定値>
```

`Hit` を差し替える。既存フィールドの後ろに既定値付きで足すので、
`Hit(text=..., distance=..., metadata=...)` という既存の呼び出しはそのまま通る。

```python
@dataclass(frozen=True)
class Hit:
    text: str
    distance: float | None
    metadata: dict
    # BM25だけで当たった場合は distance が None、ベクトルだけで当たった場合は
    # bm25_score が None になる。どちらの経路で拾ったかを画面に出すために持つ。
    bm25_score: float | None = None
    rrf_score: float = 0.0
```

`search` を差し替える。

```python
def _vector_candidates(collection, query, session):
    """(チャンクID → 順位) と、IDをキーにした距離・本文・メタデータ。"""
    results = collection.query(
        query_embeddings=[embed_query(query, session=session)],
        n_results=CANDIDATE_COUNT,
    )
    ids = results["ids"][0]
    ranks = {chunk_id: rank for rank, chunk_id in enumerate(ids, start=1)}
    rows = {
        chunk_id: (distance, text, metadata)
        for chunk_id, distance, text, metadata in zip(
            ids, results["distances"][0], results["documents"][0], results["metadatas"][0]
        )
    }
    return ranks, rows


def search(
    collection,
    query,
    index=None,
    session=None,
    threshold=None,
    bm25_floor=None,
    n_results=SEARCH_RESULT_COUNT,
):
    """ベクトルとBM25を融合して検索する。

    index を渡さないとベクトル単独で動く。BM25を必要としない呼び出しと
    既存のテストのために残してある。

    並べ替えはRRF、採用可否は各アームの生の指標によるOR条件で行う。cosine距離と
    BM25スコアは互いに正規化できないため重み付き和は意味を持たず、順位だけを
    使うRRFがこれを回避する。一方でRRFスコアは順位のみに依存し、圏外の質問でも
    1位は必ず 1/(RRF_K+1) を得るため、足切りには使えない。
    """
    if collection.count() == 0:
        return []
    distance_limit = threshold if threshold is not None else RELEVANCE_THRESHOLD
    score_floor = bm25_floor if bm25_floor is not None else BM25_FLOOR

    vector_ranks, vector_rows = _vector_candidates(collection, query, session)
    lexical_ranked = lexical.search(index, query, CANDIDATE_COUNT) if index else []
    lexical_scores = dict(lexical_ranked)
    lexical_ranks = {
        chunk_id: rank for rank, (chunk_id, _) in enumerate(lexical_ranked, start=1)
    }

    # BM25だけで当たったチャンクは本文とメタデータを持っていないので取りに行く。
    missing = [chunk_id for chunk_id in lexical_scores if chunk_id not in vector_rows]
    if missing:
        found = collection.get(ids=missing, include=["documents", "metadatas"])
        for chunk_id, text, metadata in zip(
            found["ids"], found["documents"], found["metadatas"]
        ):
            vector_rows[chunk_id] = (None, text, metadata)

    hits = []
    for chunk_id in set(vector_ranks) | set(lexical_ranks):
        distance, text, metadata = vector_rows[chunk_id]
        score = lexical_scores.get(chunk_id)
        near = distance is not None and distance <= distance_limit
        matched = score is not None and score >= score_floor
        if not text or not (near or matched):
            continue
        rrf = 0.0
        if chunk_id in vector_ranks:
            rrf += 1 / (RRF_K + vector_ranks[chunk_id])
        if chunk_id in lexical_ranks:
            rrf += 1 / (RRF_K + lexical_ranks[chunk_id])
        hits.append(
            Hit(
                text=text,
                distance=distance,
                metadata=metadata,
                bm25_score=score,
                rrf_score=rrf,
            )
        )
    # 同点はベクトル距離の昇順、次にBM25スコアの降順で決める。並びを決定的に
    # しないと、同じ質問で根拠の順序が変わって再現しなくなる。
    hits.sort(
        key=lambda hit: (
            -hit.rrf_score,
            hit.distance if hit.distance is not None else 99.0,
            -(hit.bm25_score or 0.0),
        )
    )
    return hits[:n_results]
```

- [ ] **Step 4: テストを実行して成功を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest -q
```

Expected: PASS（250件 = 241 + 本タスクの9）

- [ ] **Step 5: コミット**

```bash
git add ingest/retrieval.py tests/test_retrieval.py
git commit -m "feat: fuse vector and BM25 results with RRF and an OR cutoff

Cosine distance and BM25 scores cannot be normalised against each other, so
ordering uses ranks alone. The RRF score cannot gate relevance either - an
out-of-domain query still scores 1/(k+1) at rank one - so each arm keeps its
own floor and a hit needs to clear only one of them.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: チャット画面に結線する

**Files:**
- Modify: `ingest/prompting.py`
- Modify: `rag_chat_app.py`
- Test: `tests/test_prompting.py`

**Interfaces:**
- Consumes: `retrieval.build_index`, `retrieval.search(..., index=...)`, `Hit.bm25_score`
- Produces: `prompting.format_hit_caption(hit) -> str`

**置き場所について:** 出典キャプションの整形は `rag_chat_app.py` ではなく
`ingest/prompting.py` に置く。`rag_chat_app.py` はimportしただけでスクリプト
全体が走り本番の `chroma_db` を開いてしまうため、UIから呼ぶがUIに依存しない
文字列整形はこのモジュールへ分離する、というのが既存の作法である
（`ingest/prompting.py` の冒頭コメント）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_prompting.py` の末尾に追記する。

```python
from ingest.prompting import format_hit_caption
from ingest.retrieval import Hit


def _slide_hit(distance, bm25_score):
    return Hit(
        text="本文",
        distance=distance,
        metadata={
            "source": "生成AI活用セミナー.pptx",
            "location_type": "slide",
            "location": 11,
            "ocr": False,
            "heading": "",
        },
        bm25_score=bm25_score,
    )


def test_caption_shows_both_scores():
    caption = format_hit_caption(_slide_hit(0.312, 4.25))
    assert "生成AI活用セミナー.pptx スライド11" in caption
    assert "0.312" in caption
    assert "4.25" in caption


def test_caption_handles_a_hit_found_only_by_bm25():
    """BM25だけで当たったヒットは距離を持たない。'None' を画面に出さない。"""
    caption = format_hit_caption(_slide_hit(None, 4.25))
    assert "None" not in caption
    assert "4.25" in caption


def test_caption_handles_a_hit_found_only_by_the_vector_arm():
    """言い換えの質問は語が一致しない。BM25側が空でも壊れないこと。"""
    caption = format_hit_caption(_slide_hit(0.312, None))
    assert "None" not in caption
    assert "0.312" in caption
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest tests/test_prompting.py -v
```

Expected: FAIL — `ImportError: cannot import name 'format_hit_caption' from 'ingest.prompting'`

- [ ] **Step 3: 最小限の実装を書く**

`rag_chat_app.py` の import を差し替える。`RELEVANCE_THRESHOLD` はここでは
使わなくなる（`format_hit_caption` が持つ）ので**外す**。

```python
from ingest.prompting import (
    build_catalog_prompt,
    build_prompt,
    format_hit_caption,
    format_report,
)
from ingest.retrieval import build_index, contextual_query, search
```

`get_schema` の下にインデックス構築を追加する。

```python
@st.cache_resource
def get_index(_collection, chunk_count):
    """BM25インデックスをDBから組む。

    永続化しないため起動のたびに作り直す。chunk_count を引数に取るのは、
    差分取り込みでチャンク数が変わったときにキャッシュを無効化するためである。
    先頭のアンダースコアはStreamlitにこの引数をハッシュさせないための目印で、
    ChromaDBのコレクションはハッシュ化できない。
    """
    return build_index(_collection)
```

`ingest/prompting.py` の末尾に整形関数を追加する。

```python
def format_hit_caption(hit) -> str:
    """出典と、どちらの経路で拾ったかを1行で示す。

    経路を出すのは、しきい値を調整するときにどちらのアームが効いたのかを
    画面から読み取れるようにするためである。両方のしきい値が実測で決まって
    いるので（spec 9）、その根拠を利用者にも見せる。

    BM25だけで当たったヒットは距離を持たず、ベクトルだけで当たったヒットは
    スコアを持たない。素直に書式化すると 'None' が画面に出る。
    """
    # 循環importを避けるためここで読む。retrieval は prompting を参照しない。
    from ingest.retrieval import BM25_FLOOR, RELEVANCE_THRESHOLD

    distance = (
        f"cosine距離 {hit.distance:.3f}（しきい値 {RELEVANCE_THRESHOLD}）"
        if hit.distance is not None
        else "cosine距離 圏外"
    )
    score = (
        f"BM25 {hit.bm25_score:.2f}（しきい値 {BM25_FLOOR}）"
        if hit.bm25_score is not None
        else "BM25 一致なし"
    )
    return f"{hit.citation} ／ {distance} ／ {score}"
```

`rag_chat_app.py` の `render_hits` を差し替える。

```python
def render_hits(hits):
    if not hits:
        return
    with st.expander(f"参考にした情報（{len(hits)}件）"):
        for hit in hits:
            st.caption(format_hit_caption(hit))
            st.write(hit.text)
```

`collection = get_collection(DB_DIR)` の直後に追加する。

```python
index = get_index(collection, collection.count())
```

検索の呼び出しを差し替える（`hits = search(collection, query)` の行）。

```python
            hits = search(collection, query, index=index)
```

差分取り込みボタンの `st.rerun()` の直前に追加する。

```python
        # 取り込んだ資料がベクトル検索でだけ引ける状態になるのを防ぐ。
        get_index.clear()
```

- [ ] **Step 4: テストを実行して成功を確認する**

```powershell
.\myvenv313\Scripts\python.exe -m pytest -q
```

Expected: PASS（253件 = 250 + 本タスクの3）

- [ ] **Step 5: 画面を目視で確認する**

```powershell
.\myvenv313\Scripts\python.exe -m streamlit run rag_chat_app.py
```

「ファインチューニングについて教えてほしい」と入力し、次を確認する。

- 「参考にした情報」に `生成AI活用セミナー.pptx スライド11` が含まれる
- 各行に cosine距離とBM25スコアの両方が出ている
- 回答が「言及されていません」ではなく、追加学習によるモデル再生成の説明になっている

**確認後、必ずStreamlitを停止する。** 起動したままだと以降のDB操作で
HNSWインデックスを壊す恐れがある。

- [ ] **Step 6: コミット**

```bash
git add ingest/prompting.py rag_chat_app.py tests/test_prompting.py
git commit -m "feat: search with both arms and show how each hit was found

The index is rebuilt from the DB at startup and cleared after an incremental
ingest; without the clear, freshly ingested documents would be reachable by
vector search only.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: 受け入れ確認とドキュメント更新

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: 全タスクの成果
- Produces: なし

- [ ] **Step 1: テスト全体を回す**

```powershell
.\myvenv313\Scripts\python.exe -m pytest -q
```

Expected: 253件 PASS、1件 deselected、失敗ゼロ

- [ ] **Step 2: しきい値の分離を再確認する**

Streamlitが停止していることを確認してから実行する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.check_retrieval
```

Expected: 終了コード 0。`分離できています` が出ること

- [ ] **Step 3: spec 第1節の受け入れ基準を確認する**

```powershell
.\myvenv313\Scripts\python.exe -c "import chromadb; from ingest import embedder, store; from ingest.retrieval import build_index, search; from scripts.ingest_source import DB_DIR; c=store.open_collection(chromadb.PersistentClient(path=str(DB_DIR))); i=build_index(c); s=embedder.new_session(); [print(q, '->', [h.citation for h in search(c, q, index=i, session=s)]) for q in ['ファインチューニングについて教えてほしい','ファインチューニング','今日の東京の天気を教えてください']]; s.close()"
```

Expected:
- 前者2つの出力に `生成AI活用セミナー.pptx スライド11` が含まれる
- 「今日の東京の天気」は `[]`（空）

3つ目が空にならない場合、`BM25_FLOOR` が低すぎる。Task 6 の実測値を見直す。

- [ ] **Step 4: READMEを更新する**

次を反映する。

- 総チャンク数を 460 → 496 に
- 検索がハイブリッド（ベクトル + BM25 / RRF融合）になったこと
- しきい値が2つ（`RELEVANCE_THRESHOLD` と `BM25_FLOOR`）になり、資料を
  入れ替えたら `scripts/check_retrieval.py` で両方を再実測する必要があること
- PPTXが1スライド複数チャンクになったこと

- [ ] **Step 5: コミット**

```bash
git add README.md
git commit -m "docs: describe hybrid retrieval and the two measured thresholds

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: 完了を報告する**

次を人間へ伝える。

- 「ファインチューニングについて教えてほしい」で スライド11 が根拠に入るようになったこと（実測の出典を添える）
- テスト件数と結果
- 確定した `BM25_FLOOR` の値と、その根拠になった実測値
- DB総チャンク数の変化（460 → 496）

`superpowers:finishing-a-development-branch` でマージ方針を決める。
