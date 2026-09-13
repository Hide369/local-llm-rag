---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/user-defined-conversion-operators.md
title: User-defined explicit and implicit conversion operators - provide conversions to different types
version: 0.0.0
fetched_at: 2026-09-13
---
# User-defined explicit and implicit conversion operators

A user-defined type can define a custom implicit or explicit conversion from or to another type, provided a standard conversion doesn't exist between the same two types. Implicit conversions don't require special syntax to be invoked and can occur in various situations, for example, in assignments and methods invocations. Predefined C# implicit conversions always succeed and never throw an exception. User-defined implicit conversions should behave in that way as well. If a custom conversion can throw an exception or lose information, define it as an explicit conversion.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The [is](type-testing-and-cast.md#the-is-operator) and [as](type-testing-and-cast.md#the-as-operator) operators don't consider user-defined conversions. Use a [cast expression](type-testing-and-cast.md#cast-expression) to invoke a user-defined explicit conversion.

Use the `operator` and `implicit` or `explicit` keywords to define an implicit or explicit conversion, respectively. The type that defines a conversion must be either a source type or a target type of that conversion. You can define a conversion between two user-defined types in either of the two types.

The following example demonstrates how to define an implicit and explicit conversion:

```csharp
using System;

public readonly struct Digit
{
    private readonly byte digit;

    public Digit(byte digit)
    {
        if (digit > 9)
        {
            throw new ArgumentOutOfRangeException(nameof(digit), "Digit cannot be greater than nine.");
        }
        this.digit = digit;
    }

    public static implicit operator byte(Digit d) => d.digit;
    public static explicit operator Digit(byte b) => new Digit(b);

    public override string ToString() => $"{digit}";
}

public static class UserDefinedConversions
{
    public static void Main()
    {
        var d = new Digit(7);

        byte number = d;
        Console.WriteLine(number);  // output: 7

        Digit digit = (Digit)number;
        Console.WriteLine(digit);  // output: 7
    }
}
```

You can define *checked* explicit conversion operators. For more information, see the [User-defined checked operators](arithmetic-operators.md#user-defined-checked-operators) section of the [Arithmetic operators](arithmetic-operators.md) article.

You also use the `operator` keyword to overload a predefined C# operator. For more information, see [Operator overloading](operator-overloading.md).

## C# language specification

For more information, see the following sections of the [C# language specification](~/_csharpstandard/standard/README.md):

- [Conversion operators](~/_csharpstandard/standard/classes.md#15104-conversion-operators)
- [User-defined conversions](~/_csharpstandard/standard/conversions.md#105-user-defined-conversions)
- [Implicit conversions](~/_csharpstandard/standard/conversions.md#102-implicit-conversions)
- [Explicit conversions](~/_csharpstandard/standard/conversions.md#103-explicit-conversions)

## See also

- [C# operators and expressions](index.md)
- [Operator overloading](operator-overloading.md)
- [Type-testing and cast operators](type-testing-and-cast.md)
- [Casting and type conversion](../../programming-guide/types/casting-and-type-conversions.md)
- [Design guidelines - Conversion operators](../../../standard/design-guidelines/operator-overloads.md#conversion-operators)
- [Chained user-defined explicit conversions in C#](/archive/blogs/ericlippert/chained-user-defined-explicit-conversions-in-c)
