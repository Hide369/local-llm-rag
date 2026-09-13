---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/descending.md
title: descending contextual keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# descending (C# Reference)

Use the `descending` contextual keyword in the [orderby clause](./orderby-clause.md) of query expressions to specify that the sort order is from largest to smallest.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows how to use `descending` in an [orderby clause](./orderby-clause.md).

```csharp
IEnumerable<string> sortDescendingQuery =
    from vegetable in vegetables
    orderby vegetable descending
    select vegetable;
```

## See also

- [LINQ in C#](../../linq/index.md)
- [ascending](./ascending.md)
