from ingest.prompting import build_catalog_prompt, build_prompt, format_report
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


def test_prompt_includes_retrieved_text():
    prompt = build_prompt("経費の上限は", [_hit(text="上限は1万円です")])
    assert "上限は1万円です" in prompt
    assert "経費の上限は" in prompt


def test_prompt_includes_citations_so_the_model_can_cite_them():
    prompt = build_prompt("経費の上限は", [_hit()])
    assert "a.pdf p.48" in prompt


def test_prompt_instructs_the_model_to_decline_when_hits_are_irrelevant():
    """しきい値だけでは、挨拶のような意味的に空な入力を弾けない
    （Task 9で実測・許容: 「こんにちは」が距離0.41前後でRELEVANCE_THRESHOLD=0.50を
    すり抜け、無関係なチャンクが1件返る）。距離やUI側のフィルタでは解決できないため、
    根拠が質問と無関係なら使わずにその旨を答えるよう、プロンプト自身がモデルに
    指示する。この指示文が失われると、無関係な文書がそのまま回答として
    復唱されてしまう（例: 「こんにちは」への回答にセミナー資料の挨拶スライドが
    紛れ込む）ため、ここでロックしておく。
    """
    prompt = build_prompt("経費の上限は", [_hit()])
    assert "無関係" in prompt
    assert "回答できない旨" in prompt


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


def test_catalog_prompt_tells_the_model_to_name_products_by_model_id():
    """一覧の1行が1つの製品仕様書なので、型番がそのまま出典になる。"""
    prompt = build_catalog_prompt("26dB以下は", "表")
    assert "型番 | " in prompt  # 行の並びを説明しているか
    assert "型番で示して" in prompt


def test_catalog_prompt_asks_for_prose_with_an_example():
    """指示だけでは4回とも行を丸写しした。文例まで足して初めて文章になった。"""
    prompt = build_catalog_prompt("26dB以下は", "表")
    assert "日本語の文章" in prompt
    assert "AAA-000" in prompt  # 架空の型番。実在の値を書くと答えに写る


def test_catalog_prompt_asks_for_every_product_that_ties():
    """同点の2機種のうち1つしか挙げないことがある。この一文で両モデルが改善した。

    実測（4回ずつ）: qwen2.5:7b-instruct 0/4 → 3/4、llama3.1:8b 3/4 → 4/4。
    """
    assert "同じ値の製品が複数あるとき" in build_catalog_prompt("最大容量は", "表")


def test_catalog_prompt_forbids_inventing_values():
    """表に無い数値を補われると、絞り込みで正確にした意味が消える。"""
    prompt = build_catalog_prompt("26dB以下は", "表")
    assert "推測" in prompt
