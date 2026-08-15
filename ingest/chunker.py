"""ParsedUnit を ベクトルDB に入れる Chunk へ変換する。

基本単位はパーサーが返すユニットであり、長すぎるものだけを再分割する。
1ユニット=1ページ・1スライドとは限らない。PPTXはテキストボックスのまとまり
ごとに複数ユニットを返す（1スライドから平均で2ユニット弱）。実測では
就業規則841字/ページ、PPTX43スライド→80ユニット（平均156字/ユニット）、
画像PDF約1,673字/ページであり、議事録(551〜615字)は分割されず1件1チャンクに
収まる。
"""
from collections import Counter

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingest.models import Chunk, ParsedUnit

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 内容がなさすぎるチャンクは検索の役に立たないだけでなく、実害がある。
# 実測（scripts/check_retrieval.py, bge-m3 / 当時280チャンクだったコーパスで）で、
# 句読点1字だけのチャンク（'。'）が埋め込まれてDBに残っており、その位置がコーパスの重心付近
# だったため、「こんにちは」のような意味的に空な入力の最近傍として必ず
# ヒットしてしまっていた。10はその1字を切り捨てるための値である。
#
# 余裕は当初の5字から1字まで縮んでいる。PPTXをテキストボックス単位に
# 再分割した後の実測では、コーパス中で最短の意味あるユニットは11字
# （スライド5「1\n生成AIの基礎知識」）であり、10との差はわずか1字しかない。
# 現状これで捨てられているチャンクは無いが、将来また再チャンク化して
# 10字ちょうどのユニットが生まれれば、この定数は何の警告も出さずにそれを
# 静かに捨てる。値を動かす／再分割するときはこの余裕を再測定すること。
MIN_CHUNK_CHARS = 10

# チャンク自身が使うメタデータのキー。フロントマター由来の属性がこれらと
# 同名だった場合は採用しない。source を上書きされると出典表示と差分取り込みの
# ハッシュ判定が同時に壊れ、しかも例外が出ないため気づけない。
RESERVED_METADATA_KEYS = frozenset(
    {
        "source",
        "file_hash",
        "location_type",
        "location",
        "ocr",
        "heading",
        "chunk_index",
        "indexed_at",
    }
)

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
