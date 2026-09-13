---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/builtin-types/value-types.md
title: Value types
version: 0.0.0
fetched_at: 2026-09-13
---
# Value types (C# reference)

*Value types* and [reference types](../keywords/reference-types.md) are the two main categories of C# types. A variable of a value type contains an instance of the type. This behavior differs from a variable of a reference type, which contains a reference to an instance of the type. By default, on [assignment](../operators/assignment-operator.md), passing an argument to a method, and returning a method result, you copy variable values. In the case of value-type variables, you copy the corresponding type instances. The following example demonstrates that behavior:

```csharp
using System;

public struct MutablePoint
{
    public int X;
    public int Y;

    public MutablePoint(int x, int y) => (X, Y) = (x, y);

    public override string ToString() => $"({X}, {Y})";
}

public class Program
{
    public static void Main()
    {
        var p1 = new MutablePoint(1, 2);
        var p2 = p1;
        p2.Y = 200;
        Console.WriteLine($"{nameof(p1)} after {nameof(p2)} is modified: {p1}");
        Console.WriteLine($"{nameof(p2)}: {p2}");

        MutateAndDisplay(p2);
        Console.WriteLine($"{nameof(p2)} after passing to a method: {p2}");
    }

    private static void MutateAndDisplay(MutablePoint p)
    {
        p.X = 100;
        Console.WriteLine($"Point mutated in a method: {p}");
    }
}
// Expected output:
// p1 after p2 is modified: (1, 2)
// p2: (1, 200)
// Point mutated in a method: (100, 200)
// p2 after passing to a method: (1, 200)
```

As the preceding example shows, operations on a value-type variable affect only that instance of the value type, stored in the variable.

If a value type contains a data member of a reference type, you copy only the reference to the instance of the reference type when you copy a value-type instance. Both the copy and original value-type instance have access to the same reference-type instance. The following example demonstrates that behavior:

```csharp
using System;
using System.Collections.Generic;

public struct TaggedInteger
{
    public int Number;
    private List<string> tags;

    public TaggedInteger(int n)
    {
        Number = n;
        tags = new List<string>();
    }

    public void AddTag(string tag) => tags.Add(tag);

    public override string ToString() => $"{Number} [{string.Join(", ", tags)}]";
}

public class Program
{
    public static void Main()
    {
        var n1 = new TaggedInteger(0);
        n1.AddTag("A");
        Console.WriteLine(n1);  // output: 0 [A]

        var n2 = n1;
        n2.Number = 7;
        n2.AddTag("B");

        Console.WriteLine(n1);  // output: 0 [A, B]
        Console.WriteLine(n2);  // output: 7 [A, B]
    }
}
```

> [!NOTE]
> To make your code less error-prone and more robust, define and use immutable value types. This article uses mutable value types only for demonstration purposes.

## Kinds of value types and type constraints

A value type can be one of the following kinds:

- A [structure type](struct.md), which encapsulates data and related functionality.
- An [enumeration type](enum.md), which is defined by a set of named constants and represents a choice or a combination of choices.
- A [union declaration](union.md), which defines a closed set of case types that a value can represent.

A [nullable value type](nullable-value-types.md) `T?` represents all values of its underlying value type `T` and an additional [null](../keywords/null.md) value. You can't assign `null` to a variable of a value type, unless it's a nullable value type.

Use the [`struct` constraint](../../programming-guide/generics/constraints-on-type-parameters.md) to specify that a type parameter is a non-nullable value type. Both structure and enumeration types satisfy the `struct` constraint. Use `System.Enum` in a base class constraint (that is known as the [enum constraint](../../programming-guide/generics/constraints-on-type-parameters.md#enum-constraints)) to specify that a type parameter is an enumeration type.

## Built-in value types

C# provides the following built-in value types, also known as *simple types*:

- [Integral numeric types](integral-numeric-types.md)
- [Floating-point numeric types](floating-point-numeric-types.md)
- [bool](bool.md) that represents a Boolean value
- [char](char.md) that represents a Unicode UTF-16 character

All simple types are struct types. They differ from other struct types in that they permit certain additional operations:

- You can use literals to provide a value of a simple type.
<br/>For example, `'A'` is a literal of the type `char`, `2001` is a literal of the type `int`, and `12.34m` is a literal of the type `decimal`.

- You can declare constants of the simple types by using the [const](../keywords/const.md) keyword.
<br/>For example, you can define `const decimal = 12.34m`.
<br/>You can't declare constants of other struct types.

- Constant expressions, whose operands are all constants of the simple types, are evaluated at compile time.

A [value tuple](value-tuples.md) is a value type, but not a simple type.

## C# language specification

For more information, see the following sections of the [C# language specification](~/_csharpstandard/standard/README.md):

- [Value types](~/_csharpstandard/standard/types.md#83-value-types)
- [Simple types](~/_csharpstandard/standard/types.md#835-simple-types)
- [Variables](~/_csharpstandard/standard/variables.md)

## See also

- <xref:System.ValueType?displayProperty=nameWithType>
- [Reference types](../keywords/reference-types.md)
