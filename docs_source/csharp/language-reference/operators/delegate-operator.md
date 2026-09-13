---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/delegate-operator.md
title: delegate operator - Create an anonymous method that can be converted to a delegate type.
version: 0.0.0
fetched_at: 2026-09-13
---
# delegate operator

The `delegate` operator creates an anonymous method that you can convert to a delegate type.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

You can convert an anonymous method to types such as <xref:System.Action?displayProperty=nameWithType> and <xref:System.Func`1?displayProperty=nameWithType>. Many methods use these types as arguments.

```csharp
Func<int, int, int> sum = delegate (int a, int b) { return a + b; };
Console.WriteLine(sum(3, 4));  // output: 7
```

> [!NOTE]
> Lambda expressions provide a more concise and expressive way to create an anonymous function. Use the [=> operator](lambda-operator.md) to construct a lambda expression:
>
```csharp
Func<int, int, int> sum = (a, b) => a + b;
Console.WriteLine(sum(3, 4));  // output: 7
```
>
> For more information about features of lambda expressions, such as capturing outer variables, see [Lambda expressions](lambda-expressions.md).

When you use the `delegate` operator, you can omit the parameter list. If you omit the parameter list, you create an anonymous method that you can convert to a delegate type with any list of parameters, as the following example shows:

```csharp
Action greet = delegate { Console.WriteLine("Hello!"); };
greet();

Action<int, double> introduce = delegate { Console.WriteLine("This is world!"); };
introduce(42, 2.7);

// Output:
// Hello!
// This is world!
```

This functionality is the only feature of anonymous methods that lambda expressions don't support. In all other cases, use a lambda expression to write inline code. You can use [discards](../../fundamentals/functional/discards.md) to specify two or more input parameters of an anonymous method that the method doesn't use:

```csharp
Func<int, int, int> constant = delegate (int _, int _) { return 42; };
Console.WriteLine(constant(3, 4));  // output: 42
```

For backwards compatibility, if only a single parameter is named `_`, the compiler treats `_` as the name of that parameter within an anonymous method.

Use the `static` modifier when you declare an anonymous method:

```csharp
Func<int, int, int> sum = static delegate (int a, int b) { return a + b; };
Console.WriteLine(sum(10, 4));  // output: 14
```

A static anonymous method can't capture local variables or instance state from enclosing scopes.

Use the `delegate` keyword to declare a [delegate type](../builtin-types/reference-types.md#the-delegate-type).

The compiler can cache the delegate object that it creates from a method group. Consider the following method:

```csharp
static void StaticFunction() { }
```

When you assign the method group to a delegate, the compiler caches the delegate:

```csharp
Action a = StaticFunction;
```

## C# language specification

For more information, see the [Anonymous function expressions](~/_csharpstandard/standard/expressions.md#1222-anonymous-function-expressions) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
- [=> operator](lambda-operator.md)
