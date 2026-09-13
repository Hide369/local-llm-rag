---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/reference-types.md
title: Reference types
version: 0.0.0
fetched_at: 2026-09-13
---
# Reference types (C# reference)

C# has two kinds of types: reference types and value types. Variables of reference types store references to their data (objects), while variables of value types directly contain their data. With reference types, two variables can reference the same object. Therefore, operations on one variable can affect the object referenced by the other variable. With value types, each variable has its own copy of the data. Operations on one variable can't affect the other variable, except in the case of `in`, `ref`, and `out` parameter variables. For more information, see [in](method-parameters.md#in-parameter-modifier), [ref](ref.md), and [out](method-parameters.md#out-parameter-modifier) parameter modifier.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

 Use the following keywords to declare reference types:

- [class](class.md)
- [interface](interface.md)
- [delegate](../builtin-types/reference-types.md#the-delegate-type)
- [record](../builtin-types/record.md)

 C# also provides the following built-in reference types:

- [dynamic](../builtin-types/reference-types.md#the-dynamic-type)
- [object](../builtin-types/reference-types.md#the-object-type)
- [string](../builtin-types/reference-types.md#the-string-type)

## See also

- [C# keywords](index.md)
- [Pointer types](../unsafe-code.md#pointer-types)
- [Value types](../builtin-types/value-types.md)
