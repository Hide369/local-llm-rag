---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/public.md
title: public keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# public (C# reference)

Use the `public` keyword as an access modifier for types and type members. Public access is the most permissive access level. The following example shows that you can access public members without any restrictions:

```csharp
class SampleClass
{
    public int x; // No access restrictions.
}
```

For more information, see [Access Modifiers](../../programming-guide/classes-and-structs/access-modifiers.md) and [Accessibility Levels](accessibility-levels.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

In the following example, two classes are declared, `PointTest` and `Program`. The public members `x` and `y` of `PointTest` are accessed directly from `Program`.

:::code language="csharp" source="./snippets/csrefKeywordsModifiers.cs" id="13":::

If you change the `public` access level to [private](private.md) or [protected](protected.md), you get the error message:

'PointTest.y' is inaccessible due to its protection level.

## C# language specification  

For more information, see [Declared accessibility](~/_csharpstandard/standard/basic-concepts.md#752-declared-accessibility) in the [C# Language Specification](~/_csharpstandard/standard/README.md). The language specification is the definitive source for C# syntax and usage.

## See also

- [Access Modifiers](../../programming-guide/classes-and-structs/access-modifiers.md)
- [C# Keywords](index.md)
- [Access Modifiers](access-modifiers.md)
- [Accessibility Levels](accessibility-levels.md)
- [Modifiers](index.md)
- [private](private.md)
- [protected](protected.md)
- [internal](internal.md)
