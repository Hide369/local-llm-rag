---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/types/built-in-types.md
title: Built-in types and literals
version: 0.0.0
fetched_at: 2026-09-13
---
# Built-in types and literals

> [!TIP]
> **New to developing software?** Start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first. They introduce types as you write your first programs.
>
> **Experienced in another language?** C# built-in types map closely to types in Java, C++, and other languages. Skim the [literal syntax](#literal-syntax) and [type inference](#implicitly-typed-variables-with-var) sections for C#-specific details.

C# provides a set of built-in types that you can use in any program without additional references. These types cover the most common data you work with: numbers, true/false values, individual characters, and text. For a complete reference table mapping C# keywords to .NET types, see [Built-in types (C# reference)](../../language-reference/builtin-types/built-in-types.md).

## Numeric types

C# has built-in types for integers, floating-point numbers, and decimal numbers. The most commonly used types are `int`, `double`, and `decimal`:

```csharp
int population = 67_000_000;
long distance = 384_400_000L;
short temperature = -40;
byte red = 255;

double pi = 3.141592653589793;
float gravity = 9.81f;
decimal price = 19.99m;
```

Each numeric type has a fixed size and range. `int` stores 32-bit integers (roughly ±2.1 billion), `long` stores 64-bit integers, and `short` and `byte` store smaller values. For the full list of sizes and ranges, see [Integral numeric types](../../language-reference/builtin-types/integral-numeric-types.md) and [Floating-point numeric types](../../language-reference/builtin-types/floating-point-numeric-types.md).

Use `double` for general floating-point math, `float` when memory is constrained, and `decimal` when you need exact decimal precision (such as financial calculations). Append the `f` suffix for `float` literals and `m` for `decimal` literals. Without a suffix, the compiler treats a number with a decimal point as `double`.

### Unsigned types

Each signed integer type has an unsigned counterpart that stores only non-negative values with twice the positive range:

```csharp
uint fileSize = 4_294_967_295;
ulong totalBytes = 18_446_744_073_709_551_615;
ushort port = 443;
```

You might use unsigned types when negative values aren't valid for the data, such as file sizes or network ports. In practice, many applications use `int` or `long` even for positive-only values because signed types are the default throughout the .NET APIs.

### Native-sized integers

The `nint` and `nuint` types represent integers whose size matches the platform's native pointer size: 32 bits on a 32-bit platform, 64 bits on a 64-bit platform:

```csharp
nint bufferSize = 1024;
nuint elementCount = 256;
```

You're unlikely to need `nint` or `nuint` in everyday code. They exist for interop scenarios and low-level memory operations where matching the platform's pointer size is important. Stick with `int` or `long` unless you have a specific reason to use native-sized types. For more information, see [`nint` and `nuint`](../../language-reference/builtin-types/integral-numeric-types.md#native-sized-integers).

## `bool`, `char`, and `string`

Beyond numbers, C# provides three other frequently used built-in types:

```csharp
bool isValid = true;
char grade = 'A';
string greeting = "Hello, world!";
```

- **`bool`** — Stores `true` or `false`. Use it in conditions, loops, and logical expressions.
- **`char`** — Stores a single Unicode character (UTF-16 code unit), enclosed in single quotes.
- **`string`** — Stores a sequence of characters, enclosed in double quotes. Strings are *immutable*. Once you create a string, you can't change its contents. Operations that appear to modify a string actually create a new one.

Strings are one of the most used types in C#. For in-depth coverage of string operations, including interpolation, raw string literals, searching, splitting, and comparison, see the [Strings](../../language-reference/builtin-types/reference-types.md#the-string-type) section.

## Literal syntax

A *literal* is a value you write directly in your code. The compiler assigns each literal a type based on its format and any suffix you provide. C# supports the following kinds of literals:

- **Integer literals** — Decimal (`42`), hexadecimal (`0x2A`), and binary (`0b_0010_1010`).
- **Floating-point literals** — `double` by default (`3.14`), `float` with the `f` suffix (`3.14f`), and `decimal` with `m` (`3.14m`).
- **Character literals** — A single character in single quotes (`'A'`), including escape sequences (`'\n'`).
- **String literals** — Regular (`"hello"`), verbatim (`@"C:\path"`), raw (`""" ... """`), and interpolated (`$"value: {x}"`).
- **Boolean literals** — `true` and `false`.
- **The `null` literal** — Represents the absence of a value for reference types and nullable value types.
- **The `default` literal** — Produces the default value for any type (covered in [`default` expressions](#default-expressions)).

The following sections cover the most common literal forms in detail.

### Integer literals

```csharp
int dec = 42;
int hex = 0x2A;
int bin = 0b_0010_1010;
long big = 1_000_000_000L;
```

Use the `0x` prefix for hexadecimal and `0b` for binary. Append `L` for `long`, `U` for `uint`, or `UL` for `ulong`.

Place the `_` digit separator anywhere within a number to make it easier to read. Common patterns include thousand separators in decimal literals (`1_000_000_000`), byte or word boundaries in hexadecimal (`0xFF_FF`), and nibble boundaries in binary (`0b_0010_1010`).

### Floating-point literals

```csharp
double d = 3.14;
float f = 3.14f;
decimal m = 3.14m;
double scientific = 1.5e6; // 1,500,000
```

Without a suffix, a numeric literal with a decimal point is `double`. Append `f` for `float` and `m` for `decimal`. Scientific notation (`1.5e6`) is also supported.

### Character and string literals

```csharp
char newline = '\n';
char unicode = '\u0041'; // 'A'

string message = $"Found {dec} items";            // interpolated string
string path = @"C:\Users\docs\file.txt";        // verbatim string
string json = """
    { "name": "Alice", "age": 30 }
    """;                                           // raw string literal
string raw = $"""
    Found {dec} items in "{greeting}"
    """;                                           // raw + interpolated
```

Character literals use single quotes and support escape sequences (`\n`, `\t`, `\u`). String literals use double quotes.

Prefix strings with `$` for interpolation. When a string contains quotes, backslashes, or embedded JSON or XML, use a raw string literal (delimited by `"""`) instead of escaping each character. Raw string literals also combine with interpolation (`$"""`).

Older code uses `@` (verbatim strings) to avoid escape processing. Raw string literals are easier to read and write, so prefer them for new code.

## `default` expressions

The `default` expression produces the default value for a type: `0` for numeric types, `false` for `bool`, and `null` for reference types:

```csharp
int defaultInt = default;          // 0
bool defaultBool = default;        // false
string? defaultString = default;   // null

// Use default in a conditional:
var limit = (args.Length > 0) ? int.Parse(args[0]) : default(int);
```

The `default` expression is most useful in generic code, where you don't know the concrete type and can't hard-code a specific value like `0` or `null`. Write `default` (without a type argument) when the compiler can infer the type from context, or `default(T)` when the type isn't obvious. For the complete list of default values by type, see [Default values of C# types](../../language-reference/builtin-types/default-values.md).

## Implicitly typed variables with `var`

The `var` keyword tells the compiler to infer a local variable's type from its initializer:

```csharp
var count = 10;              // compiler infers int
var name = "C#";             // compiler infers string
var items = new List<int>(); // compiler infers List<int>

// var requires an initializer — the compiler needs a value to infer the type.
// The following line wouldn't compile:
// var unknown;
```

The variable is still strongly typed; `var` doesn't make it dynamic. The compiler determines the type at compile time and enforces type safety as usual. Use `var` when the type is obvious from the right-hand side to reduce visual noise. Spell out the type when it makes the code clearer. For more information, see [Implicitly typed local variables](../../language-reference/statements/declarations.md#implicitly-typed-local-variables).

## Target-typed `new` expressions

When you already know the target type from context, such as a variable declaration or a method parameter, you can omit the type name from the `new` expression:

```csharp
List<string> names = new() { "Alice", "Bob", "Charlie" };
Dictionary<string, int> scores = new()
{
    ["Alice"] = 95,
    ["Bob"] = 87
};
```

Target-typed `new` reduces repetition when the type name is long or appears on the left-hand side of the assignment. It works anywhere the compiler can determine the target type, including method arguments and return statements. For more information, see [`new` operator — target-typed `new`](../../language-reference/operators/new-operator.md#target-typed-new).

## The `dynamic` type

The `dynamic` type bypasses compile-time type checking. The compiler resolves operations on a `dynamic` variable at run time instead:

```csharp
dynamic value = 42;
Console.WriteLine(value.GetType()); // System.Int32

value = "Now I'm a string";
Console.WriteLine(value.GetType()); // System.String

// The compiler doesn't check operations on dynamic at compile time.
// Errors surface at run time instead.
```

Use `dynamic` when interacting with COM APIs, dynamic languages, or reflection-heavy scenarios where types aren't known at compile time. Avoid `dynamic` in most application code because you lose compile-time safety. Errors that the compiler normally catches become run-time exceptions instead. For more information, see [The dynamic type](../../language-reference/builtin-types/reference-types.md#the-dynamic-type).

## See also

<!-- Remove this HTML comment after dotnet/docs#55469 is merged and this branch is rebased.
- [Operators](../expressions/operators.md)
-->

- [Type system overview](index.md)
- [Built-in types (C# reference)](../../language-reference/builtin-types/built-in-types.md)
- [Integral numeric types](../../language-reference/builtin-types/integral-numeric-types.md)
- [Floating-point numeric types](../../language-reference/builtin-types/floating-point-numeric-types.md)
- [Value types](../../language-reference/builtin-types/value-types.md)
