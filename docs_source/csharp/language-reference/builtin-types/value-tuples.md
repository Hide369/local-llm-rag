---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/builtin-types/value-tuples.md
title: Tuple types
version: 0.0.0
fetched_at: 2026-09-13
---
# Tuple types (C# reference)

The *tuples* feature provides a concise syntax to group multiple data elements in a lightweight data structure.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows how you can declare a tuple variable, initialize it, and access its data members:

```csharp
(double, int) t1 = (4.5, 3);
Console.WriteLine($"Tuple with elements {t1.Item1} and {t1.Item2}.");
// Output:
// Tuple with elements 4.5 and 3.

(double Sum, int Count) t2 = (4.5, 3);
Console.WriteLine($"Sum of {t2.Count} elements is {t2.Sum}.");
// Output:
// Sum of 3 elements is 4.5.
```

As the preceding example shows, to define a tuple type, you specify the types of all its data members and, optionally, the [field names](#tuple-field-names). You can't define methods in a tuple type, but you can use the methods provided by .NET, as the following example shows:

```csharp
(double, int) t = (4.5, 3);
Console.WriteLine(t.ToString());
Console.WriteLine($"Hash code of {t} is {t.GetHashCode()}.");
// Output:
// (4.5, 3)
// Hash code of (4.5, 3) is 718460086.
```

Tuple types support [equality operators](../operators/equality-operators.md) `==` and `!=`. For more information, see the [Tuple equality](#tuple-equality) section.

Tuple types are [value types](value-types.md); tuple elements are public fields. That design makes tuples *mutable* value types.

You can define tuples with an arbitrarily large number of elements:

```csharp
var t =
(1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
11, 12, 13, 14, 15, 16, 17, 18,
19, 20, 21, 22, 23, 24, 25, 26);
Console.WriteLine(t.Item26);  // output: 26
```

## Use cases for tuples

One of the most common use cases for tuples is as a method return type. Instead of defining [`out` method parameters](../keywords/method-parameters.md#out-parameter-modifier), group method results in a tuple return type, as the following example shows:

```csharp
int[] xs = new int[] { 4, 7, 9 };
var limits = FindMinMax(xs);
Console.WriteLine($"Limits of [{string.Join(" ", xs)}] are {limits.min} and {limits.max}");
// Output:
// Limits of [4 7 9] are 4 and 9

int[] ys = new int[] { -9, 0, 67, 100 };
var (minimum, maximum) = FindMinMax(ys);
Console.WriteLine($"Limits of [{string.Join(" ", ys)}] are {minimum} and {maximum}");
// Output:
// Limits of [-9 0 67 100] are -9 and 100

(int min, int max) FindMinMax(int[] input)
{
    if (input is null || input.Length == 0)
    {
        throw new ArgumentException("Cannot find minimum and maximum of a null or empty array.");
    }

    // Initialize min to MaxValue so every value in the input
    // is less than this initial value.
    var min = int.MaxValue;
    // Initialize max to MinValue so every value in the input
    // is greater than this initial value.
    var max = int.MinValue;
    foreach (var i in input)
    {
        if (i < min)
        {
            min = i;
        }
        if (i > max)
        {
            max = i;
        }
    }
    return (min, max);
}
```

As the preceding example shows, you can work with the returned tuple instance directly or [deconstruct](#tuple-assignment-and-deconstruction) it in separate variables.

You can also use tuple types instead of anonymous types; for example, in LINQ queries. For more information, see [Choosing between anonymous and tuple types](../../../standard/base-types/choosing-between-anonymous-and-tuple.md).

Typically, use tuples to group loosely related data elements. In public APIs, consider defining a [class](../keywords/class.md) or a [structure](struct.md) type.

## Tuple field names

You explicitly specify tuple field names in a tuple initialization expression or in the definition of a tuple type, as the following example shows:

[!code-csharp[explicit field names](snippets/shared/ValueTuples.cs#ExplicitFieldNames)]

If you don't specify a field name, the compiler might infer it from the name of the corresponding variable in a tuple initialization expression, as the following example shows:

```csharp
var sum = 4.5;
var count = 3;
var t = (sum, count);
Console.WriteLine($"Sum of {t.count} elements is {t.sum}.");
```

This feature is called tuple projection initializers. The name of a variable isn't projected onto a tuple field name in the following cases:

- The candidate name is a member name of a tuple type, for example, `Item3`, `ToString`, or `Rest`.
- The candidate name is a duplicate of another tuple field name, either explicit or implicit.

In the preceding cases, you either explicitly specify the name of a field or access a field by its default name.

The default names of tuple fields are `Item1`, `Item2`, `Item3`, and so on. You can always use the default name of a field, even when a field name is specified explicitly or inferred, as the following example shows:

```csharp
var a = 1;
var t = (a, b: 2, 3);
Console.WriteLine($"The 1st element is {t.Item1} (same as {t.a}).");
Console.WriteLine($"The 2nd element is {t.Item2} (same as {t.b}).");
Console.WriteLine($"The 3rd element is {t.Item3}.");
// Output:
// The 1st element is 1 (same as 1).
// The 2nd element is 2 (same as 2).
// The 3rd element is 3.
```

[Tuple assignment](#tuple-assignment-and-deconstruction) and [tuple equality comparisons](#tuple-equality) don't take field names into account.

At compile time, the compiler replaces non-default field names with the corresponding default names. As a result, explicitly specified or inferred field names aren't available at run time.

> [!TIP]
> Enable .NET code style rule [IDE0037](../../../fundamentals/code-analysis/style-rules/ide0037.md) to set a preference on inferred or explicit tuple field names.

Beginning with C# 12, you can specify an alias for a tuple type with a [`using` directive](../keywords/using-directive.md#the-using-alias). The following example adds a `global using` alias for a tuple type with two integer values for an allowed `Min` and `Max` value:

```csharp
global using BandPass = (int Min, int Max);
```

After declaring the alias, you can use the `BandPass` name as an alias for that tuple type:

```csharp
BandPass bracket = (40, 100);
Console.WriteLine($"The bandpass filter is {bracket.Min} to {bracket.Max}");
```

An alias doesn't introduce a new *type*, but only creates a synonym for an existing type. You can deconstruct a tuple declared with the `BandPass` alias the same as you can with its underlying tuple type:

```csharp
(int a , int b) = bracket;
Console.WriteLine($"The bracket is {a} to {b}");
```

As with tuple assignment or deconstruction, the tuple member names don't need to match; the types do.

Similarly, a second alias with the same arity and member types can be used interchangeably with the original alias. You could declare a second alias:

```csharp
using Range = (int Minimum, int Maximum);
```

You can assign a `Range` tuple to a `BandPass` tuple. As with all tuple assignment, the field names need not match, only the types and the arity.

```csharp
Range r = bracket;
Console.WriteLine($"The range is {r.Minimum} to {r.Maximum}");
```

An alias for a tuple type provides more semantic information when you use tuples. It doesn't introduce a new type. To provide type safety, you should declare a positional [`record`](record.md) instead.

## Tuple assignment and deconstruction

C# supports assignment between tuple types that satisfy both of the following conditions:

- Both tuple types have the same number of elements.
- For each tuple position, the type of the right-hand tuple element is the same as or implicitly convertible to the type of the corresponding left-hand tuple element.

Assign tuple element values by following the order of tuple elements. The assignment process ignores the names of tuple fields, as the following example shows:

```csharp
(int, double) t1 = (17, 3.14);
(double First, double Second) t2 = (0.0, 1.0);
t2 = t1;
Console.WriteLine($"{nameof(t2)}: {t2.First} and {t2.Second}");
// Output:
// t2: 17 and 3.14

(double A, double B) t3 = (2.0, 3.0);
t3 = t2;
Console.WriteLine($"{nameof(t3)}: {t3.A} and {t3.B}");
// Output:
// t3: 17 and 3.14
```

Use the assignment operator `=` to *deconstruct* a tuple instance into separate variables. You can do that in many ways:

- Use the `var` keyword outside the parentheses to declare implicitly typed variables and let the compiler infer their types:

```csharp
var t = ("post office", 3.6);
var (destination, distance) = t;
Console.WriteLine($"Distance to {destination} is {distance} kilometers.");
// Output:
// Distance to post office is 3.6 kilometers.
```

- Explicitly declare the type of each variable inside parentheses:

```csharp
var t = ("post office", 3.6);
(string destination, double distance) = t;
Console.WriteLine($"Distance to {destination} is {distance} kilometers.");
// Output:
// Distance to post office is 3.6 kilometers.
```

- Declare some types explicitly and other types implicitly (with `var`) inside the parentheses:

```csharp
var t = ("post office", 3.6);
(var destination, double distance) = t;
Console.WriteLine($"Distance to {destination} is {distance} kilometers.");
// Output:
// Distance to post office is 3.6 kilometers.
```

- Use existing variables:

```csharp
var destination = string.Empty;
var distance = 0.0;

var t = ("post office", 3.6);
(destination, distance) = t;
Console.WriteLine($"Distance to {destination} is {distance} kilometers.");
// Output:
// Distance to post office is 3.6 kilometers.
```

The destination of a deconstruct expression can include both existing variables and variables declared in the deconstruction declaration.

You can also combine deconstruction with [pattern matching](../../fundamentals/functional/pattern-matching.md) to inspect the characteristics of fields in a tuple. The following example loops through several integers and prints those that are divisible by 3. It deconstructs the tuple result of <xref:System.Int32.DivRem*?displayProperty=nameWithType> and matches against a `Remainder` of 0:

```csharp
for (int i = 4; i < 20;  i++)
{
    if (Math.DivRem(i, 3) is ( Quotient: var q, Remainder: 0 ))
    {
        Console.WriteLine($"{i} is divisible by 3, with quotient {q}");
    }
}
```

For more information about deconstruction of tuples and other types, see [Deconstructing tuples and other types](../../fundamentals/functional/deconstruct.md).

## Tuple equality

Tuple types support the `==` and `!=` operators. These operators compare members of the left-hand operand with the corresponding members of the right-hand operand following the order of tuple elements.

```csharp
(int a, byte b) left = (5, 10);
(long a, int b) right = (5, 10);
Console.WriteLine(left == right);  // output: True
Console.WriteLine(left != right);  // output: False

var t1 = (A: 5, B: 10);
var t2 = (B: 5, A: 10);
Console.WriteLine(t1 == t2);  // output: True
Console.WriteLine(t1 != t2);  // output: False
```

As the preceding example shows, the `==` and `!=` operations don't take tuple field names into account.

Two tuples are comparable when both of the following conditions are satisfied:

- Both tuples have the same number of elements. For example, `t1 != t2` doesn't compile if `t1` and `t2` have different numbers of elements.
- For each tuple position, the corresponding elements from the left-hand and right-hand tuple operands are comparable by using the `==` and `!=` operators. For example, `(1, (2, 3)) == ((1, 2), 3)` doesn't compile because `1` isn't comparable with `(1, 2)`.

The `==` and `!=` operators compare tuples in a short-circuiting way. That is, an operation stops as soon as it meets a pair of non equal elements or reaches the ends of tuples. However, before any comparison, *all* tuple elements are evaluated, as the following example shows:

```csharp
Console.WriteLine((Display(1), Display(2)) == (Display(3), Display(4)));

int Display(int s)
{
    Console.WriteLine(s);
    return s;
}
// Output:
// 1
// 2
// 3
// 4
// False
```

## Tuples as out parameters

Typically, you refactor a method that has [`out` parameters](../keywords/method-parameters.md#out-parameter-modifier) into a method that returns a tuple. However, some cases exist where an `out` parameter can be a tuple type. The following example shows how to work with tuples as `out` parameters:

```csharp
var limitsLookup = new Dictionary<int, (int Min, int Max)>()
{
    [2] = (4, 10),
    [4] = (10, 20),
    [6] = (0, 23)
};

if (limitsLookup.TryGetValue(4, out (int Min, int Max) limits))
{
    Console.WriteLine($"Found limits: min is {limits.Min}, max is {limits.Max}");
}
// Output:
// Found limits: min is 10, max is 20
```

## Tuples vs `System.Tuple`

C# tuples use <xref:System.ValueTuple?displayProperty=nameWithType> types and differ from tuples that use <xref:System.Tuple?displayProperty=nameWithType> types. The main differences are:

- `System.ValueTuple` types are [value types](value-types.md). `System.Tuple` types are [reference types](../keywords/reference-types.md).
- `System.ValueTuple` types are mutable. `System.Tuple` types are immutable.
- Data members of `System.ValueTuple` types are fields. Data members of `System.Tuple` types are properties.

## C# language specification

For more information, see:

- [Tuple types](/dotnet/csharp/language-reference/language-specification/types#8311-tuple-types)
- [Tuple equality operators](/dotnet/csharp/language-reference/language-specification/expressions#121211-tuple-equality-operators)

## See also

- [Value types](value-types.md)
- [Choosing between anonymous and tuple types](../../../standard/base-types/choosing-between-anonymous-and-tuple.md)
- <xref:System.ValueTuple?displayProperty=nameWithType>
