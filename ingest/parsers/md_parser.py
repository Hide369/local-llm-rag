"""Markdownのテキスト抽出。

`##` 見出しは書き手が引いた話題の境界そのものなので、PPTXのスライドと同じく
1見出し=1ユニットとする。source/家電製品/ の30件を実測したところ、セクションは
最小76字・中央値157字・最大448字であり、CHUNK_SIZE(800)を超えないため
再分割は一度も起きない。

各ユニットの先頭にはH1（例 'UD-0900i IoTコンパクト'）を1行付ける。
'## 設置情報' だけを検索で引いたときに、どの製品の設置情報なのか分からなく
なるのを防ぐためで、これがこの形式を扱ううえでの要になる。
"""
import re
import sys
import urllib.parse
from pathlib import Path

from ingest.image_text import describe_image, has_caption, has_ocr
from ingest.models import SECTION, ParsedUnit

_FENCE = "```"

# ![alt](path) と ![alt](path "title")。altは空でもよい。パスに空白は許さない
# （Markdownでは <> で囲む記法になるが、この資料群には現れない）。
_IMAGE = re.compile(r'!\[[^\]]*\]\(\s*([^)\s]+)(?:\s+"[^"]*")?\s*\)')

# 取りに行かない参照。http(s) は外部へ出る通信になり（AGENTS.md の方針）、
# data: はこの資料群に現れない。
_REMOTE_PREFIXES = ("http://", "https://", "data:")


def _resolve(reference: str, base: Path) -> Path | None:
    """参照先をmdのあるディレクトリからの相対で解決する。

    資料が指定した文字列をそのままファイルシステムへ渡す唯一の箇所である。
    .. を辿って外へ出る参照は拒む。取り込みは利用者がアップロードした資料にも
    走るため、資料の中身が読める範囲を資料自身に決めさせてはいけない。
    """
    candidate = (base / urllib.parse.unquote(reference)).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _replace_images(line: str, base: Path, path_name: str, caption_image, ocr_bytes, on_missing_image) -> str:
    """1行の中の画像参照を説明文へ置き換える。

    行ごと消して末尾へ集めるのではなくその場で置き換えるのは、画像が前後の文と
    一緒に1つのセクション（=1チャンク）に入るようにするためである。

    読めなかった画像はリンク記法ごと消す。![](…) を残しても検索の役に立たず、
    回答へ引き写されると存在しない画像を指すことになる。
    """

    def _one(match):
        reference = match.group(1)
        if reference.startswith(_REMOTE_PREFIXES):
            # 記法をそのまま残す。取りに行かないと決めた以上、説明文は作れない。
            return match.group(0)
        resolved = _resolve(reference, base)
        if resolved is None:
            print(
                f"警告: 画像が見つかりません（{path_name}）: {reference}",
                file=sys.stderr,
            )
            if on_missing_image is not None:
                on_missing_image(reference)
            return ""
        return describe_image(
            resolved.read_bytes(),
            caption_image,
            ocr_bytes=ocr_bytes,
            label=f"{path_name} {reference}",
        ) or ""

    return _IMAGE.sub(_one, line)


def _read_lines(path: Path) -> list[str]:
    r"""CRLFを正規化して行に分ける。

    実データ30件はすべてCRLFであり、そのままだと見出し文字列の末尾に \r が残って
    出典が「＞ 設置情報\r」のように壊れる。encoding を省略しないのは、Windowsの
    既定が CP932 で日本語の読み込みに必ず失敗するため。

    utf-8 ではなく utf-8-sig を使うのは、BOM付きファイルだとBOM文字（U+FEFF）が
    先頭行の '---' にくっつき、_split_frontmatter が先頭のフロントマター境界を
    認識できず、フロントマターの生のYAMLがそのまま索引されてしまうため。
    BOMなしのファイルはutf-8-sigでも同じ結果になるので、常にこちらを使ってよい。
    """
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _scalar(value: str):
    """YAMLのスカラー値をPythonの型に直す。採用しない値には None を返す。

    数値に見えるものを int / float にするのは、絞り込みの where が数値比較を
    するため（ingest/vector_store.py の _compare）。文字列のまま入れると
    26 <= "9.0" のような比較になり、$lte が黙って効かなくなる。
    """
    text = value.strip()
    if not text or text.startswith("["):
        # 配列は where が部分一致を扱えず、メタデータとしては実用にならない。
        # 値は _array_values が本文側で拾う。
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_attributes(lines: list[str]) -> dict:
    """`key: value` の平らな行だけを拾う。

    字下げされた行は入れ子の属性であり、平らなメタデータには載せられないので飛ばす。
    """
    attributes: dict = {}
    for line in lines:
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        scalar = _scalar(value)
        if key.strip() and scalar is not None:
            attributes[key.strip()] = scalar
    return attributes


def _array_values(lines: list[str]) -> str:
    """配列の値だけを空白区切りで集める。

    `_scalar` が配列を捨てるのはメタデータとして使えないからであって、値に
    価値が無いからではない。「学生向け」「省スペース」といった語は本文に一度も
    現れないことがあり、捨てれば索引から永久に失われる。noise_wash_db を
    捨てなかったのと同じ理由で、置き場所をメタデータから本文へ移して拾う。

    キー名は載せない。`tags` のような語が全チャンクに現れると、質問にその語が
    含まれたときどの資料も等しく一致し、順位を決める力を持たないためである。

    区切りを空白にしているのは ingest/lexical.py の分かち書きに合わせるため。
    `\\W+` が境界になり、区切りを跨いだbigramは作られない。したがって
    「超コンパクト」と「洗濯専用」が混ざった語で一致することはない。
    """
    values: list[str] = []
    for line in lines:
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(":")
        text = value.strip()
        if not separator or not key.strip() or not text.startswith("["):
            continue
        values.extend(item.strip() for item in text.strip("[]").split(",") if item.strip())
    return " ".join(values)


def _split_frontmatter(lines: list[str]) -> tuple[dict, str, list[str]]:
    """先頭のYAMLフロントマターを属性と配列値に分け、本文と一緒に返す。

    フロントマターの生テキストを埋め込みに入れない判断は当初から変えていない。
    YAMLの生テキストより散文のほうが日本語の質問との類似度が出るためである。
    変えたのは「捨てる」ことのほうで、noise_wash_db は30製品中24製品で本文に
    一度も現れず、捨てると索引から永久に失われることが実測で分かった。

    スカラーと配列で行き先が分かれるのは、where で絞り込めるかどうかが違うため
    である。絞り込める値はメタデータへ、絞り込めない値は本文へ置く。
    """
    if not lines or lines[0].strip() != "---":
        return {}, "", lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            frontmatter = lines[1:index]
            return (
                _parse_attributes(frontmatter),
                _array_values(frontmatter),
                lines[index + 1 :],
            )
    return {}, "", lines  # 閉じられていないなら本文とみなす


def parse_md(path: Path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]:
    attributes, array_values, body_lines = _split_frontmatter(_read_lines(path))
    title = ""
    sections: list[tuple[str, list[str]]] = []
    heading: str = ""
    body: list[str] = []
    in_fence = False
    # 画像を読む手立てが1つも無いなら走査もしない。従来の取り込み結果と
    # 1バイトも変わらないことを保証するため。
    read_images = caption_image is not None or ocr_bytes is not None

    for line in body_lines:
        if line.startswith(_FENCE):
            in_fence = not in_fence
        elif not in_fence:
            if line.startswith("## "):
                sections.append((heading, body))
                heading, body = line[3:].strip(), []
                continue
            if not title and line.startswith("# "):
                title = line[2:].strip()
                continue
            if read_images and "![" in line:
                line = _replace_images(
                    line, path.parent, path.name, caption_image, ocr_bytes, on_missing_image
                )
                if not line.strip():
                    # 画像だけの行が読めなかった場合、空行だけが残る。
                    continue
        body.append(line)
    sections.append((heading, body))

    units: list[ParsedUnit] = []
    for section_heading, section_body in sections:
        text = "\n".join(section_body).strip()
        if not text:
            continue
        unit_text = "\n".join(
            part for part in (title, array_values, section_heading, text) if part
        )
        units.append(
            ParsedUnit(
                text=unit_text,
                location_type=SECTION,
                # 見出し文字列ではなく通し番号を位置にする。同じ見出しが2つある文書で
                # チャンクIDが衝突するのを防ぐため、IDの一意性を文書構造に依存させない。
                location=len(units) + 1,
                heading=section_heading,
                attributes=attributes,
                ocr=has_ocr(unit_text),
                vlm=has_caption(unit_text),
            )
        )
    return units
