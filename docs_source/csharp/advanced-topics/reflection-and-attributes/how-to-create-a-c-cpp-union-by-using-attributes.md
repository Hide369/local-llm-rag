---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/advanced-topics/reflection-and-attributes/how-to-create-a-c-cpp-union-by-using-attributes.md
title: How to create a C/C++ union by using attributes
version: 0.0.0
fetched_at: 2026-09-13
---
# How to create a C/C++ union by using attributes in C\#

By using attributes, you can customize how structs are laid out in memory. For example, you can create what is known as a union in C/C++ by using the `StructLayout(LayoutKind.Explicit)` and `FieldOffset` attributes.

In this code segment, all of the fields of `TestUnion` start at the same location in memory.

```csharp
[System.Runtime.InteropServices.StructLayout(LayoutKind.Explicit)]
struct TestUnion
{
    [System.Runtime.InteropServices.FieldOffset(0)]
    public int i;

    [System.Runtime.InteropServices.FieldOffset(0)]
    public double d;

    [System.Runtime.InteropServices.FieldOffset(0)]
    public char c;

    [System.Runtime.InteropServices.FieldOffset(0)]
    public byte b;
}
```

The following code is another example where fields start at different explicitly set locations.

```csharp
[System.Runtime.InteropServices.StructLayout(LayoutKind.Explicit)]
struct TestExplicit
{
    [System.Runtime.InteropServices.FieldOffset(0)]
    public long lg;

    [System.Runtime.InteropServices.FieldOffset(0)]
    public int i1;

    [System.Runtime.InteropServices.FieldOffset(4)]
    public int i2;

    [System.Runtime.InteropServices.FieldOffset(8)]
    public double d;

    [System.Runtime.InteropServices.FieldOffset(12)]
    public char c;

    [System.Runtime.InteropServices.FieldOffset(14)]
    public byte b;
}
```

The two integer fields, `i1` and `i2` combined, share the same memory locations as `lg`. Either `lg` uses the first 8 bytes, or `i1` uses the first 4 bytes and `i2` uses the next 4 bytes. This sort of control over struct layout is useful when using platform invocation.

## See also

- <xref:System.Reflection>
- <xref:System.Attribute>
- [Attributes](../../../standard/attributes/index.md)
