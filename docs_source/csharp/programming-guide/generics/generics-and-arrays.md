---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/generics/generics-and-arrays.md
title: Generics and Arrays
version: 0.0.0
fetched_at: 2026-09-13
---
# Generics and Arrays (C# Programming Guide)

Single-dimensional arrays that have a lower bound of zero automatically implement <xref:System.Collections.Generic.IList`1>. This enables you to create generic methods that can use the same code to iterate through arrays and other collection types. This technique is primarily useful for reading data in collections. The <xref:System.Collections.Generic.IList`1> interface cannot be used to add or remove elements from an array. An exception will be thrown if you try to call an <xref:System.Collections.Generic.IList`1> method such as <xref:System.Collections.Generic.IList`1.RemoveAt*> on an array in this context.

 The following code example demonstrates how a single generic method that takes an <xref:System.Collections.Generic.IList`1> input parameter can iterate through both a list and an array, in this case an array of integers.

 [!code-csharp[csProgGuideGenerics#35](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideGenerics/CS/Generics.cs#35)]

## See also

- <xref:System.Collections.Generic>
- [Generics](../../fundamentals/types/generics.md)
- [Arrays](../../language-reference/builtin-types/arrays.md)
- [Generics](../../../standard/generics/index.md)
