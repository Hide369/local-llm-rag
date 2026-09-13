---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/ref.md
title: The multiple uses of the `ref` keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# The `ref` keyword

You use the `ref` keyword in the following contexts:

- In a method signature and in a method call, to pass an argument to a method [by reference](./method-parameters.md#ref-parameter-modifier).
  :::code language="csharp" source="./snippets/refKeyword.cs" id="PassByReference":::
- In a method signature, to return a value to the caller by reference. For more information, see [`ref return`](../statements/jump-statements.md#ref-returns).
  :::code language="csharp" source="./snippets/refKeyword.cs" id="ReturnByReference":::
- In a declaration of a local variable, to declare a [reference variable](../statements/declarations.md#reference-variables).
  :::code language="csharp" source="./snippets/refKeyword.cs" id="LocalRef":::
- As the part of a [conditional ref expression](../operators/conditional-operator.md#conditional-ref-expression) or a [ref assignment operator](../operators/assignment-operator.md#ref-assignment).
  :::code language="csharp" source="./snippets/refKeyword.cs" id="ConditionalRef":::
- In a `struct` declaration, to declare a `ref struct`. For more information, see the [`ref` structure types](../builtin-types/ref-struct.md) article.
  :::code language="csharp" source="./snippets/refKeyword.cs" id="SnippetRefStruct":::
- In a `ref struct` definition, to declare a `ref` field. For more information, see the [`ref` fields](../builtin-types/ref-struct.md#ref-fields) section of the [`ref` structure types](../builtin-types/ref-struct.md) article.
  :::code language="csharp" source="./snippets/refKeyword.cs" id="SnippetRefField":::
- In a generic type declaration to specify that a type parameter [`allows ref struct`](../../programming-guide/generics/constraints-on-type-parameters.md#allows-ref-struct) types.
  :::code language="csharp" source="./snippets/refKeyword.cs" id="SnippetRefGeneric":::
