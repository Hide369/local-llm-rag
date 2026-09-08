"""Excelブックのテキスト抽出。

1シート=1ユニットにする。PDFのページ・PPTXのスライドと同じく、シートは
書き手が引いた区切りそのものだからである。長いシートは後段の chunk_units が
CHUNK_SIZE で分割する。

表は1本の文字列に潰す時点で行と列の関係を失う。セルを ' | ' で、行を改行で
つなぐのは、見出し行との対応を読み手（および回答を組み立てるLLM）が復元
できるようにするためで、区切りを空白にすると値が地続きになって復元できない。
"""
from pathlib import Path

from openpyxl import load_workbook

from ingest.models import SHEET, ParsedUnit

_CELL_SEPARATOR = " | "


def _row_text(row) -> str:
    """1行を1本の文字列にする。未入力セルは空文字として詰める。

    openpyxl は未入力セルに None を返す。str() をそのまま通すと本文に 'None'
    が並び、その語が索引されて全シートに共通の無意味な語ができる。
    """
    cells = ["" if value is None else str(value).strip() for value in row]
    while cells and not cells[-1]:
        # 末尾の空セルは列幅の都合で無限に続くことがある。落とさないと
        # 1行が ' |  |  | ...' で埋まり、本文が区切り記号だけになる。
        cells.pop()
    return _CELL_SEPARATOR.join(cells)


def parse_xlsx(path: Path) -> list[ParsedUnit]:
    # data_only=True は数式ではなく計算結果を取る。'=SUM(A1:A2)' を索引しても
    # 利用者が読む値はどこにも残らず、検索でも回答でも使えない。
    # Excelが計算結果を保存していないブックでは値が None になるが、その場合に
    # 数式を代わりに入れることはしない。数式は本文ではないためである。
    book = load_workbook(path, data_only=True, read_only=True)
    try:
        units: list[ParsedUnit] = []
        for sheet in book.worksheets:
            lines = [text for text in (_row_text(row) for row in sheet.iter_rows(values_only=True)) if text]
            if not lines:
                # 空シートはブックに残りがちである。ユニットを作ると空の
                # チャンクがDBに入り、どの質問にも弱く一致する。
                continue
            units.append(
                ParsedUnit(
                    # シート名を本文の先頭に置く。シート単体で検索に引かれたとき
                    # 何の表なのか分からなくなるのを防ぐためで、md_parser が
                    # 各セクションにH1を付けているのと同じ判断である。
                    text="\n".join([sheet.title, *lines]),
                    location_type=SHEET,
                    # 通し番号にするのはシート名の重複でチャンクIDが衝突しない
                    # ようにするため。表示にはheadingを使う。
                    location=len(units) + 1,
                    heading=sheet.title,
                )
            )
        return units
    finally:
        # read_only=True はファイルハンドルを開いたままにする。閉じないと
        # Windowsではそのブックを別プロセスが開けなくなる。
        book.close()
