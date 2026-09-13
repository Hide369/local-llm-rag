---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/tokens/comments.md
title: // and /* */ - comments
version: 0.0.0
fetched_at: 2026-09-13
---
# Code comments - `//` and `/*` - `*/`

C# supports two different forms of comments. Single line comments start with `//` and end at the end of that line of code. Multiline comments start with `/*` and end with `*/`.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following code shows an example of each form:

```csharp
// This is a single line comment.

/* This could be a summary of all the
   code that's in this class.
   You might add multiple paragraphs, or links to pages
   like https://learn.microsoft.com/dotnet/csharp.

   You could even include emojis. This example is 🔥
   Then, when you're done, close with
   */
```

You can use a multiline comment to insert text in a line of code. Because these comments have an explicit closing character, you can include more executable code after the comment:

```csharp
public static int Add(int left, int right)
{
    return left /* first operand */ + right /* second operand */;
}
```

A single line comment can appear after executable code on the same line. The comment ends at the end of the text line:

```csharp
return source++; // increment the source.
```

Some comments start with three slashes: `///`. *Triple-slash comments* are *XML documentation comments*. The compiler reads these comments to produce human documentation. You can read more about [XML doc comments](../xmldoc/index.md) in the section on triple-slash comments.
