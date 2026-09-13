---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/null-safety/null-operators.md
title: Null operators in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# C# null operators

> [!TIP]
> This article is part of the **Fundamentals** section for developers who know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first. For the complete operator reference, see [Member access operators](../../language-reference/operators/member-access-operators.md) and [null-coalescing operators](../../language-reference/operators/null-coalescing-operator.md) in the language reference.

C# provides several operators that make null-safe code concise. Instead of nesting `if (x != null)` guards throughout your code, these operators let you express null-safe access, fallback values, and null tests in a single expression.

This article covers `?.` and `?[]` for null-conditional access, `??` for null-coalescing, `??=` for null-coalescing assignment, and `is null`/`is not null` for null pattern matching.

## Null-conditional member access `?.`

The `?.` operator accesses a member only when the object is non-null. When the object is `null`, the entire expression evaluates to `null` instead of throwing a <xref:System.NullReferenceException>:

```csharp
string? name = null;

// Without ?., accessing a member on null throws NullReferenceException:
// int len = name.Length; // throws if name is null

// ?. returns null instead of throwing:
int? len = name?.Length;
Console.WriteLine(len.HasValue); // False

name = "C#";
Console.WriteLine(name?.Length); // 2
```

The `?.` operator *short-circuits*: when the left-hand side is `null`, everything to the right is skipped. No method calls run and no side effects occur.

You can chain multiple `?.` operators in a single expression. The chain stops at the first `null` it encounters:

```csharp
string? input = null;

// Chain ?. across multiple method calls — short-circuits at the first null:
string? upper = input?.Trim()?.ToUpperInvariant();
Console.WriteLine(upper ?? "(none)"); // (none)

input = "  hello  ";
Console.WriteLine(input?.Trim()?.ToUpperInvariant()); // HELLO
```

## Null-conditional indexer access `?[]`

The `?[]` operator applies the same short-circuit behavior to indexer and array access. Use it when the collection itself might be `null`:

```csharp
string[]? tags = null;

// ?[] accesses an element only when the collection is non-null
string? first = tags?[0];
Console.WriteLine(first ?? "(none)"); // (none)

tags = ["csharp", "dotnet", "nullable"];
Console.WriteLine(tags?[0]);          // csharp
```

## Chain null-conditional operators

Chain multiple `?.` operators to traverse a path of potentially null references. The chain short-circuits at the first `null`:

```csharp
var order = new Order("ORD-001", null);

// Each ?. short-circuits when null: Customer is null, so Address and City are never accessed
string? city = order.Customer?.Address?.City;
Console.WriteLine(city ?? "(no city)"); // (no city)

var fullOrder = new Order("ORD-002",
    new Customer("Alice", new Address("123 Main St", "Springfield", "IL")));

Console.WriteLine(fullOrder.Customer?.Address?.City); // Springfield
```

When `Customer` is `null`, neither `Address` nor `City` is evaluated. The whole expression returns `null`.

## Thread-safe delegate invocation

`?.` provides a clean, thread-safe way to invoke a delegate or raise an event. The delegate expression is evaluated only once, so there's no window for another thread to unsubscribe between the null check and the invocation:

```csharp
EventHandler? clicked = null;

// No subscribers — ?.Invoke does nothing instead of throwing NullReferenceException
clicked?.Invoke(null, EventArgs.Empty);

clicked += (_, _) => Console.WriteLine("Button clicked!");

// With a subscriber — ?.Invoke calls the handler
clicked?.Invoke(null, EventArgs.Empty);
// Output: Button clicked!
```

This pattern replaces the older `if (clicked != null) clicked(...)` idiom.

## Null-coalescing `??`

The `??` operator returns its left-hand operand when it's non-null, and its right-hand operand when the left is `null`. Use it to provide a default value:

```csharp
string? username = null;

// ?? returns the right-hand value when the left-hand is null
string display = username ?? "Guest";
Console.WriteLine(display); // Guest

username = "alice";
display  = username ?? "Guest";
Console.WriteLine(display); // alice
```

`??` is right-associative, so `a ?? b ?? c` evaluates as `a ?? (b ?? c)`. The first non-null value wins. A common pattern is to chain `?.` with `??`: use `?.` to safely traverse a null-possible chain, then `??` to substitute a default if the chain returned `null`. For a complete example, see [Combine null operators](#combine-null-operators).

## Null-coalescing assignment `??=`

The `??=` operator assigns the right-hand value to a variable only when the variable is `null`. Use it for lazy initialization:

```csharp
List<string>? cache = null;

// ??= assigns only when the variable is null
cache ??= LoadData();
Console.WriteLine(cache.Count); // 3

// cache is already non-null, so LoadData() isn't called again
cache ??= LoadData();
Console.WriteLine(cache.Count); // 3

static List<string> LoadData() => ["alpha", "beta", "gamma"];
```

The right-hand expression is evaluated only when the variable is `null`. When the variable already has a value, the right side isn't evaluated at all.

## Null-conditional assignment (C# 14)

Beginning in C# 14, you can use `?.` and `?[]` as assignment targets. The assignment runs only when the left-hand object is non-null:

```csharp
AppConfig? config = new AppConfig();

// Assigns only when config is non-null (C# 14)
config?.Theme = "dark";
Console.WriteLine(config?.Theme); // dark

AppConfig? missing = null;
missing?.Theme = "light";                         // no-op: missing is null
Console.WriteLine(missing?.Theme ?? "(no config)"); // (no config)
```

The right-hand side is evaluated only when the left-hand side is known to be non-null.

## Null pattern matching: `is null` and `is not null`

The `is null` and `is not null` patterns test whether an expression is `null`:

```csharp
string? input = null;

// is null is the preferred test — unaffected by operator overloading
if (input is null)
{
    Console.WriteLine("No input provided.");
}

// == null also works, but a custom == operator can change its behavior
if (input == null)
{
    Console.WriteLine("Still no input.");
}
```

Prefer `is null` over `== null` for null checks. The `==` operator can be overloaded, meaning `x == null` might return `true` even when `x` isn't `null` if the type defines a custom equality operator. The `is null` pattern always tests for the actual null reference, regardless of operator overloading.

```csharp
string? value = "hello";

if (value is not null)
{
    Console.WriteLine(value.ToUpper()); // HELLO
}
```

## Combine null operators

In practice, you often combine several of these operators. One expression can safely traverse a deep object graph, apply a fallback, and then guard on the result:

```csharp
Order? order = GetPendingOrder();

// Chain ?. for safe traversal, ?? for a fallback, is null for a clear guard
string city = order?.Customer?.Address?.City ?? "unknown";

if (order is null)
{
    Console.WriteLine("No pending order.");
}
else
{
    Console.WriteLine($"Shipping to: {city}");
}
// Output: No pending order.
```

## Null-forgiving operator `!`

The `!` postfix operator suppresses nullable warnings. Append `!` to tell the compiler "this expression is definitely not null." The operator has no effect at runtime. It only affects the compiler's null-state analysis.

```csharp
string? name = FindUser("alice");

// Use ! only when you have information the compiler doesn't.
// FindUser guarantees a non-null result for known usernames.
int length = name!.Length;
Console.WriteLine(length); // 5
```

Use `!` sparingly, and only when you have information the compiler doesn't. Examples include tests that intentionally pass `null` to validate argument-checking logic, or calling a method whose contract guarantees a non-null return for a known input. Overusing `!` defeats the purpose of nullable reference types. For a full explanation, see [Nullable reference types](nullable-reference-types.md).

## See also

<!-- Remove this HTML comment after dotnet/docs#55469 is merged and this branch is rebased.
- [Expressions overview](../expressions/index.md)
-->

- [Null safety overview](index.md)
- [Nullable value types](nullable-value-types.md)
- [Nullable reference types](nullable-reference-types.md)
- [Member access operators (language reference)](../../language-reference/operators/member-access-operators.md)
- [Null-coalescing operators (language reference)](../../language-reference/operators/null-coalescing-operator.md)
