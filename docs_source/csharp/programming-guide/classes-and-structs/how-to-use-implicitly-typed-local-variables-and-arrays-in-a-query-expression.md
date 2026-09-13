---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/classes-and-structs/how-to-use-implicitly-typed-local-variables-and-arrays-in-a-query-expression.md
title: How to use implicitly typed local variables and arrays in a query expression
version: 0.0.0
fetched_at: 2026-09-13
---
# How to use implicitly typed local variables and arrays in a query expression (C# Programming Guide)

You can use implicitly typed local variables whenever you want the compiler to determine the type of a local variable. You must use implicitly typed local variables to store anonymous types, which are often used in query expressions. The following examples illustrate both optional and required uses of implicitly typed local variables in queries.  
  
 Implicitly typed local variables are declared by using the [var](../../language-reference/statements/declarations.md#implicitly-typed-local-variables) contextual keyword. For more information, see [Implicitly Typed Local Variables](./implicitly-typed-local-variables.md) and [Implicitly Typed Arrays](../../language-reference/builtin-types/arrays.md#implicitly-typed-arrays).  
  
## Examples  

 The following example shows a common scenario in which the `var` keyword is required: a query expression that produces a sequence of anonymous types. In this scenario, both the query variable and the iteration variable in the `foreach` statement must be implicitly typed by using `var` because you do not have access to a type name for the anonymous type. For more information about anonymous types, see [Anonymous Types](anonymous-types.md).  
  
 [!code-csharp[csProgGuideLINQ#32](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideLINQ/CS/csRef30LangFeatures_2.cs#32)]  
  
 The following example uses the `var` keyword in a situation that is similar, but in which the use of `var` is optional. Because `student.LastName` is a string, execution of the query returns a sequence of strings. Therefore, the type of `queryId` could be declared as `System.Collections.Generic.IEnumerable<string>` instead of `var`. Keyword `var` is used for convenience. In the example, the iteration variable in the `foreach` statement is explicitly typed as a string, but it could instead be declared by using `var`. Because the type of the iteration variable is not an anonymous type, the use of `var` is an option, not a requirement. Remember, `var` itself is not a type, but an instruction to the compiler to infer and assign the type.  
  
 [!code-csharp[csProgGuideLINQ#33](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideLINQ/CS/csRef30LangFeatures_2.cs#33)]  
  
## See also

- [Extension members](./extension-methods.md)
- [LINQ (Language-Integrated Query)](../../linq/index.md)
- [LINQ in C#](../../linq/index.md)
