"""ParsedUnit を ベクトルDB に入れる Chunk へ変換する。

1ページ・1スライドを基本単位とし、長すぎるものだけを再分割する。
実測では就業規則841字/ページ、PPTX304字/スライド、画像PDF約1,673字/ページであり、
議事録(551〜615字)は分割されず1件1チャンクに収まる。
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingest.models import Chunk, ParsedUnit

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 内容がなさすぎるチャンクは検索の役に立たないだけでなく、実害がある。
# 実測（scripts/check_retrieval.py, bge-m3 / 280チャンク）で、句読点1字だけの
# チャンク（'。'）が埋め込まれてDBに残っており、その位置がコーパスの重心付近
# だったため、「こんにちは」のような意味的に空な入力の最近傍として必ず
# ヒットしてしまっていた。コーパス中で最短の意味あるチャンクは15字
# （'。 横展開：コア構成はそのまま'）、内容のないチャンクは1字（'。'）のみ
# だったため、両者の間に余裕を持って10を採る（RELEVANCE_THRESHOLDと同じ、
# 実測して決める方法）。
MIN_CHUNK_CHARS = 10

# 日本語は空白で語が区切られないため、句読点を区切り候補に含める。
# これがないと文の途中で不自然に切れて検索精度が落ちる。
_SEPARATORS = ["\n\n", "\n", "。", "、", " ", ""]

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=_SEPARATORS,
)


def _split(text: str) -> list[str]:
    """800字以下はそのまま返す。分割器を通すと余計な境界調整が入るため。

    素通りでも分割器を通した後でも、最後に必ずMIN_CHUNK_CHARS未満を捨てる。
    分割の副産物として句読点だけの断片が末尾に残ることがあり、素通りする
    3字の文書も分割で生じる3字の断片も、検索に使えないという点で同じだから。
    """
    parts = [text] if len(text) <= CHUNK_SIZE else _splitter.split_text(text)
    return [part for part in parts if len(part.strip()) >= MIN_CHUNK_CHARS]


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
