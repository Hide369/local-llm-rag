---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/strings/common-tasks/concatenate.md
title: Concatenate strings in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# Concatenate strings in C\#

> [!TIP]
> This article is part of the **Fundamentals** section for developers who already know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../../tour-of-csharp/tutorials/index.md) tutorials first.
>
> **Coming from another language?** C# concatenation with `+` parallels Java and JavaScript. C# adds [string interpolation](../interpolation.md) (`$"{x}"`), similar to JavaScript template literals and Python f-strings, as the preferred way to build strings from variables. For building strings in a loop, C# offers <xref:System.Text.StringBuilder>, much like Java's `StringBuilder`.

*Concatenation* appends one string to the end of another to produce a new string. C# gives you several ways to concatenate, and the best choice depends on whether you're joining a fixed set of values or a collection, or building a string piece by piece in a loop.

## Concatenate string literals

When you concatenate string literals or constants with `+`, the compiler joins them at compile time. Splitting a long literal across several lines improves readability in source without any run-time cost:

```csharp
// The compiler joins adjacent string literals at compile time,
// so splitting a long literal across lines has no run-time cost.
string message =
    "This is the first sentence of a longer message. " +
    "This is the second sentence. " +
    "This is the third and final sentence.";

Console.WriteLine(message);
// => This is the first sentence of a longer message. This is the second sentence. This is the third and final sentence.
```

## Use the `+` and `+=` operators

To combine string variables, use the `+` operator to produce a new string, or `+=` to append to an existing one. The `+` operator is intuitive, and the compiler copies the string content only once even when you chain several operators in a single expression:

```csharp
string name = "Alex";
string day = "Monday";

// Use + to build a string from variables and literals.
string greeting = "Hello " + name + ". Today is " + day + ".";
Console.WriteLine(greeting);
// => Hello Alex. Today is Monday.

// Use += to append to an existing string.
greeting += " How are you today?";
Console.WriteLine(greeting);
// => Hello Alex. Today is Monday. How are you today?
```

> [!NOTE]
> In string concatenation, C# treats a `null` string the same as an empty string, so concatenating `null` adds nothing to the result.

## Use string interpolation

To embed computed expressions in a string, prefer [string interpolation](../interpolation.md) over positional placeholders like the `{0}` and `{1}` tokens that <xref:System.String.Format*?displayProperty=nameWithType> inherits from C-style formatting. Interpolation places each expression inline where its value appears, so the result string stays readable and you can't misalign an argument:

```csharp
string name = "Alex";
string day = "Monday";

// String interpolation reads better than a chain of + operators.
string greeting = $"Hello {name}. Today is {day}.";
Console.WriteLine(greeting);
// => Hello Alex. Today is Monday.
```

When every interpolated expression is itself a constant string, you can assign the interpolated result to a `const` string.

## Join a collection of strings

To combine the elements of a collection, use <xref:System.String.Concat*?displayProperty=nameWithType> to join them with no separator, or <xref:System.String.Join*?displayProperty=nameWithType> to place a separator between each element:

```csharp
string[] words = ["The", "quick", "brown", "fox"];

// Concat joins the sequence with no separator.
string runTogether = string.Concat(words);
Console.WriteLine(runTogether);
// => Thequickbrownfox

// Join places a separator between each element.
string sentence = string.Join(' ', words);
Console.WriteLine(sentence);
// => The quick brown fox
```

`string.Join` is the right tool whenever you need delimited output, such as comma-separated values or space-separated words.

## Build a string in a loop

Each `+` or `+=` operation creates a new string, because strings are immutable. When you append many pieces in a loop, that allocation adds up. The <xref:System.Text.StringBuilder> class builds the result in a single buffer instead:

```csharp
// StringBuilder builds a string in place, which suits loops
// that append many pieces.
var builder = new StringBuilder();
for (int i = 1; i <= 3; i++)
{
    builder.AppendLine($"Line {i}");
}

Console.Write(builder.ToString());
// => Line 1
// => Line 2
// => Line 3
```

Reach for `StringBuilder` when the number of pieces is large or unknown at compile time. For a fixed, small set of values, the `+` operator and string interpolation are clearer. For guidance on when each approach performs best, see [The `string` and `StringBuilder` types](xref:System.Text.StringBuilder#the-string-and-stringbuilder-types).

## See also

- [String interpolation in C#](../interpolation.md)
- <xref:System.String.Concat*?displayProperty=nameWithType>
- <xref:System.String.Join*?displayProperty=nameWithType>
- <xref:System.Text.StringBuilder>
