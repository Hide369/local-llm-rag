---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/orderby-clause.md
title: orderby clause
version: 0.0.0
fetched_at: 2026-09-13
---
# orderby clause (C# Reference)

In a query expression, the `orderby` clause sorts the returned sequence or subsequence (group) in either ascending or descending order. You can specify multiple keys to perform one or more secondary sort operations. The default comparer for the type of the element performs the sorting. The default sort order is ascending. You can also specify a custom comparer, but you can only provide it by using method-based syntax. For more information, see [Sorting Data](../../linq/standard-query-operators/sorting-data.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

In the following example, the first query sorts the words in alphabetical order starting from A, and second query sorts the same words in descending order. (The `ascending` keyword is the default sort value and can be omitted.)

:::code language="csharp" source="./snippets/Orderby.cs" id="20":::

The following example performs a primary sort on the students' last names, and then a secondary sort on their first names.

:::code language="csharp" source="./snippets/Orderby.cs" id="22":::

At compile time, the `orderby` clause translates to a call to the <xref:System.Linq.Enumerable.OrderBy*> method. Multiple keys in the `orderby` clause translate to <xref:System.Linq.Enumerable.ThenBy*> method calls.

## See also

- [Query Keywords (LINQ)](query-keywords.md)
- [LINQ in C#](../../linq/index.md)
- [group clause](group-clause.md)
- [Language Integrated Query (LINQ)](../../linq/index.md)
