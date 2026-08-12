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


def _row(product: Product) -> str:
    attributes = " | ".join(
        f"{key}={value}" for key, value in sorted(product.attributes.items())
    )
    return f"{product.source} | {attributes}"


def format_table(conditions: dict, matched: list[Product], relaxed: list) -> str:
    """モデルに渡す一覧を組み立てる。

    各行の先頭に出典（ファイル名）を置く。散文チャンクを渡していたときと同じ形で
    出典を示せるようにするためである。
    """
    lines = [f"条件: {_describe(conditions)}", "", f"■ 全条件に合致（{len(matched)}件）"]
    if matched:
        lines.extend(_row(product) for product in matched)
    else:
        lines.append("該当なし")
    for dropped, products in relaxed:
        lines.append("")
        lines.append(f"■ 「{dropped}」の条件を外すと合致（{len(products)}件）")
        lines.extend(_row(product) for product in products)
    return "\n".join(lines)
