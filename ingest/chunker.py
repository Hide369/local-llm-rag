"""ParsedUnit を ベクトルDB に入れる Chunk へ変換する。

1ページ・1スライドを基本単位とし、長すぎるものだけを再分割する。
実測では就業規則841字/ページ、PPTX304字/スライド、画像PDF約1,673字/ページであり、
議事録(551〜615字)は分割されず1件1チャンクに収まる。
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingest.models import Chunk, ParsedUnit

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 日本語は空白で語が区切られないため、句読点を区切り候補に含める。
# これがないと文の途中で不自然に切れて検索精度が落ちる。
_SEPARATORS = ["\n\n", "\n", "。", "、", " ", ""]

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=_SEPARATORS,
)


def _split(text: str) -> list[str]:
    """800字以下はそのまま返す。分割器を通すと余計な境界調整が入るため。"""
    if len(text) <= CHUNK_SIZE:
        return [text]
    return [part for part in _splitter.split_text(text) if part.strip()]


def chunk_units(
    units: list[ParsedUnit], source: str, file_hash: str, indexed_at: str
) -> list[Chunk]:
    """各ユニットを独立にチャンク化する。

    ユニットをまたいで結合しない。結合するとチャンクがページ境界を越え、
    「何ページ目の記述か」を一意に示せなくなる。
    """
    chunks: list[Chunk] = []
    for unit in units:
        text = unit.text.strip()
        if not text:
            continue
        for index, part in enumerate(_split(text)):
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
                        "chunk_index": index,
                        "indexed_at": indexed_at,
                    },
                )
            )
    return chunks
