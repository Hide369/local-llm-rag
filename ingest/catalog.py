"""条件に合う資料を集めて、モデルが読める表に整える。

ベクトル検索と違い where は取りこぼさない。条件に合うものは必ず全件そろうので、
「該当する型番をすべて」という質問に構造的に答えられる。

LLMには一切依存しない。ここを純粋な計算に保つことで、絞り込みと表組みの規則を
実機のOllamaなしでテストできる。
"""
from dataclasses import dataclass

from ingest.chunker import RESERVED_METADATA_KEYS

_OPERATOR_LABELS = {"$lte": "以下", "$gte": "以上", "$eq": "＝"}


@dataclass(frozen=True)
class Product:
    """1つの資料（＝1製品）とその属性。"""

    source: str
    attributes: dict


def _where(conditions: dict) -> dict:
    """ChromaDBは条件が2つ以上のとき $and で包む必要がある。"""
    clauses = [{key: condition} for key, condition in conditions.items()]
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def select(collection, conditions: dict) -> list[Product]:
    """条件に合う資料を、1資料1件にまとめて返す。

    同じ製品の6セクションは同じ属性を持つ。畳まずに返すと件数を尋ねる質問に
    誤って答えることになるため、source ごとに1つにする。
    """
    if not conditions:
        return []
    found = collection.get(where=_where(conditions), include=["metadatas"])
    products: dict[str, dict] = {}
    for metadata in found.get("metadatas") or []:
        source = metadata.get("source")
        if source and source not in products:
            products[source] = {
                key: value
                for key, value in metadata.items()
                if key not in RESERVED_METADATA_KEYS
            }
    return [Product(source=source, attributes=products[source]) for source in sorted(products)]


def relaxations(collection, conditions: dict) -> list[tuple[str, list[Product]]]:
    """条件を1つずつ外して、惜しくも外れた資料を返す。

    「同じ26dBでも設置できない機種がある場合、その型番と理由も」という問いに
    答えるために要る。条件が1つのときは外した先が全件になり意味がないので何もしない。
    get は埋め込み計算を伴わないため、条件の数だけ引いても追加コストはほぼない。
    """
    if len(conditions) < 2:
        return []
    matched = {product.source for product in select(collection, conditions)}
    results: list[tuple[str, list[Product]]] = []
    for dropped in conditions:
        remaining = {key: value for key, value in conditions.items() if key != dropped}
        extra = [p for p in select(collection, remaining) if p.source not in matched]
        if extra:
            results.append((dropped, extra))
    return results


def _describe(conditions: dict) -> str:
    parts = []
    for key, condition in conditions.items():
        for operator, value in condition.items():
            parts.append(f"{key} {value}{_OPERATOR_LABELS.get(operator, operator)}")
    return " / ".join(parts)


def _shown(key: str, value, conditions: dict) -> bool:
    """比較に使える列だけを残す。

    設計書6.4の表は型番と数値の列だけを並べている。全属性を出すと1行が8列になり、
    20行の表で数値が180個ほど並ぶ。実測では、その表を渡された llama3.1:8b が
    「1つだけ条件を満たさない機種」を挙げられなかった。brand は全製品で同じ値、
    product_name は型番の言い換えであり、比較には何も足さない。
    絞り込みに使われた属性は、文字列でも残す（price_tier のような一致条件のため）。
    """
    return key in conditions or key == "model_id" or isinstance(value, (int, float))


def _row(product: Product, conditions: dict) -> str:
    attributes = " | ".join(
        f"{key}={value}"
        for key, value in sorted(product.attributes.items())
        if _shown(key, value, conditions)
    )
    return f"{product.source} | {attributes}"


def format_table(conditions: dict, matched: list[Product], relaxed: list) -> str:
    """モデルに渡す一覧を組み立てる。

    各行の先頭に出典（ファイル名）を置く。散文チャンクを渡していたときと同じ形で
    出典を示せるようにするためである。
    """
    lines = [f"条件: {_describe(conditions)}", "", f"■ 全条件に合致（{len(matched)}件）"]
    if matched:
        lines.extend(_row(product, conditions) for product in matched)
    else:
        lines.append("該当なし")
    for dropped, products in relaxed:
        # 見出しが「条件を外すと合致」だけだったとき、モデルは「条件を満たさない
        # 製品はありません」と、表と正反対のことを答えた。何を満たし何を満たさない
        # かを書くと、その矛盾した断定は出なくなった。ただし llama3.1:8b は
        # 依然として「同じ26dBだが設置できない機種は」という後半に答えられていない
        # （設計書13節の限界。表の側の情報は正しく揃っている）。
        condition = conditions.get(dropped)
        described = _describe({dropped: condition}) if condition else dropped
        lines.append("")
        lines.append(
            f"■ 「{described}」だけを満たさない（他の条件は満たす）（{len(products)}件）"
        )
        lines.extend(_row(product, conditions) for product in products)
    return "\n".join(lines)
