---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/into.md
title: into keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# into (C# Reference)

Use the `into` contextual keyword to create a temporary identifier that stores the results of a [`group`](group-clause.md), [`join`](join-clause.md), or [`select`](select-clause.md) clause. This identifier can act as a generator for additional query commands. When you use the new identifier in a `group` or `select` clause, it's sometimes called a *continuation*.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows how to use the `into` keyword to create a temporary identifier named `fruitGroup`, which has an inferred type of `IGrouping`. By using this identifier, you can call the <xref:System.Linq.Enumerable.Count*> method on each group and select only those groups that contain two or more words.

:::code language="csharp" source="./snippets/into.cs" id="18":::

You only need to use `into` in a `group` clause when you want to perform additional query operations on each group. For more information, see [group clause](group-clause.md).

For an example of using `into` in a `join` clause, see [join clause](join-clause.md).

## See also

- [Query Keywords (LINQ)](query-keywords.md)
- [LINQ in C#](../../linq/index.md)
- [group clause](group-clause.md)
