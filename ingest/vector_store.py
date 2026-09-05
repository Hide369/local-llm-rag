"""SQLite + numpy によるベクトルストア。

design: docs/superpowers/specs/2026-09-05-sqlite-vector-store-design.md

近似最近傍探索（HNSW）を持たない。686件・1024次元での総当たりcosine検索は
実測0.19msであり、100倍の規模でも8.93msで済む。索引を持たないことは性能上の
妥協ではなく、索引の破損という故障モードを持たないための選択である。
"""


class WhereError(Exception):
    """絞り込み条件が扱えない。"""


# ChromaDBの where から実際に使われている演算子だけを実装する。
# 増やすときは ingest/conditions.py の COMPARISONS / EQUALITY も揃えること。
_OPERATORS = {
    "$eq": lambda actual, expected: actual == expected,
    "$gte": lambda actual, expected: actual >= expected,
    "$lte": lambda actual, expected: actual <= expected,
}


def _compare(operator: str, actual, expected) -> bool:
    compare = _OPERATORS.get(operator)
    if compare is None:
        # 黙って無視してはならない。条件が消えたまま全件が返り、誤った一覧が
        # 根拠として使われる（ingest/conditions.py が記録している事故と同じ形）。
        raise WhereError(f"未対応の演算子です: {operator}")
    try:
        return compare(actual, expected)
    except TypeError:
        # 文字列と数値の大小比較。条件に合わないだけであり、異常ではない。
        return False


def matches(metadata: dict, where: dict | None) -> bool:
    """1件のメタデータが条件に合うかを判定する。

    SQLへ翻訳せずPythonで評価するのは、演算子の対応付けと文字列の組み立てが
    静かに間違える種類のコードだからである。686件では総当たりでも数マイクロ秒で、
    性能上の理由は無い。
    """
    if not where:
        return True
    for key, condition in where.items():
        if key == "$and":
            if not all(matches(metadata, clause) for clause in condition):
                return False
        elif isinstance(condition, dict):
            if key not in metadata:
                return False
            if not all(
                _compare(operator, metadata[key], expected)
                for operator, expected in condition.items()
            ):
                return False
        elif metadata.get(key) != condition:
            return False
    return True
