"""雛形なしで文書を書かせる。

雛形ありの経路（docgen/filling.py）との違いは1点だけである。埋める欄の一覧の
代わりに、出力の形の指示を載せる。材料（依頼・検索結果・添付・プロジェクトの
ファイル）は同じものを同じ形で受け取る。

形式ごとにプロンプトを分けない。Markdown を1回書かせ、そこから4形式を組む
（docgen/markdown_document.py）。分けるとプロンプトが4本になり、品質のばらつきも
4箇所で別々に面倒を見ることになる。
"""
from docgen.filling import MAX_PROMPT_CHARS, PromptTooLongError

# xlsx のときだけ足す指示。一覧表が欲しいのに文章が返ると、変換のしようがない。
_TABLE_INSTRUCTION = (
    "この文書は Excel にします。本文は Markdown の表で書いてください。"
    "表の直前には、その表が何かを示す `##` の見出しを置いてください"
    "（見出しがシート名になります）。\n"
)


def build_prompt(question, sources, attachments, tree_text: str, suffix: str) -> str:
    """依頼・検索結果・添付・プロジェクトの一覧を1つのプロンプトにまとめる。

    sources は (資料の種類の名前, ヒットの並び) の並びである。種類ごとに節を
    分けるのは、混ぜて並べるとどれが社内の決定事項でどれが外部ライブラリの
    説明なのかをモデルが区別できないためである（filling.build_prompt と同じ）。
    """
    found = "\n\n".join(
        f"## {kind}の検索結果\n"
        + ("\n\n".join(f"【{hit.citation}】\n{hit.text}" for hit in hits)
           or f"（{kind}の検索結果はありません）")
        for kind, hits in sources
    ) or "## 検索結果\n（検索していません）"
    attached = "\n\n".join(
        f"【{name}】\n{text}" for name, text in attachments
    ) or "（添付ファイルはありません）"
    listing = tree_text or "（プロジェクトフォルダは指定されていません）"
    return (
        "あなたは社内文書を作成する担当者です。\n"
        "次の資料をもとに、依頼された文書を Markdown で書いてください。\n\n"
        "資料に書かれていないことは書かないでください。"
        "根拠が見つからない項目は、推測で埋めずに省いてください。\n\n"
        f"## 依頼\n{question}\n\n"
        f"{found}\n\n"
        f"## 資料の本文\n{attached}\n\n"
        f"## プロジェクトのファイル一覧\n{listing}\n\n"
        "## 書き方\n"
        "Markdown だけを返してください。説明や前置きは書かないでください。\n"
        "見出しは `#` `##` `###` を使ってください。\n"
        "表は Markdown の表で書いてください。\n"
        + (_TABLE_INSTRUCTION if suffix.lower() == ".xlsx" else "")
        + "図で表すほうがよい箇所は、```mermaid のコードブロックにしてください。\n"
        "「参照したファイル」の節は書かないでください。こちらで付けます。\n"
    )


def write_markdown(
    question, sources, attachments, tree_text: str, suffix: str, ask
) -> str:
    """モデルが書いた Markdown をそのまま返す。

    上限の判定を呼ぶ前に置くのは、呼んでから落ちると利用者が30〜60秒待たされた
    うえで何も受け取れないためである（filling.fill_values と同じ）。
    """
    prompt = build_prompt(question, sources, attachments, tree_text, suffix)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise PromptTooLongError(
            f"資料が長すぎます（{len(prompt):,}文字 / 上限 {MAX_PROMPT_CHARS:,}文字）。"
            "参照するフォルダや添付を減らしてください"
        )
    return ask(prompt)
