---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/conditional-operator.md
title: ?: operator - the ternary conditional operator
version: 0.0.0
fetched_at: 2026-09-13
---
# ?: operator - the ternary conditional operator

The conditional operator `?:`, also known as the ternary conditional operator, evaluates a Boolean expression and returns the result of one of the two expressions, depending on whether the Boolean expression evaluates to `true` or `false`, as the following example shows:

```csharp
string GetWeatherDisplay(double tempInCelsius) => tempInCelsius < 20.0 ? "Cold." : "Perfect!";

Console.WriteLine(GetWeatherDisplay(15));  // output: Cold.
Console.WriteLine(GetWeatherDisplay(27));  // output: Perfect!
```

As the preceding example shows, the syntax for the conditional operator is as follows:

```csharp
condition ? consequent : alternative
```

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The `condition` expression must evaluate to `true` or `false`. If `condition` evaluates to `true`, the `consequent` expression is evaluated, and its result becomes the result of the operation. If `condition` evaluates to `false`, the `alternative` expression is evaluated, and its result becomes the result of the operation. Only `consequent` or `alternative` is evaluated. Conditional expressions are target-typed. That is, if a target type of a conditional expression is known, the types of `consequent` and `alternative` must be implicitly convertible to the target type, as the following example shows:

```csharp
var rand = new Random();
var condition = rand.NextDouble() > 0.5;

int? x = condition ? 12 : null;

IEnumerable<int> xs = x is null ? new List<int>() { 0, 1 } : new int[] { 2, 3 };
```

If a target type of a conditional expression is unknown (for example, when you use the [`var`](../statements/declarations.md#implicitly-typed-local-variables) keyword) or the type of `consequent` and `alternative` must be the same or there must be an implicit conversion from one type to the other:

```csharp
var rand = new Random();
var condition = rand.NextDouble() > 0.5;

var x = condition ? 12 : (int?)null;
```

The conditional operator is right-associative, that is, an expression of the form

```csharp
a ? b : c ? d : e
```

is evaluated as

```csharp
a ? b : (c ? d : e)
```

> [!TIP]
> You can use the following mnemonic device to remember how the conditional operator is evaluated:
>
> ```text
> is this condition true ? yes : no
> ```

## Conditional ref expression

A conditional ref expression conditionally returns a variable reference, as the following example shows:

```csharp
int[] smallArray = {1, 2, 3, 4, 5};
int[] largeArray = {10, 20, 30, 40, 50};

int index = 7;
ref int refValue = ref ((index < 5) ? ref smallArray[index] : ref largeArray[index - 5]);
refValue = 0;

index = 2;
((index < 5) ? ref smallArray[index] : ref largeArray[index - 5]) = 100;

Console.WriteLine(string.Join(" ", smallArray));
Console.WriteLine(string.Join(" ", largeArray));
// Output:
// 1 2 100 4 5
// 10 20 0 40 50
```

You can [`ref` assign](assignment-operator.md#ref-assignment) the result of a conditional ref expression. Use it as a [reference return](../statements/jump-statements.md#ref-returns) or pass it as a `ref`, `out`, `in`, or `ref readonly` [method parameter](../keywords/method-parameters.md#reference-parameters). You can also assign to the result of a conditional ref expression, as the preceding example shows.

The syntax for a conditional ref expression is as follows:

```csharp
condition ? ref consequent : ref alternative
```

Like the conditional operator, a conditional ref expression evaluates only one of the two expressions: either `consequent` or `alternative`.

In a conditional ref expression, the type of `consequent` and `alternative` must be the same. Conditional ref expressions aren't target-typed.

## Conditional operator and an `if` statement

Using the conditional operator instead of an [`if` statement](../statements/selection-statements.md#the-if-statement) can result in more concise code when you need to conditionally compute a value. The following example demonstrates two ways to classify an integer as negative or nonnegative:

```csharp
int input = new Random().Next(-5, 5);

string classify;
if (input >= 0)
{
    classify = "nonnegative";
}
else
{
    classify = "negative";
}

classify = (input >= 0) ? "nonnegative" : "negative";
```

## Operator overloadability

A user-defined type can't overload the conditional operator.

## C# language specification

For more information, see the [Conditional operator](~/_csharpstandard/standard/expressions.md#1221-conditional-operator) section of the [C# language specification](~/_csharpstandard/standard/README.md).

Specifications for newer features are:

- [Target-typed conditional expression](~/_csharpstandard/standard/expressions.md#1221-conditional-operator)

## See also

- [Simplify conditional expression (style rule IDE0075)](../../../fundamentals/code-analysis/style-rules/ide0075.md)
- [C# operators and expressions](index.md)
- [if statement](../statements/selection-statements.md#the-if-statement)
- [?. and ?[] operators](member-access-operators.md#null-conditional-operators--and-)
- [?? and ??= operators](null-coalescing-operator.md)
- [ref keyword](../keywords/ref.md)
