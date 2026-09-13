---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/types/structs.md
title: C# structs
version: 0.0.0
fetched_at: 2026-09-13
---
# C# structs

> [!TIP]
> **New to developing software?** Start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first. You'll encounter structs once you need lightweight value types in your code.
>
> **Experienced in another language?** C# structs are value types similar to structs in C++ or Swift, but they live on the managed heap when boxed and support interfaces, constructors, and methods. Skim the [readonly structs](#readonly-structs-and-readonly-members) section for C#-specific patterns. For record structs, see [Records](records.md).

A *struct* is a value type that holds its data directly in the instance, rather than through a reference to an object on the heap. When you assign a struct to a new variable, the runtime copies the entire instance. Changes to one variable don't affect the other because each variable represents a different instance. Use structs for small, lightweight types whose primary role is storing data rather than modeling behavior. Examples include coordinates, colors, measurements, or configuration settings.

## When to use structs

Use a struct when your type:

- Represents a single value or a small group of related values (roughly 16 bytes or less).
- Has value semantics—two instances with the same data should be equal.
- Is primarily a data container rather than a model of behavior.
- Doesn't need inheritance from a base type (structs can't inherit from other structs or classes, but they can implement interfaces).

For a broader comparison that includes classes, records, tuples, and interfaces, see [Choose which kind of type](index.md#choose-which-kind-of-type).

## Declare a struct

Define a struct with the `struct` keyword. A struct can contain fields, properties, methods, and constructors, just like a class:

```csharp
struct Point
{
    public double X { get; set; }
    public double Y { get; set; }

    public readonly double DistanceTo(Point other)
    {
        var dx = X - other.X;
        var dy = Y - other.Y;
        return Math.Sqrt(dx * dx + dy * dy);
    }

    public override string ToString() => $"({X}, {Y})";
}
```

The `Point` struct stores two `double` values and provides a method to calculate the distance between two points. The `DistanceTo` method is marked `readonly` because it doesn't modify the struct's state. That pattern is covered in [readonly members](#readonly-structs-and-readonly-members).

## Value semantics

Structs are *value types*. Assignment copies the data, so each variable holds its own independent copy:

```csharp
var p1 = new Point { X = 3, Y = 4 };
var p2 = p1; // copies the data
p2.X = 10;

Console.WriteLine(p1); // (3, 4)  — p1 is unchanged
Console.WriteLine(p2); // (10, 4) — only p2 was modified
```

Because structs are data containers, assignment copies every data member into a new, independent instance. Each copy is distinct. Modifying one doesn't affect the other. This behavior differs from [classes](classes.md), where assignment copies only the reference and both variables share the same object. For more on the distinction, see [Value types and reference types](index.md#value-types-and-reference-types).

## Struct constructors

You can define constructors in structs the same way you do in classes. Structs can have *parameterless constructors* that set custom default values. The term "parameterless constructor" distinguishes an instance created with `new` (which runs your constructor logic) from a *default* instance created with the `default` expression (which zero-initializes all fields):

```csharp
struct ConnectionSettings
{
    public string Host { get; set; }
    public int Port { get; set; }
    public int MaxRetries { get; set; }

    public ConnectionSettings()
    {
        Host = "localhost";
        Port = 8080;
        MaxRetries = 3;
    }
}
```

A parameterless constructor runs when you use `new` with no arguments. The `default` expression bypasses the constructor and sets all fields to their default values (`0`, `null`, `false`). Be aware of the difference:

```csharp
var custom = new ConnectionSettings();
Console.WriteLine($"{custom.Host}:{custom.Port} (retries: {custom.MaxRetries})");
// localhost:8080 (retries: 3)

var defaults = default(ConnectionSettings);
Console.WriteLine($"{defaults.Host ?? "(null)"}:{defaults.Port} (retries: {defaults.MaxRetries})");
// (null):0 (retries: 0)
```

The compiler automatically initializes any fields you don't explicitly set in a constructor. You can initialize only the fields that need non-default values:

```csharp
struct GameTile
{
    public int Row { get; set; }
    public int Column { get; set; }
    public bool IsBlocked { get; set; }

    public GameTile(int row, int column)
    {
        Row = row;
        Column = column;
        // IsBlocked is automatically initialized to false
    }
}
```

The following example displays the default value for `IsBlocked`:

```csharp
var tile = new GameTile(2, 5);
Console.WriteLine($"Tile ({tile.Row}, {tile.Column}), blocked: {tile.IsBlocked}");
// Tile (2, 5), blocked: False
```

The `IsBlocked` property isn't assigned in the constructor, so the compiler sets it to `false` (the default for `bool`). This feature reduces boilerplate in constructors that only need to set a few fields.

## Readonly structs and readonly members

A `readonly struct` guarantees that no instance member modifies the struct's state. The compiler enforces this guarantee by requiring all fields and auto-implemented properties to be read-only:

```csharp
readonly struct Temperature
{
    public double Celsius { get; }

    public Temperature(double celsius) => Celsius = celsius;

    public double Fahrenheit => Celsius * 9.0 / 5.0 + 32.0;

    public override string ToString() => $"{Celsius:F1}°C ({Fahrenheit:F1}°F)";
}
```

The following example creates a `Temperature` instance and reads its properties:

```csharp
var temp = new Temperature(100);
Console.WriteLine(temp); // 100.0°C (212.0°F)
// temp.Celsius = 50; // Error: property is read-only
```

When you don't need the entire struct to be immutable, mark individual members as `readonly` instead. A `readonly` member can't modify the struct's state, and the compiler verifies that guarantee:

```csharp
struct Velocity
{
    public double X
    {
        readonly get;
        set;
    }

    public double Y
    {
        readonly get;
        set;
    }

    public readonly double Speed => Math.Sqrt(X * X + Y * Y);

    public readonly override string ToString() => $"({X}, {Y}) speed={Speed:F2}";
}
```

The following example shows that `readonly` members return updated values when mutable properties change:

```csharp
var v = new Velocity { X = 3, Y = 4 };
Console.WriteLine(v.Speed); // 5
Console.WriteLine(v);       // (3, 4) speed=5.00
v.X = 6;
Console.WriteLine(v.Speed); // 7.211...
```

Marking members `readonly` helps the compiler optimize defensive copies. When you pass a `readonly` struct to a method that accepts an `in` parameter, the compiler knows no copy is needed.

## See also

- [Type system overview](index.md)
- [Classes](classes.md)
- [Records](records.md)
- [Structure types (C# reference)](../../language-reference/builtin-types/struct.md)
