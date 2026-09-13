---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/types/tuples.md
title: Tuples and deconstruction
version: 0.0.0
fetched_at: 2026-09-13
---
# Tuples and deconstruction

> [!TIP]
> **New to developing software?** Start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials. You'll encounter tuples when you need to return multiple values from a method or group values without defining a named type.
>
> **Experienced in another language?** C# tuples are value types similar to tuples in Python or Swift, but with optional named elements and full deconstruction support. Skim the [deconstruction](#deconstruct-tuples) and [equality](#tuple-equality) sections for C#-specific patterns.

A *tuple* groups multiple values into a single, lightweight structure without requiring you to define a named type. Tuples are value types that you can declare inline, return from methods, and deconstruct into individual variables. Use tuples when you need a quick, temporary grouping of related values. For example, when you return multiple results from a method or store a coordinate pair.

The following example creates a tuple with named elements and accesses each element by name:

```csharp
var location = (Latitude: 47.6062, Longitude: -122.3321);
Console.WriteLine($"Location: {location.Latitude}, {location.Longitude}");
// Output: Location: 47.6062, -122.3321
```

Tuples work well for short-lived groupings where defining a class, struct, or record would add unnecessary ceremony. For long-lived domain concepts or types with behavior, prefer [records](records.md), [classes](classes.md), or [structs](structs.md). For a comparison of when to use each, see [Choose which kind of type](index.md#choose-which-kind-of-type).

## Declare and initialize tuples

Declare a tuple by listing the element types in parentheses. You can optionally name each element to make the code more readable:

```csharp
// Tuple with named elements
(string Name, int Age) person = ("Alice", 30);
Console.WriteLine($"{person.Name} is {person.Age} years old");

// Tuple with default element names (Item1, Item2)
(string, int) unnamed = ("Bob", 25);
Console.WriteLine($"{unnamed.Item1} is {unnamed.Item2} years old");

// Tuple declared with var and inline names
var city = (Name: "Seattle", Population: 749_256);
Console.WriteLine($"{city.Name}: population {city.Population}");
```

When you don't provide names, elements use default names `Item1`, `Item2`, and so on. Named elements make your code self-documenting without requiring a separate type definition.

### Inferred element names

The compiler infers element names from the variable names or property names you use to initialize the tuple. This feature avoids redundancy when the names match:

```csharp
var name = "Carol";
var age = 28;

// The compiler infers element names from the variable names
var person = (name, age);
Console.WriteLine($"{person.name} is {person.age}");
// Output: Carol is 28
```

Inferred names keep your code concise. If you need a different element name, specify it explicitly.

## Return multiple values from a method

One of the most common uses for tuples is returning multiple values from a method. Instead of defining a class or using `out` parameters, return a tuple with named elements:

```csharp
static (double Minimum, double Maximum, double Average) ComputeStats(List<double> values)
{
    var min = values.Min();
    var max = values.Max();
    var avg = values.Average();
    return (min, max, avg);
}
```

Named tuple elements make the return values readable at both the call site and the method signature. The caller can access each value by name without needing to remember positional order.

## Deconstruct tuples

*Deconstruction* unpacks a tuple's elements into separate variables in a single statement. You can deconstruct tuples in several ways:

```csharp
var point = (X: 3, Y: 7);

// Deconstruct with var (infer all types)
var (x, y) = point;
Console.WriteLine($"x={x}, y={y}");

// Deconstruct with explicit types
(int px, int py) = point;
Console.WriteLine($"px={px}, py={py}");

// Deconstruct into existing variables
int a, b;
(a, b) = point;
Console.WriteLine($"a={a}, b={b}");

// Deconstruct a method return value directly
List<double> data = [10.0, 20.0, 30.0];
var (min, max, avg) = ComputeStats(data);
Console.WriteLine($"Min: {min}, Max: {max}, Avg: {avg}");
```

Deconstruction is especially useful when you receive a tuple from a method call and immediately need to work with its individual values.

You can deconstruct tuples directly in `foreach` loops, which makes iterating over collections of grouped values concise:

```csharp
List<(string Name, int Score)> results =
[
    ("Alice", 92),
    ("Bob", 87),
    ("Carol", 95)
];

foreach (var (name, score) in results)
{
    Console.WriteLine($"{name}: {score}");
}
```

When you don't need every element, use a *discard* (`_`) in place of each value you want to ignore. Use a separate `_` for each discarded position:

```csharp
List<double> values = [5.0, 10.0, 15.0];
var (_, max, _) = ComputeStats(values);
Console.WriteLine($"Only need the max: {max}");
// Output: Only need the max: 15
```

For more about using discards across different contexts, see [Discards](../functional/discards.md).

## Tuple equality

You can compare tuples using `==` and `!=`. These operators compare each element in order, so two tuples are equal when all their corresponding elements are equal:

```csharp
var order1 = (Product: "Widget", Quantity: 5);
var order2 = (Product: "Widget", Quantity: 5);
var order3 = (Product: "Gadget", Quantity: 3);

Console.WriteLine(order1 == order2); // True
Console.WriteLine(order1 == order3); // False

// Element names don't affect equality—only values matter
var named = (X: 1, Y: 2);
var different = (A: 1, B: 2);
Console.WriteLine(named == different); // True
```

Tuple equality uses the `==` operator defined on each element type, which means the comparison works correctly for strings, numbers, and other types that define `==`. Element names don't affect equality—only values and positions matter.

## Nondestructive mutation with `with`

The `with` expression creates a copy of a tuple with one or more elements changed, leaving the original unchanged:

```csharp
var original = (Name: "Widget", Price: 19.99m, InStock: true);
var discounted = original with { Price = 14.99m };

Console.WriteLine($"Original: {original.Name} at {original.Price:C}");
Console.WriteLine($"Discounted: {discounted.Name} at {discounted.Price:C}");
// Output:
// Original: Widget at $19.99
// Discounted: Widget at $14.99
```

This pattern is useful when you want a variation of an existing tuple without modifying the original. The `with` expression works the same way on tuples as it does on [records](records.md).

## Tuples in dictionaries and lookups

Tuples make convenient dictionary values when you need to associate a key with multiple pieces of data:

```csharp
var sizeChart = new Dictionary<string, (int Min, int Max)>
{
    ["Small"] = (0, 50),
    ["Medium"] = (51, 100),
    ["Large"] = (101, 200)
};

if (sizeChart.TryGetValue("Medium", out var range))
{
    Console.WriteLine($"Medium: {range.Min}–{range.Max}");
}
// Output: Medium: 51–100
```

Tuples also work as dictionary *keys*, giving you a composite key without defining a custom type. Because tuples implement structural equality, lookups match on the combined values of all elements:

```csharp
var grid = new Dictionary<(int Row, int Column), string>
{
    [(0, 0)] = "Origin",
    [(1, 3)] = "Sensor A",
    [(2, 5)] = "Sensor B"
};

var target = (Row: 1, Column: 3);
if (grid.TryGetValue(target, out var label))
{
    Console.WriteLine($"({target.Row}, {target.Column}): {label}");
}
// Output: (1, 3): Sensor A
```

This pattern avoids needing a separate class for simple multi-key lookups or key-to-multiple-value mappings.

## Tuples vs. anonymous types

Tuples are the preferred choice when you need a lightweight unnamed data structure. Anonymous types remain available for expression tree scenarios and for code that requires reference types, but tuples offer better performance, deconstruction support, and more flexible syntax. For more about anonymous types, see [Choosing between anonymous and tuple types](../../../standard/base-types/choosing-between-anonymous-and-tuple.md).

## See also

- [Tuple types (C# reference)](../../language-reference/builtin-types/value-tuples.md) for complete syntax details
- [Deconstructing tuples and other types](../functional/deconstruct.md) for user-defined `Deconstruct` methods
- [Discards](../functional/discards.md)
- [Records](records.md)
