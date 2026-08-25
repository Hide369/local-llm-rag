"""モデルの回答を表示する前に整える。

llama3.1:8b は結論を「答え： 型番：UD-1100iE 達成率：125%」のように言い直す。
この「答え：」は検証用の正解リストと同じ体裁で紛らわしいため、表示しない。

プロンプトで書かせない方向は実測して棄却した。「結論は一度だけ簡潔に述べ、同じ
内容を言い換えて繰り返さないでください」を足した版は、7回中2回で型番そのものを
答えられなくなった（「型番は出典されていません」）。「『答え：』のような要約行で
繰り返してはいけません」と名指しで禁じた版は、3回中1回で逆に「答え：」を出した。
言い回しは指示で押さえられず、回答の中身だけが痩せる。

消すのはラベルの文字だけで、中身は残す。実測では
「答え：省エネ基準達成率が125%の機種は、UD-1100iEです。」のように回答本体が
その行にしか無い出力があり、行ごと捨てると回答が消えてしまうため。
"""
import re

# 行頭のラベルだけを対象にする。「答えは125%です」のような普通の文を壊さないため。
# 全角・半角のコロンと、その前後の空白（全角空白を含む）まで落とす。
_LABEL = re.compile(r"^[ \t　]*答え[ \t　]*[：:][ \t　]*")

# 「　答え　：　」と空白が挟まってもこの長さに収まる。これを超えたら
# ラベルではないと判断して、溜めていた文字を流す。
_MAX_LABEL_CHARS = 8


def strip_label(line: str) -> str:
    """行頭の「答え：」を取り除く。"""
    return _LABEL.sub("", line, count=1)


def _could_become_label(text: str) -> bool:
    """あと数文字でラベルになりうるか（＝判定を保留すべきか）。"""
    if len(text) >= _MAX_LABEL_CHARS:
        return False
    head = text.lstrip(" \t　")
    if not "答え".startswith(head[:2]):
        return False
    # 「答え」まで来ていれば、あとはコロンを待つ間の空白だけが許される。
    return head[2:].strip(" \t　") == ""


def without_label(chunks):
    """ストリームから行頭の「答え：」を落としながら流す。

    ラベルは「答」「え」「：」のようにトークンへ分かれて届くため、行頭では
    ラベルになりうる間だけ文字を溜める。溜めるのを行頭の数文字に限ることで、
    1行ずつまとめて出す（8トークン毎秒では1行あたり数秒待たされる）のを避ける。
    """
    pending = ""
    at_line_start = True
    for chunk in chunks:
        while chunk:
            if not at_line_start:
                head, newline, chunk = chunk.partition("\n")
                yield head + newline
                at_line_start = bool(newline)
                continue
            pending += chunk
            chunk = ""
            match = _LABEL.match(pending)
            if "\n" in pending:
                # 行が終わった以上、この行の判定はもう保留できない。
                line, _, chunk = pending.partition("\n")
                yield strip_label(line) + "\n"
                pending = ""
            elif match and pending[match.end() :]:
                # ラベルの後ろに中身が来た。ラベルだけ捨てて残りを流す。
                # コロンの直後で流さないのは、「答え： 型番…」の空白を
                # ラベルもろとも落とすため。
                yield pending[match.end() :]
                pending = ""
                at_line_start = False
            elif not (match or _could_become_label(pending)):
                yield pending
                pending = ""
                at_line_start = False
    if pending:
        yield strip_label(pending)


# gpt-oss:20b などが表のセル内で複数行や箇条書きを示すのに <br> や
# <ul><li> を使うことがある。StreamlitのMarkdownレンダラーは既定でHTMLを
# 解釈しないため、そのまま画面に文字列として出てしまう（unsafe_allow_html は
# 文書由来のテキストをそのままHTMLとして描画することになり避けたいため、
# タグ自体を落とす）。
#
# 表のセル内には改行を書けない（GFM表の1行が崩れる）ため、<li> は改行では
# なく「・」に、</li> は項目の区切りの空白に置き換える。
#
# (完全一致, 溜めている途中でありうるか, 置き換え後の文字列) の並び。
_TAG_PATTERNS: list[tuple[re.Pattern, re.Pattern, str]] = [
    (
        re.compile(r"<br\s*/?>", re.IGNORECASE),
        re.compile(r"^<(b(r(\s*/?)?)?)?$", re.IGNORECASE),
        "",
    ),
    (re.compile(r"<ul>", re.IGNORECASE), re.compile(r"^<(u(l)?)?$", re.IGNORECASE), ""),
    (
        re.compile(r"</ul>", re.IGNORECASE),
        re.compile(r"^<(/(u(l)?)?)?$", re.IGNORECASE),
        "",
    ),
    (re.compile(r"<li>", re.IGNORECASE), re.compile(r"^<(l(i)?)?$", re.IGNORECASE), "・"),
    (
        re.compile(r"</li>", re.IGNORECASE),
        re.compile(r"^<(/(l(i)?)?)?$", re.IGNORECASE),
        " ",
    ),
]

# 対象タグの中で最長は "<br />"（6文字）。これより長く溜めてどのタグにも
# なりえなければ、先頭の "<" をただの文字として素通りさせる。
_MAX_TAG_CHARS = 6


def strip_html_tags(text: str) -> str:
    """<br>・<ul>・<li> 系のHTMLタグを取り除く。改行や区切りの意図は前後の句読点・空白に任せる。"""
    for full, _partial, replacement in _TAG_PATTERNS:
        text = full.sub(replacement, text)
    return text


def strip_html_tags_stream(chunks):
    """ストリームから <br>・<ul>・<li> 系タグを落としながら流す。

    タグはトークン境界で "<" "li" ">" のように分かれて届きうるため、
    "<" を見た時点でどれかのタグになりうる間だけ文字を溜める。
    """
    pending = ""
    for chunk in chunks:
        for ch in chunk:
            if not pending:
                if ch == "<":
                    pending = ch
                else:
                    yield ch
                continue
            candidate = pending + ch
            full_match = next(
                (
                    replacement
                    for full, _partial, replacement in _TAG_PATTERNS
                    if full.fullmatch(candidate)
                ),
                None,
            )
            if full_match is not None:
                if full_match:
                    yield full_match
                pending = ""
            elif len(candidate) < _MAX_TAG_CHARS and any(
                partial.match(candidate) for _full, partial, _replacement in _TAG_PATTERNS
            ):
                pending = candidate
            else:
                yield candidate
                pending = ""
    if pending:
        yield pending
