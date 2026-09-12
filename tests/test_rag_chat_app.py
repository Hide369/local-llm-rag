"""チャット画面の異常系。

回答生成の失敗（chat.ChatError）はチャット欄に短いメッセージとして出るが、
検索の失敗はどこにも捕まえていなかった。実測: 2026-08-13 07:04〜08:10 の間
Ollamaが停止しており、質問すると ingest.embedder.EmbeddingError の
トレースバックがそのまま画面に出た。

生成は ingest/chat.py 経由でOllamaのネイティブAPI（/api/chat）を直接叩く
（openaiパッケージ経由ではnum_ctxが反映されなかったため、実測を経て切り替えた。
ingest/chat.py のモジュールdocstring参照）。テストでは chat.ask_json /
chat.stream_chat をこの階層で差し替える。

AppTest は rag_chat_app.py を同じプロセスで実行する。本番のストア
（vector_store.sqlite3）を開くと、テストの結果がその時点の取り込み内容に左右され、
再現しなくなる。1チャンクだけの決まった状態を作るため、store.open_store を
インメモリのものへ差し替える。
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import ingest.retrieval as retrieval
from ingest import chat
from ingest import embedder as embedder_module
from ingest import reranker as reranker_module
from ingest import store as store_module
from ingest import vlm as vlm_module
from ingest.embedder import EmbeddingError
from ingest.vector_store import open_store as open_real_store
from scripts import ingest_source

APP_PATH = Path(__file__).resolve().parent.parent / "rag_chat_app.py"

OFFLINE_MESSAGE = "Ollamaに接続できません（テスト）"


def _stub_open_store(metadata):
    """store.open_store の代わりに、1チャンクだけ入ったインメモリDBを返す。"""

    def factory(*args, **kwargs):
        # 実体を直接呼ぶ。この factory 自身が store.open_store の差し替え先であり、
        # 再公開された名前を呼ぶと自分を呼び戻して無限再帰になる。
        collection = open_real_store(":memory:")
        collection.add(
            ids=["chunk-1"],
            documents=["洗濯機の運転音は26dBです。"],
            embeddings=[[0.1, 0.2]],
            metadatas=[metadata],
        )
        return collection

    return factory


def _offline_embed_query(*args, **kwargs):
    raise EmbeddingError(OFFLINE_MESSAGE)


def _fake_stream_chat(text):
    """生成だけを差し替える。条件抽出は属性なしのDBでそもそも呼ばれない。

    呼び出しの引数（model・messages・temperature）は .calls に積む。
    ingest/chat.py の実シグネチャ stream_chat(model, messages, temperature, session=None)
    に合わせる。
    """
    calls = []

    def stream(model, messages, temperature, session=None):
        calls.append({"model": model, "messages": messages, "temperature": temperature})
        yield from text

    stream.calls = calls
    return stream


@pytest.fixture
def app():
    # get_collection / get_schema は @st.cache_resource で、キャッシュはプロセス
    # 全体で共有される。前のテストのDBを引き継がないよう毎回捨てる。
    st.cache_resource.clear()
    return AppTest.from_file(str(APP_PATH), default_timeout=60)


@pytest.fixture(autouse=True)
def _reranker_check_and_rerank_stubbed_by_default():
    """Rerankerチェックボックスは既定ONなので、他のテストのapp.run()でも
    ensure_reranker() だけでなく search() に渡る reranker.rerank まで実際に
    呼ばれてしまう。_stub_open_store は埋め込み [0.1, 0.2] の1チャンクを
    入れており、多くのテストが embed_query を [0.1, 0.2] にモックしているため
    distance=0で圏内判定を通り、_reranked() の head が空にならず本物の rerank()
    （実ONNXセッション構築・hf_hub_download）が呼ばれてしまう。ネットワークにも
    実モデルにも触れさせないよう、check_reranker と rerank の両方を既定で
    スタブする。rerank側は [0.0]*len(texts) を返す。全件同スコアなら
    _reranked() のsortは安定ソートなので元のRRF順のまま返り、既存テストの
    並び順に関するアサーションには影響しない。
    リランカー自体の疎通確認や配線を検証するテストは、この既定をネストした
    patch.objectで上書きする。
    """
    with (
        patch.object(reranker_module, "check_reranker", lambda: None),
        patch.object(reranker_module, "rerank", lambda query, texts: [0.0] * len(texts)),
    ):
        yield


@pytest.fixture(autouse=True)
def _vlm_check_stubbed_by_default():
    """VLMの疎通確認は自動で走るようになったので、既定でスタブする。

    チェックボックスがあった頃は、外したままの取り込みでVLMに触れなかった。
    自動判定になった今は取り込みのたびに check_vlm() が呼ばれ、素のままでは
    テストが OLLAMA_HOST へHTTPを出す（.env のngrok URLに10秒待たされる）。
    ネットワークにも実モデルにも触れさせない。

    既定は「VLMが使える」側にする。VLMが無い場合の振る舞いを見るテストは、
    リランカーの既定と同じくネストした patch.object で上書きする。
    """
    with patch.object(vlm_module, "check_vlm", lambda *a, **k: None):
        yield


def test_search_failure_is_reported_instead_of_crashing(app):
    """埋め込みAPIが落ちていても、画面に出るのはメッセージであってトレースバックではない。

    エラー文は st.error() でその場に出るだけでなく、履歴にも残す
    （入力欄を再有効化する直後の st.rerun() で st.error() の描画自体は
    消えるため、履歴に残していなければ最終的な画面から跡形もなく消える）。
    """
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(retrieval, "embed_query", _offline_embed_query),
    ):
        app.run()
        app.chat_input[0].set_value("運転音が静かな機種は？").run()

    assert not app.exception
    assert OFFLINE_MESSAGE in app.session_state.messages[-1]["content"]


def test_search_failure_does_not_also_claim_it_will_search(app):
    """条件抽出と検索が同じ原因で落ちたときに、通常の検索を約束する警告を出さない。

    Ollamaが落ちていれば条件抽出（LLM）も検索（埋め込み）も失敗する。
    「通常の検索で回答します」と告げた直後にその検索が失敗するのでは、
    利用者にとって嘘になる。
    """
    # 数値属性を1つ持たせてスキーマを空でなくすると、条件抽出のLLM呼び出しが走る。
    metadata = {"source": "a.md", "noise_db": 26}
    with (
        patch("ingest.store.open_store", _stub_open_store(metadata)),
        # JSONにならない応答を返し、条件抽出を失敗させる
        patch.object(chat, "ask_json", lambda model, prompt, session=None: "not json"),
        patch.object(retrieval, "embed_query", _offline_embed_query),
    ):
        app.run()
        app.chat_input[0].set_value("運転音26dB以下の機種は？").run()

    assert not app.exception
    assert OFFLINE_MESSAGE in app.session_state.messages[-1]["content"]
    assert app.session_state.messages[-1].get("note") is None


def test_a_follow_up_question_is_searched_with_the_previous_one(app):
    """「決定事項を教えてほしい」だけでは議事録を引けない（実測で上位4件が別資料）。"""
    queries = []

    def record(text, session=None):
        queries.append(text)
        return [0.1, 0.2]

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat("第5回会議の決定事項は…")),
        patch.object(retrieval, "embed_query", record),
    ):
        app.run()
        app.chat_input[0].set_value("第5回会議のタイトルを教えてほしい").run()
        app.chat_input[0].set_value("決定事項を教えてほしい").run()

    assert queries == [
        "第5回会議のタイトルを教えてほしい",
        "第5回会議のタイトルを教えてほしい 決定事項を教えてほしい",
    ]


def test_the_model_is_picked_from_the_pulled_models(app):
    """モデル名の自由入力ではなく、pull済みモデルの固定リストからの選択にする。

    自由入力だと打ち間違いが生成時のchat.ChatErrorになるまで分からなかった。
    現在の候補は gpt-oss:20b だけで、これは接続先のOllamaに置いてある生成モデルが
    これだけだからである（README「モデルの比較」）。
    """
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat("回答")),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()

    assert not app.exception
    assert app.selectbox[0].options == ["gpt-oss:20b"]
    assert app.selectbox[0].value == "gpt-oss:20b"


def test_the_picked_model_is_the_one_that_generates(app):
    """プルダウンが持つ値がそのまま生成に渡る。見た目だけの切り替えにしない。

    **候補が1つの間、このテストの区別力は落ちている。** 以前は既定と別のモデルを
    選び直して「選択が反映される」ことを確かめていたが、MODELSがgpt-oss:20bだけに
    なったため選び直す先が無い。いまはウィジェットの値と生成に渡った値が一致する
    ことしか言えず、モデル名をハードコードした実装でも通ってしまう。
    MODELSに2つ目を足したら、別の候補を選び直す形に戻して強度を回復させること。

    リテラルではなくウィジェットの値と突き合わせているのは、MODELSを変えたときに
    ここが黙って無意味にならず、少なくとも連結だけは見続けるためである。
    """
    fake_stream = _fake_stream_chat("回答です。")
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", fake_stream),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        picked = app.selectbox[0].value
        app.chat_input[0].set_value("運転音は？").run()

    assert not app.exception
    used = [call["model"] for call in fake_stream.calls]
    assert used == [picked]


def _fake_ask_json_for_the_catalog_route(condition_json, ranking_json):
    """条件抽出・並べ替え抽出の2種類の呼び出しをプロンプト文面で見分けて返す。

    呼ばれる順に並べると、順序が変わるたびにテストが壊れる。
    """

    def ask_json(model, prompt, session=None):
        return ranking_json if "最大・最小" in prompt else condition_json

    return ask_json


def test_products_that_fail_the_condition_are_shown_but_not_sent_to_the_model(app):
    """設置できない機種をモデルに渡すと、答えとして挙げてしまう（実測8回中5回）。

    利用者には見せる価値があるので、画面の一覧にだけ残す。
    """
    prompts = []

    def factory(*args, **kwargs):
        collection = open_real_store(":memory:")  # 差し替え先なので実体を呼ぶ
        for model, capacity, depth in (
            ("UD-1100S", 11.0, 510),
            ("UD-1400X", 14.0, 545),
        ):
            collection.add(
                ids=[f"{model}::0"],
                documents=[f"{model}の本文"],
                embeddings=[[0.1, 0.2]],
                metadatas=[
                    {
                        "source": f"家電製品/{model}.md",
                        "model_id": model,
                        "washing_capacity_kg": capacity,
                        "installation_depth_min_mm": depth,
                    }
                ],
            )
        return collection

    fake_ask_json = _fake_ask_json_for_the_catalog_route(
        '{"installation_depth_min_mm": {"$lte": 510}}',
        '{"washing_capacity_kg": "最大"}',
    )
    fake_stream = _fake_stream_chat("最大11.0kgです。")
    with (
        patch("ingest.store.open_store", factory),
        patch.object(chat, "ask_json", fake_ask_json),
        patch.object(chat, "stream_chat", fake_stream),
    ):
        app.run()
        app.chat_input[0].set_value("510mmに設置できる最大の洗濯容量は").run()

    prompts = [call["messages"][-1]["content"] for call in fake_stream.calls]
    assert prompts, "生成が呼ばれていない"
    assert "UD-1400X" not in prompts[0]
    shown = "\n".join(element.value for element in app.code)
    assert "UD-1400X" in shown
    assert "条件を満たさないので選べない" in shown


def test_no_quality_switches_are_left_to_the_reader(app):
    """VLMもRerankerもチェックボックスにしない。どちらも常に効かせる。

    「画像を含む資料か」も「並べ替えを使うか」も、利用者が判断する材料を
    画面から得られない。外し忘れれば図表の説明や並べ替えが黙って落ちるだけで、
    落ちたことは結果からは分からない。

    どちらも常時ONにできる根拠がある。パーサーは画像を見つけたときだけ
    caption_image を呼ぶので図の無い資料の取り込みは遅くならず、リランカーは
    1問あたり約1.3秒（実測。8候補の中央値）で常用に耐える。
    """
    with patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})):
        app.run()

    assert not app.exception
    assert app.checkbox.values == []


def test_ingesting_passes_the_captioner_without_being_asked(app):
    """疎通確認が通れば caption_image を渡す。CLIの --with-vlm と同じ配線である。"""
    calls = []
    checked = []

    def fake_ingest_directory(*args, **kwargs):
        calls.append(kwargs)
        return ingest_source.IngestReport()

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(vlm_module, "check_vlm", lambda *a, **k: checked.append(True)),
        patch.object(ingest_source, "ingest_directory", fake_ingest_directory),
    ):
        app.run()
        app.button[0].click().run()

    assert not app.exception
    assert checked == [True]
    assert calls == [{"caption_image": vlm_module.caption_image}]


def test_ingesting_without_a_vlm_still_ingests_and_says_why(app):
    """VLMが無いことは取り込みを止める理由にしない。図表の説明が付かないだけである。

    caption_image を渡したまま失敗させる選択は取らない。画像1枚ごとに4回の
    リトライ（1+2+4秒）が走り、モデル未pullの環境で取り込みが極端に遅くなる
    （ingest/vlm.py の _MAX_ATTEMPTS）。
    """
    calls = []

    def fake_ingest_directory(*args, **kwargs):
        calls.append(kwargs)
        return ingest_source.IngestReport()

    def failing_check_vlm(*a, **k):
        raise vlm_module.VlmError("VLMモデル qwen2.5vl:7b がありません")

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(vlm_module, "check_vlm", failing_check_vlm),
        patch.object(ingest_source, "ingest_directory", fake_ingest_directory),
    ):
        app.run()
        app.button[0].click().run()

    assert not app.exception
    assert calls == [{"caption_image": None}]
    assert any("qwen2.5vl:7b" in warning.value for warning in app.warning)


def test_the_ingest_result_survives_the_rerun(app):
    """取り込みの要約を画面に残す。

    st.rerun() の前に出したメッセージは破棄される（実測）。直後に再実行する
    このボタンでは、その場で st.sidebar.success() を呼ぶだけでは要約が一度も
    画面に出ない。次の実行で描くために session_state へ預ける。
    """

    def fake_ingest_directory(*args, **kwargs):
        return ingest_source.IngestReport(indexed={"議事録.docx": 3})

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(vlm_module, "check_vlm", lambda *a, **k: None),
        patch.object(ingest_source, "ingest_directory", fake_ingest_directory),
    ):
        app.run()
        app.button[0].click().run()

    assert not app.exception
    assert any("1ファイル" in success.value for success in app.success)


def test_answer_is_shown_without_the_repeated_label(app):
    """モデルが付ける「答え：」は表示しない。中身は残す。"""
    generated = "省エネ基準達成率が最も高いのはUD-1100iEです。\n答え： 型番：UD-1100iE 達成率：125%"
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat(generated)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("省エネ基準達成率が最も高い機種は？").run()

    assert not app.exception
    shown = "\n".join(element.value for element in app.markdown)
    assert "答え：" not in shown


def test_input_is_re_enabled_and_history_has_exactly_one_exchange_after_answering(app):
    """生成中は入力欄を無効化し、完了後に再有効化する。

    生成中の無効化そのものを直接観測はできない（AppTest.run()は内部の
    st.rerun()を全部消化してから戻るため）。代わりに、完了後の最終状態で
    (1) 入力欄が有効に戻っていること (2) やりとりが二重に積まれていない
    （無効化の仕組み自体がバグって多重発火していないか）ことを確認する。
    """
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat("回答です。")),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は？").run()

    assert not app.exception
    assert app.chat_input[0].disabled is False
    assert [m["role"] for m in app.session_state.messages] == ["user", "assistant"]


def test_a_reranker_model_failure_says_what_happens_instead():
    """570MBの取得に失敗したとき、生のトレースバックを画面に出さない。

    理由だけでは足りない。切る手段を利用者から取り上げた以上、そのまま検索が
    続くのか止まるのかを画面に書く（VLMが使えないときの見せ方に揃える）。
    """
    st.cache_resource.clear()
    message = "リランカーのモデルを取得できません（テスト）"
    with patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})), patch.object(
        reranker_module, "check_reranker", side_effect=reranker_module.RerankError(message)
    ):
        app = AppTest.from_file(str(APP_PATH)).run()
    assert not app.exception
    assert any(
        message in warning.value and "並べ替え" in warning.value
        for warning in app.sidebar.warning
    )


def test_the_reranker_is_always_wired_into_search(app):
    """search()には常にreranker.rerankが渡る。

    ここを確認しないと、常にrerank=Noneを渡す退行（機能が画面上は何も変わらず
    静かに無効化される）でも他のアサーションを全て通り抜けてしまう。
    rag_chat_app.py は `from ingest.retrieval import ... search` でトップレベル
    importしているが、AppTestはスクリプトをrun()のたびに再実行するため、
    run()より前に ingest.retrieval.search をパッチしておけば、その回のimportで
    差し替え後の関数が束縛される
    （test_a_follow_up_question_is_searched_with_the_previous_one で
    embed_query に対して使っているのと同じ仕組み）。
    """
    calls = []

    def fake_search(
        collection, query, index=None, session=None, threshold=None, n_results=4, rerank=None
    ):
        calls.append(rerank)
        return []

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(retrieval, "search", fake_search),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は？").run()

    assert not app.exception
    assert calls == [reranker_module.rerank]


def test_a_missing_reranker_model_does_not_stop_the_search(app):
    """モデルが用意できなければ、並べ替えずに検索する。

    常に渡す側だけを確認すると、モデルの取得に失敗した環境で検索ごと落ちる実装
    でも通ってしまう。並べ替えは検索結果の順序を良くするものであって、検索が
    成立する条件ではない（VLMが無くても取り込みを止めないのと同じ考え方）。
    """
    calls = []

    def fake_search(
        collection, query, index=None, session=None, threshold=None, n_results=4, rerank=None
    ):
        calls.append(rerank)
        return []

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(
            reranker_module,
            "check_reranker",
            lambda: (_ for _ in ()).throw(reranker_module.RerankError("モデルがありません")),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(retrieval, "search", fake_search),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は？").run()

    assert not app.exception
    assert calls == [None]


def test_the_caches_are_keyed_on_the_revision_not_the_chunk_count(app):
    """BM25索引と属性一覧の鍵は、書き込みと不可分に進む revision であること。

    チャンク数を鍵にすると「同数の差し替え」を取りこぼす（設計書4.5節）。本文だけ
    直したMarkdownを外部プロセスで取り込み直しても件数は変わらないため、BM25索引が
    消えた旧チャンクIDを持ち続け、retrieval.search がその行を引けずに黙って落とす。
    count() を鍵に戻すと revision() は一度も呼ばれなくなり、このテストが落ちる。
    """
    seen = []

    def factory(*args, **kwargs):
        collection = open_real_store(":memory:")
        collection.add(
            ids=["chunk-1"],
            documents=["洗濯機の運転音は26dBです。"],
            embeddings=[[0.1, 0.2]],
            metadatas=[{"source": "a.md"}],
        )
        original = collection.revision
        collection.revision = lambda: (seen.append(1), original())[1]
        return collection

    with patch("ingest.store.open_store", factory):
        app.run()

    # VectorStore.search() も内部で revision() を読むため >= では将来ゆるくなる。
    # 初期描画では検索が走らないので、鍵として読まれる2回ちょうどが期待値。
    assert len(seen) == 2, "get_index と get_schema の両方が revision を鍵にすること"


def test_get_index_and_get_schema_are_keyed_on_the_corpus_not_revision_alone():
    """revision だけでは鍵として足りない。コーパス（DBパス）も要る。

    revision は各DBが自分の meta テーブルに持つ、ファイルごとに独立した
    カウンタである（vector_store.sqlite3 と docs_store.sqlite3 はどちらも
    取り込みのたびに1ずつ進むだけで、互いのカウンタを知らない）。そのため
    2つのDBが同じ revision を持つことは普通に起こる。get_index / get_schema は
    @st.cache_resource で、_collection は先頭アンダースコアでハッシュ対象から
    外れているため、鍵に revision しか無いと、たまたま値が揃った瞬間に後から
    呼ばれた側が先に呼ばれた側のコーパスの結果をそのまま受け取ってしまう
    （設計書4.5節が警告する「理由の説明なく古い結果を返す」ことの一種）。

    実際にDBの取り込み回数を揃えて衝突を作らなくても、呼び出し側で revision を
    同じ値に固定すれば同じ状況を再現できる。ここでは2つの別コーパス（別の
    中身を持つ2つのインメモリDB）に同じ revision=7 を渡し、返ってくる結果が
    別物であることを見る。db_path を鍵に加えていなければ、2回目の呼び出しは
    1回目の呼び出し結果をキャッシュからそのまま受け取り、中身が同じになる。
    """
    st.cache_resource.clear()
    # rag_chat_app はモジュール直下で get_collection(DB_PATH) と
    # ensure_reranker() を実行する。初回 import 時にそれが実DBやネットワークへ
    # 触れないよう、ここでだけ store.open_store をスタブに差し替える
    # （reranker.check_reranker は本ファイルのautouseフィクスチャで既にスタブ
    # 済みなので、ここでは触れなくてよい）。2回目以降の import はキャッシュ
    # 済みのモジュールを返すだけなので、このパッチは無害である。
    with patch.object(store_module, "open_store", _stub_open_store({"source": "import.md"})):
        import rag_chat_app
    st.cache_resource.clear()

    collection_a = open_real_store(":memory:")
    collection_a.add(
        ids=["a-chunk-1"],
        documents=["社内資料の本文。"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"source": "internal.md", "shelf_id": 1}],
    )
    collection_b = open_real_store(":memory:")
    collection_b.add(
        ids=["b-chunk-1", "b-chunk-2"],
        documents=["技術ドキュメントの本文。", "もう1チャンク。"],
        embeddings=[[0.3, 0.4], [0.5, 0.6]],
        metadatas=[
            {"source": "docs.md", "page_count": 5},
            {"source": "docs.md", "page_count": 5},
        ],
    )

    # 同じ revision=7 を、パスが違う2つのコーパスに対して渡す。
    index_a = rag_chat_app.get_index(collection_a, "internal/path", 7)
    index_b = rag_chat_app.get_index(collection_b, "docs/path", 7)
    assert index_a.ids != index_b.ids, (
        "get_index が revision だけを鍵にしており、コーパスが違っても"
        "同じBM25索引を返している"
    )

    schema_a = rag_chat_app.get_schema(collection_a, "internal/path", 7)
    schema_b = rag_chat_app.get_schema(collection_b, "docs/path", 7)
    assert schema_a != schema_b, (
        "get_schema が revision だけを鍵にしており、コーパスが違っても"
        "同じ属性一覧を返している"
    )


# --- 取り込みダイアログ ---------------------------------------------------
#
# 利用者のブラウザーから資料を取り込む経路。source/ はサーバー側にあり、
# クライアントからは触れない。ダイアログは session_state のフラグで開閉する。
# ボタンのクリックで再実行が起きるため、フラグを持たないと最初の操作で閉じる
# （AppTestでも実機と同じように閉じることを確認済み）。


def _open_upload_dialog(app):
    app.button(key="open_upload_dialog").click().run()
    return app


def test_the_upload_dialog_writes_the_file_and_ingests_it(app):
    """アップロードされた中身を一時ファイルに書き出してから取り込みへ渡す。"""
    received = []

    def fake_ingest_uploads(paths, collection, **kwargs):
        received.extend((path.name, path.read_bytes()) for path in paths)
        return ingest_source.IngestReport(indexed={"uploads/持ち込み.md": 1})

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(ingest_source, "ingest_uploads", fake_ingest_uploads),
    ):
        app.run()
        _open_upload_dialog(app)
        app.file_uploader[0].set_value(("持ち込み.md", b"# \xe8\xad\xb0\xe4\xba\x8b\xe9\x8c\xb2", "text/markdown"))
        app.run()
        app.button(key="run_upload").click().run()

    assert not app.exception
    assert received == [("持ち込み.md", b"# \xe8\xad\xb0\xe4\xba\x8b\xe9\x8c\xb2")]


def test_the_upload_dialog_does_not_ingest_when_nothing_is_selected(app):
    """ファイルを選ばずに押しても、埋め込みAPIを呼びに行かせない。"""
    calls = []

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(
            ingest_source,
            "ingest_uploads",
            lambda *a, **k: calls.append(a) or ingest_source.IngestReport(),
        ),
    ):
        app.run()
        _open_upload_dialog(app)
        app.button(key="run_upload").click().run()

    assert not app.exception
    assert calls == []
    assert any("選んで" in warning.value for warning in app.warning)


def test_the_upload_dialog_lists_only_the_uploaded_documents(app):
    """source/ 由来の資料は一覧に出さない。削除できるのはアップロード分だけである。"""
    with patch("ingest.store.open_store", _stub_open_store({"source": "議事録.docx"})):
        app.run()
        _open_upload_dialog(app)

    assert not app.exception
    keys = [button.key for button in app.button if button.key]
    assert [key for key in keys if key.startswith("delete_")] == []


def test_the_upload_dialog_deletes_an_uploaded_document(app):
    """一覧の削除ボタンでDBから消える。消える時期を利用者が握るための操作である。"""
    # 画面が開くストアをテスト側で握る。session_state に置いてもらう手も
    # あるが、確認のためだけの経路を画面のコードへ足すことになる。
    collection = open_real_store(":memory:")
    collection.add(
        ids=["chunk-1"],
        documents=["持ち込んだ資料の本文です。"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"source": "uploads/持ち込み.md"}],
    )
    with patch("ingest.store.open_store", lambda *a, **k: collection):
        app.run()
        _open_upload_dialog(app)
        assert store_module.indexed_sources(collection) == {"uploads/持ち込み.md"}
        app.button(key="delete_uploads/持ち込み.md").click().run()

    assert not app.exception
    assert store_module.indexed_sources(collection) == set()


def test_the_upload_dialog_reports_an_offline_ollama_without_ingesting(app):
    """取り込みを始めてから落ちるのではなく、先に疎通確認して短く伝える。"""
    calls = []

    def offline(*args, **kwargs):
        raise EmbeddingError(OFFLINE_MESSAGE)

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", offline),
        patch.object(
            ingest_source,
            "ingest_uploads",
            lambda *a, **k: calls.append(a) or ingest_source.IngestReport(),
        ),
    ):
        app.run()
        _open_upload_dialog(app)
        app.file_uploader[0].set_value(("持ち込み.md", b"# a", "text/markdown"))
        app.run()
        app.button(key="run_upload").click().run()

    assert not app.exception
    assert calls == []
    assert any(OFFLINE_MESSAGE in error.value for error in app.error)


def test_an_uploaded_document_really_reaches_the_store(app):
    """ダイアログから実際の取り込み処理を通し、DBに入って一覧に出るまでを見る。

    他のダイアログのテストは ingest_uploads() を差し替えており、画面側の配線しか
    見ていない。解析・チャンク・格納まで本物を通すのはここだけである。埋め込みの
    HTTP呼び出しだけは固定ベクトルに差し替える（Ollamaに依存させない）。
    """
    collection = open_real_store(":memory:")

    with (
        patch("ingest.store.open_store", lambda *a, **k: collection),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(
            embedder_module,
            "embed_texts",
            lambda texts, session=None: [[0.1, 0.2] for _ in texts],
        ),
    ):
        app.run()
        _open_upload_dialog(app)
        app.file_uploader[0].set_value(
            ("持ち込み.md", "# 議題\n\n取り込みUIの設計を決めた。\n".encode(), "text/markdown")
        )
        app.run()
        app.button(key="run_upload").click().run()

    assert not app.exception
    assert store_module.indexed_sources(collection) == {"uploads/持ち込み.md"}
    assert app.button(key="delete_uploads/持ち込み.md") is not None


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


# --- 記法そのものの表示 ---------------------------------------------------
#
# Streamlit 1.61 は mermaid を同梱しており、```mermaid フェンスは図として
# 描画される。マークダウンも st.write が描画する。記法を見たい・他所へ
# 持ち出したい利用者は、今の画面からはそれを取り出せない。
# 判定は ingest/display_mode.py が質問文に対して行う。


def test_a_markdown_request_shows_the_notation_instead_of_rendering_it(app):
    """st.write は記法を描画してしまい、記法が欲しい利用者には渡らない。"""
    answer = "| 型番 | 容量 |\n|---|---|\n| UD-0900i | 9.0kg |"

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat(answer)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("一覧をマークダウンで表示して").run()

    assert not app.exception
    assert any(answer in element.value for element in app.code)


def _asked_for_mermaid(app, answer):
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat(answer)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("流れをマーメイドで表示して").run()
    return app


def test_a_mermaid_request_shows_both_the_notation_and_the_diagram(app):
    """記法だけでも図だけでも足りない。記法は持ち出すため、図は読むために要る。

    st.mermaid_chart は本文をフェンスで包んで markdown 要素として出す（実測）。
    """
    answer = "処理の流れです。\n\n```mermaid\ngraph TD;\n  A-->B;\n```"
    _asked_for_mermaid(app, answer)

    assert not app.exception
    assert any(answer in element.value for element in app.code)
    assert any(
        "mermaid" in element.value and "graph TD;" in element.value
        for element in app.markdown
    )


def test_the_diagram_is_drawn_from_the_fence_only(app):
    """回答全体を mermaid_chart へ渡すと地の文が構文エラーになる。
    st.write(回答) で描くと地の文がコードブロックと二重に出る。
    """
    answer = "処理の流れです。\n\n```mermaid\ngraph TD;\n  A-->B;\n```"
    _asked_for_mermaid(app, answer)

    rendered = [
        element.value for element in app.markdown if "graph TD;" in element.value
    ]
    assert rendered, "図が描かれていない"
    assert all("処理の流れです。" not in value for value in rendered)


def test_a_bare_definition_is_still_drawn(app):
    """モデルがフェンス無しで素の定義だけを返すことがある。"""
    _asked_for_mermaid(app, "graph TD;\n  A-->B;")

    assert not app.exception
    assert any(
        "mermaid" in element.value and "graph TD;" in element.value
        for element in app.markdown
    )


def test_a_markdown_request_draws_no_diagram(app):
    """図を出すのはマーメイドのときだけである。"""
    answer = "| 型番 | 容量 |\n|---|---|\n| UD-0900i | 9.0kg |"

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat(answer)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("一覧をマークダウンで表示して").run()

    assert not app.exception
    assert all("mermaid" not in element.value for element in app.markdown)


def test_an_ordinary_question_still_renders_markdown(app):
    """既定の見え方は変えない。記法で頼まれたときだけ切り替える。"""
    answer = "運転音は26dBです。"

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat(answer)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は").run()

    assert not app.exception
    assert any(answer in element.value for element in app.markdown)
    assert all(answer not in element.value for element in app.code)


def test_the_notation_survives_a_rerun(app):
    """履歴の再描画でレンダリングに戻ると、画面を触るたび見え方が変わる。

    生成時の分岐だけを直しても足りない。履歴側は message の display を読む。
    """
    answer = "```mermaid\ngraph TD;\n  A-->B;\n```"

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat(answer)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("流れをマーメイドで表示して").run()
        # 生成が終わった状態でもう一度描かせ、履歴側の描画経路を通す。
        app.run()

    assert not app.exception
    assert any(answer in element.value for element in app.code)


def test_the_display_mode_does_not_carry_over_to_the_next_question(app):
    """判定は質問1つごとに閉じる。持ち越すと、利用者が何も言っていないのに
    コードブロックで返り続ける。
    """
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat("普通の回答です。")),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("一覧をマークダウンで表示して").run()
        app.chat_input[0].set_value("運転音は").run()

    assert not app.exception
    # 2問目の回答は描画される。1問目の分はコードブロックのまま残る。
    assert any("普通の回答です。" in element.value for element in app.markdown)


def test_a_search_failure_is_not_shown_as_notation(app):
    """エラー文は記法ではない。書式を頼まれていても普通に読める形で出す。"""
    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(retrieval, "embed_query", _offline_embed_query),
    ):
        app.run()
        app.chat_input[0].set_value("一覧をマークダウンで表示して").run()
        app.run()

    assert not app.exception
    assert all(OFFLINE_MESSAGE not in element.value for element in app.code)


def _stub_open_store_per_path(bodies):
    """パスごとに中身の違うインメモリDBを返す。

    既存の _stub_open_store は引数を無視して同じDBを返すため、
    2つのコーパスを区別するテストには使えない。
    """
    stores = {}

    def factory(path, *args, **kwargs):
        key = str(path)
        if key not in stores:
            collection = open_real_store(":memory:")
            body = next(
                (text for marker, text in bodies.items() if marker in key),
                "該当なし",
            )
            collection.add(
                ids=["chunk-1"],
                documents=[body],
                embeddings=[[0.1, 0.2]],
                metadatas=[{"source": "a.md", "location_type": "section", "location": 1}],
            )
            stores[key] = collection
        return stores[key]

    return factory


def test_the_corpus_switch_offers_both_choices(app):
    with patch.object(store_module, "open_store", _stub_open_store_per_path({})):
        app.run()
    assert list(app.sidebar.radio[0].options) == ["社内資料", "技術ドキュメント"]


def _fake_ask_json_returning_query(translated):
    """検索クエリ翻訳（ingest/query_translation.py）用のask_jsonの代役。

    どのテストも実際のOllamaへ触れさせないため、技術ドキュメントのコーパスへ
    切り替えるテストでは常にこれで chat.ask_json を差し替える。
    """
    return lambda model, prompt, session=None: json.dumps({"query": translated})


def test_choosing_the_documentation_corpus_searches_the_other_database(app):
    """切り替えが本当に別のDBを引いていることを、返る本文で見る。

    ラジオが画面に出ているだけでは配線されている証拠にならない。
    """
    stream = _fake_stream_chat("回答")
    with (
        patch.object(
            store_module,
            "open_store",
            _stub_open_store_per_path(
                {"docs_store": "st.dialog でダイアログを出します。",
                 "vector_store": "洗濯機の運転音は26dBです。"},
            ),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "stream_chat", stream),
        patch.object(chat, "ask_json", _fake_ask_json_returning_query("dialog")),
    ):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()
        app.chat_input[0].set_value("ダイアログの出し方は").run()

    sent = stream.calls[-1]["messages"][-1]["content"]
    assert "st.dialog でダイアログを出します。" in sent
    assert "洗濯機" not in sent


def test_the_documentation_corpus_uses_the_documentation_prompt(app):
    """社内資料向けの歯止めが技術ドキュメントに混ざらないことを見る。"""
    stream = _fake_stream_chat("回答")
    with (
        patch.object(
            store_module,
            "open_store",
            _stub_open_store_per_path({"docs_store": "st.dialog を使います。"}),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "stream_chat", stream),
        patch.object(chat, "ask_json", _fake_ask_json_returning_query("dialog")),
    ):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()
        app.chat_input[0].set_value("ダイアログの出し方は").run()

    sent = stream.calls[-1]["messages"][-1]["content"]
    assert "混ぜないでください" in sent
    assert "社内文書" not in sent


def test_the_documentation_corpus_searches_with_the_translated_query(app):
    """技術ドキュメントの検索クエリは英語へ翻訳したものであること。

    生成側（build_docs_prompt）に渡す質問は原文の日本語のままでなければ
    ならない（Task 8の設計制約）。search() に渡ったクエリと、生成に渡った
    プロンプト文面の両方を見て、両者が別物であることを確認する。
    """
    stream = _fake_stream_chat("回答")
    search_calls = []

    def fake_search(
        collection, query, index=None, session=None, threshold=None, n_results=4, rerank=None
    ):
        search_calls.append(query)
        return []

    with (
        patch.object(store_module, "open_store", _stub_open_store_per_path({})),
        patch.object(retrieval, "search", fake_search),
        patch.object(chat, "stream_chat", stream),
        patch.object(
            chat, "ask_json", _fake_ask_json_returning_query("modal dialog st.dialog")
        ),
    ):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()
        app.chat_input[0].set_value("Streamlitでモーダルダイアログを出す書き方").run()

    # search() に渡ったのは翻訳後のクエリであり、原文の日本語ではない。
    assert search_calls == ["modal dialog st.dialog"]
    # ヒットなしの build_docs_prompt は「ユーザーの質問: {question}」を含む。
    # ここに原文の日本語質問がそのまま出ていること（生成は翻訳前の質問で行う）。
    sent = stream.calls[-1]["messages"][-1]["content"]
    assert "Streamlitでモーダルダイアログを出す書き方" in sent
    assert "modal dialog st.dialog" not in sent


def test_the_internal_corpus_never_calls_translation(app):
    """社内資料のコーパスでは、翻訳のためのLLM呼び出しが一切起きないこと。

    メタデータを source だけにするとスキーマが空になり、条件抽出
    （conditions.extract）自体もLLMを呼ばずに即座に戻る
    （ingest/conditions.py の schema が空なら呼ばない、という既存の門番）。
    その状態で chat.ask_json の呼び出し回数が0であることは、翻訳のための
    追加呼び出しがこの経路に一切配線されていないことの直接の証拠になる。
    """
    calls = []

    def ask_json(model, prompt, session=None):
        calls.append(prompt)
        return "{}"

    with (
        patch("ingest.store.open_store", _stub_open_store({"source": "a.md"})),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "ask_json", ask_json),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は？").run()

    assert not app.exception
    assert calls == []


def test_the_internal_corpus_is_unchanged_by_the_switch(app):
    """既定は社内資料で、振る舞いは変更前と同じでなければならない。"""
    stream = _fake_stream_chat("回答")
    with (
        patch.object(
            store_module,
            "open_store",
            _stub_open_store_per_path({"vector_store": "洗濯機の運転音は26dBです。"}),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "stream_chat", stream),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は").run()

    sent = stream.calls[-1]["messages"][-1]["content"]
    assert "洗濯機の運転音は26dBです。" in sent
    assert "社内文書" in sent


def _stub_open_store_docs_empty_internal_filled():
    """技術ドキュメント側だけ、チャンクを1件も入れない状態を作る。

    _stub_open_store_per_path は marker が当たらなくても "該当なし" の
    1チャンクを必ず入れるため、count() が0になるケースを作れない。
    open_store がタイポでも例外を出さず空のDBを新規作成する
    （ingest/store.py）状況そのものを再現するには、このように別の factory が要る。
    """
    stores = {}

    def factory(path, *args, **kwargs):
        key = str(path)
        if key not in stores:
            collection = open_real_store(":memory:")
            if "docs_store" not in key:
                collection.add(
                    ids=["chunk-1"],
                    documents=["洗濯機の運転音は26dBです。"],
                    embeddings=[[0.1, 0.2]],
                    metadatas=[{"source": "a.md"}],
                )
            stores[key] = collection
        return stores[key]

    return factory


def test_switching_to_the_empty_documentation_corpus_warns_with_the_cli_commands(app):
    """CLIをまだ一度も走らせていない場合、切り替えただけでは何も分からない。

    open_store はパスを間違えても例外を出さず空のDBを新規作成する
    （ingest/store.py）。件数0のまま黙って検索するのではなく、取り込みに
    使う2つのコマンドをサイドバーの警告として出す（設計書5.4節が
    CLI側に要求している「0件なら警告」の画面側）。
    """
    with patch.object(
        store_module, "open_store", _stub_open_store_docs_empty_internal_filled()
    ):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()

    warnings = [w.value for w in app.sidebar.warning]
    assert any("scripts.fetch_docs" in w and "scripts.ingest_source" in w for w in warnings)


def test_the_nonempty_documentation_corpus_does_not_warn(app):
    """中身があるときは、警告ではなく従来どおりのキャプションだけを出す。"""
    with patch.object(
        store_module,
        "open_store",
        _stub_open_store_per_path({"docs_store": "st.dialog を使います。"}),
    ):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()

    warnings = [w.value for w in app.sidebar.warning]
    assert not any("scripts.fetch_docs" in w for w in warnings)
    captions = [c.value for c in app.sidebar.caption]
    assert any("scripts.fetch_docs" in c for c in captions)


def test_switching_corpus_clears_history_and_does_not_poison_the_next_query(app):
    """検索対象を切り替えたら会話履歴を破棄し、次の質問に前コーパスの質問が
    混ざらないこと。

    再現手順（レビューの指摘）: 社内資料で「就業規則の有給休暇は？」と尋ね、
    技術ドキュメントへ切り替えて「キャッシュの書き方は？」と尋ねると、
    contextual_query が前の質問を継ぎ足し、翻訳後の検索クエリが
    「paid leave work regulations cache」のようになって検索が外れる。
    history にも前コーパスの回答が残り、build_docs_prompt の
    「ドキュメントに書いてあることだけを使う」指示と矛盾する。
    """
    stream = _fake_stream_chat("回答")
    translation_prompts = []

    def fake_ask_json(model, prompt, session=None):
        translation_prompts.append(prompt)
        return json.dumps({"query": "cache usage"})

    with (
        patch.object(
            store_module,
            "open_store",
            _stub_open_store_per_path(
                {"docs_store": "キャッシュの書き方はst.cache_dataです。"}
            ),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "stream_chat", stream),
        patch.object(chat, "ask_json", fake_ask_json),
    ):
        app.run()
        app.chat_input[0].set_value("就業規則の有給休暇は？").run()
        assert app.session_state.messages != []

        # コーパスを切り替えた直後、履歴は残っていない。
        app.sidebar.radio[0].set_value("技術ドキュメント").run()
        assert app.session_state.messages == []
        assert any("リセット" in info.value for info in app.sidebar.info)

        app.chat_input[0].set_value("キャッシュの書き方は？").run()

    # 翻訳へ渡したプロンプト（contextual_queryの出力）に前コーパスの質問語が
    # 混ざっていないこと。
    assert not any("有給休暇" in prompt for prompt in translation_prompts)
    assert any("キャッシュ" in prompt for prompt in translation_prompts)

    # 生成へ渡す履歴にも前コーパスの回答が残っていないこと。
    sent_history = stream.calls[-1]["messages"]
    assert not any("有給" in m["content"] for m in sent_history)


def test_switching_corpus_with_no_prior_history_does_not_show_the_reset_notice(app):
    """まだ何も質問していない状態での切り替えでは、消す履歴が無いので
    リセット通知も出さない（切り替えのたびに毎回出ると煩わしい）。"""
    with patch.object(store_module, "open_store", _stub_open_store_per_path({})):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()

    assert list(app.sidebar.info) == []
