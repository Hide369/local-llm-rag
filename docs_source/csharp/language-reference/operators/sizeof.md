---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/sizeof.md
title: sizeof operator - determine the storage needs for a type
version: 0.0.0
fetched_at: 2026-09-13
---
# sizeof operator - determine the memory needs for a given type

The `sizeof` operator returns the number of bytes occupied by a variable of a given type. In safe code, the argument to the `sizeof` operator must be the name of a built-in [unmanaged type](../builtin-types/unmanaged-types.md) whose size isn't platform-dependent, or an [enumeration type](../builtin-types/enum.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The expressions presented in the following table are evaluated at compile time to the corresponding constant values and don't require an unsafe context:

| Expression        | Constant value |
|-------------------|----------------|
| `sizeof(sbyte)`   |  1             |
| `sizeof(byte)`    |  1             |
| `sizeof(short)`   |  2             |
| `sizeof(ushort)`  |  2             |
| `sizeof(int)`     |  4             |
| `sizeof(uint)`    |  4             |
| `sizeof(long)`    |  8             |
| `sizeof(ulong)`   |  8             |
| `sizeof(char)`    |  2             |
| `sizeof(float)`   |  4             |
| `sizeof(double)`  |  8             |
| `sizeof(decimal)` | 16             |
| `sizeof(bool)`    |  1             |

The size of the types in the preceding table is a compile-time constant.

For an enum type, the result of the `sizeof` operator is the size of the enum's underlying integral type. The result is computed at compile time.

In [unsafe](../keywords/unsafe.md) code, you can use `sizeof` on any non-`void` type, including types constructed from type parameters.

> [!NOTE]
> The [memory safety](../unsafe-code.md#the-updated-memory-safety-model-preview) preview feature available in C# 15 lets you use `sizeof` on any unmanaged type outside an `unsafe` context.

- The size of a reference or pointer type is the size of a reference or pointer, not the size of the object it might refer to.
- The size of a value type, unmanaged or not, is the size of such a value.
- The size of an enumeration type is the size of its underlying integral type. This size is a compile-time constant. If the underlying type of an enum defined in a referenced assembly later changes, code that applied `sizeof` to that enum must be recompiled to observe the new size.
- The size of a `ref struct` type is the size of the value. The size of every `ref` field is the size of a reference or pointer, not the size of the value it refers to.

The following example demonstrates the usage of the `sizeof` operator:

```csharp
public struct Point
{
    public Point(byte tag, double x, double y) => (Tag, X, Y) = (tag, x, y);

    public byte Tag { get; }
    public double X { get; }
    public double Y { get; }
}

public class SizeOfOperator
{
    public static void Main()
    {
        Console.WriteLine(sizeof(byte));  // output: 1
        Console.WriteLine(sizeof(double));  // output: 8

        DisplaySizeOf<Point>();  // output: Size of Point is 24
        DisplaySizeOf<decimal>();  // output: Size of System.Decimal is 16

        unsafe
        {
            Console.WriteLine(sizeof(Point*));  // output: 8
            Console.WriteLine(sizeof(nint));  // output: 8 on 64-bit, 4 on 32-bit
            Console.WriteLine(sizeof(nuint)); // output: 8 on 64-bit, 4 on 32-bit
            Console.WriteLine(sizeof(Span<int>));  // output: 16 on 64-bit, 12 on 32-bit
        }
    }

    static unsafe void DisplaySizeOf<T>() where T : unmanaged
    {
        Console.WriteLine($"Size of {typeof(T)} is {sizeof(T)}");
    }
}
```

The `sizeof` operator returns the number of bytes allocated by the common language runtime in managed memory. For [struct](../builtin-types/struct.md) types, that value includes any padding, as the preceding example demonstrates. The result of the `sizeof` operator might differ from the result of the <xref:System.Runtime.InteropServices.Marshal.SizeOf*?displayProperty=nameWithType> method, which returns the size of a type in *unmanaged* memory.

> [!IMPORTANT]
>
> The value returned by `sizeof` can differ from the result of <xref:System.Runtime.InteropServices.Marshal.SizeOf(System.Object)?displayProperty=nameWithType>, which returns the size of the type in unmanaged memory.

## C# language specification

For more information, see the [`sizeof` operator](~/_csharpstandard/standard/unsafe-code.md#2469-the-sizeof-operator) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
- [Pointer related operators](pointer-related-operators.md)
- [Pointer types](../unsafe-code.md#pointer-types)
- [Memory and span-related types](../../../standard/memory-and-spans/index.md)
- [Generics in .NET](../../../standard/generics/index.md)
