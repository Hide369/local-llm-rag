---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/let-clause.md
title: let clause
version: 0.0.0
fetched_at: 2026-09-13
---
# `let` clause (C# Reference)

In a query expression, it can be useful to store the result of a subexpression so you can use it in later clauses. Use the `let` keyword to create a new range variable and initialize it with the result of an expression. After you initialize the range variable with a value, you can't assign it another value. However, if the range variable holds a queryable type, you can query it.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

In the following example, `let` is used in two ways:

1. It creates an enumerable type that you can query.
1. It enables the query to call `ToLower` only one time on the range variable `word`. Without using `let`, you'd have to call `ToLower` in each predicate in the `where` clause.

:::code language="csharp" source="./snippets/let.cs" id="28":::

## See also

- [Query Keywords (LINQ)](query-keywords.md)
- [LINQ in C#](../../linq/index.md)
- [Language Integrated Query (LINQ)](../../linq/index.md)
- [Handle exceptions in query expressions](../../linq/get-started/write-linq-queries.md)
