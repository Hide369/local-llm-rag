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


def _fold(found) -> list[Product]:
    """チャンクの並びを1資料1件にまとめる。

    同じ製品の6セクションは同じ属性を持つ。畳まずに返すと件数を尋ねる質問に
    誤って答えることになるため、source ごとに1つにする。
    """
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


def select(collection, conditions: dict) -> list[Product]:
    """条件に合う資料を、1資料1件にまとめて返す。"""
    if not conditions:
        return []
    return _fold(collection.get(where=_where(conditions), include=["metadatas"]))


def _ranked_value(product: Product, ranking):
    value = product.attributes.get(ranking.key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def exceeding(collection, conditions: dict, ranking, matched: list[Product]) -> list[Product]:
    """条件から外れるが、尋ねられた属性では合致分を上回る資料。

    「もっと大容量が欲しいが、なぜそれが選べないのか」に答えるために要る。
    条件が1つのとき relaxations は何も返さない（外した先が全件になるため）が、
    順位の上側だけに絞れば数件で済む。実測の例では、奥行き510mm以下で最大は
    11.0kgの2機種、その上に13.0kg・14.0kgの3機種があり、いずれも防水パン
    545mm以上を要する。
    """
    if ranking is None or not conditions or not matched:
        return []
    best_values = [v for v in (_ranked_value(p, ranking) for p in matched) if v is not None]
    if not best_values:
        return []
    limit = max(best_values) if ranking.descending else min(best_values)
    known = {product.source for product in matched}
    beyond = []
    for product in _fold(collection.get(include=["metadatas"])):
        if product.source in known:
            continue
        value = _ranked_value(product, ranking)
        if value is None:
            continue
        if value > limit if ranking.descending else value < limit:
            beyond.append(product)
    return beyond


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
    model_id は行頭に出すので、属性としては繰り返さない。
    """
    if key == "model_id":
        return False
    return key in conditions or isinstance(value, (int, float))


def _row(product: Product, conditions: dict, ranking=None) -> str:
    """「型番 | 属性」の1行。ファイル名は載せない。

    実測では、モデルは表の行をそのまま丸写しして答える（4回中3回）。行にファイル名が
    あれば回答にも必ず出てきて、「UD-1100S_spec_step3.md です」と利用者には意味のない
    取り込み元の名前で製品を指すことになる。列を末尾へ動かしても行ごと写されるので
    効かず、「ファイル名で呼ぶな」という指示も llama3.1:8b には効かない
    （ingest/answer_text.py の実測を参照）。渡さなければ書きようがない。

    出典を捨てることにはならない。この一覧の1行は1つの製品仕様書であり、型番
    UD-1100S は source/家電製品/UD-1100S_spec_step3.md と1対1で対応する。
    利用者に見せる一覧（絞り込んだ一覧）も同じ表なので、表示も型番でそろう。
    """
    keys = sorted(
        key for key, value in product.attributes.items() if _shown(key, value, conditions)
    )
    if ranking is not None and ranking.key in keys:
        # 尋ねられた属性を最初の列に出す。実測では、モデルは行の最初の数値を
        # 「容量」として拾い、アルファベット順で先頭に来る
        # drying_capacity_kg=6.0 を洗濯容量として答えた（4回中2回）。
        keys.remove(ranking.key)
        keys.insert(0, ranking.key)
    attributes = " | ".join(f"{key}={product.attributes[key]}" for key in keys)
    # model_id はフロントマターを持つMarkdownにしか無い。無い資料でも行が
    # 成立するよう、そのときはファイル名を呼び名として使う。
    name = product.attributes.get("model_id") or product.source
    return f"{name} | {attributes}"


def _ordered(products: list[Product], ranking) -> list[Product]:
    """尋ねられた属性の順に並べ替える。値を持たない資料は末尾へ回す。

    モデルは表の先頭の行を掴む。探させる代わりに、掴む場所へ答えを置く。
    """
    if ranking is None:
        return products

    def sort_key(product):
        value = product.attributes.get(ranking.key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return (1, 0.0)
        return (0, -value if ranking.descending else value)

    return sorted(products, key=sort_key)


def format_table(
    conditions: dict, matched: list[Product], relaxed: list, ranking=None, beyond=()
) -> str:
    """モデルに渡す一覧を組み立てる。

    行の先頭は型番で、出典（ファイル名）は載せない（`_row` 参照）。
    ranking（`ingest/conditions.py` の `Ranking`）を渡すと、その属性の順に
    並べ替え、列も先頭へ出す。「最大の洗濯容量は」に答えられるようにするためで、
    渡さなければ従来どおり型番順・アルファベット順の列で出す。
    """
    matched = _ordered(matched, ranking)
    lines = [f"条件: {_describe(conditions)}", "", f"■ 全条件に合致（{len(matched)}件）"]
    if matched:
        lines.extend(_row(product, conditions, ranking) for product in matched)
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
        lines.extend(_row(product, conditions, ranking) for product in _ordered(products, ranking))
    if beyond:
        # 「条件を満たさない」ことを見出しに書く。実測では、見出しが弱いと
        # モデルはこの群を条件に合う機種として混ぜて答える。
        larger = "大きい" if ranking.descending else "小さい"
        lines.append("")
        lines.append(
            f"■ 条件を満たさないので選べないが、{ranking.key} はこれより{larger}"
            f"（{len(beyond)}件）"
        )
        lines.extend(_row(product, conditions, ranking) for product in _ordered(beyond, ranking))
    return "\n".join(lines)
