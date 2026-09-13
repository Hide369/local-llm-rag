---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/is.md
title: The `is` operator - Match an expression against a type or constant pattern
version: 0.0.0
fetched_at: 2026-09-13
---
# The `is` operator (C# reference)

The `is` operator checks if the result of an expression is compatible with a given type. For information about the type-testing `is` operator, see the [is operator](type-testing-and-cast.md#the-is-operator) section of the [Type-testing and cast operators](type-testing-and-cast.md) article. You can also use the `is` operator to match an expression against a pattern, as the following example shows:

```csharp
static bool IsFirstFridayOfOctober(DateTime date) =>
    date is { Month: 10, Day: <=7, DayOfWeek: DayOfWeek.Friday };
```

In the preceding example, the `is` operator matches an expression against a [property pattern](patterns.md#property-pattern) with nested [constant](patterns.md#constant-pattern) and [relational](patterns.md#relational-patterns) patterns.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The `is` operator can be useful in the following scenarios:

- To check the run-time type of an expression, as the following example shows:

```csharp
int i = 34;
object iBoxed = i;
int? jNullable = 42;
if (iBoxed is int a && jNullable is int b)
{
    Console.WriteLine(a + b);  // output 76
}
```

  The preceding example shows the use of a [declaration pattern](patterns.md#declaration-and-type-patterns).

- To check for `null`, as the following example shows:

```csharp
if (input is null)
{
    return;
}
```

  When you match an expression against `null`, the compiler guarantees that no user-overloaded `==` or `!=` operator is invoked.

- To do a non-null check by using a [negation pattern](patterns.md#logical-patterns), as the following example shows:

```csharp
if (result is not null)
{
    Console.WriteLine(result.ToString());
}
```

- To match elements of a list or array by using [list patterns](patterns.md#list-patterns). The following code checks arrays for integer values in expected positions:

```csharp
int[] empty = [];
int[] one = [1];
int[] odd = [1, 3, 5];
int[] even = [2, 4, 6];
int[] fib = [1, 1, 2, 3, 5];

Console.WriteLine(odd is [1, _, 2, ..]);   // false
Console.WriteLine(fib is [1, _, 2, ..]);   // true
Console.WriteLine(fib is [_, 1, 2, 3, ..]);     // true
Console.WriteLine(fib is [.., 1, 2, 3, _ ]);     // true
Console.WriteLine(even is [2, _, 6]);     // true
Console.WriteLine(even is [2, .., 6]);    // true
Console.WriteLine(odd is [.., 3, 5]); // true
Console.WriteLine(even is [.., 3, 5]); // false
Console.WriteLine(fib is [.., 3, 5]); // true
```

> [!NOTE]
> For the complete list of patterns supported by the `is` operator, see [Patterns](patterns.md).

## C# language specification

For more information, see [The is operator](~/_csharpstandard/standard/expressions.md#121512-the-is-operator) section of the [C# language specification](~/_csharpstandard/standard/README.md) and [Pattern matching](/dotnet/csharp/language-reference/language-specification/patterns).

## See also

- [C# operators and expressions](index.md)
- [Patterns](patterns.md)
- [Tutorial: Use pattern matching to build type-driven and data-driven algorithms](../../fundamentals/tutorials/pattern-matching.md)
- [Type-testing and cast operators](../operators/type-testing-and-cast.md)
