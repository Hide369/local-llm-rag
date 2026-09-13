---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/generics/generic-type-parameters.md
title: Generic Type Parameters
version: 0.0.0
fetched_at: 2026-09-13
---
# Generic type parameters (C# Programming Guide)

In a generic type or method definition, a type parameter is a placeholder for a specific type that a client specifies when they create an instance of the generic type. A generic class, such as `GenericList<T>` listed in [Introduction to Generics](../../fundamentals/types/generics.md), cannot be used as-is because it is not really a type; it is more like a blueprint for a type. To use `GenericList<T>`, client code must declare and instantiate a constructed type by specifying a type argument inside the angle brackets. The type argument for this particular class can be any type recognized by the compiler. Any number of constructed type instances can be created, each one using a different type argument, as follows:

[!code-csharp[csProgGuideGenerics#7](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideGenerics/CS/Generics.cs#7)]

In each of these instances of `GenericList<T>`, every occurrence of `T` in the class is substituted at run time with the type argument. By means of this substitution, we have created three separate type-safe and efficient objects using a single class definition. For more information on how this substitution is performed by the CLR, see [Generics in the Runtime](./generics-in-the-run-time.md).

You can learn the naming conventions for generic type parameters in the article on [naming conventions](../../fundamentals/coding-style/identifier-names.md#type-parameter-naming-guidelines).

## See also

- <xref:System.Collections.Generic>
- [Generics](../../fundamentals/types/generics.md)
- [Differences Between C++ Templates and C# Generics](./differences-between-cpp-templates-and-csharp-generics.md)
