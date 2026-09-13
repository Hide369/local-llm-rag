---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/builtin-types/unmanaged-types.md
title: Unmanaged types
version: 0.0.0
fetched_at: 2026-09-13
---
# Unmanaged types (C# reference)

A type is an **unmanaged type** if it's any of the following types:

- `sbyte`, `byte`, `short`, `ushort`, `int`, `uint`, `long`, `ulong`, `nint`, `nuint`, `char`, `float`, `double`, `decimal`, or `bool`
- Any [enum](enum.md) type
- Any [pointer](../unsafe-code.md#pointer-types) type
- A [tuple](value-tuples.md) whose members are all of an unmanaged type
- Any user-defined [struct](struct.md) type that contains fields of unmanaged types only.

You can use the [`unmanaged` constraint](../../programming-guide/generics/constraints-on-type-parameters.md#unmanaged-constraint) to specify that a type parameter is a non-pointer, non-nullable unmanaged type.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

A *constructed* struct type that contains fields of unmanaged types only is also unmanaged, as the following example shows:

```csharp
using System;

public struct Coords<T>
{
    public T X;
    public T Y;
}

public class UnmanagedTypes
{
    public static void Main()
    {
        DisplaySize<Coords<int>>();
        DisplaySize<Coords<double>>();
    }

    private unsafe static void DisplaySize<T>() where T : unmanaged
    {
        Console.WriteLine($"{typeof(T)} is unmanaged and its size is {sizeof(T)} bytes");
    }
}
// Output:
// Coords`1[System.Int32] is unmanaged and its size is 8 bytes
// Coords`1[System.Double] is unmanaged and its size is 16 bytes
```

A generic struct can define both unmanaged and managed constructed types. The preceding example defines a generic struct `Coords<T>` and presents examples of unmanaged constructed types. The example of a managed type is `Coords<object>`. It's managed because it has the fields of the `object` type, which is managed. If you want *all* constructed types to be unmanaged types, use the `unmanaged` constraint in the definition of a generic struct:

```csharp
public struct Coords<T> where T : unmanaged
{
    public T X;
    public T Y;
}
```

## C# language specification

For more information, see the [Pointer types](~/_csharpstandard/standard/unsafe-code.md#243-pointer-types) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [Pointer types](../unsafe-code.md#pointer-types)
- [Memory and span-related types](../../../standard/memory-and-spans/index.md)
- [sizeof operator](../operators/sizeof.md)
- [stackalloc](../operators/stackalloc.md)
