---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/new-constraint.md
title: new constraint
version: 0.0.0
fetched_at: 2026-09-13
---
# new constraint (C# Reference)

The `new` constraint specifies that a type argument in a generic class or method declaration must have a public parameterless constructor. To use the `new` constraint, the type can't be abstract.

Apply the `new` constraint to a type parameter when a generic class creates new instances of the type, as shown in the following example:

:::code language="csharp" source="./snippets/csrefKeywordsOperators.cs" id="5":::

When you use the `new()` constraint with other constraints, you must specify it last:

:::code language="csharp" source="./snippets/csrefKeywordsOperators.cs" id="6":::

For more information, see [Constraints on Type Parameters](../../programming-guide/generics/constraints-on-type-parameters.md).

You can also use the `new` keyword to [create an instance of a type](../operators/new-operator.md) or as a [member declaration modifier](new-modifier.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

## C# language specification

For more information, see the [Type parameter constraints](~/_csharpstandard/standard/classes.md#1525-type-parameter-constraints) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# Keywords](index.md)
- [Generics](../../fundamentals/types/generics.md)
