---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/null-safety/index.md
title: Null safety in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# C# null safety

> [!TIP]
> This article is part of the **Fundamentals** section for developers who already know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first.
>
> **Coming from Java or C++?** C# provides compile-time null safety through nullable reference types. The goal is similar to Java's `@NonNull` annotations but enforced by the compiler. C# also has dedicated operators like `?.` and `??` that make null-safe expressions concise.

`null` represents the absence of a value. When you try to access a member on a `null` reference, by calling a method or reading a property, the runtime throws a <xref:System.NullReferenceException>:

```csharp
// Accessing a member on null throws NullReferenceException at runtime:
// string? name = null;
// int length = name.Length; // throws NullReferenceException

// Check before you dereference:
string? name = null;
if (name is not null)
{
    Console.WriteLine($"Name has {name.Length} characters.");
}
else
{
    Console.WriteLine("Name has no value.");
}
// Output: Name has no value.
```

C# gives you three complementary tools to write null-safe code:

- **Nullable value types**: let a value type such as `int` or `bool` also hold `null`
- **Nullable reference types**: let the compiler track whether a reference might be `null`
- **Null operators**: express null-safe access and fallback logic concisely

## Nullable value types

Value types such as `int`, `double`, and `bool` can't hold `null` by default. Add `?` to the type name to create a *nullable value type* that holds either a value or `null`:

```csharp
int? score = null;
Console.WriteLine(score.HasValue);               // False

score = 95;
Console.WriteLine(score.HasValue);               // True
Console.WriteLine(score.GetValueOrDefault());    // 95

int? missing = null;
Console.WriteLine(missing.GetValueOrDefault(-1)); // -1
```

Nullable value types are useful when an underlying value type needs to represent "no data." Common scenarios include database columns that might be absent, optional configuration settings, and sensor readings that aren't captured yet.

For full coverage of declaration, checking, and conversion, see [Nullable value types](nullable-value-types.md).

## Nullable reference types

Reference types, such as `string`, arrays, and class instances, can hold `null` at runtime. *Nullable reference types* is a compiler feature that makes null intent explicit and catches mistakes at compile time.

By using the `?` annotation, you declare your intent:

- `string?` — this reference *might* be `null`; the compiler warns if you dereference it without checking first
- `string` — this reference *should not* be `null`; the compiler warns if you assign `null` to it

```csharp
// string?  means this reference might be null
// string   means this reference should not be null
string? nullableName = null;
string  nonNullName  = "Alice";

// ?. safely accesses a member when the reference might be null
string display = nullableName?.ToUpper() ?? "(no name)";
Console.WriteLine(display);         // (no name)

display = nonNullName.ToUpper();    // safe: nonNullName is never null
Console.WriteLine(display);         // ALICE
```

All .NET projects that modern SDK templates create enable nullable reference types by default. For complete guidance on enabling and annotating, see [Nullable reference types](nullable-reference-types.md).

## Null operators

C# includes several operators that let you write null-safe code without manual `if`-null guards everywhere:

| Operator                  | Name                            | Purpose                                                |
|---------------------------|---------------------------------|--------------------------------------------------------|
| `?.`                      | Null-conditional member access  | Access a member only when the object is non-null       |
| `?[]`                     | Null-conditional indexer access | Access an element only when the collection is non-null |
| `??`                      | Null-coalescing                 | Return a fallback value when the expression is `null`  |
| `??=`                     | Null-coalescing assignment      | Assign only when the variable is `null`                |
| `is null` / `is not null` | Null pattern                    | Preferred null test                                    |

```csharp
string? city = GetCity();

// ?. — access a member only when non-null
int? len = city?.Length;

// ?? — substitute a default when null
string display = city ?? "unknown";

// is null — preferred null test
if (city is null)
{
    Console.WriteLine("No city provided.");
}
else
{
    Console.WriteLine($"{display} ({len} chars)");
}
// Output: No city provided.
```

For detailed examples of each operator, see [Null operators](null-operators.md).

## Nullable value types and nullable reference types serve different purposes

Nullable value types and nullable reference types aren't alternatives. They solve different problems:

- Use `T?` for a value type that needs to represent "no value." For example, use `int?` for an optional database column or `DateTime?` for an event that isn't scheduled yet.
- Use `string?` and other nullable reference annotations to document that a reference *might* be `null`, so the compiler can warn you before a `NullReferenceException` occurs at runtime.

Together, these features and the null operators give you a complete set of tools to write null-safe C# code.
