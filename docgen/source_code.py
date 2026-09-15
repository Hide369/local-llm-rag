"""雛形なしでソースコードを書かせる。

文書の経路（docgen/freeform.py → docgen/markdown_document.py）とは分ける。
あちらは Markdown を1回書かせ、見出し・段落・表・箇条書きに解析してから4つの
形式へ組む。コードをその解析器へ通すと、`#` で始まるコメントが見出しになり、
`|` を含む行が表になる。コードに「文書の構造」は無いので、中間表現を挟まず
そのままファイルにする。

材料の並べ方（検索結果・添付・プロジェクトの一覧）は文書と同じものを使う
（freeform.evidence_sections）。2つに分かれていると、片方にだけ資料の種類が
足された状態が例外を出さずに成立する。
"""
import re

from docgen.filling import MAX_PROMPT_CHARS, PromptTooLongError
from docgen.freeform import evidence_sections

# 拡張子から、プロンプトでモデルに名乗る言語名へ。「コードを書け」だけでは
# 何の言語か決まらない。
_LANGUAGES = {".go": "Go", ".cs": "C#"}

OUTPUT_SUFFIXES = tuple(_LANGUAGES)

# 参照したファイルの見出し。Go も C# も行コメントは // である。
_COMMENT = "//"
REFERENCES_HEADING = "参照したファイル"

# 返答に混ざったコードフェンス。情報文字列（```go など）を伴ってよい。
# フェンスの外側にある「以下が実装です」のような前置きごと落とすため、
# 本文全体からフェンスの中身だけを取り出す形にしてある。
_FENCE = re.compile(r"```[ \t]*\w*[ \t]*\r?\n(?P<source>.*?)\r?\n?```", re.DOTALL)


class UnsupportedLanguageError(Exception):
    """ソースコードとして出力できない拡張子を渡された。"""


def _language(suffix: str) -> str:
    found = _LANGUAGES.get(suffix.lower())
    if found is None:
        raise UnsupportedLanguageError(f"ソースコードにできない形式です: {suffix}")
    return found


def build_prompt(question, sources, attachments, tree_text: str, suffix: str) -> str:
    """依頼と資料を1つのプロンプトにまとめる。

    「フェンスも前置きも書くな」と明示するのは、返答をそのままファイルへ書く
    ためである。剥がす処理（strip_fence）も入れてあるが、剥がせる形で返って
    くる保証はない。書かせないほうが確実で、剥がす側は保険である。
    """
    language = _language(suffix)
    return (
        f"あなたは {language} を書く開発者です。\n"
        f"次の資料をもとに、依頼された {language} のソースコードを書いてください。\n\n"
        "資料に書かれていないことは書かないでください。"
        "根拠が見つからない部分は、推測で埋めずに省いてください。\n\n"
        f"## 依頼\n{question}\n\n"
        f"{evidence_sections(sources, attachments, tree_text)}\n\n"
        "## 書き方\n"
        f"{language} のソースコードだけを返してください。\n"
        "説明や前置き、後書きは書かないでください。\n"
        "```go のようなコードフェンスで囲まないでください。"
        "返答をそのままファイルに保存します。\n"
        f"「{REFERENCES_HEADING}」のコメントは書かないでください。こちらで付けます。\n"
    )


def strip_fence(text: str) -> str:
    """返答にコードフェンスが混ざっていたら、中身だけを取り出す。

    フェンスの外側にある前置きや後書きも一緒に落ちる。それらをファイルへ
    残すとコンパイルが通らないので、落とすのが正しい。

    フェンスが無ければそのまま返す。頼んだとおりに返ってきた場合である。
    """
    match = _FENCE.search(text)
    return (match.group("source") if match else text).strip()


def build(code: str, paths, citations, suffix: str) -> tuple[bytes, list[str]]:
    """コードの先頭に参照したファイルのコメントを付け、バイト列で返す。

    返り値を (データ, 警告) にしてあるのは markdown_document.build と揃えるため
    である。画面は形式で経路を分けるが、受け取る形まで変わると分岐が伸びる。

    参照の一覧はここが組み立て、モデルには書かせない。書かせると、渡していない
    ファイルを参照元として並べうる（文書側と同じ判断）。
    """
    _language(suffix)
    body = strip_fence(code)
    names = list(paths) + list(citations)
    if not names:
        # 見出しだけが先頭に残っても読む人には何も伝わらない。
        return body.encode("utf-8"), []
    header = "\n".join(
        [f"{_COMMENT} {REFERENCES_HEADING}"]
        + [f"{_COMMENT} - {name}" for name in names]
    )
    return f"{header}\n\n{body}".encode("utf-8"), []


def write_source(
    question, sources, attachments, tree_text: str, suffix: str, ask
) -> str:
    """モデルが書いたコードをそのまま返す。フェンスの除去は build が行う。

    上限の判定を呼ぶ前に置くのは、呼んでから落ちると利用者が30〜60秒待たされた
    うえで何も受け取れないためである（freeform.write_markdown と同じ）。
    """
    prompt = build_prompt(question, sources, attachments, tree_text, suffix)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise PromptTooLongError(
            f"資料が長すぎます（{len(prompt):,}文字 / 上限 {MAX_PROMPT_CHARS:,}文字）。"
            "参照するフォルダや添付を減らしてください"
        )
    return ask(prompt)
