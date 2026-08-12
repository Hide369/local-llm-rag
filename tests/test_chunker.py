from ingest.chunker import CHUNK_SIZE, MIN_CHUNK_CHARS, chunk_units
from ingest.models import ParsedUnit


def _unit(text, location=1, location_type="page", ocr=False):
    return ParsedUnit(text=text, location_type=location_type, location=location, ocr=ocr)


def _chunk(units):
    return chunk_units(units, source="a.pdf", file_hash="abc123", indexed_at="2026-08-11")


def test_short_unit_becomes_exactly_one_chunk():
    """議事録のような800字未満の文書は分割せず1つの文脈として保つ。"""
    text = "本日の会議では今後のプロジェクト方針について話し合いました。"
    chunks = _chunk([_unit(text)])
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_long_unit_is_split():
    chunks = _chunk([_unit("あ" * 2000)])
    assert len(chunks) > 1
    assert all(len(c.text) <= CHUNK_SIZE for c in chunks)


def test_unit_at_exactly_chunk_size_is_not_split():
    """CHUNK_SIZEちょうどは「800字以下」に含まれるため分割してはいけない境界値。"""
    chunks = _chunk([_unit("あ" * CHUNK_SIZE)])
    assert len(chunks) == 1
    assert len(chunks[0].text) == CHUNK_SIZE


def test_unit_one_char_over_chunk_size_is_split():
    """CHUNK_SIZEを1字でも超えたら分割が必要になる境界値。off-by-oneの回帰を検知する。"""
    chunks = _chunk([_unit("あ" * (CHUNK_SIZE + 1))])
    assert len(chunks) >= 2


def test_empty_unit_produces_no_chunk():
    assert _chunk([_unit("   ")]) == []


def test_punctuation_only_unit_produces_no_chunk():
    """句読点だけのチャンクは埋め込むとコーパスの重心付近に位置し、挨拶のような
    意味的に空な入力の最近傍になって紛れ込んでしまうため、そもそも作らない。"""
    assert _chunk([_unit("。")]) == []


def test_unit_under_min_chars_is_dropped():
    """MIN_CHUNK_CHARS未満の境界値。9字は検索の役に立たないため捨てる。"""
    assert _chunk([_unit("あ" * (MIN_CHUNK_CHARS - 1))]) == []


def test_unit_at_min_chars_is_kept():
    """MIN_CHUNK_CHARSちょうどの境界値。10字は残す。"""
    text = "あ" * MIN_CHUNK_CHARS
    chunks = _chunk([_unit(text)])
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_split_tail_fragment_of_only_punctuation_is_dropped():
    """長い文書を分割した結果、末尾に「。」だけの断片が残ることがある。
    分割由来でも素通りでも同じ基準で捨てないと、断片だけ検索を汚染する。"""
    text = "あ" * (CHUNK_SIZE + 1) + "。"
    chunks = _chunk([_unit(text)])
    assert all(len(c.text) >= MIN_CHUNK_CHARS for c in chunks)
    assert "。" not in [c.text for c in chunks]


def test_id_is_deterministic():
    """同じ資料を再取り込みしても同じIDになり、重複登録が起きない。"""
    text = "議事録の本文として十分な長さのある文章です。"
    first = _chunk([_unit(text, location=48)])
    second = _chunk([_unit(text, location=48)])
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
    chunk = _chunk([_unit("メタデータの伝播を確認するための本文です。")])[0]
    assert chunk.metadata["source"] == "a.pdf"
    assert chunk.metadata["file_hash"] == "abc123"
    assert chunk.metadata["indexed_at"] == "2026-08-11"


def test_units_are_processed_independently():
    """ページをまたいで結合しない。混ざるとページ番号が特定できなくなる。"""
    chunks = _chunk(
        [
            _unit("これは一ページ目に記載されている内容です。", location=1),
            _unit("これは二ページ目に記載されている内容です。", location=2),
        ]
    )
    assert len(chunks) == 2
    assert chunks[0].metadata["location"] == 1
    assert chunks[1].metadata["location"] == 2
