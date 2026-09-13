---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/value.md
title: The `value` implicit parameter
version: 0.0.0
fetched_at: 2026-09-13
---
# The `value` implicit parameter

The `set` accessor in [property](../../programming-guide/classes-and-structs/properties.md) and [indexer](../../programming-guide/indexers/index.md) declarations uses the implicit parameter `value`. This parameter acts as an input for the method. The word `value` refers to the value that client code tries to assign to the property or indexer.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

In the following example, `TimePeriod2` has a property named `Seconds` that uses the `value` parameter to assign a new string to the backing field `_seconds`. From the point of view of client code, the operation is written as a simple assignment.

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

For more information, see the [Properties](../../programming-guide/classes-and-structs/properties.md) and [Indexers](../../programming-guide/indexers/index.md) articles.

## C# language specification

[!INCLUDE[CSharplangspec](~/includes/csharplangspec-md.md)]
