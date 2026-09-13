---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/interfaces/how-to-explicitly-implement-interface-members.md
title: How to explicitly implement interface members
version: 0.0.0
fetched_at: 2026-09-13
---
# How to explicitly implement interface members (C# Programming Guide)

This example declares an [interface](../../language-reference/keywords/interface.md), `IDimensions`, and a class, `Box`, which explicitly implements the interface members `GetLength` and `GetWidth`. The members are accessed through the interface instance `dimensions`.  
  
## Example  

 [!code-csharp[csProgGuideInheritance#8](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideInheritance/CS/Inheritance.cs#8)]  
  
## Robust Programming  
  
- Notice that the following lines, in the `Main` method, are commented out because they would produce compilation errors. An interface member that is explicitly implemented cannot be accessed from a [class](../../language-reference/keywords/class.md) instance:  
  
     [!code-csharp[csProgGuideInheritance#45](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideInheritance/CS/Inheritance.cs#45)]  
  
- Notice also that the following lines, in the `Main` method, successfully print out the dimensions of the box because the methods are being called from an instance of the interface:  
  
     [!code-csharp[csProgGuideInheritance#46](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideInheritance/CS/Inheritance.cs#46)]  
  
## See also

- [Object oriented programming](../../fundamentals/object-oriented/index.md)
- [Interfaces](../../fundamentals/types/interfaces.md)
- [How to explicitly implement members of two interfaces](./how-to-explicitly-implement-members-of-two-interfaces.md)
