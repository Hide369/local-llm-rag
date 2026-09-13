---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/tokens/discard.md
title: Discard - _
version: 0.0.0
fetched_at: 2026-09-13
---
# Discard - A `_` acts as a placeholder for a variable

The `_` character serves as a *discard*, which is a placeholder for an unused variable.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

Use the *discard* token in two ways:

1. To declare an unused variable. You can't read or access a discard.
   - Unused `out` arguments: `var r = M(out int _, out var _, out _);`
   - Unused lambda expression parameters: `Action<int> _ => WriteMessage();`
   - Unused deconstruction arguments: `(int _, var answer) = M();`
1. To match any expression in a [discard pattern](../operators/patterns.md#discard-pattern). You can add a `_` pattern to satisfy exhaustiveness requirements.

The `_` token is a valid identifier in C#. The compiler interprets the `_` token as a discard only when it doesn't find a valid identifier named `_` in scope.

You can't read a discard as a variable. If your code reads a discard, the compiler reports an error. In some situations, the compiler can avoid allocating storage for a discard when it's safe to do so.

## See also

- [Tuples](../builtin-types/value-tuples.md)
- [Deconstruction](../tokens/discard.md)
- [Discard pattern](../operators/patterns.md#discard-pattern)
