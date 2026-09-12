"""質問文から、回答を記法そのもので出すかどうかを決める。

Streamlit 1.61 は mermaid を同梱しており（streamlit/static/static/js/ に
architectureDiagram 等が入っている）、```mermaid フェンスは図として描画される。
マークダウンも st.write が描画する。記法を見たい・コピーしたい利用者は、
今の画面からはそれを取り出せない。

書式の語があるだけでは判定しない。「マークダウンとは何ですか」のような
記法自体を尋ねる質問で、回答が丸ごとコードブロックになってしまうためである。
"""
import pytest

from ingest.display_mode import detect


@pytest.mark.parametrize(
    "question",
    [
        "マークダウンで表示して",
        "マークダウン記法そのものを表示してください",
        "結果をマークダウンで出力して",
        "マークダウンのソースを見せて",
        "Markdownで書いてください",
        "markdown形式で出して",
    ],
)
def test_a_markdown_request_is_detected(question):
    assert detect(question) == "markdown"


@pytest.mark.parametrize(
    "question",
    [
        "マーメイドで表示して",
        "マーメイド記法で書いてください",
        "処理の流れをmermaidで図示して",
        "Mermaidのコードを見せて",
    ],
)
def test_a_mermaid_request_is_detected(question):
    assert detect(question) == "mermaid"


@pytest.mark.parametrize(
    "question",
    [
        "マークダウンとは何ですか",
        "手順書.md の内容を教えて",
        "就業規則について教えてください",
        "マーメイドという言葉の意味は",
        "",
    ],
)
def test_an_ordinary_question_is_not_a_format_request(question):
    """書式の語があるだけでは成立させない。誤作動すると回答が読めなくなる。"""
    assert detect(question) is None


def test_asking_what_markdown_is_does_not_switch_the_display():
    """「〜を教えてください」はこのアプリのほぼ全質問の語尾であり、
    書式の意図を示さない。意図語に含めると、記法を尋ねる質問で
    回答が丸ごとコードブロックになる。
    """
    assert detect("マークダウンとは何か教えてください") is None


def test_mermaid_wins_when_both_words_appear():
    """両方出たときはより具体的な指定を採る。

    「マークダウンの中にマーメイドで」のような頼み方で、図の記法のほうが
    利用者の狙いである可能性が高い。
    """
    assert detect("マークダウンの中にマーメイドで図を書いて") == "mermaid"


def test_bare_md_is_not_a_format_word():
    """.md がファイル名として質問に現れるため、素の md は語として採らない。"""
    assert detect("md で表示して") is None


def test_a_known_false_positive_asking_about_the_source_format():
    """既知の誤検出であり、直さない。

    「この資料はマークダウンで書いてありますか」は資料の書式を尋ねているだけで
    表示形式の指定ではないが、「マークダウン」から8文字以内に意図語「書い」
    （「書いてあります」の一部）が来るため "markdown" と判定される。
    「Markdownで書いてください」（意図的な陽性、上のテスト）と語彙だけでは
    区別できず、意図語から「書い」を抜くと今度はこちらを取りこぼす。
    結果はコードブロック表示という見た目の崩れだけで、回答自体は失われない
    ため、実害の小さいこの誤検出は許容する（レビュー2026-09-12）。
    """
    assert detect("この資料はマークダウンで書いてありますか") == "markdown"


def test_the_returned_name_is_usable_as_a_code_language():
    """返り値は st.code の language にそのまま渡す。表記を揺らさない。"""
    assert detect("マークダウンで表示して") == "markdown"
    assert detect("マーメイドで表示して") == "mermaid"
