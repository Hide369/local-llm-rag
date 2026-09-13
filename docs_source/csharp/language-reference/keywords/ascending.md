---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/ascending.md
title: ascending keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# ascending (C# Reference)

Use the `ascending` contextual keyword in the [orderby clause](./orderby-clause.md) of query expressions to specify that the sort order goes from smallest to largest. Because `ascending` is the default sort order, you don't need to specify it.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows how to use `ascending` in an [orderby clause](./orderby-clause.md).

```csharp
IEnumerable<string> sortAscendingQuery =
    from vegetable in vegetables
    orderby vegetable ascending
    select vegetable;
```

## See also

- [LINQ in C#](../../linq/index.md)
- [descending](./descending.md)
