---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/interfaces/how-to-explicitly-implement-members-of-two-interfaces.md
title: How to explicitly implement members of two interfaces
version: 0.0.0
fetched_at: 2026-09-13
---
# How to explicitly implement members of two interfaces (C# Programming Guide)

Explicit [interface](../../language-reference/keywords/interface.md) implementation also allows the programmer to implement two interfaces that have the same member names and give each interface member a separate implementation. This example displays the dimensions of a box in both metric and English units. The Box [class](../../language-reference/keywords/class.md) implements two interfaces IEnglishDimensions and IMetricDimensions, which represent the different measurement systems. Both interfaces have identical member names, Length and Width.  
  
## Example  

 [!code-csharp[csProgGuideInheritance#9](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideInheritance/CS/Inheritance.cs#9)]  
  
## Robust Programming  

 If you want to make the default measurements in English units, implement the methods Length and Width normally, and explicitly implement the Length and Width methods from the IMetricDimensions interface:  
  
 [!code-csharp[csProgGuideInheritance#10](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideInheritance/CS/Inheritance.cs#10)]  
  
 In this case, you can access the English units from the class instance and access the metric units from the interface instance:  
  
 [!code-csharp[csProgGuideInheritance#11](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideInheritance/CS/Inheritance.cs#11)]  
  
## See also

- [Object oriented programming](../../fundamentals/object-oriented/index.md)
- [Interfaces](../../fundamentals/types/interfaces.md)
- [How to explicitly implement interface members](./how-to-explicitly-implement-interface-members.md)
