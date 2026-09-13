---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/tokens/interpolated.md
title: $ - string interpolation - format string output
version: 0.0.0
fetched_at: 2026-09-13
---

# String interpolation using `$`

Use the `$` character to identify a string literal as an _interpolated string_. An interpolated string is a string literal that might contain _interpolation expressions_. When you resolve an interpolated string to a result string, the compiler replaces items with interpolation expressions by the string representations of the expression results.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

String interpolation provides a more readable, convenient syntax to format strings. It's easier to read than [string composite formatting](../../../standard/base-types/composite-formatting.md). The following example uses both features to produce the same output:

```csharp
var name = "Mark";
var date = DateTime.Now;

// Composite formatting:
Console.WriteLine("Hello, {0}! Today is {1}, it's {2:HH:mm} now.", name, date.DayOfWeek, date);
// String interpolation:
Console.WriteLine($"Hello, {name}! Today is {date.DayOfWeek}, it's {date:HH:mm} now.");
// Both calls produce the same output that is similar to:
// Hello, Mark! Today is Wednesday, it's 19:40 now.
```

You can use an interpolated string to initialize a [constant](../keywords/const.md) string. You can do that only if all interpolation expressions within the interpolated string are constant strings as well.

## Structure of an interpolated string

To make a string literal an interpolated string, add the `$` symbol at the beginning. Don't include any white space between the `$` and the `"` that starts a string literal.

The structure of an item with an interpolation expression is as follows:

```csharp
{<interpolationExpression>[,<width>][:<formatString>]}
```

Elements in square brackets are optional. The following table describes each element:

| Element                   | Description |
|---------------------------|-------------|
| `interpolationExpression` | The expression that produces a result to be formatted. When the expression is `null`, the output is the empty string (<xref:System.String.Empty?displayProperty=nameWithType>). |
| `width`               | The constant expression whose value defines the minimum number of characters in the string representation of the expression result. If positive, the string representation is right-aligned; if negative, left-aligned. For more information, see the [Width component](../../../standard/base-types/composite-formatting.md#width-component) section of the [Composite formatting](../../../standard/base-types/composite-formatting.md) article. |
| `formatString`            | A format string supported by the type of the expression result. For more information, see the [Format string component](../../../standard/base-types/composite-formatting.md#format-string-component) section of the [Composite formatting](../../../standard/base-types/composite-formatting.md) article. |

The following example uses optional formatting components described in the preceding table:

```csharp
Console.WriteLine($"|{"Left",-7}|{"Right",7}|");

const int FieldWidthRightAligned = 20;
Console.WriteLine($"{Math.PI,FieldWidthRightAligned} - default formatting of the pi number");
Console.WriteLine($"{Math.PI,FieldWidthRightAligned:F3} - display only three decimal digits of the pi number");
// Output is:
// |Left   |  Right|
//     3.14159265358979 - default formatting of the pi number
//                3.142 - display only three decimal digits of the pi number
```

To make the code more readable, use new lines within an interpolation expression. The following example shows how new lines can improve the readability of an expression involving [pattern matching](../operators/patterns.md):

```csharp
string message = $"The usage policy for {safetyScore} is {
    safetyScore switch
    {
        > 90 => "Unlimited usage",
        > 80 => "General usage, with daily safety check",
        > 70 => "Issues must be addressed within 1 week",
        > 50 => "Issues must be addressed within 1 day",
        _ => "Issues must be addressed before continued use",
    }
    }";
```

## Interpolated raw string literals

You can use an interpolated [raw string literal](../builtin-types/reference-types.md#string-literals), as the following example shows:

```csharp
int X = 2;
int Y = 3;

var pointMessage = $"""The point "{X}, {Y}" is {Math.Sqrt(X * X + Y * Y):F3} from the origin""";

Console.WriteLine(pointMessage);
// Output is:
// The point "2, 3" is 3.606 from the origin
```

To embed `{` and `}` characters in the result string, start an interpolated raw string literal with multiple `$` characters. When you do that, any sequence of `{` or `}` characters shorter than the number of `$` characters is embedded in the result string. To enclose any interpolation expression within that string, you need to use the same number of braces as the number of `$` characters, as the following example shows:

```csharp
int X = 2;
int Y = 3;

var pointMessage = $$"""{The point {{{X}}, {{Y}}} is {{Math.Sqrt(X * X + Y * Y):F3}} from the origin}""";
Console.WriteLine(pointMessage);
// Output is:
// {The point {2, 3} is 3.606 from the origin}
```

In the preceding example, an interpolated raw string literal starts with two `$` characters. You need to put every interpolation expression between double braces (`{{` and `}}`). A single brace is embedded into a result string. If you need to embed repeated `{` or `}` characters into a result string, use an appropriately greater number of `$` characters to designate an interpolated raw string literal. If the string literal has more repeated braces than the number of `$` characters, the `{` and `}` characters are grouped from inside to outside. In the preceding example, the literal `The point {{{X}}, {{Y}}}` interprets `{{X}}` and `{{Y}}` as interpolated expressions. The outer `{` and `}` are included verbatim in the output string.

[!INCLUDE[raw-string-tip](../../includes/raw-string-parsing.md)]

## Special characters

To include a brace, "{" or "}", in the text produced by an interpolated string, use two braces, "{{" or "}}". For more information, see the [Escaping braces](../../../standard/base-types/composite-formatting.md#escaping-braces) section of the [Composite formatting](../../../standard/base-types/composite-formatting.md) article.

The colon (":") has special meaning in an interpolation expression item. To use a [conditional operator](../operators/conditional-operator.md) in an interpolation expression, enclose that expression in parentheses.

The following example shows how to include a brace in a result string. It also shows how to use a conditional operator:

```csharp
string name = "Horace";
int age = 34;
Console.WriteLine($"He asked, \"Is your name {name}?\", but didn't wait for a reply :-{{");
Console.WriteLine($"{name} is {age} year{(age == 1 ? "" : "s")} old.");
// Output is:
// He asked, "Is your name Horace?", but didn't wait for a reply :-{
// Horace is 34 years old.
```

An interpolated [verbatim](verbatim.md) string starts with both the `$` and `@` characters. You can use `$` and `@` in any order: both `$@"..."` and `@$"..."` are valid interpolated verbatim strings. For more information about verbatim strings, see the [string](../builtin-types/reference-types.md) and [verbatim identifier](verbatim.md) articles.

## Culture-specific formatting

By default, an interpolated string uses the current culture defined by the <xref:System.Globalization.CultureInfo.CurrentCulture?displayProperty=nameWithType> property for all formatting operations.

To resolve an interpolated string to a culture-specific result string, use the <xref:System.String.Create(System.IFormatProvider,System.Runtime.CompilerServices.DefaultInterpolatedStringHandler%40)?displayProperty=nameWithType> method, which is available beginning with .NET 6. The following example shows how to do that:

```csharp
double speedOfLight = 299792.458;

System.Globalization.CultureInfo.CurrentCulture = System.Globalization.CultureInfo.GetCultureInfo("nl-NL");
string messageInCurrentCulture = $"The speed of light is {speedOfLight:N3} km/s.";

var specificCulture = System.Globalization.CultureInfo.GetCultureInfo("en-IN");
string messageInSpecificCulture = string.Create(
    specificCulture, $"The speed of light is {speedOfLight:N3} km/s.");

string messageInInvariantCulture = string.Create(
    System.Globalization.CultureInfo.InvariantCulture, $"The speed of light is {speedOfLight:N3} km/s.");

Console.WriteLine($"{System.Globalization.CultureInfo.CurrentCulture,-10} {messageInCurrentCulture}");
Console.WriteLine($"{specificCulture,-10} {messageInSpecificCulture}");
Console.WriteLine($"{"Invariant",-10} {messageInInvariantCulture}");
// Output is:
// nl-NL      The speed of light is 299.792,458 km/s.
// en-IN      The speed of light is 2,99,792.458 km/s.
// Invariant  The speed of light is 299,792.458 km/s.
```

In .NET 5 and earlier versions of .NET, use implicit conversion of an interpolated string to a <xref:System.FormattableString> instance. Then, you can use an instance <xref:System.FormattableString.ToString(System.IFormatProvider)?displayProperty=nameWithType> method or a static <xref:System.FormattableString.Invariant*?displayProperty=nameWithType> method to produce a culture-specific result string. The following example shows how to do that:

```csharp
double speedOfLight = 299792.458;
FormattableString message = $"The speed of light is {speedOfLight:N3} km/s.";

var specificCulture = System.Globalization.CultureInfo.GetCultureInfo("en-IN");
string messageInSpecificCulture = message.ToString(specificCulture);
Console.WriteLine(messageInSpecificCulture);
// Output:
// The speed of light is 2,99,792.458 km/s.

string messageInInvariantCulture = FormattableString.Invariant(message);
Console.WriteLine(messageInInvariantCulture);
// Output is:
// The speed of light is 299,792.458 km/s.
```

For more information about custom formatting, see the [Custom formatting with ICustomFormatter](../../../standard/base-types/formatting-types.md#custom-formatting-with-icustomformatter) section of the [Formatting types in .NET](../../../standard/base-types/formatting-types.md) article.

## Other resources

If you're new to string interpolation, see the [String interpolation in C#](../../fundamentals/tutorials/string-interpolation.md) tutorial. That tutorial demonstrates how to use interpolated strings to produce formatted strings.

## Compilation of interpolated strings

The compiler checks if an interpolated string is assigned to a type that satisfies the [_interpolated string handler pattern_](~/_csharpstandard/standard/attributes.md#235101-custom-interpolated-string-expression-handlers). An _interpolated string handler_ is a type that converts the interpolated string into a result string. When an interpolated string has the type `string`, the <xref:System.Runtime.CompilerServices.DefaultInterpolatedStringHandler?displayProperty=fullName> processes it. For the example of a custom interpolated string handler, see the [Write a custom string interpolation handler](../../advanced-topics/performance/interpolated-string-handler.md) tutorial. Use of an interpolated string handler is an advanced scenario, typically required for performance reasons.

> [!NOTE]
> One side effect of interpolated string handlers is that a custom handler, including <xref:System.Runtime.CompilerServices.DefaultInterpolatedStringHandler?displayProperty=nameWithType>, might not evaluate all the interpolation expressions within the interpolated string under all conditions. That behavior means side effects of those expressions might not occur.

If an interpolated string has the type `string`, the compiler typically transforms it into a <xref:System.String.Format*?displayProperty=nameWithType> method call. The compiler can replace <xref:System.String.Format*?displayProperty=nameWithType> with <xref:System.String.Concat*?displayProperty=nameWithType> if the analyzed behavior would be equivalent to concatenation.

If an interpolated string has the type <xref:System.IFormattable> or <xref:System.FormattableString>, the compiler generates a call to the <xref:System.Runtime.CompilerServices.FormattableStringFactory.Create*?displayProperty=nameWithType> method.

## C# language specification

For more information, see the [Interpolated string expressions](~/_csharpstandard/standard/expressions.md#1283-interpolated-string-expressions) and [custom interpolated string expression handlers](~/_csharpstandard/standard/attributes.md#235101-custom-interpolated-string-expression-handlers) sections of the [C# language specification](~/_csharpstandard/standard/README.md). See also [String literals](~/_csharpstandard/standard/lexical-structure.md#6456-string-literals) for raw string literals.

## See also

- [C# special characters](index.md)
- [Strings](../../programming-guide/strings/index.md)
- [Standard numeric format strings](../../../standard/base-types/standard-numeric-format-strings.md)
- [Composite formatting](../../../standard/base-types/composite-formatting.md)
- <xref:System.String.Format*?displayProperty=nameWithType>
- [Simplify interpolation (style rule IDE0071)](../../../fundamentals/code-analysis/style-rules/ide0071.md)
- [String interpolation in C# 10 and .NET 6 (.NET blog)](https://devblogs.microsoft.com/dotnet/string-interpolation-in-c-10-and-net-6/)
