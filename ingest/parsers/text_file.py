"""テキストファイルの読み取り。文字コードの判定だけを受け持つ。

txt・HTML・ソースコードのどれもここを通る。判定を各パーサーに持たせると、
片方にだけ符号化が足された状態が生まれ、同じ資料が形式によって読めたり
読めなかったりする。
"""
from pathlib import Path

# utf-8-sig を先に試すのは、BOM付きでもBOM無しでも正しく読めるためである
# （ingest/parsers/md_parser.py と同じ判断）。BOMを残すとU+FEFFが先頭語に
# くっつき、その語で永久に引けなくなる。
#
# cp932 を後ろに置くのは、Windowsのメモ帳が長らく既定でこれを使っており、
# 社内資料に現に混ざるためである。utf-8 だけで決め打つと UnicodeDecodeError
# になり、その資料は「取り込み失敗」として丸ごと落ちる。バッチファイル
# （.bat）も同じ理由でこちらに倒れる。
#
# 逆順にはできない。cp932 はほぼ任意のバイト列を（無意味な文字列としてでも）
# 復号してしまうため、先に試すとUTF-8の資料が文字化けしたまま通ってしまう。
ENCODINGS = ("utf-8-sig", "cp932")


def read_text_file(path: Path) -> str:
    """改行を \n に揃えたテキストを返す。判別できなければ ValueError。"""
    last_error: UnicodeDecodeError | None = None
    for encoding in ENCODINGS:
        try:
            text = path.read_text(encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error
            continue
        return text.replace("\r\n", "\n").replace("\r", "\n")
    raise ValueError(
        f"文字コードを判別できません（{' / '.join(ENCODINGS)} で失敗）: {path.name}"
    ) from last_error
