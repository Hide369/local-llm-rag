""":::code の解決。

MS Learn 形式のドキュメントは、コード例を外部ファイルへの参照で書く。
実測 2026-09-13 では、C# のどのサブディレクトリでも参照の割合が33%〜93%
あり、解決しないと「検索は当たるのにコードが書けない」状態になる
（設計書4.5節）。
"""
from scripts import code_references


def _fetcher(files):
    def fetch(path):
        return files[path]

    return fetch


def test_a_reference_without_a_selector_inlines_the_whole_file():
    text = ':::code language="csharp" source="snippets/Program.cs":::\n'
    files = {"docs/csharp/snippets/Program.cs": "int x = 1;\nint y = 2;\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nint x = 1;\nint y = 2;\n```\n"
    assert unresolved == 0


def test_an_id_selector_inlines_only_that_region():
    """id= は .cs 側の #region 〜 #endregion を指す。"""
    text = ':::code language="csharp" source="snippets/P.cs" id="Snippet1":::\n'
    files = {
        "docs/csharp/snippets/P.cs": (
            "using System;\n"
            "#region Snippet1\n"
            "Console.WriteLine(1);\n"
            "#endregion\n"
            "// tail\n"
        )
    }
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nConsole.WriteLine(1);\n```\n"
    assert unresolved == 0


def test_an_id_selector_removes_the_shared_indentation():
    """#region の中は class の内側にあり、丸ごと字下げされている。

    字下げのまま差し込むと、そのままでは動かないコードが例として出る。
    """
    text = ':::code language="csharp" source="snippets/P.cs" id="S":::\n'
    files = {
        "docs/csharp/snippets/P.cs": (
            "class C {\n    #region S\n    int a = 1;\n    int b = 2;\n    #endregion\n}\n"
        )
    }
    resolved, _ = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nint a = 1;\nint b = 2;\n```\n"


def test_a_range_selector_inlines_those_lines_inclusive():
    """range="2-3" は2行目と3行目の両方を含む（1始まり）。"""
    text = ':::code language="csharp" source="snippets/P.cs" range="2-3":::\n'
    files = {"docs/csharp/snippets/P.cs": "a\nb\nc\nd\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nb\nc\n```\n"
    assert unresolved == 0


def test_a_relative_parent_path_is_resolved():
    text = ':::code language="csharp" source="../shared/P.cs":::\n'
    files = {"docs/csharp/shared/P.cs": "ok\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/linq/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nok\n```\n"
    assert unresolved == 0


def test_a_reference_outside_the_tree_is_not_fetched():
    """木に無いパスは取りに行かない。外部 URL は絶対に辿らない（設計書5.4節）。

    AGENTS.md は「設定に書かれたURLしか取りに行かない。ページ内のリンクは
    辿らない」と約束している。解決先を同じ木の中に限ることが、その約束を
    保つ唯一の歯止めである。
    """
    asked = []

    def fetch(path):
        asked.append(path)
        return "should not be read"

    text = ':::code language="csharp" source="snippets/Missing.cs":::\n'
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(), fetch
    )
    assert asked == []
    assert resolved == text
    assert unresolved == 1


def test_an_unknown_region_leaves_the_directive_and_is_counted():
    """黙って落とすと、コードの入っていないページが混ざったことに気付けない。"""
    text = ':::code language="csharp" source="snippets/P.cs" id="Nope":::\n'
    files = {"docs/csharp/snippets/P.cs": "#region Other\nx\n#endregion\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == text
    assert unresolved == 1


def test_text_without_any_directive_is_returned_unchanged():
    text = "# Records\n\n```csharp\nint x = 1;\n```\n"
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(), _fetcher({})
    )
    assert resolved == text
    assert unresolved == 0


def test_several_directives_in_one_page_are_all_resolved():
    text = (
        "# A\n"
        ':::code language="csharp" source="s/One.cs":::\n'
        "text between\n"
        ':::code language="csharp" source="s/Two.cs":::\n'
    )
    files = {"docs/csharp/s/One.cs": "one\n", "docs/csharp/s/Two.cs": "two\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == (
        "# A\n```csharp\none\n```\ntext between\n```csharp\ntwo\n```\n"
    )
    assert unresolved == 0


def test_a_missing_language_falls_back_to_csharp():
    """language= を書かないページがある。タグ無しのフェンスにすると、
    チャンカーがコードとして扱えるかが読み手の目に頼ることになる。"""
    text = ':::code source="s/P.cs":::\n'
    files = {"docs/csharp/s/P.cs": "x\n"}
    resolved, _ = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nx\n```\n"


def test_an_id_selector_reads_the_comment_markers_dotnet_docs_actually_uses():
    """実測 2026-09-13: dotnet/docs の .cs は #region ではなく
    `// <Name>` 〜 `// </Name>` でコード例を囲んでいる。

    #region しか見ていなかったとき、581ページの取得で1,384件の :::code が
    解決できなかった。片方だけでは足りない。
    """
    text = ':::code language="csharp" source="snippets/P.cs" id="AddExpression":::\n'
    files = {
        "docs/csharp/snippets/P.cs": (
            "public static void AddExpression()\n"
            "{\n"
            "    // <AddExpression>\n"
            "    Expression<Func<int>> sum = () => 1 + 2;\n"
            "    // </AddExpression>\n"
            "}\n"
        )
    }
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nExpression<Func<int>> sum = () => 1 + 2;\n```\n"
    assert unresolved == 0


def test_an_indented_directive_inside_a_list_is_resolved():
    """箇条書きの中の :::code は字下げされている。

    実測 2026-09-13: 581ページ中254件がこの形で、行頭しか見ていなかったため
    解決も報告もされず素通りしていた。数えられない取りこぼしがいちばん悪い。
    """
    text = '  :::code language="csharp" source="./snippets/P.cs" id="S":::\n'
    files = {"docs/csharp/snippets/P.cs": "// <S>\nint x = 1;\n// </S>\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    # フェンスは字下げしない。ingest/chunker.py の _CODE_BLOCK は行頭の ``` しか
    # 見ないため、字下げするとコードブロックとして扱われなくなる。
    assert resolved == "```csharp\nint x = 1;\n```\n"
    assert unresolved == 0


def test_an_indented_directive_that_cannot_be_resolved_is_counted():
    text = '    :::code source="snippets/Missing.cs":::\n'
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(), _fetcher({})
    )
    assert resolved == text
    assert unresolved == 1


def test_an_id_matches_a_marker_with_the_snippet_prefix():
    """`id="PublicAccess"` が `//<SnippetPublicAccess>` を指すページがある。

    実測 2026-09-13: 木にある .cs を参照していながら印が見つからなかった333件の
    うち219件がこの形だった。id をそのまま探して無ければ Snippet を付けて探す。
    """
    text = ':::code language="csharp" source="s/P.cs" id="PublicAccess":::\n'
    files = {
        "docs/csharp/s/P.cs": (
            "//<SnippetPublicAccess>\npublic class Bicycle { }\n//</SnippetPublicAccess>\n"
        )
    }
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\npublic class Bicycle { }\n```\n"
    assert unresolved == 0


def test_a_byte_order_mark_does_not_hide_the_first_marker():
    """.cs の先頭に BOM が付いていることがある。

    実測 2026-09-13: 13件がこれで、ファイルの最初の印だけが見つからなかった。
    """
    text = ':::code language="csharp" source="s/P.cs" id="HelloWorld":::\n'
    files = {
        "docs/csharp/s/P.cs": (
            '\ufeff// <HelloWorld>\nConsole.WriteLine("Hi");\n// </HelloWorld>\n'
        )
    }
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == '```csharp\nConsole.WriteLine("Hi");\n```\n'
    assert unresolved == 0


def test_the_attribute_names_are_matched_regardless_of_case():
    """ID= と大文字で書いたページが3件あった（実測 2026-09-13）。"""
    text = ':::code language="csharp" SOURCE="s/P.cs" ID="S":::\n'
    files = {"docs/csharp/s/P.cs": "// <S>\nint x = 1;\n// </S>\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nint x = 1;\n```\n"
    assert unresolved == 0


def test_a_directive_inside_a_blockquote_is_resolved():
    """引用ブロックの中の :::code は `> ` が前に付く。

    実測 2026-09-13: 581ページ中3件がこの形で、字下げを許すだけでは拾えず、
    解決も報告もされずに素通りしていた（報告154件に対し実在157件）。
    件数が少なくても、報告に出ない取りこぼしは別扱いにしない。
    """
    text = '> :::code language="csharp" source="./snippets/P.cs" id="Singleton":::\n'
    files = {"docs/csharp/snippets/P.cs": "// <Singleton>\nint x = 1;\n// </Singleton>\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nint x = 1;\n```\n"
    assert unresolved == 0
