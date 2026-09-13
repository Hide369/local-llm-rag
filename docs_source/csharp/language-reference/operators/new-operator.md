---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/new-operator.md
title: new operator - Create and initialize a new instance of a type
version: 0.0.0
fetched_at: 2026-09-13
---
# new operator - The `new` operator creates a new instance of a type

The `new` operator creates a new instance of a type. You can also use the `new` keyword as a [member declaration modifier](../keywords/new-modifier.md) or a [generic type constraint](../keywords/new-constraint.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

## Constructor invocation

To create a new instance of a type, invoke one of the [constructors](../../programming-guide/classes-and-structs/constructors.md) of that type by using the `new` operator:

```csharp
var dict = new Dictionary<string, int>();
dict["first"] = 10;
dict["second"] = 20;
dict["third"] = 30;

Console.WriteLine(string.Join("; ", dict.Select(entry => $"{entry.Key}: {entry.Value}")));
// Output:
// first: 10; second: 20; third: 30
```

You can use an [object or collection initializer](../../programming-guide/classes-and-structs/object-and-collection-initializers.md) with the `new` operator to instantiate and initialize an object in one statement, as the following example shows:

```csharp
var dict = new Dictionary<string, int>
{
    ["first"] = 10,
    ["second"] = 20,
    ["third"] = 30
};

Console.WriteLine(string.Join("; ", dict.Select(entry => $"{entry.Key}: {entry.Value}")));
// Output:
// first: 10; second: 20; third: 30
```

### Target-typed `new`

Constructor invocation expressions are target-typed. That is, if a target type of an expression is known, you can omit a type name, as the following example shows:

```csharp
List<int> xs = new();
List<int> ys = new(capacity: 10_000);
List<int> zs = new() { Capacity = 20_000 };

Dictionary<int, List<int>> lookup = new()
{
    [1] = new() { 1, 2, 3 },
    [2] = new() { 5, 8, 3 },
    [5] = new() { 1, 0, 4 }
};
```

As the preceding example shows, always use parentheses in a target-typed `new` expression.

If a target type of a `new` expression is unknown (for example, when you use the [`var`](../statements/declarations.md#implicitly-typed-local-variables) keyword), you must specify a type name.

## Array creation

You also use the `new` operator to create an array instance, as the following example shows:

```csharp
var numbers = new int[3];
numbers[0] = 10;
numbers[1] = 20;
numbers[2] = 30;
Console.WriteLine(string.Join(", ", numbers));
// Output:
// 10, 20, 30
```

Use array initialization syntax to create an array instance and populate it with elements in one statement. The following example shows various ways how you can do that:

```csharp
var a = new int[3] { 10, 20, 30 };
var b = new int[] { 10, 20, 30 };
var c = new[] { 10, 20, 30 };
Console.WriteLine(c.GetType());  // output: System.Int32[]
```

For more information about arrays, see [Arrays](../builtin-types/arrays.md).

## Instantiation of anonymous types

To create an instance of an [anonymous type](../../programming-guide/classes-and-structs/anonymous-types.md), use the `new` operator and object initializer syntax:

```csharp
var example = new { Greeting = "Hello", Name = "World" };
Console.WriteLine($"{example.Greeting}, {example.Name}!");
// Output:
// Hello, World!
```

## Destruction of type instances

You don't need to destroy previously created type instances. The system automatically destroys instances of both reference and value types. The system destroys instances of value types as soon as the context that contains them is destroyed. The [garbage collector](../../../standard/garbage-collection/index.md) destroys instances of reference types at some unspecified time after the last reference to them is removed.

For type instances that contain unmanaged resources, such as a file handle, employ deterministic clean-up to ensure that the resources are released as soon as possible. For more information, see the <xref:System.IDisposable?displayProperty=nameWithType> API reference and the [`using` statement](../statements/using.md) article.

## Operator overloadability

A user-defined type can't overload the `new` operator.

## C# language specification

For more information, see [The new operator](~/_csharpstandard/standard/expressions.md#12817-the-new-operator) section of the [C# language specification](~/_csharpstandard/standard/README.md).

For more information about a target-typed `new` expression, see the [Object creation expressions](~/_csharpstandard/standard/expressions.md#128172-object-creation-expressions) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
- [Object and collection initializers](../../programming-guide/classes-and-structs/object-and-collection-initializers.md)
