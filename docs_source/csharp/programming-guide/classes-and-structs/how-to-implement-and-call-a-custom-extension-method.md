---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/classes-and-structs/how-to-implement-and-call-a-custom-extension-method.md
title: How to implement and call a custom extension method
version: 0.0.0
fetched_at: 2026-09-13
---
# How to implement and call a custom extension method (C# Programming Guide)

This article shows how to implement your own extension methods for any .NET type. Client code can use your extension methods. Client projects must reference the assembly that contains them. Client projects must add a [using](../../language-reference/keywords/using-directive.md) directive that specifies the namespace in which the extension methods are defined.

Beginning with C# 14, there are two syntaxes you can use to define extension methods. C# 14 adds [extension](../../language-reference/keywords/extension.md) blocks, where you define extension members for a type. Before C# 14, you add the [this](../../language-reference/keywords/this.md) modifier to the first parameter of a static method to indicate that the method appears as a member of an instance of the parameter type.

## Extension blocks (C# 14 and later)

Beginning with C# 14, you can declare extension methods using *extension blocks*. An extension block is a block in a non-nested, non-generic, static class that contains extension members for a type or an instance of that type.

To define and call an extension method using extension blocks:

1. Define a static [class](./static-classes-and-static-class-members.md) to contain the extension method. The class can't be nested inside another type and must be visible to client code. For more information about accessibility rules, see [Access Modifiers](./access-modifiers.md).
1. Use an [extension](../../language-reference/keywords/extension.md) block to declare extension members for a type.
1. In the calling code, add a `using` directive to specify the [namespace](../../language-reference/keywords/namespace.md) that contains the extension method class.
1. Call the methods as instance methods on the type.

The following example implements an extension method named `WordCount` using the C# 14 extension block syntax. The method operates on the <xref:System.String> class. The `CustomExtensions` namespace is imported into the application namespace, and the method is called as if it were an instance method on the string.

```csharp
using CustomExtensions;

string s = "The quick brown fox jumped over the lazy dog.";
// Call the method as if it were an
// instance method on the type. Note that the first
// parameter is not specified by the calling code.
int i = s.WordCount();
System.Console.WriteLine($"Word count of s is {i}");


namespace CustomExtensions
{
    // Extension methods must be defined in a static class.
    public static class StringExtension
    {
        extension(string str)
        {
            // This is the extension member.
            // The `str` parameter is declared on the extension declaration.
            public int WordCount()
            {
                return str.Split(new char[] { ' ', '.', '?' }, StringSplitOptions.RemoveEmptyEntries).Length;
            }
        }
    }
}
```

## Extension methods (earlier versions)

Before C# 14, you declare an extension method by adding the [this](../../language-reference/keywords/this.md) modifier to the first parameter of a static method.

To define and call an extension method using the classic syntax:

1. Define a static [class](./static-classes-and-static-class-members.md) to contain the extension method. The class can't be nested inside another type and must be visible to client code. For more information about accessibility rules, see [Access Modifiers](./access-modifiers.md).
1. Implement the extension method as a static method with at least the same visibility as the containing class.
1. The first parameter of the method specifies the type that the method operates on; it must be preceded with the [this](../../language-reference/keywords/this.md) modifier.
1. In the calling code, add a `using` directive to specify the [namespace](../../language-reference/keywords/namespace.md) that contains the extension method class.
1. Call the methods as instance methods on the type.

The following example implements an extension method named `WordCount` using the classic syntax. The method operates on the <xref:System.String> class, which is specified as the first method parameter with the `this` modifier. The `CustomExtensions` namespace is imported into the application namespace, and the method is called as if it were an instance method on the string.

```csharp
using CustomExtensions;

string s = "The quick brown fox jumped over the lazy dog.";
// Call the method as if it were an
// instance method on the type. Note that the first
// parameter is not specified by the calling code.
int i = s.WordCount();
System.Console.WriteLine($"Word count of s is {i}");


namespace CustomExtensions
{
    // Extension methods must be defined in a static class.
    public static class StringExtension
    {
        // This is the extension method.
        // The first parameter takes the "this" modifier
        // and specifies the type to be extended.
        public static int WordCount(this string str)
        {
            return str.Split(new char[] { ' ', '.', '?' }, StringSplitOptions.RemoveEmptyEntries).Length;
        }
    }
}
```

> [!NOTE]
> The first parameter is not specified by calling code because it represents the type on which the method is being applied, and the compiler already knows the type of your object. You only have to provide arguments for parameters 2 through `n`.

## General information

Overload resolution prefers instance or static methods defined by the type itself to extension methods. Extension methods can't access any private data in the extended class.

## See also

- [Extension Methods](./extension-methods.md)
- [LINQ (Language-Integrated Query)](../../linq/index.md)
- [Static Classes and Static Class Members](./static-classes-and-static-class-members.md)
- [protected](../../language-reference/keywords/protected.md)
- [internal](../../language-reference/keywords/internal.md)
- [public](../../language-reference/keywords/public.md)
- [this](../../language-reference/keywords/this.md)
- [namespace](../../language-reference/keywords/namespace.md)
