"""プロンプト組み立てと取り込み結果の要約。

UIから呼ばれるがUIには依存しない。Streamlitスクリプトに置くと、テストが
インポートしただけでスクリプト全体が走り本番DBを開いてしまうため、ここに分離する。
"""


def build_prompt(question: str, hits) -> str:
    """検索結果を今回の質問にだけ添える。

    履歴には生の質問を残す。ここで作った文字列を履歴に入れると、
    次のターン以降に古いコンテキストが混ざる。

    しきい値0.50は「関連度が高い」ことまでは保証しない。挨拶のような
    意味的に空な入力は、コーパスの重心付近に落ちて距離0.41前後になり、
    しきい値では弾けない（ingest/retrieval.pyのコメント参照）。そのため
    ここでは、根拠が質問に無関係なら使わずにその旨を答えるようモデルに
    明示的に指示する。距離やUI側でのフィルタでは解決しない問題であり、
    プロンプトが最後の砦になる。
    """
    if not hits:
        return question
    context = "\n\n".join(f"[{hit.citation}]\n{hit.text}" for hit in hits)
    return (
        "以下の社内文書を参考に回答してください。"
        "回答の根拠にした箇所は [ ] 内の出典を示してください。"
        "参考文書が質問と無関係、または回答の根拠にならない場合は、"
        "文書の内容を無理に使わず、社内文書からは回答できない旨を伝えてください。\n\n"
        f"{context}\n\nユーザーの質問: {question}"
    )


def format_report(report) -> str:
    lines = [
        f"取り込み: {sum(report.indexed.values())}チャンク / {len(report.indexed)}ファイル",
        f"スキップ: {len(report.skipped)}ファイル",
        f"削除: {len(report.removed)}ファイル",
    ]
    for source, message in report.failed.items():
        lines.append(f"失敗 {source}: {message}")
    return "\n".join(lines)
