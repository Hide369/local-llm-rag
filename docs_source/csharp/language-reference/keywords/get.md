---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/get.md
title: The get keyword: property accessor
version: 0.0.0
fetched_at: 2026-09-13
---
# The `get` keyword

The `get` keyword defines an *accessor* method in a property or indexer that returns the property value or the indexer element. For more information, see [Properties](../../programming-guide/classes-and-structs/properties.md), [Automatically implemented Properties](../../programming-guide/classes-and-structs/auto-implemented-properties.md), and [Indexers](../../programming-guide/indexers/index.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

For simple cases where a property's `get` and `set` accessors perform no other operation than setting or retrieving a value in a private backing field, take advantage of the C# compiler's support for automatically implemented properties. The following example implements `Hours` as an automatically implemented property.

```csharp
class TimePeriod3
{
    public double Hours { get; set; }
}
```

> [!IMPORTANT]
> You can't use automatically implemented properties for [interface property declarations](../../programming-guide/classes-and-structs/interface-properties.md) or the implementing declaration for a [partial property](./partial-member.md). The compiler interprets syntax matching an automatically implemented property as the declaring declaration, not an implementing declaration.

Often, the `get` accessor consists of a single statement that returns a value, as it did in the previous example. You can implement the `get` accessor as an expression-bodied member. The following example implements both the `get` and the `set` accessor as expression-bodied members.

```csharp
class TimePeriod2
{
    private double _seconds;

    public double Seconds
    {
        get => _seconds;
        set => _seconds = value;
    }
}
```

You might find that you need to implement one of the accessor bodies. Use a field backed property to let the compiler generate one accessor while you write the other by hand. Use the `field` keyword, added in C# 14, to access the compiler synthesized backing field:

```csharp
class TimePeriod4
{
    public double Hours {
        get;
        set => field = (value >= 0)
            ? value
            : throw new ArgumentOutOfRangeException(nameof(value), "The value must not be negative");
    }
}
```

The following example defines both a `get` and a `set` accessor for a property named `Seconds`. It uses a private field named `_seconds` to back the property value.

```csharp
class TimePeriod
{
    private double _seconds;

    public double Seconds
    {
        get { return _seconds; }
        set
        {
            if (value < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(value), "The value of the time period must be non-negative.");
            }
            _seconds = value;
        }
    }
}
```

## C# Language Specification

[!INCLUDE[CSharplangspec](~/includes/csharplangspec-md.md)]

## See also

- [C# Keywords](./index.md)
- [Properties](../../programming-guide/classes-and-structs/properties.md)
