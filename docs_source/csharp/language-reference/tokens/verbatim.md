---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/tokens/verbatim.md
title: Verbatim text and strings - @
version: 0.0.0
fetched_at: 2026-09-13
---
# Verbatim text - `@` in variables, attributes, and string literals

The `@` special character serves as a verbatim identifier. Use it in the following ways:

1. To indicate that a string literal is to be interpreted verbatim. The `@` character in this instance defines a *verbatim string literal*. Simple escape sequences (such as `"\\"` for a backslash), hexadecimal escape sequences (such as `"\x0041"` for an uppercase A), and Unicode escape sequences (such as `"\u0041"` for an uppercase A) are interpreted literally. Only a quote escape sequence (`""`) isn't interpreted literally; it produces one double quotation mark. Additionally, in case of a verbatim [interpolated string](interpolated.md) brace escape sequences (`{{` and `}}`) aren't interpreted literally; they produce single brace characters. The following example defines two identical file paths, one by using a regular string literal and the other by using a verbatim string literal. This is one of the more common uses of verbatim string literals.

```csharp
string filename1 = @"c:\documents\files\u0066.txt";
string filename2 = "c:\\documents\\files\\u0066.txt";

Console.WriteLine(filename1);
Console.WriteLine(filename2);
// The example displays the following output:
//     c:\documents\files\u0066.txt
//     c:\documents\files\u0066.txt
```

   The following example illustrates the effect of defining a regular string literal and a verbatim string literal that contain identical character sequences.

```csharp
string s1 = "He said, \"This is the last \u0063hance\x0021\"";
string s2 = @"He said, ""This is the last \u0063hance\x0021""";

Console.WriteLine(s1);
Console.WriteLine(s2);
// The example displays the following output:
//     He said, "This is the last chance!"
//     He said, "This is the last \u0063hance\x0021"
```

1. To use C# keywords as identifiers. The `@` character prefixes a code element that the compiler interprets as an identifier rather than a C# keyword. The following example uses the `@` character to define an identifier named `for` that it uses in a `for` loop.

```csharp
string[] @for = { "John", "James", "Joan", "Jamie" };
for (int ctr = 0; ctr < @for.Length; ctr++)
{
   Console.WriteLine($"Here is your gift, {@for[ctr]}!");
}
// The example displays the following output:
//     Here is your gift, John!
//     Here is your gift, James!
//     Here is your gift, Joan!
//     Here is your gift, Jamie!
```

1. To enable the compiler to distinguish between attributes in cases of a naming conflict. An attribute is a class that derives from <xref:System.Attribute>. Its type name typically includes the suffix **Attribute**, although the compiler doesn't enforce this convention. You can reference the attribute in code either by its full type name (for example, `[InfoAttribute]`) or by its shortened name (for example, `[Info]`). However, a naming conflict occurs if two shortened attribute type names are identical, and one type name includes the **Attribute** suffix but the other doesn't. For example, the following code fails to compile because the compiler can't determine whether the `Info` or `InfoAttribute` attribute is applied to the `Example` class. For more information, see [CS1614](../compiler-messages/attribute-usage-errors.md#attribute-class-requirements).

```csharp
using System;

[AttributeUsage(AttributeTargets.Class)]
public class Info : Attribute
{
   private string information;

   public Info(string info)
   {
      information = info;
   }
}

[AttributeUsage(AttributeTargets.Method)]
public class InfoAttribute : Attribute
{
   private string information;

   public InfoAttribute(string info)
   {
      information = info;
   }
}

[Info("A simple executable.")] // Generates compiler error CS1614. Ambiguous Info and InfoAttribute.
// Prepend '@' to select 'Info' ([@Info("A simple executable.")]). Specify the full name 'InfoAttribute' to select it.
public class Example
{
   [InfoAttribute("The entry point.")]
   public static void Main()
   {
   }
}
```

## See also

- [C# Special Characters](./index.md)
