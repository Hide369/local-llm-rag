---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/switch-expression.md
title: switch expression - Evaluate a pattern match expression using the `switch` expression
version: 0.0.0
fetched_at: 2026-09-13
---
# `switch` expression - pattern matching expressions using the `switch` keyword

Use the `switch` expression to evaluate a single expression from a list of candidate expressions. The evaluation is based on a pattern match with an input expression. For information about the `switch` statement that supports `switch`-like semantics in a statement context, see the [`switch` statement](../statements/selection-statements.md#the-switch-statement) section of the [Selection statements](../statements/selection-statements.md) article.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example demonstrates a `switch` expression. It converts values of an [`enum`](../builtin-types/enum.md) representing visual directions in an online map to the corresponding cardinal directions:

```csharp
public static class SwitchExample
{
    public enum Direction
    {
        Up,
        Down,
        Right,
        Left
    }

    public enum Orientation
    {
        North,
        South,
        East,
        West
    }

    public static Orientation ToOrientation(Direction direction) => direction switch
    {
        Direction.Up    => Orientation.North,
        Direction.Right => Orientation.East,
        Direction.Down  => Orientation.South,
        Direction.Left  => Orientation.West,
        _ => throw new ArgumentOutOfRangeException(nameof(direction), $"Not expected direction value: {direction}"),
    };

    public static void Main()
    {
        var direction = Direction.Right;
        Console.WriteLine($"Map view direction is {direction}");
        Console.WriteLine($"Cardinal orientation is {ToOrientation(direction)}");
        // Output:
        // Map view direction is Right
        // Cardinal orientation is East
    }
}
```

The preceding example shows the basic elements of a `switch` expression:

- An expression followed by the `switch` keyword. In the preceding example, it's the `direction` method parameter.
- The *`switch` expression arms*, separated by commas. Each `switch` expression arm contains a *pattern*, an optional [*case guard*](#case-guards), the `=>` token, and an *expression*.

In the preceding example, a `switch` expression uses the following patterns:

- A [constant pattern](patterns.md#constant-pattern): to handle the defined values of the `Direction` enumeration.
- A [discard pattern](patterns.md#discard-pattern): to handle any integer value that doesn't have the corresponding member of the `Direction` enumeration (for example, `(Direction)10`). That pattern makes the `switch` expression [exhaustive](#nonexhaustive-switch-expressions).

> [!IMPORTANT]
> For information about the patterns supported by the `switch` expression and more examples, see [Patterns](patterns.md).

The result of a `switch` expression is the value of the expression of the first `switch` expression arm whose pattern matches the input expression and whose case guard, if present, evaluates to `true`. The `switch` expression arms are evaluated in text order.

The compiler generates an error when a lower `switch` expression arm can't be chosen because a higher `switch` expression arm matches all its values.

## Case guards

A pattern might not be expressive enough to specify the condition for the evaluation of an arm's expression. In such a case, use a *case guard*. A *case guard* is another condition that must be satisfied together with a matched pattern. A case guard must be a Boolean expression. Specify a case guard after the `when` keyword that follows a pattern, as the following example shows:

```csharp
public readonly struct Point
{
    public Point(int x, int y) => (X, Y) = (x, y);

    public int X { get; }
    public int Y { get; }
}

static Point Transform(Point point) => point switch
{
    { X: 0, Y: 0 }                    => new Point(0, 0),
    { X: var x, Y: var y } when x < y => new Point(x + y, y),
    { X: var x, Y: var y } when x > y => new Point(x - y, y),
    { X: var x, Y: var y }            => new Point(2 * x, 2 * y),
};
```

The preceding example uses [property patterns](patterns.md#property-pattern) with nested [var patterns](patterns.md#var-pattern).

## Nonexhaustive switch expressions

If none of a `switch` expression's patterns matches an input value, the runtime throws an exception. In .NET Core 3.0 and later versions, the exception is a <xref:System.Runtime.CompilerServices.SwitchExpressionException?displayProperty=nameWithType>. In .NET Framework, the exception is an <xref:System.InvalidOperationException>. In most cases, the compiler generates a warning if a `switch` expression doesn't handle all possible input values. [List patterns](patterns.md#list-patterns) don't generate a warning when all possible inputs aren't handled.

For [union types](../builtin-types/union.md), a `switch` expression is exhaustive when it handles all case types. A catch-all arm isn't needed. If the null state of the union's `Value` property is "maybe null," you must also handle `null` to avoid a warning. For more information, see [Union exhaustiveness](../builtin-types/union.md#union-exhaustiveness).

> [!TIP]
> To guarantee that a `switch` expression handles all possible input values, provide a `switch` expression arm with a [discard pattern](patterns.md#discard-pattern).

## C# language specification

For more information, see the [`switch` expression](~/_csharpstandard/standard/expressions.md#1212-switch-expression) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [Use switch expression (style rule IDE0066)](../../../fundamentals/code-analysis/style-rules/ide0066.md)
- [Add missing cases to switch expression (style rule IDE0072)](../../../fundamentals/code-analysis/style-rules/ide0072.md)
- [C# operators and expressions](index.md)
- [Patterns](patterns.md)
- [Tutorial: Use pattern matching to build type-driven and data-driven algorithms](../../fundamentals/tutorials/pattern-matching.md)
- [`switch` statement](../statements/selection-statements.md#the-switch-statement)
