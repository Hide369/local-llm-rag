---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/strings/common-tasks/modify.md
title: Modify string contents in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# Modify string contents in C\#

> [!TIP]
> This article is part of the **Fundamentals** section for developers who already know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../../tour-of-csharp/tutorials/index.md) tutorials first.
>
> **Coming from another language?** Like Java and JavaScript, C# strings are *immutable*: methods such as `Replace` and `Trim` return a new string instead of changing the original. The patterns here parallel `String` methods in those languages.

A C# `string` is *immutable*, which means its contents never change after you create it. Every method that appears to modify a string actually returns a new `string` with the changes, leaving the original intact. The examples in this article store each result in a new variable so you can see both the source and the modified value.

Choose the technique that matches your scenario: replace known text, trim whitespace, remove a span of characters, replace text that matches a pattern, or edit individual characters.

## Replace known text

The <xref:System.String.Replace*?displayProperty=nameWithType> method substitutes every occurrence of one string with another and returns the result as a new string:

```csharp
string source = "The mountains are behind the clouds today.";

// Replace returns a new string; the original is unchanged.
string updated = source.Replace("mountains", "peaks");

Console.WriteLine(source);
// => The mountains are behind the clouds today.
Console.WriteLine(updated);
// => The peaks are behind the clouds today.
```

The original string is unchanged, which demonstrates immutability: `Replace` creates a new string with the substitution.

`Replace` also has an overload that swaps single characters. The following example replaces every space with an underscore:

```csharp
string source = "The mountains are behind the clouds today.";

// Replace every occurrence of one character with another.
string updated = source.Replace(' ', '_');

Console.WriteLine(updated);
// => The_mountains_are_behind_the_clouds_today.
```

Both overloads replace *every* match in the string, not just the first. Whether you pass a single character or a string, `Replace` substitutes all occurrences in one call.

## Trim whitespace

Use <xref:System.String.Trim*?displayProperty=nameWithType>, <xref:System.String.TrimStart*?displayProperty=nameWithType>, and <xref:System.String.TrimEnd*?displayProperty=nameWithType> to remove leading or trailing whitespace. Each method returns a new string:

```csharp
string source = "    I'm wider than I need to be.      ";

// Each method returns a new string with whitespace removed.
Console.WriteLine($"<{source.Trim()}>");
// => <I'm wider than I need to be.>
Console.WriteLine($"<{source.TrimStart()}>");
// => <I'm wider than I need to be.      >
Console.WriteLine($"<{source.TrimEnd()}>");
// => <    I'm wider than I need to be.>
```

## Remove a span of characters

The <xref:System.String.Remove*?displayProperty=nameWithType> method deletes a number of characters starting at an index. Combine it with <xref:System.String.IndexOf*?displayProperty=nameWithType> to locate the text to remove:

```csharp
string source = "Many mountains are behind many clouds today.";
string toRemove = "many ";

// Find the text, then remove that span by index and length.
int index = source.IndexOf(toRemove);
string result = index >= 0
    ? source.Remove(index, toRemove.Length)
    : source;

Console.WriteLine(result);
// => Many mountains are behind clouds today.
```

## Replace text that matches a pattern

When you need to replace text that follows a pattern rather than an exact string, use [regular expressions](../../../../standard/base-types/regular-expressions.md). The <xref:System.Text.RegularExpressions.Regex.Replace*?displayProperty=nameWithType> method accepts a function that computes each replacement, so you can preserve details such as the original capitalization. The pattern `the\s` matches "the" followed by a whitespace character, which prevents it from matching "there":

```csharp
string source = "The mountains are still there behind the clouds today.";

// Replace "the" or "The" followed by whitespace, preserving the original case.
// The \s in the pattern keeps "there" from matching.
string result = Regex.Replace(
    source,
    """the\s""",
    match => char.IsUpper(match.Value[0]) ? "Many " : "many ",
    RegexOptions.IgnoreCase);

Console.WriteLine(result);
// => Many mountains are still there behind many clouds today.
```

For pattern-based searching rather than replacement, see [Search strings in C#](search.md). For the regular expression syntax, see [Regular expression language quick reference](../../../../standard/base-types/regular-expression-language-quick-reference.md).

## Modify individual characters

To change characters by position, copy the string into a <xref:System.Span`1> of characters, modify the span, and then build a new string from it. The following example finds the word "fox" and replaces it with "cat":

```csharp
string phrase = "The quick brown fox jumps over the fence.";

// A string is immutable, so copy it into a Span<char> to edit in place.
Span<char> characters = stackalloc char[phrase.Length];
phrase.CopyTo(characters);
int index = phrase.IndexOf("fox");
if (index != -1)
{
    characters[index] = 'c';
    characters[index + 1] = 'a';
    characters[index + 2] = 't';
}

// Build a new string from the modified characters.
string updated = new string(characters);
Console.WriteLine(updated);
// => The quick brown cat jumps over the fence.
```

For high-performance scenarios that avoid intermediate allocations, the runtime provides lower-level APIs such as <xref:System.String.Create*?displayProperty=nameWithType>. Those techniques are advanced; for everyday code, the methods in this article are the right choice.

## See also

- [Search strings in C#](search.md)
- [.NET regular expressions](../../../../standard/base-types/regular-expressions.md)
- <xref:System.String.Replace*?displayProperty=nameWithType>
- <xref:System.Text.StringBuilder>
