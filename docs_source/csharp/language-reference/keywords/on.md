---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/on.md
title: on keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# on (C# Reference)

Use the `on` contextual keyword in the [join clause](join-clause.md) of a query expression to specify the join condition.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows how to use `on` in a `join` clause.

```csharp
var innerJoinQuery =
    from category in categories
    join prod in products on category.ID equals prod.CategoryID
    select new { ProductName = prod.Name, Category = category.Name };
```

## See also

- [Language Integrated Query (LINQ)](../../linq/index.md)
