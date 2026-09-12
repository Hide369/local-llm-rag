from ingest.chunker import (
    CHUNK_SIZE,
    MAX_CODE_BLOCK_CHARS,
    MIN_CHUNK_CHARS,
    RESERVED_METADATA_KEYS,
    chunk_units,
)
from ingest.models import SECTION, ParsedUnit


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


def test_vlm_flag_is_carried_into_every_chunk():
    unit = ParsedUnit(text="あ" * 2000, location_type="page", location=1, vlm=True)
    chunks = _chunk([unit])
    assert all(c.metadata["vlm"] is True for c in chunks)


def test_vlm_flag_defaults_to_false():
    chunks = _chunk([_unit("これは十分な長さのある本文です。")])
    assert chunks[0].metadata["vlm"] is False


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


def test_units_sharing_a_location_get_distinct_ids():
    """PPTXは1スライドが複数ユニットになる（spec 7.5）。IDが衝突すると
    ストアが黙って上書きし、チャンクが消える。例外は出ない。"""
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


def _long_prose(marker: str, length: int) -> str:
    """分割器に確実に掛かる長さの地の文。句点があるので日本語の区切りで切れる。"""
    sentence = f"{marker}はここに説明があります。"
    return sentence * (length // len(sentence) + 1)


def test_a_code_block_is_not_split_when_code_blocks_are_kept():
    """コードブロックが割れると、モデルには不完全なコードが渡る。

    実測（2026-09-12、Streamlit の llms-full.txt）では、既定の分割で
    3,427チャンク中284件（8.3%）がフェンスの途中で割れていた。
    """
    code = "```python\n" + "x = 1\n" * 60 + "```"
    text = _long_prose("前置き", 900) + "\n\n" + code + "\n\n" + _long_prose("後書き", 900)
    unit = ParsedUnit(text=text, location_type=SECTION, location=1)

    chunks = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)

    assert all(chunk.text.count("```") % 2 == 0 for chunk in chunks)
    assert any(chunk.text.strip() == code for chunk in chunks)


def test_a_code_block_longer_than_the_limit_is_split():
    """上限未満のブロックは丸ごと残り、上限を超えるブロックは割れる。

    この対比を同じユニット内で確認するのが目的である。単に「巨大な入力を
    渡して len(chunks) > 1 かつ全チャンクが上限以下」なことだけを見るテスト
    では、フェンス認識が丸ごと壊れて地の文の分割器（_split）に落ちても
    両方の条件がそのまま成立してしまう（800字ずつに割られた断片は当然
    2400字の上限以下になるため）。それではコードブロックが実際に
    フェンスとして認識されたことの証明にならない。

    上限未満のブロック（913字。CHUNK_SIZE=800より長いので、フェンスを
    認識せず地の文の分割器に落ちれば必ず割れる）が丸ごと1チャンクとして
    残ることと、上限超えのブロック（bge-m3 の入力窓を超え、実測の最大値
    24,864字に近い規模）が複数チャンクに割れて上限以下に収まることを
    同時に確認することで、フェンス認識が効いていることを検証する。
    """
    kept_whole = "```python\n" + "x = 1\n" * 150 + "```"
    assert CHUNK_SIZE < len(kept_whole) <= MAX_CODE_BLOCK_CHARS
    huge = "```python\n" + "y = 2\n" * 1000 + "```"
    assert len(huge) > MAX_CODE_BLOCK_CHARS

    text = (
        _long_prose("前置き", 900)
        + "\n\n" + kept_whole
        + "\n\n" + _long_prose("中間", 900)
        + "\n\n" + huge
    )
    unit = ParsedUnit(text=text, location_type=SECTION, location=1)

    chunks = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)

    # 上限未満のブロックは丸ごと1チャンクのまま現れる。
    assert any(chunk.text.strip() == kept_whole for chunk in chunks)
    # 上限超えのブロックは丸ごとのままでは現れず、複数チャンクに割れている。
    assert not any(chunk.text.strip() == huge for chunk in chunks)
    huge_pieces = [chunk for chunk in chunks if "y = 2" in chunk.text]
    assert len(huge_pieces) > 1
    assert all(len(chunk.text) <= MAX_CODE_BLOCK_CHARS for chunk in huge_pieces)


def test_keeping_code_blocks_is_off_by_default():
    """社内資料の取り込み結果を1バイトも変えないための既定。"""
    code = "```python\n" + "x = 1\n" * 60 + "```"
    text = _long_prose("前置き", 900) + "\n\n" + code
    unit = ParsedUnit(text=text, location_type=SECTION, location=1)

    default = chunk_units([unit], "a.md", "hash", "2026-09-12")
    explicit = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=False)

    assert [chunk.text for chunk in default] == [chunk.text for chunk in explicit]


def test_prose_without_any_code_block_is_chunked_the_same_either_way():
    """コードが無ければ、どちらの経路でも結果は同じでなければならない。

    切り分けの処理が地の文の分割まで変えてしまっていないかを見る。
    """
    unit = ParsedUnit(text=_long_prose("本文", 2000), location_type=SECTION, location=1)

    off = chunk_units([unit], "a.md", "hash", "2026-09-12")
    on = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)

    assert [chunk.text for chunk in off] == [chunk.text for chunk in on]


def test_chunk_ids_stay_sequential_when_code_blocks_are_kept():
    """IDが重複すると、ストアが例外を出さずに上書きしてチャンクを失う。

    INSERT OR REPLACE のため、衝突は静かに起きる。
    """
    code = "```python\nx = 1\n```"
    unit = ParsedUnit(
        text=_long_prose("前", 900) + "\n\n" + code + "\n\n" + _long_prose("後", 900),
        location_type=SECTION,
        location=1,
    )
    chunks = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)
    ids = [chunk.id for chunk in chunks]
    assert len(ids) == len(set(ids))
    assert ids == [f"a.md::section1::{index}" for index in range(len(chunks))]
