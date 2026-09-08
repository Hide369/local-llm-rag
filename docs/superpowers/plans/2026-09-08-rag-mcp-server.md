# RAG MCP サーバ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 取り込み済みの社内資料を、Codex から `search_documents` ツールで引けるようにする。

**Architecture:** `scripts/rag_mcp_server.py` に stdio MCP サーバを1本置き、`ingest/retrieval.py` の `search()` をラップして Markdown を返す。常駐し、`revision()` で BM25 索引の鮮度を見る。リランカーは初回検索時に遅延ロードする。`ingest/` と取り込み側は一切変更しない。

**Tech Stack:** Python 3.13、`mcp` 2.2.0（stdio）、pytest、SQLite + numpy のベクトルストア、Ollama（bge-m3）

**Spec:** `docs/superpowers/specs/2026-09-05-rag-mcp-server-design.md`（改訂版、コミット `72aedbe`）

## Global Constraints

- **作業は専用ワークツリー `.worktrees/rag-mcp-server` で行う。** 作業前に `git rev-parse --abbrev-ref HEAD` が `feat/rag-mcp-server` であることを確認する。本セッションで作業ツリーが別ブランチへ移る事故が2回起きている。
- **Python の起動は `../../myvenv313/Scripts/python.exe`**（ワークツリーからの相対パス）。仮想環境はリポジトリ本体にあり、ワークツリー側には無い。
- **スクリプトは `python -m scripts.X` で起動する。** `python scripts/X.py` は `ModuleNotFoundError: No module named 'ingest'` で落ちる。`sys.path` を足して回避しないこと。
- **テストは `-m pytest`。** 開始時点の件数は最初のタスクで実測して記録する。
- **`git add -A` / `git add .` は禁止。** 触ったファイルを個別に指定する。
- **`ingest/` 配下と `scripts/ingest_source.py` は変更しない**（設計書4.2節）。サーバは `retrieval.search()` を呼ぶだけである。
- **`vector_store.sqlite3` に書き込まない。** テストはインメモリのストアを使う。
- **MCP SDK の API は実測で確認済み。** `mcp` 2.2.0 で `from mcp.server import MCPServer`。**`FastMCP` は存在しない**（`ModuleNotFoundError`）。`@mcp.tool()` は元の関数をそのまま返すため、テストから直接呼べる。`mcp.run()` の既定は stdio。
- コミットはコンベンショナルコミット形式、英語、末尾に `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。
- 数字を書くときは実測するか、いつ・どの規模で測ったかを添える。測っていない数字を実測済みに見せない。

---

### Task 1: 依存の追加と、整形関数の骨格

**Files:**
- Create: `scripts/rag_mcp_server.py`
- Create: `tests/test_rag_mcp_server.py`
- Modify: `requirements.txt`
- Modify: `docs/依存関係一覧.md`

**Interfaces:**
- Consumes: `ingest.retrieval.Hit`、`ingest.prompting.format_hit_caption`
- Produces: `format_results(hits: list) -> str` — `Hit` の並びから設計書4.5節の Markdown を組む。0件のときは4.6節の文言を返す

このタスクは整形だけを扱う。検索もサーバも次のタスクで足す。整形を先に切り出すのは、**サーバを起動せずにテストできる唯一の部分**だからである。

- [ ] **Step 1: 現状のテスト件数を記録する**

Run: `../../myvenv313/Scripts/python.exe -m pytest -q`

出力の末尾（`NNN passed, N deselected`）を報告に控える。以降のタスクはこの値を基準にする。

- [ ] **Step 2: `mcp` を入れて実測バージョンを固定する**

```bash
../../myvenv313/Scripts/python.exe -m pip install mcp
../../myvenv313/Scripts/python.exe -c "import importlib.metadata as m; print(m.version('mcp'))"
```

**注意: この依存は12パッケージを連れてくる**（`cryptography`、`PyJWT`、`opentelemetry-api`、`sse-starlette`、`truststore` など）。`requirements.txt` の方針は「直接importするパッケージだけを固定する」なので、**`mcp` の1行だけを足す。** 推移的な依存は書かない。

`requirements.txt` の末尾に、既存の分類コメントに倣って次を足す。

```
# コーディングエージェント向けMCPサーバ
mcp==2.2.0
```

（バージョンは Step 2 で実測した値にすること。上は2026-09-08時点の実測値。）

`docs/依存関係一覧.md` の表にも1行足す。用途は「Codex から社内資料を引く stdio MCP サーバ（`scripts/rag_mcp_server.py`）」、使用箇所は `scripts/rag_mcp_server.py`。

- [ ] **Step 3: 失敗するテストを書く**

`tests/test_rag_mcp_server.py` を新規作成する。

```python
"""MCPサーバの整形。

サーバを起動せずに検証する。@mcp.tool() は元の関数をそのまま返すため、
ツール関数もモジュールから直接呼べる。
"""
from ingest.retrieval import Hit
from scripts.rag_mcp_server import format_results


def _hit(text="本文です。", distance=0.413, bm25=45.76, rerank=1.9, occurrences=None):
    return Hit(
        text=text,
        distance=distance,
        occurrences=occurrences
        or [
            {"source": "セミナー資料/CNN画像認識セミナー.pptx",
             "location_type": "slide", "location": 25},
        ],
        bm25_score=bm25,
        rerank_score=rerank,
    )


def test_no_hits_returns_the_instruction_not_an_empty_string():
    """0件のときこそ空を返してはいけない。

    エージェントは根拠が無いときに自分の知識で答えにいく。空文字や空配列は
    「探したが無かった」ではなく「何も起きなかった」と読まれる（設計書4.6節）。
    """
    text = format_results([])
    assert text.strip()
    assert "見つかりませんでした" in text
    assert "推測で答えず" in text


def test_every_source_is_listed_not_rolled_up():
    """出典は全件並べる。

    Hit.citation は「ほか6資料」と丸めるが、エージェントはどのファイルを
    開けばよいか分からなくなる（設計書4.5節）。
    """
    hit = _hit(occurrences=[
        {"source": "a.pptx", "location_type": "slide", "location": 25},
        {"source": "b.pptx", "location_type": "slide", "location": 22},
        {"source": "c.pdf", "location_type": "page", "location": 12},
    ])
    text = format_results([hit])
    assert "a.pptx" in text
    assert "b.pptx" in text
    assert "c.pdf" in text
    assert "ほか" not in text


def test_the_caption_comes_from_prompting_not_a_reimplementation():
    """整形を再実装していないことの確認。

    位置種別（ページ・スライド・見出し）の書式は Hit と prompting が持つ。
    ここで組み直すと、画面とMCPで出典の見え方が食い違う。
    """
    from ingest.prompting import format_hit_caption

    hit = _hit()
    text = format_results([hit])
    caption = format_hit_caption(hit)
    # caption は「出典 ／ 距離 ／ BM25 ／ Reranker」の1行。
    # 出典部分は別に並べるため、スコア部分が本文に現れることを見る。
    scores = caption.split(" ／ ", 1)[1]
    assert scores in text


def test_the_body_text_is_included():
    text = format_results([_hit(text="第38条 年次有給休暇は…")])
    assert "第38条 年次有給休暇は…" in text


def test_the_caution_is_appended_to_the_results():
    """歯止めをツール結果の末尾に置く（設計書4.6節）。

    build_prompt が持っていた2つの歯止め（無関係な根拠を使わない、資料にない
    主体を補わない）は、チャンクを返す方式では失われる。AGENTS.md に恒久的な
    規範として書くのに加えて、結果そのものにも添える。AGENTS.md を読んでいない
    経路でも歯止めが効くようにするためである。
    """
    text = format_results([_hit()])
    assert "関連しない場合は根拠に使わず" in text
    assert "資料に書かれていない主体を補わないでください" in text


def test_hits_are_numbered_in_order():
    text = format_results([_hit(text="いち"), _hit(text="に")])
    assert text.index("[1]") < text.index("いち")
    assert text.index("[2]") < text.index("に")
    assert text.index("いち") < text.index("[2]")
```

- [ ] **Step 4: 落ちることを確認する**

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.rag_mcp_server'`

- [ ] **Step 5: 実装する**

`scripts/rag_mcp_server.py` を新規作成する。このタスクでは整形だけを書く。

```python
"""Codex から社内資料を引く stdio MCP サーバ。

取り込み済みのDBを検索し、根拠となる原文をそのまま返す。回答文を作らないのは、
コーディングエージェントに要るのが判断済みの答えではなく、コードや設定へ統合
できる原文だからである（設計書3.2節）。

サーバは常駐し、リクエストのたびに revision() を読んでBM25索引の鮮度を見る。
取り込み中でもロックは取らない。SQLiteの読み手は書き込み中も一貫した
スナップショットを得るため（設計書5節、実測で待ち0ms）。
"""
from ingest.prompting import format_hit_caption

# 0件のときに返す文言。空文字や空配列を返してはならない。エージェントは根拠が
# 無いときこそ自分の知識で答えにいくため、「探したが無かった」ことを明示的に
# 伝える必要がある（設計書4.6節）。
_NO_HITS = (
    "社内資料を検索しましたが、この質問に関連する記述は見つかりませんでした。\n"
    "推測で答えず、社内資料からは回答できない旨を伝えてください。"
)

# 結果の末尾に添える歯止め。build_prompt が持っていたものを引き継ぐ（設計書4.6節）。
# しきい値0.50は関連度の高さまでは保証しないため、距離が閾値内であることを
# 関連性の根拠にしてはならない。AGENTS.md にも同じ規範を書くが、そちらを
# 読んでいない経路でも効くよう、結果自体にも添える。
_CAUTION = (
    "---\n"
    "上記は検索結果です。質問に関連しない場合は根拠に使わず、"
    "資料からは回答できない旨を伝えてください（距離が閾値内であることは"
    "関連性を保証しません）。資料に書かれていない主体を補わないでください。"
)


def format_results(hits: list) -> str:
    """Hit の並びを Markdown に組む。

    出典は all_citations() で全件並べる。画面表示に使う citation は
    「ほか6資料」と丸めるが、エージェントは出典ファイルを直接開くため、
    丸めるとその経路が塞がる（設計書4.5節）。
    """
    if not hits:
        return _NO_HITS

    blocks = [f"社内資料から {len(hits)} 件が見つかりました。"]
    for number, hit in enumerate(hits, start=1):
        # スコア部分だけを取る。出典は下で全件並べるため重複させない。
        scores = format_hit_caption(hit).split(" ／ ", 1)[1]
        citations = "\n".join(f"- {one}" for one in hit.all_citations())
        blocks.append(f"## [{number}] {scores}\n出典:\n{citations}\n\n{hit.text}")
    blocks.append(_CAUTION)
    return "\n\n".join(blocks)
```

- [ ] **Step 6: 通ることを確認する**

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q`
Expected: PASS（6件）

- [ ] **Step 7: 出典を丸めるとテストが赤くなることを確かめる**

`format_results` の `hit.all_citations()` を一時的に `[hit.citation]` に書き換えて実行する。

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q`
Expected: FAIL — `test_every_source_is_listed_not_rolled_up`

**確認できたら元に戻し、`git diff scripts/rag_mcp_server.py` で戻ったことを確かめる。**

- [ ] **Step 8: コミット**

```bash
git add scripts/rag_mcp_server.py tests/test_rag_mcp_server.py requirements.txt "docs/依存関係一覧.md"
git commit -m "feat: format search hits for an agent to read

Lists every citation rather than the rolled-up form the UI uses. An agent
opens the source files it is given; 'and 6 others' names none of them.

Returning the no-hits instruction instead of an empty string matters for
the same reason build_prompt has a zero-hit branch: an agent with no
grounds falls back on its own knowledge.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: 常駐する状態と鮮度判定

**Files:**
- Modify: `scripts/rag_mcp_server.py`
- Test: `tests/test_rag_mcp_server.py`

**Interfaces:**
- Consumes: `format_results(hits) -> str`（Task 1）
- Produces: `_State` — `store` / `index` / `index_revision` / `reranker_loaded` を持つモジュール内の状態。`_get_index(state, collection)` が `revision()` を見て必要なときだけ `build_index()` を呼ぶ

サーバは常駐する。理由はDBを開くのが重いからではなく（実測 0.40ms）、**BM25索引の構築が57msかかる**からである（実測、本文512種）。エージェントは1タスク中に何度も検索するため、毎回組み直すと積み上がる。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rag_mcp_server.py` の末尾に足す。

```python
class _FakeCollection:
    """revision() と count() だけを持つ最小のストア。"""

    def __init__(self, revision=1):
        self._revision = revision

    def revision(self):
        return self._revision

    def count(self):
        return 512

    def bump(self):
        self._revision += 1


def test_the_index_is_built_once_and_reused(monkeypatch):
    """revision が変わらない限り組み直さない。

    判定を誤って常に真にすると、毎リクエストで57msの索引構築が走る。
    例外は出ず、遅くなるだけなので、テストでしか捕まえられない。
    """
    from scripts import rag_mcp_server

    calls = []
    monkeypatch.setattr(
        rag_mcp_server, "build_index", lambda collection: calls.append(1) or "索引"
    )
    state = rag_mcp_server._State()
    collection = _FakeCollection()

    assert rag_mcp_server._get_index(state, collection) == "索引"
    assert rag_mcp_server._get_index(state, collection) == "索引"
    assert rag_mcp_server._get_index(state, collection) == "索引"
    assert len(calls) == 1, "revisionが変わっていないのに組み直している"


def test_the_index_is_rebuilt_when_the_revision_changes(monkeypatch):
    """取り込みが走ったら組み直す。

    revision は書き込みトランザクションの内側で加算される。チャンク数を鍵に
    すると「同数の差し替え」を取りこぼし、消えた旧チャンクIDを持ったままの
    索引が理由の説明なくヒットを落とす（設計書6節）。
    """
    from scripts import rag_mcp_server

    calls = []
    monkeypatch.setattr(
        rag_mcp_server, "build_index", lambda collection: calls.append(1) or "索引"
    )
    state = rag_mcp_server._State()
    collection = _FakeCollection()

    rag_mcp_server._get_index(state, collection)
    collection.bump()
    rag_mcp_server._get_index(state, collection)

    assert len(calls) == 2
```

- [ ] **Step 2: 落ちることを確認する**

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q -k index`
Expected: FAIL — `AttributeError: module 'scripts.rag_mcp_server' has no attribute '_State'`

- [ ] **Step 3: 実装する**

`scripts/rag_mcp_server.py` の import に足す。

```python
from dataclasses import dataclass

from ingest.prompting import format_hit_caption
from ingest.retrieval import build_index
```

`format_results` の下に足す。

```python
@dataclass
class _State:
    """プロセスの生存期間だけ持つ状態。

    サーバは Codex がセッションごとに起こす子プロセスであり、常駐する。
    常駐する理由はDBを開くのが重いからではない（実測0.40ms）。BM25索引の
    構築が57msかかり、エージェントは1タスク中に何度も検索するためである
    （2026-09-08、570出現・本文512種の実測）。
    """

    index: object | None = None
    index_revision: int | None = None


def _get_index(state: _State, collection):
    """BM25索引を返す。revision が変わっていれば組み直す。

    revision は replace_source() の書き込みトランザクションの内側で加算される
    ため、これだけを見れば鮮度を判定できる。読むコストは0.02msで、57msの
    組み直しを避けられるかの判定には十分に軽い。
    """
    revision = collection.revision()
    if state.index is None or revision != state.index_revision:
        state.index = build_index(collection)
        state.index_revision = revision
    return state.index
```

- [ ] **Step 4: 通ることを確認する**

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q`
Expected: PASS（8件）

- [ ] **Step 5: 判定を壊すとテストが赤くなることを確かめる**

`_get_index` の条件を `if True:` に書き換えて実行する。

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q -k index`
Expected: FAIL — `test_the_index_is_built_once_and_reused`（`assert 3 == 1`）

次に条件を `if state.index is None:` に書き換える（revision を見ない）。

Expected: FAIL — `test_the_index_is_rebuilt_when_the_revision_changes`

**両方確認できたら元に戻し、`git diff` で戻ったことを確かめる。**

- [ ] **Step 6: コミット**

```bash
git add scripts/rag_mcp_server.py tests/test_rag_mcp_server.py
git commit -m "feat: rebuild the BM25 index only when the store's revision moves

Staying resident is about the 57ms index build, not about opening the
store, which measures 0.40ms. revision() costs 0.02ms and moves inside
the write transaction, so it catches a same-count replacement that a
chunk count would miss.

Both directions are pinned by tests: always rebuilding and never
rebuilding are each silent failures that only cost time or serve stale
hits.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: 検索ツールと遅延ロード

**Files:**
- Modify: `scripts/rag_mcp_server.py`
- Test: `tests/test_rag_mcp_server.py`

**Interfaces:**
- Consumes: `format_results(hits)`（Task 1）、`_State` / `_get_index(state, collection)`（Task 2）
- Produces: `search_documents(query: str, n_results: int = 4) -> str` — MCP ツール本体。`@mcp.tool()` は元の関数を返すのでテストから直接呼べる

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rag_mcp_server.py` の末尾に足す。

```python
def test_the_reranker_is_not_loaded_until_the_first_search(monkeypatch):
    """検索しないセッションはリランカーを払わない。

    Codex はセッション開始時にサーバを起こす。起動時にロードすると、検索を
    1度もしないセッションが3.3秒と約570MBを払う（実測）。常にロードするよう
    壊しても例外は出ず、遅くなるだけなのでテストでしか捕まえられない。

    spy を仕掛けてから reload するのが要点である。import 済みのモジュールに
    後から spy を入れて表明しても、起動時ロードは既に終わっており、壊れた実装
    でもテストが通ってしまう（隔離環境で再現済み）。
    """
    import importlib

    from ingest import reranker
    from scripts import rag_mcp_server

    loaded = []
    monkeypatch.setattr(reranker, "check_reranker", lambda: loaded.append(1))
    importlib.reload(rag_mcp_server)

    assert loaded == [], "検索していないのにリランカーをロードしている"


def test_search_returns_the_no_hits_text_when_nothing_is_in_range(monkeypatch):
    """圏外なら0件が返り、その旨の文言になる。"""
    from scripts import rag_mcp_server

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", lambda *a, **k: [])

    text = rag_mcp_server.search_documents("圏外の質問")
    assert "見つかりませんでした" in text


def test_search_passes_n_results_through(monkeypatch):
    """n_results がそのまま search() に渡る。"""
    from scripts import rag_mcp_server

    seen = {}

    def fake_search(collection, query, **kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", fake_search)

    rag_mcp_server.search_documents("質問", n_results=2)
    assert seen["n_results"] == 2


def test_an_empty_store_says_the_ingest_has_not_run(monkeypatch):
    """0チャンクは「見つかりませんでした」ではない（設計書7節）。

    取り込みを忘れているのか、資料に無いのかを取り違えると、利用者は
    延々と質問を言い換えることになる。
    """
    from scripts import rag_mcp_server

    class _Empty(_FakeCollection):
        def count(self):
            return 0

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _Empty())

    text = rag_mcp_server.search_documents("質問")
    assert "取り込みが未実行" in text


def test_ollama_failure_is_returned_as_its_own_message(monkeypatch):
    """Ollama 未疎通の文言をそのまま返す。

    サーバは起動時に疎通確認しない。Codex がセッション開始時にサーバを起こす
    ため、そこで失敗させると Ollama を使わない作業まで巻き添えになる
    （設計書4.4節）。確認は最初の検索時に行う。
    """
    from ingest.embedder import EmbeddingError
    from scripts import rag_mcp_server

    def boom(*a, **k):
        raise EmbeddingError("Ollamaに接続できません（http://localhost:11434）")

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", boom)

    text = rag_mcp_server.search_documents("質問")
    assert "Ollamaに接続できません" in text
```

- [ ] **Step 2: 落ちることを確認する**

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q -k "reranker or search or ollama"`
Expected: FAIL — `AttributeError: module 'scripts.rag_mcp_server' has no attribute 'reranker'`

- [ ] **Step 3: 実装する**

import に足す。

```python
from pathlib import Path

from mcp.server import MCPServer

from ingest import embedder, reranker
from ingest.retrieval import SEARCH_RESULT_COUNT, build_index, search
from ingest.store import open_store
```

**`FastMCP` ではない。** `mcp` 2.2.0 に `mcp.server.fastmcp` は存在しない（実測）。

モジュール末尾に足す。

```python
# DBのパスは rag_chat_app.py・scripts/ingest_source.py と同じ場所を指す。
# 引数や環境変数で受け取らないのは、3か所で食い違うと空のDBを黙って検索する
# 状態が生まれるためである（設計書4.2節）。
_DB_PATH = Path(__file__).resolve().parent.parent / "vector_store.sqlite3"

mcp = MCPServer("local_docs")
_state = _State()
_reranker_ready = False


def _open():
    return open_store(str(_DB_PATH))


def _ensure_reranker():
    """初回検索時にだけリランカーを用意する。

    起動時にロードしない。Codex はセッション開始時にサーバを起こすため、
    検索を1度もしないセッションが3.3秒と約570MBを払うことになる（実測）。
    代償は初回検索が4.75秒になることで、2回目以降は0.72秒である。

    取得に失敗しても検索は続ける。既存の劣化運転方針に揃える（設計書7節）。
    """
    global _reranker_ready
    if _reranker_ready:
        return reranker.rerank
    try:
        reranker.check_reranker()
    except reranker.RerankError:
        return None
    _reranker_ready = True
    return reranker.rerank


@mcp.tool()
def search_documents(query: str, n_results: int = SEARCH_RESULT_COUNT) -> str:
    """社内資料を検索し、根拠となる原文を出典つきで返す。

    Args:
        query: 検索したい内容。自然文で書く。
        n_results: 返すチャンク数。
    """
    try:
        collection = _open()
        if collection.count() == 0:
            # 「関連する記述が無い」と取り違えさせない。取り込みを忘れている
            # 利用者は、質問を言い換え続けても永遠に0件を得る（設計書7節）。
            return (
                "ベクトルDBが空です。取り込みが未実行の可能性があります。"
                "python -m scripts.ingest_source を実行してください。"
            )
        index = _get_index(_state, collection)
        hits = search(
            collection,
            query,
            index=index,
            n_results=n_results,
            rerank=_ensure_reranker(),
        )
    except Exception as error:
        # 文言をそのまま返す。embedder は「ollama pull bge-m3 を実行して
        # ください」のように、利用者が次に何をすればよいかを書いている。
        return str(error)
    return format_results(hits)


if __name__ == "__main__":
    mcp.run()
```

> **訂正（2026-09-08）:** 上のコード片にある「初回4.75秒・2回目以降0.72秒」は
> 再現しなかった。同一CPU（i5-1240P / Windows 11、570出現・本文512種）での
> 実測は初回 6.99 秒、2回目以降 3.4〜3.5 秒である。確定値は設計書
> `docs/superpowers/specs/2026-09-05-rag-mcp-server-design.md` 4.4節の表にある。
> この計画書は実行時点の記録として残すため、コード片自体は書き換えていない。


- [ ] **Step 4: 通ることを確認する**

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q`
Expected: PASS（13件）

- [ ] **Step 5: 遅延ロードを壊すとテストが赤くなることを確かめる**

モジュール末尾（`if __name__` の直前）に `reranker.check_reranker()` を一時的に足す。これは「起動時にロードする」実装を模したものである。テストは spy を仕掛けてから `importlib.reload` するので、この行が spy を通って落ちる。

Run: `../../myvenv313/Scripts/python.exe -m pytest tests/test_rag_mcp_server.py -q -k reranker`
Expected: FAIL — `test_the_reranker_is_not_loaded_until_the_first_search`

**確認できたら元に戻し、`git diff` で戻ったことを確かめる。**

- [ ] **Step 6: サーバが実際に起動することを確かめる**

テストはツール関数を直接呼ぶだけで、MCP の配線は通っていない。**1度だけ実物を起動して、配線が生きていることを確認する。**

```bash
cd ../..
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' | ./myvenv313/Scripts/python.exe -m scripts.rag_mcp_server
```

Expected: JSON-RPC の応答が標準出力に出て、`"serverInfo"` に `local_docs` が含まれる。エラーで即座に終了しないこと。

**この確認はワークツリーではなくリポジトリ本体で行う**（`vector_store.sqlite3` があるのは本体側で、`cwd` の解決を実物と揃えるため）。確認後は `cd` を戻す。応答が得られない場合は、その出力をそのまま報告すること。

- [ ] **Step 7: コミット**

```bash
git add scripts/rag_mcp_server.py tests/test_rag_mcp_server.py
git commit -m "feat: expose search_documents over stdio

The reranker loads on the first search, not at import. Codex starts this
server for every session, so loading at import charges 3.3s and ~570MB to
sessions that never search. A test pins that, because loading eagerly
raises nothing - it only costs time.

Errors are returned as their own text. embedder already writes messages
that say what to do next, such as running ollama pull bge-m3.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: 設定手順と規範

**Files:**
- Create: `docs/mcp-server.md`
- Modify: `AGENTS.md`
- Modify: `docs/処理箇所マップ.md`

**Interfaces:**
- Consumes: すべて
- Produces: なし

- [ ] **Step 1: `docs/mcp-server.md` を書く**

導入先向けの設定手順。設計書8.1節と9節の内容を、読んで手を動かせる形にする。含めるもの:

- `~/.codex/config.toml` への3サーバの登録（設計書8.1節のTOMLをそのまま）
- **`cwd` の指定が必須である理由**（`-m` 起動でないと `from ingest import ...` が `ModuleNotFoundError` になる）
- `ollama pull bge-m3` が必須であること。欠くと検索が一切成立しないこと
- context7 の API キーは `env_http_headers` で環境変数から取ること。`config.toml` に直接書かないこと
- 動作確認の手順（Codex から「社内資料で〜を調べて」と頼み、出典が返ることを見る）

- [ ] **Step 2: `AGENTS.md` に節を追記する**

**このファイルは既に存在する。** Codex 開発ガイドラインとスキル選択の手順が書かれている。**既存の内容を消さないこと。** 末尾に設計書8.2節の2つの節（「社内資料の参照」「外部ドキュメントの参照」）を足す。

追記前に `git diff AGENTS.md` で、既存行が1行も消えていないことを確かめる。

- [ ] **Step 3: 処理箇所マップに節を足す**

`docs/処理箇所マップ.md` は本番コード（`ingest/`, `scripts/`, `rag_chat_app.py`）の索引である。`scripts/rag_mcp_server.py` の節を足す。

**行番号は必ず実ファイルを開いて照合すること。** 次のスクリプトで全参照を機械照合できる。

```bash
../../myvenv313/Scripts/python.exe - <<'PY'
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

**このスクリプトは行の「内容」までは見ない。** 足した参照については、実際に開いて説明文とその行にあるコードが一致するか確かめること。

- [ ] **Step 4: テストを通す**

Run: `../../myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS（Task 1 Step 1 で控えた件数 + 13）

- [ ] **Step 5: コミット**

```bash
git add "docs/mcp-server.md" AGENTS.md "docs/処理箇所マップ.md"
git commit -m "docs: describe how to wire the MCP server into Codex

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
