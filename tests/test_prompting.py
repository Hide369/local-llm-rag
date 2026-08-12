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
