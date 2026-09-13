"""雛形の印に入れる値を決める。

検索を1回、LLM呼び出しを1回で全部の印を決める。印ごとに検索してLLMを呼ぶ案も
検討したが、議事録の雛形で印が8個あればLLM呼び出しが8回になり、1回30〜60秒として
数分かかる。さらに印どうしの整合が保証されず、「会議名は第5回なのに決定事項は
第4回」という食い違いが構造的に起こりうる（設計書6節）。

ask を引数で受け取るのは ingest/conditions.py と同じ理由である。ここを
モジュール内でOllamaクライアントに束縛すると、値を決める規則のテストに実機の
Ollamaが要るようになる。
"""
import json

# 生成に使う文脈の大きさ。coding_agent/connection.py が使う 32768／65536 の
# 小さいほうに合わせる。ingest/chat.py の NUM_CTX（8192）は条件抽出とクエリ翻訳の
# ための値であり、添付ファイルを丸ごと渡すこの経路には足りない。
GENERATION_NUM_CTX = 32768

# プロンプトの上限。日本語は1文字が1トークン以上になることがあるため
# 「1文字 = 1トークン」とみなす安全側の見積もりを採り、32,768 から回答用に
# 約4,000を残した値である。トークナイザを持ち込んで正確に数えることはしない。
# 判定に使うだけの目的に対して依存が重く、生成モデルを替えるたびに数え方が
# 変わる。この値は上限の目安であって、超えたら止めるという一点にしか使わない。
MAX_PROMPT_CHARS = 28000


class PromptTooLongError(Exception):
    """添付と検索結果が文脈に収まらない。"""


def build_prompt(placeholders, question, sources, attachments) -> str:
    """印の一覧・検索結果・添付を1つのプロンプトにまとめる。

    sources は (資料の種類の名前, ヒットの並び) の並びである。種類ごとに節を
    分けるのは、混ぜて並べるとどれが社内の決定事項でどれが外部ライブラリの
    説明なのかをモデルが区別できないためである。
    """
    found = "\n\n".join(
        f"## {kind}の検索結果\n"
        + ("\n\n".join(f"【{hit.citation}】\n{hit.text}" for hit in hits)
           or f"（{kind}の検索結果はありません）")
        for kind, hits in sources
    ) or "## 検索結果\n（検索していません）"
    attached = "\n\n".join(
        f"【添付 {name}】\n{text}" for name, text in attachments
    ) or "（添付ファイルはありません）"
    names = "\n".join(f"- {name}" for name in placeholders)
    return (
        "あなたは社内文書を作成する担当者です。\n"
        "次の資料をもとに、雛形の各欄に入れる文章を決めてください。\n\n"
        "資料に書かれていないことは書かないでください。"
        "根拠が見つからない欄は、その欄を含めずに返してください。"
        "推測で埋めるより、空欄のまま人が書き足せるほうが安全です。\n\n"
        f"## 依頼\n{question}\n\n"
        f"{found}\n\n"
        f"## 添付ファイル\n{attached}\n\n"
        f"## 埋める欄\n{names}\n\n"
        "欄の名前をキー、入れる文章を値とするJSONオブジェクトだけを返してください。"
        "説明や前置きは書かないでください。\n"
        "箇条書きなど複数行になる場合は、値の中で改行してください。\n"
        # 印の名前から図かどうかを当てる仕組み（「図」で終わる名前を探す等）は
        # 作らない。名前の付け方は雛形を書く人の自由であり、規則を決めると
        # 雛形の書き方に制約が生まれる。
        "図で表すほうがよい欄は、```mermaid で始まるコードブロックだけを"
        "値にしてください。説明文と図を同じ欄に混ぜないでください。\n"
    )


def fill_values(placeholders, question, sources, attachments, ask) -> dict[str, str]:
    """印の名前から値への対応を返す。決まらなかった印は含めない。

    JSONが壊れて返っても例外は投げない。止めると雛形すら受け取れないため、
    全欄が「埋まらなかった」扱いになり、印の残った雛形が出る
    （ingest/query_translation.py が翻訳の失敗で原文に落とすのと同じ考え方）。

    LLM そのものが落ちた場合は投げ直す。こちらは利用者に伝えるべき失敗であり、
    黙って空の雛形を返してはいけない。
    """
    prompt = build_prompt(placeholders, question, sources, attachments)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise PromptTooLongError(
            f"添付と検索結果が長すぎます（{len(prompt):,}文字 / 上限 "
            f"{MAX_PROMPT_CHARS:,}文字）。添付を減らすか、短いものに分けてください"
        )
    raw = ask(prompt)
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    wanted = set(placeholders)
    return {
        name: value
        for name, value in loaded.items()
        # 雛形に無いキー、文字列でない値、空文字はいずれも「埋まらなかった」と
        # 同じ扱いにする。空文字を通すと、印が消えて空欄になり、埋め損ねたことに
        # 利用者が気づけない。
        if name in wanted and isinstance(value, str) and value.strip()
    }
