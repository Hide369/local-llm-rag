---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/null-safety/nullable-value-types.md
title: Nullable value types in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# Nullable value types: C# Fundamentals

> [!TIP]
> This article is part of the **Fundamentals** section for developers who know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first. For more details, see [Nullable value types](../../language-reference/builtin-types/nullable-value-types.md) in the language reference.

A *nullable value type* `T?` represents all values of its underlying value type `T`, plus an additional `null` value. A variable of type `int?` holds any integer or `null` to represent "no value."

Value types such as `int`, `bool`, and `DateTime` can't hold `null` by default. This behavior is efficient and prevents many errors. However, this limitation creates a problem when a value might genuinely be absent. A common scenario is reading from a database: an integer column might contain a number, or it might contain no value at all (`NULL` in SQL). A plain `int` can't represent that absence, but `int?` can.

## Declare a nullable value type

Append `?` to any value type to make it nullable:

```csharp
int?    age      = null;    // integer with no value yet
double? price    = 9.99;    // nullable double with a value
bool?   isActive = null;    // boolean with no value

age = 30;                   // assign a value later

int?[] scores = [100, null, 85, null, 72]; // array with absent entries
```

The default value of a nullable value type is `null`, not the underlying type's default.

## Check whether a value is present

The recommended way to check a nullable value type and extract its value is with a *type pattern*:

```csharp
int? temperature = 72;

if (temperature is int degrees)
{
    Console.WriteLine($"Temperature is {degrees}°F.");
}
else
{
    Console.WriteLine("Temperature is not recorded.");
}
// Output: Temperature is 72°F.
```

The `is int degrees` pattern matches only when `temperature` is non-null, and it simultaneously binds the value to `degrees`. You get both the null check and the value extraction in one step.

Alternatively, use the `HasValue` and `Value` properties:

```csharp
int? count = 42;

if (count.HasValue)
{
    Console.WriteLine($"Count is {count.Value}.");
}
else
{
    Console.WriteLine("Count has no value.");
}
// Output: Count is 42.
```

Prefer the `is T value` pattern for new code. It introduces a new non-nullable variable scoped to the matched branch, which makes the intent clearer and eliminates any temptation to accidentally use `Value` outside a null check, where it would throw an <xref:System.InvalidOperationException>.

You can also compare directly with `null`:

```csharp
int? quantity = null;

if (quantity != null)
{
    Console.WriteLine($"Quantity: {quantity.Value}");
}
else
{
    Console.WriteLine("Quantity is not set.");
}
// Output: Quantity is not set.
```

## Get a value with a fallback

When you need a non-nullable value from a nullable, use `GetValueOrDefault` or the null-coalescing `??` operator:

```csharp
int? rating = null;

int result1 = rating.GetValueOrDefault();    // 0 (default for int)
int result2 = rating.GetValueOrDefault(-1);  // -1 (specified fallback)

Console.WriteLine(result1); // 0
Console.WriteLine(result2); // -1

rating = 5;
int result3 = rating.GetValueOrDefault(-1);  // 5 (actual value)
Console.WriteLine(result3); // 5
```

The `??` operator is often cleaner inline:

```csharp
int? priority = null;

int effective = priority ?? 0;  // 0 because priority is null
Console.WriteLine(effective);   // 0

priority  = 3;
effective = priority ?? 0;      // 3 because priority has a value
Console.WriteLine(effective);   // 3
```

Both approaches return the actual value when one is present, and the fallback you specify when it isn't.

## Arithmetic with nullable value types

Arithmetic and comparison operators on nullable value types are *lifted*: when either operand is `null`, the result is `null` rather than an error.

```csharp
int? a = 10;
int? b = 20;
int? c = null;

int? sum     = a + b;   // both non-null: result is 30
int? product = a * c;   // one operand is null: result is null

Console.WriteLine(sum);               // 30
Console.WriteLine(product.HasValue);  // False — null propagates through arithmetic
```

Null propagates through arithmetic by default. To prevent a null result from cascading further, extract the value with `??` or `GetValueOrDefault` before you use it in a calculation.

## See also

- [Null safety overview](index.md)
- [Null operators](null-operators.md)
- [Nullable value types (language reference)](../../language-reference/builtin-types/nullable-value-types.md)
- [Nullable reference types](nullable-reference-types.md)
