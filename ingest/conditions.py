"""質問から絞り込み条件を取り出す。

ベクトルは「510以下」のような数値条件を表現できない。実測では、防水パン510mmを
問う質問で設置不可のUD-1400X（545mm必要）が上位に入り、上位20件の距離が
0.375〜0.421に密集して製品を区別しなかった。距離ではなく where で絞るために、
質問を機械が扱える条件へ変換する。

LLMの呼び出しは ask として外から渡す。ここをモジュール内でOpenAIクライアントに
束縛すると、変換規則のテストに実機のOllamaが要るようになるため。
"""
import json
from dataclasses import dataclass, field

from ingest.chunker import RESERVED_METADATA_KEYS

# ChromaDBの where がそのまま受け取れる演算子だけを許す。変換層を挟まずに済む。
COMPARISONS = ("$lte", "$gte")
EQUALITY = "$eq"


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
    keys = "\n".join(f"- {key}（{kind}）" for key, kind in sorted(schema.items()))
    return (
        "次の質問から、資料を絞り込む条件だけを抜き出してJSONで答えてください。\n"
        "使ってよい属性は以下だけです。\n\n"
        f"{keys}\n\n"
        "演算子は $lte（以下）、$gte（以上）、$eq（一致）の3つだけを使ってください。\n"
        '形式: {"属性名": {"演算子": 値}}\n'
        "条件が読み取れない質問には {} と答えてください。\n"
        "説明は書かず、JSONだけを返してください。\n\n"
        f"質問: {question}"
    )


def _valid(operator: str, value) -> bool:
    if isinstance(value, bool):  # True は 1 として比較できてしまうため弾く
        return False
    if operator in COMPARISONS:
        return isinstance(value, (int, float))
    return operator == EQUALITY and isinstance(value, (int, float, str))


def _sanitise(loaded: dict, schema: dict[str, str]) -> dict:
    """スキーマに無いキー・許可外の演算子・型の合わない値を1件ずつ捨てる。

    1つでも壊れていたら全部捨てる作りにはしない。2条件のうち片方だけが壊れて
    いる場合、残った条件で絞り込めるほうが利用者にとって有益なためである。
    """
    conditions: dict = {}
    for key, condition in loaded.items():
        if key not in schema or not isinstance(condition, dict):
            continue
        for operator, value in condition.items():
            if _valid(operator, value):
                conditions[key] = {operator: value}
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
    return Extraction(conditions=_sanitise(loaded, schema))
