---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/stackalloc.md
title: stackalloc expression - Allocate variable storage on the stack instead of the heap
version: 0.0.0
fetched_at: 2026-09-13
---
# stackalloc expression (C# reference)

A `stackalloc` expression allocates a block of memory on the stack. A stack-allocated memory block created during the method execution is automatically discarded when that method returns. You can't explicitly free the memory allocated by `stackalloc`. A stack-allocated memory block isn't subject to [garbage collection](../../../standard/garbage-collection/index.md) and doesn't need to be pinned by a [`fixed` statement](../statements/fixed.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

You can assign the result of a `stackalloc` expression to a variable of one of the following types:

- <xref:System.Span`1?displayProperty=nameWithType> or <xref:System.ReadOnlySpan`1?displayProperty=nameWithType>, as the following example shows:

```csharp
int length = 3;
Span<int> numbers = stackalloc int[length];
for (var i = 0; i < length; i++)
{
    numbers[i] = i;
}
```

  You don't need to use an [unsafe](../keywords/unsafe.md) context when you assign a stack-allocated memory block to a <xref:System.Span`1> or <xref:System.ReadOnlySpan`1> variable.

  When you work with those types, you can use a `stackalloc` expression in [conditional](conditional-operator.md) or assignment expressions, as the following example shows:

```csharp
int length = 1000;
Span<byte> buffer = length <= 1024 ? stackalloc byte[length] : new byte[length];
```

  You can use a `stackalloc` expression or a collection expression inside other expressions whenever a <xref:System.Span`1> or <xref:System.ReadOnlySpan`1> variable is allowed, as the following example shows:

```csharp
Span<int> numbers = stackalloc[] { 1, 2, 3, 4, 5, 6 };
var ind = numbers.IndexOfAny(stackalloc[] { 2, 4, 6, 8 });
Console.WriteLine(ind);  // output: 1

Span<int> numbers2 = [1, 2, 3, 4, 5, 6];
var ind2 = numbers2.IndexOfAny([2, 4, 6, 8]);
Console.WriteLine(ind2);  // output: 1
```

  > [!NOTE]
  > Use <xref:System.Span`1> or <xref:System.ReadOnlySpan`1> types to work with stack-allocated memory whenever possible.

- A [pointer type](../unsafe-code.md#pointer-types), as the following example shows:

```csharp
unsafe
{
    int length = 3;
    int* numbers = stackalloc int[length];
    for (var i = 0; i < length; i++)
    {
        numbers[i] = i;
    }
}
```

  You must use an `unsafe` context when you work with pointer types.

  > [!NOTE]
  > The [memory safety](../unsafe-code.md#the-updated-memory-safety-model-preview) preview feature available in C# 15 lets you convert a `stackalloc` expression to a pointer outside an `unsafe` context. Operations that access the allocated memory through the pointer still require an `unsafe` context.

  For pointer types, you can use a `stackalloc` expression only in a local variable declaration to initialize the variable.

The amount of memory available on the stack is limited. If you allocate too much memory on the stack, a <xref:System.StackOverflowException> is thrown. To avoid that exception, follow these rules:

- Limit the amount of memory you allocate by using `stackalloc`. For example, if the intended buffer size is below a certain limit, allocate the memory on the stack. Otherwise, use an array of the required length, as the following code shows:

```csharp
const int MaxStackLimit = 1024;
Span<byte> buffer = inputLength <= MaxStackLimit ? stackalloc byte[inputLength] : new byte[inputLength];
```

  > [!NOTE]
  > Because the amount of memory available on the stack depends on the environment in which the code runs, be conservative when you define the actual limit value.

- Avoid using `stackalloc` inside loops. Allocate the memory block outside a loop and reuse it inside the loop.

The content of the newly allocated memory is undefined. You should initialize it before it's used, either with a `stackalloc` initializer or a method like <xref:System.Span`1.Clear*?displayProperty=nameWithType>.

> [!IMPORTANT]
> Not initializing memory allocated by `stackalloc` is an important difference from the `new` operator. Memory allocated by using the `new` operator is initialized to the 0 bit pattern.

You can use array initializer syntax to define the content of the newly allocated memory. The following example demonstrates various ways to do that:

```csharp
Span<int> first = stackalloc int[3] { 1, 2, 3 };
Span<int> second = stackalloc int[] { 1, 2, 3 };
ReadOnlySpan<int> third = stackalloc[] { 1, 2, 3 };

// Using collection expressions:
Span<int> fourth = [1, 2, 3];
ReadOnlySpan<int> fifth = [1, 2, 3];
```

In expression `stackalloc T[E]`, `T` must be an [unmanaged type](../builtin-types/unmanaged-types.md) and `E` must evaluate to a non-negative [int](../builtin-types/integral-numeric-types.md) value. When you use the [collection expression](./collection-expressions.md) syntax to initialize the span, the compiler can use stack-allocated storage for a span if it doesn't violate ref safety.

## Security

Using `stackalloc` automatically turns on buffer overrun detection features in the common language runtime (CLR). If the runtime detects a buffer overrun, it terminates the process as quickly as possible to reduce the chance that malicious code runs.

## C# language specification

For more information, see the [Stack allocation](~/_csharpstandard/standard/unsafe-code.md#249-stack-allocation) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
- [Pointer related operators](pointer-related-operators.md)
- [Pointer types](../unsafe-code.md#pointer-types)
- [Memory and span-related types](../../../standard/memory-and-spans/index.md)
- [Dos and Don'ts of stackalloc](https://vcsjones.dev/2020/02/24/stackalloc/)
