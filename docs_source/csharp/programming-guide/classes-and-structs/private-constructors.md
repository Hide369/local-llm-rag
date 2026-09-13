---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/classes-and-structs/private-constructors.md
title: Private Constructors
version: 0.0.0
fetched_at: 2026-09-13
---
# Private Constructors (C# Programming Guide)

A private constructor is a special instance constructor. It is generally used in classes that contain static members only. If a class has one or more private constructors and no public constructors, other classes (except nested classes) cannot create instances of this class. For example:  
  
 [!code-csharp[ClassWithPrivateConstructorExample#1](snippets/private-constructors/Program.cs#1)]
  
 The declaration of the empty constructor prevents the automatic generation of a parameterless constructor. Note that if you do not use an access modifier with the constructor it will still be private by default. However, the [private](../../language-reference/keywords/private.md) modifier is usually used explicitly to make it clear that the class cannot be instantiated.  
  
 Private constructors are used to prevent creating instances of a class when there are no instance fields or methods, such as the <xref:System.Math> class, or when a method is called to obtain an instance of a class. If all the methods in the class are static, consider making the complete class static. For more information see [Static Classes and Static Class Members](./static-classes-and-static-class-members.md).  
  
## Example  

 The following is an example of a class using a private constructor.  
  
 [!code-csharp[CounterClassWithPrivateConstructor#2](snippets/private-constructors/Program.cs#2)]
  
 Notice that if you uncomment the following statement from the example, it will generate an error because the constructor is inaccessible because of its protection level:  
  
 [!code-csharp[ErrorInstantiatingUsingPrivateConstructor#13](snippets/private-constructors/Program.cs#3)]
  
## See also

- [The C# type system](../../fundamentals/types/index.md)
- [Constructors](./constructors.md)
- [Finalizers](./finalizers.md)
- [private](../../language-reference/keywords/private.md)
- [public](../../language-reference/keywords/public.md)
