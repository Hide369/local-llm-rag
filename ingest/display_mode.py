"""質問文から、回答を記法そのもので出すかどうかを決める。

design: docs/superpowers/plans/2026-09-11-image-ingestion.md の Task 11

Streamlit 1.61 は mermaid を同梱しており（streamlit/static/static/js/ に
architectureDiagram 等が入っている）、```mermaid フェンスは図として描画される。
マークダウンも st.write が描画する。どちらも「レンダリング後」しか画面に出ず、
記法を見たい・他所へ持ち出したい利用者はそれを取り出せない。

UIからしか呼ばれないが、UIには依存しない。ingest/prompting.py と同じ理由で
ここに置く。Streamlitスクリプトに書くと、テストがインポートしただけで
スクリプト全体が走り本番DBを開いてしまう。
"""
import re

# 表示の意図を示す語。ここに「教え」は入れない。「〜を教えてください」は
# このアプリのほぼ全質問の語尾であり、書式の意図を何も示さないためである。
# 入れると「マークダウンとは何か教えてください」で回答が丸ごとコードブロックになる。
_INTENT = r"(?:表示|出力|見せ|示し|書い|出し)"

# 書式の語と意図語の間に入る「で」「記法そのものを」「のソースを」を吸収する幅。
# 広げるほど、記法自体を尋ねる質問を誤って拾う。
_GAP = r".{0,8}?"

# 素の md は語として採らない。「手順書.md の内容を教えて」のように
# ファイル名として質問に現れるためである。
#
# マーメイドを先に見る。両方の語が出たとき（「マークダウンの中にマーメイドで」）は、
# より具体的な指定である図の記法のほうが利用者の狙いである可能性が高い。
_PATTERNS = (
    ("mermaid", re.compile(rf"(?:マーメイド|mermaid)(?:記法|形式)?{_GAP}{_INTENT}", re.IGNORECASE)),
    ("markdown", re.compile(rf"(?:マークダウン|markdown)(?:記法|形式)?{_GAP}{_INTENT}", re.IGNORECASE)),
)


def detect(question: str) -> str | None:
    """記法そのものを求められているなら、その名前を返す。

    返り値は st.code の language 引数にそのまま渡せる文字列にしてある。
    表記を2箇所で持たないための約束であり、変えるときは呼び出し側も見ること。

    書式の語があるだけでは成立させない。判定は質問1つごとに閉じており、
    前のターンの指定は持ち越さない。持ち越すと、利用者が何も言っていないのに
    コードブロックで返り続けることになる。
    """
    if not question:
        return None
    for name, pattern in _PATTERNS:
        if pattern.search(question):
            return name
    return None
