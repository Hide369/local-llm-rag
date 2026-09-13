"""ParsedUnit を ベクトルDB に入れる Chunk へ変換する。

基本単位はパーサーが返すユニットであり、長すぎるものだけを再分割する。
1ユニット=1ページ・1スライドとは限らない。PPTXはテキストボックスのまとまり
ごとに複数ユニットを返す（1スライドから平均で2ユニット弱）。実測では
就業規則841字/ページ、PPTX43スライド→80ユニット（平均156字/ユニット）、
画像PDF約1,673字/ページであり、議事録(551〜615字)は分割されず1件1チャンクに
収まる。
"""
import re
from collections import Counter

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingest.models import Chunk, ParsedUnit
# フェンスの判定は取り込み側と同じ規則を使う。別々に持つと、CommonMark に
# 合わせた規則（commit 9c212ee、字下げされた開きフェンスを数え落として2,205件の
# 見出しを失っていた）が片方にしか入らない状態が生まれる。
from ingest.parsers.md_parser import scan_fences

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
#
# **この定数は既にチャンクを捨てている。** feat/drop-navigation-slides の実測
# （2026-09-07、セミナー資料7本・ナビゲーション判定40ユニット）で、そのうち
# 2件が10字未満だった。
#
#   9字 '4\n推論結果の評価'  (CNN画像認識セミナー.pptx)
#   8字 '1\nマイコンとは'    (組み込みセミナー.pptx)
#
# この2件は本ブランチ以前からここで静かに捨てられており、DBに入っていなかった。
# 警告は出ないので、同じことが本文のユニットに起きても同じように気づけない。
#
# なお上の「最短11字」は章扉であり、現在は ingest/navigation.py が
# チャンク化の前に落とすためここには届かない。余裕は測り直す必要がある。
# 値を動かす／再分割するときはこの余裕を再測定すること。
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
        "vlm",
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

# コードブロックを丸ごと1チャンクに保つときの上限。
#
# 上限が要るのは、丸ごと保持すると巨大なチャンクが生じるためである。実測
# （2026-09-12、Streamlit の llms-full.txt）では chunk_size を超えるチャンクが
# 100件生じ、最大は24,864字だった。bge-m3 は入力窓を超えた分を切り捨てるので、
# 丸ごと残すと後ろが黙って失われる。割れても分割するほうがましである。
#
# 2400字（CHUNK_SIZEの3倍）にしたのは分布による。ブロック938個の中央値は122字、
# 平均465字で、2400字を超えるのは33個（3.5%）にとどまる。
MAX_CODE_BLOCK_CHARS = CHUNK_SIZE * 3

# 行頭のフェンスから行頭のフェンスまでを1ブロックとする。
#
# 区切り（_SEPARATORS）にフェンスを足す方法は採らない。実測では割れが
# 8.3%から17.0%へ悪化する。RecursiveCharacterTextSplitter は区切りの手前で
# 切るため、開きフェンスの手前だけでなく閉じフェンスの手前でも切り、
# コードブロックが本体と閉じフェンスに分断されるからである。
_CODE_BLOCK = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)

# 4字下げ（またはタブ）のコードブロック。Markdown はフェンスの前からこの記法を
# 持っており、HTML から変換した資料はこちらで書かれていることがある。
#
# 実測 2026-09-13: Python の言語リファレンス（548KB）はコードフェンスが18個しか
# 無く、文法の生成規則もコード例もすべて4字下げだった。フェンスだけを守っていた
# ときは、2行以上の字下げ塊244個のうち**61個（25%）**がチャンクの境界で割れて
# いた。
_INDENTED_LINE = re.compile(r"^(?: {4}|\t)")

# 箇条書きの行。字下げの塊を守る判定にだけ使う。
#
# **直前が箇条書きなら守らない。** 箇条書きの継続行も4字下げで書かれるため
# （`- 手順3` の下にぶら下がる説明など）、これを塊として切り出すと、継続行が
# 親の項目から切り離された単独のチャンクになって何の話か分からなくなる。
# 実測 2026-09-13（docs_source/ と source/ の全Markdown）: 2行以上の字下げ塊
# 2,494個のうち**671個（26.9%）が箇条書きの直後**にある。CommonMark の規則を
# 正しく実装するには本物のパーサーが要るので、取りこぼす側へ倒している。
_LIST_ITEM = re.compile(r"^[ \t]*([-*+]|\d+[.)])[ \t]+")


def _split(text: str) -> list[str]:
    """800字以下はそのまま返す。分割器を通すと余計な境界調整が入るため。

    素通りでも分割器を通した後でも、最後に必ずMIN_CHUNK_CHARS未満を捨てる。
    分割の副産物として句読点だけの断片が末尾に残ることがあり、素通りする
    3字の文書も分割で生じる3字の断片も、検索に使えないという点で同じだから。
    """
    parts = [text] if len(text) <= CHUNK_SIZE else _splitter.split_text(text)
    return [part for part in parts if len(part.strip()) >= MIN_CHUNK_CHARS]


def _indented_spans(text: str) -> list[tuple[int, int]]:
    """4字下げのコードブロックの範囲を返す。フェンスの中と箇条書きの下は除く。

    塊とみなす条件は3つある。どれも「本物のコードブロックだけを拾う」ために
    厳しめにしてある。取りこぼしても割れるだけだが、取りすぎると地の文が
    文脈から切り離された単独のチャンクになる。

    1. 空行のあとに始まること。段落の途中に現れる字下げはコードブロックでは
       ない（CommonMark: indented code block は段落を中断できない）。
    2. 直前の非空行が箇条書きでないこと（_LIST_ITEM のコメント）。
    3. 2行以上あること。1行だけの字下げは表の桁揃えや引用の折り返しが多い。
    """
    lines = text.split("\n")
    offsets, position = [], 0
    for line in lines:
        offsets.append(position)
        position += len(line) + 1
    flags = list(scan_fences(lines))

    spans: list[tuple[int, int]] = []
    previous = ""
    index = 0
    while index < len(flags):
        line, in_fence = flags[index]
        # 直前の行が空でなければ段落の続きである。ここを見落とすと地の文を
        # 塊として切り出してしまい、手前に残った短い断片が MIN_CHUNK_CHARS で
        # 捨てられて本文が消える。
        after_blank = index == 0 or not flags[index - 1][0].strip()
        if in_fence or not _INDENTED_LINE.match(line) or not line.strip() or not after_blank:
            if line.strip():
                previous = line
            index += 1
            continue
        # 字下げが続くかぎり進む。間の空行は塊の一部として認める（コード例は
        # 空行を含む）が、末尾の空行は塊に入れない。
        end = index
        while end < len(flags) and not flags[end][1] and (
            _INDENTED_LINE.match(flags[end][0]) or not flags[end][0].strip()
        ):
            end += 1
        while end > index and not flags[end - 1][0].strip():
            end -= 1
        if end - index >= 2 and not _LIST_ITEM.match(previous):
            spans.append((offsets[index], offsets[end - 1] + len(flags[end - 1][0])))
        previous = flags[end - 1][0]
        index = end
    return spans


def _atomic_spans(text: str) -> list[tuple[int, int]]:
    """分割器に通さない範囲。フェンスが優先で、重なる字下げは捨てる。"""
    fenced = [(m.start(), m.end()) for m in _CODE_BLOCK.finditer(text)]
    spans = fenced + [
        span
        for span in _indented_spans(text)
        if not any(start < span[1] and span[0] < end for start, end in fenced)
    ]
    return sorted(spans)


def _split_keeping_code(text: str) -> list[str]:
    """コードブロックは分割器に通さず1片として残し、地の文だけを分割する。

    コード例が途中で切れると、検索で当たってもモデルには構文として壊れた
    断片が渡る。実測（2026-09-12、Streamlit の llms-full.txt）では、既定の
    分割で3,427チャンク中284件（8.3%）が割れていた。この方式では4件（0.1%）
    まで落ちる（残る4件は元の文書のフェンスが対になっていない箇所である）。

    守るのはフェンスだけではない。4字下げのコードブロックも同じ扱いにする
    （_indented_spans）。HTML から変換した資料はこちらで書かれていることがあり、
    実測では Python の言語リファレンスの塊244個中61個が割れていた。

    MAX_CODE_BLOCK_CHARS を超えるブロックだけは地の文と同じ分割器に通す。
    理由は定数のコメントを参照。
    """
    parts: list[str] = []
    last = 0
    for start, end in _atomic_spans(text):
        prose = text[last:start]
        emitted = _split(prose)
        parts.extend(emitted)
        # 分割器が拾わなかった末尾をブロックの先頭に付ける。_split は
        # MIN_CHUNK_CHARS 未満を捨てるので、そのまま流すと「And:」「After」の
        # ような短い導入文がどのチャンクにも入らず消える（実測 2026-09-13:
        # 技術ドキュメント全体で14行）。付ける先をブロックにするのは、導入文が
        # そもそもその例を指しているからでもある。
        tail = prose[prose.rfind(emitted[-1]) + len(emitted[-1]) :] if emitted else prose
        block = tail + text[start:end]
        parts.extend([block] if len(block) <= MAX_CODE_BLOCK_CHARS else _split(block))
        last = end
    parts.extend(_split(text[last:]))
    return parts


def chunk_units(
    units: list[ParsedUnit],
    source: str,
    file_hash: str,
    indexed_at: str,
    keep_code_blocks: bool = False,
) -> list[Chunk]:
    """各ユニットを独立にチャンク化する。

    ユニットをまたいで結合しない。結合するとチャンクがページ境界を越え、
    「何ページ目の記述か」を一意に示せなくなる。

    チャンク番号はユニット内ではなく (location_type, location) ごとの通し番号に
    する。PPTXは1スライドが複数ユニットになるため（spec 7.5）、ユニット内で
    0から振り直すとIDが衝突し、ストアが例外を出さずに上書きしてチャンクを失う
    （INSERT OR REPLACE のため。ChromaDB時代から変わらない）。
    1ロケーション1ユニットの他形式では 0,1,2… の並びが従来と変わらないため、
    既存チャンクのIDは1件も変化しない。

    keep_code_blocks は技術ドキュメントの取り込みだけが True にする。既定を
    False にしているのは、社内資料の取り込み結果を1バイトも変えないためである。
    """
    chunks: list[Chunk] = []
    numbers: Counter = Counter()
    for unit in units:
        text = unit.text.strip()
        if not text:
            continue
        location_key = (unit.location_type, unit.location)
        split = _split_keeping_code if keep_code_blocks else _split
        for part in split(text):
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
                        "vlm": unit.vlm,
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
