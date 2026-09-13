---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/nameof.md
title: The nameof expression - evaluate the text name of a symbol
version: 0.0.0
fetched_at: 2026-09-13
---
# nameof expression (C# reference)

A `nameof` expression produces the name of a variable, type, or member as the string constant. A `nameof` expression is evaluated at compile time and has no effect at run time. When the operand is a type or a namespace, the produced name isn't [fully qualified](~/_csharpstandard/standard/basic-concepts.md#783-fully-qualified-names).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows how to use a `nameof` expression:

```csharp
Console.WriteLine(nameof(System.Collections.Generic));  // output: Generic
Console.WriteLine(nameof(List<int>));  // output: List
Console.WriteLine(nameof(List<>)); // output: List
Console.WriteLine(nameof(List<int>.Count));  // output: Count
Console.WriteLine(nameof(List<int>.Add));  // output: Add

List<int> numbers = new List<int>() { 1, 2, 3 };
Console.WriteLine(nameof(numbers));  // output: numbers
Console.WriteLine(nameof(numbers.Count));  // output: Count
Console.WriteLine(nameof(numbers.Add));  // output: Add
```

The preceding example that uses `List<>` is supported in C# 14 and later. The operand of `nameof` can be an unbound generic type, such as `List<>` or `Dictionary<,>`. The result is the simple type name without arity or any type-argument list — `nameof(List<>)` returns `"List"`. Unbound generic operands are useful in logging, diagnostic messages, and attribute arguments where the generic type name matters but the type arguments don't.

You can use a `nameof` expression to make the argument-checking code more maintainable:

```csharp
public string Name
{
    get => name;
    set => name = value ?? throw new ArgumentNullException(nameof(value), $"{nameof(Name)} cannot be null");
}
```

You can use a `nameof` expression with a method parameter inside an [attribute](../../advanced-topics/reflection-and-attributes/index.md) on a method or its parameter. The following code shows how to do that for an attribute on a method, a local function, and the parameter of a lambda expression:

```csharp
[ParameterString(nameof(msg))]
public static void Method(string msg)
{
    [ParameterString(nameof(T))]
    void LocalFunction<T>(T param) { }

    var lambdaExpression = ([ParameterString(nameof(aNumber))] int aNumber) => aNumber.ToString();
}
```

A `nameof` expression with a parameter is useful when you use the [nullable analysis attributes](../attributes/nullable-analysis.md) or the [CallerArgumentExpression attribute](../attributes/caller-information.md#argument-expressions).

When the operand is a [verbatim identifier](../tokens/verbatim.md), the `@` character isn't part of the name, as the following example shows:

```csharp
var @new = 5;
Console.WriteLine(nameof(@new));  // output: new
```

## C# language specification

For more information, see the [Nameof expressions](~/_csharpstandard/standard/expressions.md#12823-the-nameof-operator) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
- [Convert `typeof` to `nameof` (style rule IDE0082)](../../../fundamentals/code-analysis/style-rules/ide0082.md)
