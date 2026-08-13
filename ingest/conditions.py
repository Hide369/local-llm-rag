"""質問から絞り込み条件を取り出す。

ベクトルは「510以下」のような数値条件を表現できない。実測では、防水パン510mmを
問う質問で設置不可のUD-1400X（545mm必要）が上位に入り、上位20件の距離が
0.375〜0.421に密集して製品を区別しなかった。距離ではなく where で絞るために、
質問を機械が扱える条件へ変換する。

LLMの呼び出しは ask として外から渡す。ここをモジュール内でOpenAIクライアントに
束縛すると、変換規則のテストに実機のOllamaが要るようになるため。
"""
import json
import re
import unicodedata
from dataclasses import dataclass, field

from ingest.chunker import RESERVED_METADATA_KEYS

# ChromaDBの where がそのまま受け取れる演算子だけを許す。変換層を挟まずに済む。
COMPARISONS = ("$lte", "$gte")
EQUALITY = "$eq"

# 質問文に書かれている数値。条件の値がここに無ければ、モデルが作った値である。
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Extraction:
    """抽出の結果。

    conditions が空であることと failed は別物である。前者は「条件のない通常の
    質問」であり黙ってベクトル検索へ回してよいが、後者は利用者に伝える必要がある。
    """

    conditions: dict = field(default_factory=dict)
    failed: bool = False


def available_keys(collection) -> dict[str, str]:
    """メタデータに実在する属性キーと、その型（number / string）を集める。

    キー一覧をコードに固定しない。資料を入れ替えてもコードを直さずに追従させるため。
    件数を絞らず全件読むのは、ChromaDBの取得順が資料の並びを保証せず、属性を
    持たないPDF由来のチャンクばかりを引いてスキーマが空になり得るため。
    460件でも数十ミリ秒であり、起動時の1回だけ呼ぶ。
    """
    if collection.count() == 0:
        return {}
    schema: dict[str, str] = {}
    for metadata in collection.get(include=["metadatas"]).get("metadatas") or []:
        for key, value in metadata.items():
            if key in RESERVED_METADATA_KEYS or key in schema:
                continue
            # bool は int の派生なので、数値より先に落とす。
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                schema[key] = "number"
            elif isinstance(value, str):
                schema[key] = "string"
    return schema


def _prompt(question: str, schema: dict[str, str]) -> str:
    """抽出プロンプト。文面は実測で決めている。

    「向き」と「作らない」の2つを明記しているのは、llama3.1:8b が実際にその2つを
    間違えたためである。防水パン510mmの質問で不等号を逆に取り、「できるだけ
    大容量」という程度の表現から washing_capacity_kg ≥ 10 という質問文に無い
    しきい値をでっち上げた。どちらも例外を出さずに誤った絞り込みになる。
    """
    keys = "\n".join(f"- {key}（{kind}）" for key, kind in sorted(schema.items()))
    return (
        "次の質問から、資料を絞り込む条件だけを抜き出してJSONで答えてください。\n"
        "使ってよい属性は以下だけです。\n\n"
        f"{keys}\n\n"
        "演算子は $lte（以下）、$gte（以上）、$eq（一致）の3つだけを使ってください。\n"
        '形式: {"属性名": {"演算子": 値}}\n\n'
        "不等号の向きは、属性の値が製品側の値であることに注意して決めてください。\n"
        "- 利用者が使える上限を述べている（設置できる寸法、これ以下の音、予算）"
        "→ 製品側の値はその値以下なので $lte\n"
        "- 利用者が求める下限を述べている（これ以上の容量がほしい）"
        "→ 製品側の値はその値以上なので $gte\n\n"
        "質問文に書かれていない値を条件にしないでください。"
        "「大容量」「静か」「コンパクト」のような程度の表現だけでは条件になりません。\n"
        "型番や製品名を挙げて1つの製品について尋ねている質問も、条件なしです。\n"
        "条件が読み取れない質問には {} と答えてください。\n"
        "説明は書かず、JSONだけを返してください。\n\n"
        f"質問: {question}"
    )


def _normalise_operator(operator: str) -> str:
    """先頭の $ の書き忘れを補う。

    実測では、意味も値も正しく取れているのに $ だけが落ちた
    {"lte": 26} が返り、条件が丸ごと捨てられた。許す演算子を増やすわけでは
    ないので、_valid の判定はこの後もそのまま効く。
    """
    return operator if operator.startswith("$") else f"${operator}"


def _valid(operator: str, value) -> bool:
    if isinstance(value, bool):  # True は 1 として比較できてしまうため弾く
        return False
    # 空文字はここで落とす。この後の _grounded は「質問文に書かれているか」を
    # 部分一致で見るため、空文字は常に真になって素通りする。実測（temperature 0
    # で再現性あり）では、議事録について尋ねた「決定事項を教えてほしい」に
    # 全属性を埋めた {"brand": {"$eq": ""}, "model_id": {"$eq": ""}, …} が返り、
    # 家電製品の絞り込み経路へ流れて該当0件の表が根拠になった。
    if isinstance(value, str) and not value.strip():
        return False
    if operator in COMPARISONS:
        return isinstance(value, (int, float))
    return operator == EQUALITY and isinstance(value, (int, float, str))


def _grounded(value, question: str) -> bool:
    """条件の値が質問文に実在することを確かめる。

    実測では、型番だけを尋ねた質問に brand=Panasonic（コーパスに無いメーカー）を、
    「できるだけ大容量」という程度の表現から washing_capacity_kg ≥ 10 という
    書かれていないしきい値を作った。どちらも例外を出さず、条件に合う製品が
    無いという誤った回答になる。プロンプトで禁じても消えなかったため、ここで落とす。

    書かれていない条件を作られるより、読み取れずベクトル検索へ落ちるほうが安全である。
    そのため「漢数字で書かれた数値を取りこぼす」側に倒している。
    全角の数字は半角へ寄せてから照合する（NFKC）。日本語入力では普通に混ざるため。

    数値は部分文字列ではなく数として突き合わせる。単純な部分一致にしたところ、
    でっち上げられた 10 が質問文中の「510mm」に含まれてしまい素通りした。
    数として比べれば 9 と 9.0 が同じものとして扱えるという利点もある。
    """
    haystack = unicodedata.normalize("NFKC", question)
    if isinstance(value, str):
        return value in haystack
    return any(float(token) == float(value) for token in _NUMBER.findall(haystack))


def _sanitise(loaded: dict, schema: dict[str, str], question: str) -> dict:
    """スキーマに無いキー・許可外の演算子・型の合わない値を1件ずつ捨てる。

    1つでも壊れていたら全部捨てる作りにはしない。2条件のうち片方だけが壊れて
    いる場合、残った条件で絞り込めるほうが利用者にとって有益なためである。
    """
    conditions: dict = {}
    for key, condition in loaded.items():
        if key not in schema or not isinstance(condition, dict):
            continue
        for operator, value in condition.items():
            normalised = _normalise_operator(operator)
            if _valid(normalised, value) and _grounded(value, question):
                conditions[key] = {normalised: value}
                break
    return conditions


def extract(question: str, schema: dict[str, str], ask) -> Extraction:
    """質問を絞り込み条件へ変換する。失敗しても例外は投げない。"""
    if not schema:
        return Extraction()
    try:
        raw = ask(_prompt(question, schema))
    except Exception:  # LLM側の事情で回答生成まで巻き添えにしない
        return Extraction(failed=True)
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return Extraction(failed=True)
    if not isinstance(loaded, dict):
        return Extraction(failed=True)
    return Extraction(conditions=_sanitise(loaded, schema, question))
