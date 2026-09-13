---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/statements/fixed.md
title: fixed statement - pin a moveable variable
version: 0.0.0
fetched_at: 2026-09-13
---
# fixed statement - pin a variable for pointer operations

The `fixed` statement prevents the [garbage collector](../../../standard/garbage-collection/index.md) from relocating a moveable variable and declares a pointer to that variable. The address of a fixed, or pinned, variable doesn't change during execution of the statement. You can use the declared pointer only inside the corresponding `fixed` statement. The declared pointer is readonly and can't be modified:

```csharp
unsafe
{
    byte[] bytes = [1, 2, 3];
    fixed (byte* pointerToFirst = bytes)
    {
        Console.WriteLine($"The address of the first array element: {(long)pointerToFirst:X}.");
        Console.WriteLine($"The value of the first array element: {*pointerToFirst}.");
    }
}
// Output is similar to:
// The address of the first array element: 2173F80B5C8.
// The value of the first array element: 1.
```

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

> [!NOTE]
> To use the `fixed` statement, compile the code with the [**AllowUnsafeBlocks**](../compiler-options/language.md#allowunsafeblocks) compiler option.
>
> The [memory safety](../unsafe-code.md#the-updated-memory-safety-model-preview) preview feature available in C# 15 feature lets you use `fixed` outside an `unsafe` context, but pointer indirection and other operations that access pinned memory still require an `unsafe` context.
You can initialize the declared pointer as follows:

- With an array, as the example at the beginning of this article shows. The initialized pointer contains the address of the first array element.
- With an address of a variable. Use the [address-of `&` operator](../operators/pointer-related-operators.md#address-of-operator-), as the following example shows:

```csharp
unsafe
{
    int[] numbers = [10, 20, 30];
    fixed (int* toFirst = &numbers[0], toLast = &numbers[^1])
    {
        Console.WriteLine(toLast - toFirst);  // output: 2
    }
}
```

  Object fields are another example of moveable variables that you can pin.

  When the initialized pointer contains the address of an object field or an array element, the `fixed` statement guarantees that the garbage collector doesn't relocate or dispose of the containing object instance during the execution of the statement body.

- With the instance of the type that implements a method named `GetPinnableReference`. That method must return a `ref` variable of an [unmanaged type](../builtin-types/unmanaged-types.md). The .NET types <xref:System.Span`1?displayProperty=nameWithType> and <xref:System.ReadOnlySpan`1?displayProperty=nameWithType> make use of this pattern. You can pin span instances, as the following example shows:

```csharp
unsafe
{
    int[] numbers = [10, 20, 30, 40, 50];
    Span<int> interior = numbers.AsSpan()[1..^1];
    fixed (int* p = interior)
    {
        for (int i = 0; i < interior.Length; i++)
        {
            Console.Write(p[i]);  
        }
        // output: 203040
    }
}
```

  For more information, see the <xref:System.Span`1.GetPinnableReference?displayProperty=nameWithType> API reference.

- With a string, as the following example shows:

```csharp
unsafe
{
    var message = "Hello!";
    fixed (char* p = message)
    {
        Console.WriteLine(*p);  // output: H
    }
}
```

- With a [fixed-size buffer](../unsafe-code.md#fixed-size-buffers).

You can allocate memory on the stack, where it's not subject to garbage collection and therefore doesn't need to be pinned. To do that, use a [`stackalloc` expression](../operators/stackalloc.md).

You can also use the `fixed` keyword to declare a [fixed-size buffer](../unsafe-code.md#fixed-size-buffers).

## C# language specification

For more information, see the following sections of the [C# language specification](~/_csharpstandard/standard/README.md):

- [The fixed statement](~/_csharpstandard/standard/unsafe-code.md#247-the-fixed-statement)
- [Fixed and moveable variables](~/_csharpstandard/standard/unsafe-code.md#244-fixed-and-moveable-variables)

## See also

- [Unsafe code, pointer types, and function pointers](../unsafe-code.md)
- [Pointer-related operators](../operators/pointer-related-operators.md)
- [unsafe](../keywords/unsafe.md)
