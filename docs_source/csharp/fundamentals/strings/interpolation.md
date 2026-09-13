---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/strings/interpolation.md
title: String interpolation in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# String interpolation in C\#

> [!TIP]
> This article is part of the **Fundamentals** section for developers who already know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first.
>
> **Coming from another language?** String interpolation in C# works much like template literals in JavaScript (`` `${x}` ``) or f-strings in Python (`f"{x}"`). The expression inside `{}` can be any valid C# expression, and you can add format and alignment specifiers without leaving the string.

*String interpolation* lets you embed expressions directly in a string literal by prefixing the literal with `$`:

```csharp
double a = 3;
double b = 4;
Console.WriteLine($"Area of the right triangle with legs of {a} and {b} is {0.5 * a * b}");
Console.WriteLine($"Length of the hypotenuse of the right triangle with legs of {a} and {b} is {CalculateHypotenuse(a, b)}");
double CalculateHypotenuse(double leg1, double leg2) => Math.Sqrt(leg1 * leg1 + leg2 * leg2);
// => Area of the right triangle with legs of 3 and 4 is 6
// => Length of the hypotenuse of the right triangle with legs of 3 and 4 is 5
```

Each `{ }` is an *interpolation expression*. C# evaluates the expression, converts the result to a string by calling its `ToString()` method, and substitutes the text into the result. The string interpolation for a `null` expression is the empty string. In most cases, the default conversion produces the output you want, and you don't need to do anything more.

Interpolated strings are a more readable alternative to <xref:System.String.Format*?displayProperty=nameWithType>, and they support the full [composite formatting](../../../standard/base-types/composite-formatting.md) feature set. Anything you can do with a classic positional format string—format specifiers, alignment, culture-aware formatting, and constant strings—you can also do with an interpolated string. The rest of this article covers those options. Reach for them only when you need finer control over the result; otherwise, the plain `$"{expression}"` form is enough.

For the language-reference treatment of the syntax and the underlying handler types, see [interpolated string](../../language-reference/tokens/interpolated.md) reference. For performance-focused topics such as `Span<char>` interpolation and custom interpolated string handlers, see [String operations](../../language-reference/builtin-types/string-operations.md).

## Apply a format string

To control how an expression result is formatted, follow the expression with a colon and a [standard or custom format string](../../../standard/base-types/formatting-types.md):

```csharp
{<expression>:<formatString>}
```

The following example formats a <xref:System.DateTime> and a <xref:System.Double> value:

```csharp
var date = new DateTime(1731, 11, 25);
Console.WriteLine($"On {date:dddd, MMMM dd, yyyy} L. Euler introduced the letter e to denote {Math.E:F5}.");
// => On Sunday, November 25, 1731 L. Euler introduced the letter e to denote 2.71828.
```

## Set the field width and alignment

To produce aligned output, follow the expression with a comma and a minimum field width. Positive widths right-align the value, and negative widths left-align it:

```csharp
{<expression>,<width>}
```

```csharp
var titles = new Dictionary<string, string>()
{
    ["Doyle, Arthur Conan"] = "Hound of the Baskervilles, The",
    ["London, Jack"] = "Call of the Wild, The",
    ["Shakespeare, William"] = "Tempest, The"
};

Console.WriteLine("Author and Title List");
Console.WriteLine();
Console.WriteLine($"|{"Author",-25}|{"Title",30}|");
foreach (var title in titles)
{
    Console.WriteLine($"|{title.Key,-25}|{title.Value,30}|");
}
// => Author and Title List
// =>
// => |Author                   |                         Title|
// => |Doyle, Arthur Conan      |Hound of the Baskervilles, The|
// => |London, Jack             |         Call of the Wild, The|
// => |Shakespeare, William     |                  Tempest, The|
```

When you need both alignment and a format string, put alignment first:

```csharp
{<expression>,<width>:<formatString>}
```

```csharp
const int NameAlignment = -9;
const int ValueAlignment = 7;
double a = 3;
double b = 4;
Console.WriteLine($"Three classical Pythagorean means of {a} and {b}:");
Console.WriteLine($"|{"Arithmetic",NameAlignment}|{0.5 * (a + b),ValueAlignment:F3}|");
Console.WriteLine($"|{"Geometric",NameAlignment}|{Math.Sqrt(a * b),ValueAlignment:F3}|");
Console.WriteLine($"|{"Harmonic",NameAlignment}|{2 / (1 / a + 1 / b),ValueAlignment:F3}|");
// => Three classical Pythagorean means of 3 and 4:
// => |Arithmetic|  3.500|
// => |Geometric|  3.464|
// => |Harmonic |  3.429|
```

If the formatted value is longer than the requested width, C# ignores the width and emits the full value.

## Escape braces and use escape sequences

Interpolated strings support the same escape sequences as ordinary string literals. To include a literal `{` or `}` character in the result, double it (`{{` or `}}`).

For paths and other strings that contain backslashes, prefer an [interpolated raw string literal](../../language-reference/tokens/raw-string.md) (`$"""..."""`) over the older verbatim form (`$@"..."`). Raw string literals don't process escape sequences, so backslashes appear as-is:

```csharp
int[] xs = [1, 2, 7, 9];
int[] ys = [7, 9, 12];
Console.WriteLine($"Find the intersection of the {{{string.Join(", ", xs)}}} and {{{string.Join(", ", ys)}}} sets.");
// => Find the intersection of the {1, 2, 7, 9} and {7, 9, 12} sets.

var userName = "Jane";
var stringWithEscapes = $"C:\\Users\\{userName}\\Documents";
var rawInterpolated = $"""C:\Users\{userName}\Documents""";
Console.WriteLine(stringWithEscapes);
Console.WriteLine(rawInterpolated);
// => C:\Users\Jane\Documents
// => C:\Users\Jane\Documents
```

## Use a conditional expression

The colon has special meaning inside an interpolation expression, so wrap a [conditional exoressuin](../../language-reference/operators/conditional-operator.md) in parentheses:

```csharp
var rand = new Random(42);
for (int i = 0; i < 3; i++)
{
    Console.WriteLine($"Coin flip: {(rand.NextDouble() < 0.5 ? "heads" : "tails")}");
}
```

## Span an expression across multiple lines

For better readability, break long interpolation expressions across multiple lines. Multi-line interpolation expressions are available since C# 11. The following example adds newlines between the `{` and `}` characters to separate the interpolated expressions from the literal text:

```csharp
int[] numbers = [3, 1, 4, 1, 5, 9, 2, 6];
Console.WriteLine($"Total: {
        numbers.Sum()
        }, average: {numbers.Average():F2}.");
// => Total: 31, average: 3.88.
```

## Build constant strings

You can build constant interpolated strings when every interpolated expression is a constant `string` value. That makes it usable for attribute arguments, `switch` patterns, and other contexts that require compile-time constants:

```csharp
const string Audience = "world";
const string Greeting = $"Hello, {Audience}!";
Console.WriteLine(Greeting);
// => Hello, world!
```

## Format with a specific culture

By default, an interpolated string formats values using <xref:System.Globalization.CultureInfo.CurrentCulture?displayProperty=nameWithType>, which affects date, number, and currency representations. For deterministic output, pass an explicit culture to <xref:System.String.Create(System.IFormatProvider,System.Runtime.CompilerServices.DefaultInterpolatedStringHandler%40)?displayProperty=nameWithType>:

```csharp
CultureInfo[] cultures =
[
    CultureInfo.GetCultureInfo("en-US"),
    CultureInfo.GetCultureInfo("en-GB"),
    CultureInfo.GetCultureInfo("nl-NL"),
    CultureInfo.InvariantCulture
];
var date = new DateTime(2026, 5, 21, 12, 35, 31);
var number = 31_415_926.536;
foreach (var culture in cultures)
{
    var cultureSpecificMessage = string.Create(culture, $"{date,23}{number,20:N3}");
    Console.WriteLine($"{culture.Name,-10}{cultureSpecificMessage}");
}
// Output is similar to:
// => en-US       5/21/2026 12:35:31 PM      31,415,926.536
// => en-GB         21/05/2026 12:35:31      31,415,926.536
// => nl-NL         21-05-2026 12:35:31      31.415.926,536
// =>               05/21/2026 12:35:31      31,415,926.536
```

For invariant output (logs, file formats, machine-readable data), pass <xref:System.Globalization.CultureInfo.InvariantCulture?displayProperty=nameWithType>:

```csharp
var timestamp = new DateTime(2026, 5, 21, 15, 46, 24);
string message = string.Create(CultureInfo.InvariantCulture, $"Date and time in invariant culture: {timestamp}");
Console.WriteLine(message);
// => Date and time in invariant culture: 05/21/2026 15:46:24
```

## See also

- [Interpolated string token](../../language-reference/tokens/interpolated.md)
- [String operations: pattern matching, performance, and span-based search](../../language-reference/builtin-types/string-operations.md)
- [Composite formatting](../../../standard/base-types/composite-formatting.md)
- [Formatting types in .NET](../../../standard/base-types/formatting-types.md)
- <xref:System.String.Format*?displayProperty=nameWithType>
- <xref:System.FormattableString?displayProperty=nameWithType>
