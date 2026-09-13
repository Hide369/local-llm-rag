"""雛形の印（プレースホルダ）の記法。

記法を知る場所をここ1つに閉じる。4つの形式（docx/xlsx/pptx/md）すべてが同じ
規則で動く必要があり、形式ごとに正規表現を書くと、片方だけ直した状態が例外を
出さずに成立する。

名前は利用者が読む日本語をそのまま使う（`{{決定事項}}`）。画面の「埋まらな
かった欄」とLLMへの指示の両方にこの文字列が出るため、読めない記号にしない。
"""
import re

# 中に { } を含まないものだけを印とみなす。コード例を載せた雛形で、入れ子の
# 波括弧を印と取り違えないため。
_MARK = re.compile(r"\{\{([^{}]+)\}\}")


def names(text: str) -> list[str]:
    """出現順に、重複を除いた印の名前を返す。

    重複を除くのは、同じ印を表紙とヘッダーの2箇所に置く雛形があるためである。
    2回数えると画面の「埋まらなかった欄」も二重に出る。
    """
    found: list[str] = []
    for match in _MARK.finditer(text):
        name = match.group(1).strip()
        if name and name not in found:
            found.append(name)
    return found


def replace(text: str, values: dict[str, str]) -> str:
    """値のある印だけを置き換える。

    値の無い印は `{{名前}}` のまま残す。空にすると、利用者はもともと空欄の
    書式なのか埋め損ねたのかを見分けられない（scripts/code_references.py が
    解決できなかった :::code を元の行のまま残すのと同じ判断）。
    """

    def _one(match: re.Match) -> str:
        name = match.group(1).strip()
        value = values.get(name)
        return match.group(0) if value is None else value

    return _MARK.sub(_one, text)
