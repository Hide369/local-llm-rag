---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/strings/index.md
title: Strings in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# C# strings

> [!TIP]
> This article is part of the **Fundamentals** section for developers who already know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first.
>
> **Coming from Java or C++?** A C# `string` is an immutable reference type backed by <xref:System.String?>. UTF-16 is the in-memory encoding, similar to Java's `String`. Unlike C/C++, strings aren't null-terminated and don't decay into pointers.

A *string* is a sequence of characters. In C#, `string` is the language keyword for the <xref:System.String?displayProperty=fullName> type. Every string literal you write produces a `System.String` instance.

## `string` vs. `String`

The `string` keyword and the `String` type name refer to the same type. They compile to identical intermediate language (IL).

```csharp
// The 'string' keyword is an alias for System.String. The two are identical.
string a = "hello";
String b = "hello";

Console.WriteLine(a == b);                // True
Console.WriteLine(typeof(string) == typeof(String)); // True
```

Prefer the `string` keyword in your own code. It's consistent with the other built-in type keywords (`int`, `bool`, `double`), and it works without a `using System;` directive.

## Strings are immutable

*Immutable* means the value can't be changed after it's created. Once you create a `string`, you can't change its characters. Methods such as `ToUpperInvariant`, `Replace`, `Substring`, and `Trim` return a *new* string that contains the modified value. The original instance stays the same.

```csharp
string greeting = "hello";

// ToUpper returns a *new* string. The original is unchanged.
string shouted = greeting.ToUpperInvariant();

Console.WriteLine(greeting);  // hello
Console.WriteLine(shouted);   // HELLO
```

Because strings are immutable, you can safely share them across methods and threads. This immutability explains why the `string` type behaves like a value type in everyday use even though it's a reference type.

When you build a string from many small pieces in a loop, use <xref:System.Text.StringBuilder> to append in place and produce a single string at the end:

```csharp
// For many sequential edits, StringBuilder avoids allocating a new string each time.
var builder = new StringBuilder();
for (int i = 1; i <= 3; i++)
{
    builder.Append("item ").Append(i).Append(';');
}
string result = builder.ToString();
Console.WriteLine(result);    // item 1;item 2;item 3;
```

## String literals

C# offers four literal forms. Each form suits different content. As a quick guide:

- Use **regular literals** for short, simple text with at most a few escape sequences.
- Use **verbatim literals** when backslashes dominate the content, such as Windows paths or regex patterns.
- Use **raw string literals** for multiline or structurally formatted text, such as inline JSON, SQL, XML, or formatted message blocks.
- Add a `$` prefix to any of the aforementioned literals to get an **interpolated string** when you need to embed values.
- Add a `u8` suffix to a literal to produce a UTF-8 byte sequence (a <xref:System.ReadOnlySpan%601> of `byte`) for byte-oriented APIs. See [UTF-8 string literals](../../language-reference/builtin-types/reference-types.md#utf-8-string-literals) in the language reference for details.

### Regular literals and escape sequences

A regular string literal is enclosed in double quotes. Backslash starts an escape sequence:

```csharp
// Common escape sequences inside a regular string literal.
string tabbed   = "name:\tAda";          // \t  tab
string twoLines = "line 1\nline 2";      // \n  newline
string quoted   = "She said \"hi\".";    // \"  literal quote
string path     = "C:\\src\\app";        // \\  literal backslash

Console.WriteLine(tabbed);
Console.WriteLine(twoLines);
Console.WriteLine(quoted);
Console.WriteLine(path);
```

Common escape sequences include `\n` (newline), `\t` (tab), `\"` (literal quote), `\\` (literal backslash), `\0` (null char), and Unicode escapes (`\uXXXX`, `\UXXXXXXXX`).

Beginning in C# 13, `\e` represents the **ESC** control character (U+001B). It's the start byte for ANSI terminal escape sequences:

```csharp
// Beginning in C# 13, \e represents the ESC control character (U+001B).
// It's used to start ANSI terminal escape sequences.
string esc = "\e[31mError\e[0m: file missing";

Console.WriteLine(esc);                  // ESC[31mError ESC[0m: file missing
Console.WriteLine((int)'\e');          // 27
```

Use a regular literal when the text is short and contains only a handful of escape sequences. Once the escapes start to outnumber the visible characters, switch to a verbatim or raw literal.

### Verbatim literals

A verbatim literal is prefixed with `@`. Backslashes are treated literally, which is useful for Windows paths and regular-expression patterns:

```csharp
// A verbatim string literal (@) treats backslashes literally.
// Useful for Windows paths and regular expressions.
string winPath = @"C:\src\app\readme.md";
string pattern = @"\d{3}-\d{4}";

Console.WriteLine(winPath);
Console.WriteLine(pattern);
```

To embed a literal quote inside a verbatim string, double it: `@"She said ""hi""."`. Verbatim strings can also span multiple physical lines.

Verbatim literals are the right choice when backslashes are part of the content but you don't have many embedded quotes. For multiline text or content with quotes, raw string literals are usually clearer.

### Raw string literals

For any literal that contains quotes, backslashes, or multiple lines, prefer **raw string literals**. They eliminate escape noise entirely, which makes them the best fit for inline JSON, SQL, XML, regex patterns, and formatted text blocks where the source should look like the output:

```csharp
// Raw string literals use three or more quotes and need no escaping.
// The source looks like the output, which is ideal for inline JSON, SQL, XML, and the like.
string json = """
    {
        "name": "Ada",
        "roles": ["admin", "editor"]
    }
    """;

string sql = """
    SELECT Id, Name
    FROM   Users
    WHERE  Name = 'O''Brien'
    """;

Console.WriteLine(json);
Console.WriteLine(sql);
```

Raw string literals all but eliminate escape sequences and accommodate any formatting and quoting you need. See [Raw string literals](raw-string-literals.md) for the full rules.

### Interpolated strings

A `$` prefix turns a literal into an *interpolated string*. Expressions in `{}` holes are evaluated and their results inserted, and you can apply standard format specifiers and alignment inside the holes. Interpolation also combines with the other literal forms — use `$@"..."` to interpolate a verbatim literal, or `$"""..."""` to interpolate a raw string literal for richly formatted output:

```csharp
// The $ prefix evaluates expressions inside { } and inserts their values.
string name = "Ada";
int score = 92;

string greeting = $"Hello, {name}! Your score is {score}.";
// Format specifiers and alignment work inside the holes.
string formatted = $"pi = {Math.PI:F3}, padded = |{name,10}|";

// Combine $ and """ for richly formatted multiline output.
string report = $"""
    Report for {name}
    -----------------
    Score : {score}
    Grade : {(score >= 90 ? "A" : "B")}
    """;

Console.WriteLine(greeting);
Console.WriteLine(formatted);
Console.WriteLine(report);
```

Interpolation is the recommended way to compose strings from values in everyday code.

## Indexing and `char`

A `string` is a sequence of UTF-16 *code units*. The indexer returns one <xref:System.Char?displayProperty=fullName>, which represents a single UTF-16 code unit, not necessarily a complete Unicode code point. `Length` returns the count of code units.

```csharp
// A string is a sequence of UTF-16 code units. s[i] returns one char.
string word = "café";

Console.WriteLine(word.Length);          // 4
Console.WriteLine(word[0]);              // c

foreach (char c in word)
{
    Console.Write($"{c} ");              // c a f é
}
Console.WriteLine();
```

For text that might contain emoji or characters outside the Basic Multilingual Plane, iterate by *rune* using <xref:System.Text.Rune> or by grapheme cluster using <xref:System.Globalization.StringInfo>. Plain `char` iteration works for most Western text and ASCII-dominant content.

## String equality

Equality on `string` compares the character sequences, not references:

```csharp
// String equality compares character sequences, not references.
string left  = "hello";
string right = string.Concat("hel", "lo");

Console.WriteLine(left == right);                                      // True
Console.WriteLine(left.Equals(right, StringComparison.Ordinal));       // True
```

For comparisons that need to be locale-aware or case-aware, pass an explicit <xref:System.StringComparison> value. Use `StringComparison.Ordinal` for protocol values, identifiers, and other non-linguistic text.

## Common string operations

Use the following table as a quick guide to everyday string operations in C#:

| Category    | What it covers                                              |
|-------------|-------------------------------------------------------------|
| Search      | Find characters or substrings, test prefixes and suffixes   |
| Split       | Break a string into substrings on separators                |
| Concatenate | Combine strings — `+`, interpolation, `Concat`, `Join`      |
| Modify      | Produce a transformed copy — `Replace`, `Trim`, `Substring` |
| Compare     | Test equality and ordering with the right `StringComparison`|

The full API surface — every overload, every method — is documented in the <xref:System.String> reference.

## See also

- [Raw string literals](raw-string-literals.md)
- [`nameof` operator](nameof.md)
- <xref:System.String>
- <xref:System.Text.StringBuilder>
- <xref:System.Char>
- <xref:System.ReadOnlySpan%601>
