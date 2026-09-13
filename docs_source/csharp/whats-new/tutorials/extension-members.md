---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/whats-new/tutorials/extension-members.md
title: Explore extension members in C# 14 and C# 15 to enhance existing types
version: 0.0.0
fetched_at: 2026-09-13
---
# Tutorial: Explore extension members in C# 14 and C# 15

C# 14 introduced extension members, an enhancement to the existing extension methods. Extension members enable you to add properties and operators. You can also extend types as well as instances of types. C# 15 adds extension indexers, so an existing type can support indexed access from an extension block.

In this tutorial, you explore extension members by enhancing the `System.Drawing.Point` type with mathematical operations, coordinate transformations, and utility properties. Then you add indexed access to a `Path` type that stores point-to-point offsets. You learn how to migrate existing extension methods to the new extension member syntax and when each approach fits.

In this tutorial, you:

> [!div class="checklist"]
>
> * Create C# 14 extension members with static properties and operators.
> * Implement coordinate transformations using extension members.
> * Migrate traditional extension methods to extension member syntax.
> * Add a C# 15 extension indexer that reads and updates absolute points in a path.
> * Compare extension members with traditional extension methods.

## Prerequisites

- The .NET 11 preview SDK. Download it from the [.NET download site](https://dotnet.microsoft.com/download/dotnet/11.0).
- Visual Studio 2026 with preview features enabled. Download it from the [Visual Studio page](https://visualstudio.microsoft.com).
- This sample sets `<LangVersion>preview</LangVersion>` because extension indexers are a C# 15 preview feature.

## Create the sample application

Start by creating a console application that demonstrates both traditional extension methods and the new extension members syntax. You create extensions for the <xref:System.Drawing.Point?displayProperty=fullName> type. This type comes from the `System.Drawing` namespace and is typically used in Windows Forms applications.

1. Create a new console application.

   ```dotnetcli
   dotnet new console -n PointExtensions
   cd PointExtensions
   ```

1. Update the project file so the sample targets .NET 11 and uses preview language features:

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net11.0</TargetFramework>
    <LangVersion>preview</LangVersion>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

</Project>
```

1. Copy the following code into a new file named `ExtensionMethods.cs`:

```csharp
using System.Drawing;
using System.Numerics;

namespace ExtensionMethods;

public static class PointExtensions
{
    public static Vector2 ToVector(this Point point) =>
        new Vector2(point.X, point.Y);

    public static void Translate(this ref Point point, int xDist, int yDist)
    {
        point.X += xDist;
        point.Y += yDist;
    }

    public static void Scale(this ref Point point, int xScale, int yScale)
    {
        point.X *= xScale;
        point.Y *= yScale;
    }

    public static void Rotate(this ref Point point, int angleInDegrees)
    {
        double theta = ((double)angleInDegrees * Math.PI) / 180.0;
        double sinTheta = Math.Sin(theta);
        double cosTheta = Math.Cos(theta);
        double newX = (double)point.X * cosTheta - (double)point.Y * sinTheta;
        double newY = (double)point.X * sinTheta + (double)point.Y * cosTheta;
        point.X = (int)newX;
        point.Y = (int)newY;
    }
}
```

1. Copy the following code that demonstrates these extension methods and other uses of the <xref:System.Drawing.Point?displayProperty=nameWithType>:

```csharp
using System.Drawing;
using System.Numerics;
using ExtensionMethods;

public static class ExtensionMethodsDemonstrations
{
    public static void TraditionalExtensionMethods()
    {
        OriginAsADataElement();
        ArithmeticWithPoints();
        DiscreteArithmeticWithPoints();
        ExtensionMethodsThis();
        MoreExamples();
    }

    static void OriginAsADataElement()
    {
        // Inline implementation since Point.Origin doesn't exist in ExtensionMethods
        Point origin = Point.Empty; // Equivalent to Point.Origin
        Console.WriteLine($"Point.Origin (inline): {origin}");
        Console.WriteLine($"Same as Point.Empty: {origin == Point.Empty}");
        Console.WriteLine();
    }

    static void ArithmeticWithPoints()
    {
        Point p1 = new Point(5, 3);
        Point p2 = new Point(2, 7);

        Console.WriteLine($"Point 1: {p1}");
        Console.WriteLine($"Point 2: {p2}");
        
        // Inline implementation since + and - operators don't exist in ExtensionMethods
        Point addition = new Point(p1.X + p2.X, p1.Y + p2.Y);
        Point subtraction1 = new Point(p1.X - p2.X, p1.Y - p2.Y);
        Point subtraction2 = new Point(p2.X - p1.X, p2.Y - p1.Y);
        
        Console.WriteLine($"Addition (p1 + p2): {addition}");
        Console.WriteLine($"Subtraction (p1 - p2): {subtraction1}");
        Console.WriteLine($"Subtraction (p2 - p1): {subtraction2}");
        Console.WriteLine();
    }

    static void DiscreteArithmeticWithPoints()
    {
        Point point = new Point(10, 8);
        int offsetX = 3;
        int offsetY = -2;
        int scaleX = 2;
        int scaleY = 3;
        int divisorX = 2;
        int divisorY = 4;

        Console.WriteLine($"Original point: {point}");
        Console.WriteLine($"Offset: ({offsetX}, {offsetY})");
        Console.WriteLine($"Scale: ({scaleX}, {scaleY})");
        Console.WriteLine($"Divisor: ({divisorX}, {divisorY})");
        Console.WriteLine();

        // Inline implementations since tuple operators don't exist in ExtensionMethods
        Point addedOffset = new Point(point.X + offsetX, point.Y + offsetY);
        Point subtractedOffset = new Point(point.X - offsetX, point.Y - offsetY);
        Point scaledPoint = new Point(point.X * scaleX, point.Y * scaleY);
        Point dividedPoint = new Point(point.X / divisorX, point.Y / divisorY);

        Console.WriteLine($"point + offset: {addedOffset}");
        Console.WriteLine($"point - offset: {subtractedOffset}");
        Console.WriteLine($"point * scale: {scaledPoint}");
        Console.WriteLine($"point / divisor: {dividedPoint}");
        Console.WriteLine();
    }

    static void ExtensionMethodsThis()
    {
        // ToVector demonstration - using extension method
        Point vectorPoint = new Point(12, 16);
        Vector2 vector = vectorPoint.ToVector();
        Console.WriteLine($"Point {vectorPoint} as Vector2: {vector}");
        Console.WriteLine();

        // Translate demonstration - using extension method
        Point translatePoint = new Point(5, 5);
        Console.WriteLine($"Before Translate: {translatePoint}");
        translatePoint.Translate(3, -2);
        Console.WriteLine($"After Translate(3, -2): {translatePoint}");
        Console.WriteLine();

        // Scale demonstration - using extension method
        Point scalePoint = new Point(4, 6);
        Console.WriteLine($"Before Scale: {scalePoint}");
        scalePoint.Scale(2, 3);
        Console.WriteLine($"After Scale(2, 3): {scalePoint}");
        Console.WriteLine();

        // Rotate demonstration - using extension method
        Point rotatePoint1 = new Point(10, 0);
        Console.WriteLine($"Before Rotate: {rotatePoint1}");
        rotatePoint1.Rotate(90);
        Console.WriteLine($"After Rotate(90°): {rotatePoint1}");

        Point rotatePoint2 = new Point(5, 5);
        Console.WriteLine($"Before Rotate: {rotatePoint2}");
        rotatePoint2.Rotate(45);
        Console.WriteLine($"After Rotate(45°): {rotatePoint2}");

        Point rotatePoint3 = new Point(3, 4);
        Console.WriteLine($"Before Rotate: {rotatePoint3}");
        rotatePoint3.Rotate(180);
        Console.WriteLine($"After Rotate(180°): {rotatePoint3}");
        Console.WriteLine();
    }

    static void MoreExamples()
    {
        // Combining operators and methods
        Console.WriteLine("Scenario 1: Building a rectangle using inline operators");
        Point topLeft = Point.Empty; // Inline equivalent of Point.Origin
        Point bottomRight = new Point(topLeft.X + 10, topLeft.Y + 8); // Inline addition
        Point topRight = new Point(bottomRight.X, topLeft.Y);
        Point bottomLeft = new Point(topLeft.X, bottomRight.Y);

        Console.WriteLine($"Rectangle corners:");
        Console.WriteLine($"  Top-Left: {topLeft}");
        Console.WriteLine($"  Top-Right: {topRight}");
        Console.WriteLine($"  Bottom-Left: {bottomLeft}");
        Console.WriteLine($"  Bottom-Right: {bottomRight}");
        Console.WriteLine();

        // Transformation chain
        Console.WriteLine("Scenario 2: Transformation chain (mixed methods)");
        Point transformPoint = new Point(2, 3);
        Console.WriteLine($"Starting point: {transformPoint}");

        // Scale up - using extension method
        transformPoint.Scale(3, 2);
        Console.WriteLine($"After scaling by (3, 2): {transformPoint}");

        // Translate - using inline addition
        transformPoint = new Point(transformPoint.X + 5, transformPoint.Y + (-3));
        Console.WriteLine($"After translating by (5, -3): {transformPoint}");

        // Rotate - using extension method
        transformPoint.Rotate(45);
        Console.WriteLine($"After rotating 45�: {transformPoint}");

        // Convert to vector - using extension method
        Vector2 finalVector = transformPoint.ToVector();
        Console.WriteLine($"Final result as Vector2: {finalVector}");
        Console.WriteLine();

        // Distance calculation using inline operators and extension methods
        Console.WriteLine("Scenario 3: Distance calculation (mixed methods)");
        Point point1 = new Point(1, 1);
        Point point2 = new Point(4, 5);
        Point difference = new Point(point2.X - point1.X, point2.Y - point1.Y); // Inline subtraction
        Vector2 diffVector = difference.ToVector(); // Extension method
        float distance = diffVector.Length();

        Console.WriteLine($"Point 1: {point1}");
        Console.WriteLine($"Point 2: {point2}");
        Console.WriteLine($"Difference: {difference}");
        Console.WriteLine($"Distance: {distance:F2}");
        Console.WriteLine();

        Console.WriteLine("Traditional extension methods demonstration complete!");
    }
}
```

1. Replace the content of `Program.cs` with the demonstration code:

```csharp
ExtensionMethodsDemonstrations.TraditionalExtensionMethods();
```

1. Run the sample application and examine the output.

Traditional extension methods can only add instance methods to existing types. Extension members enable you to add static properties, which provides a more natural way to extend types with constants or computed values.

## Add static properties with extension members

First, examine this code in the sample:

```csharp
// Inline implementation since Point.Origin doesn't exist in ExtensionMethods
Point origin = Point.Empty; // Equivalent to Point.Origin
Console.WriteLine($"Point.Origin (inline): {origin}");
Console.WriteLine($"Same as Point.Empty: {origin == Point.Empty}");
Console.WriteLine();
```

Many apps that use 2D geometry use the concept of an `Origin`, which is the same value as <xref:System.Drawing.Point.Empty?displayProperty=nameWithType>. This code uses that fact, but some developers might create a `new Point(0,0)`, which incurs some extra work. In a given domain, you want to express these common values through static properties.

Create `NewExtensionsMembers.cs` to create extension members that solve this problem:

```csharp
using System.Drawing;
using System.Numerics;

namespace ExtensionMembers;

public static class PointExtensions
{
    extension (Point)
    {
        public static Point Origin => Point.Empty;
    }
}
```

The preceding code adds a static *extension property* to the `Point` struct. The `extension` keyword introduces an *extension block*. This extension block extends the `Point` struct.

You can use this static property as though it were a member of the `Point` struct.

```csharp
Console.WriteLine("1. Static Properties");
Console.WriteLine("-------------------");

Point origin = Point.Origin;
Console.WriteLine($"Point.Origin: {origin}");
Console.WriteLine($"Same as Point.Empty: {origin == Point.Empty}");
Console.WriteLine();
```

The `Point.Origin` property now appears as if it were part of the original `Point` type, providing a more intuitive API.

## Implement arithmetic operators

Next, examine the following code that performs arithmetic with points:

```csharp
Point p1 = new Point(5, 3);
Point p2 = new Point(2, 7);

Console.WriteLine($"Point 1: {p1}");
Console.WriteLine($"Point 2: {p2}");

// Inline implementation since + and - operators don't exist in ExtensionMethods
Point addition = new Point(p1.X + p2.X, p1.Y + p2.Y);
Point subtraction1 = new Point(p1.X - p2.X, p1.Y - p2.Y);
Point subtraction2 = new Point(p2.X - p1.X, p2.Y - p1.Y);

Console.WriteLine($"Addition (p1 + p2): {addition}");
Console.WriteLine($"Subtraction (p1 - p2): {subtraction1}");
Console.WriteLine($"Subtraction (p2 - p1): {subtraction2}");
Console.WriteLine();
```

Traditional extension methods can't add operators to existing types. You must implement arithmetic operations manually, which makes the code verbose and harder to read. The algorithm gets duplicated whenever you need the operation, which creates more opportunities for small mistakes to enter the code base. It's better to place that code in one location. Add the following operators to your extension block in `NewExtensionsMembers.cs`:

```csharp
public static Point operator +(Point left, Point right) =>
    new Point(left.X + right.X, left.Y + right.Y);

public static Point operator -(Point left, Point right) =>
    new Point(left.X - right.X, left.Y - right.Y);
```

By using extension members, you can add operators directly to existing types. Now you can perform arithmetic operations by using natural syntax:

```csharp
Console.WriteLine("2. Arithmetic Operators (Point + Point, Point - Point)");
Console.WriteLine("-----------------------------------------------------");

Point p1 = new Point(5, 3);
Point p2 = new Point(2, 7);

Console.WriteLine($"Point 1: {p1}");
Console.WriteLine($"Point 2: {p2}");
Console.WriteLine($"Addition (p1 + p2): {p1 + p2}");
Console.WriteLine($"Subtraction (p1 - p2): {p1 - p2}");
Console.WriteLine($"Subtraction (p2 - p1): {p2 - p1}");
Console.WriteLine();
```

The extension operators make point arithmetic as natural as working with built-in numeric types.

## Add more operators

You can also add extension operators for the discrete operations shown in the following code example:

```csharp
Point point = new Point(10, 8);
int offsetX = 3;
int offsetY = -2;
int scaleX = 2;
int scaleY = 3;
int divisorX = 2;
int divisorY = 4;

Console.WriteLine($"Original point: {point}");
Console.WriteLine($"Offset: ({offsetX}, {offsetY})");
Console.WriteLine($"Scale: ({scaleX}, {scaleY})");
Console.WriteLine($"Divisor: ({divisorX}, {divisorY})");
Console.WriteLine();

// Inline implementations since tuple operators don't exist in ExtensionMethods
Point addedOffset = new Point(point.X + offsetX, point.Y + offsetY);
Point subtractedOffset = new Point(point.X - offsetX, point.Y - offsetY);
Point scaledPoint = new Point(point.X * scaleX, point.Y * scaleY);
Point dividedPoint = new Point(point.X / divisorX, point.Y / divisorY);

Console.WriteLine($"point + offset: {addedOffset}");
Console.WriteLine($"point - offset: {subtractedOffset}");
Console.WriteLine($"point * scale: {scaledPoint}");
Console.WriteLine($"point / divisor: {dividedPoint}");
Console.WriteLine();
```

The `+` and `-` operators are *binary operators* and require two operands, not three. Instead of two discrete integers, use a *tuple* to specify both the `X` and `Y` deltas:

```csharp
public static Point operator *(Point left, (int dx, int dy) scale) =>
    new Point(left.X * scale.dx, left.Y * scale.dy);
public static Point operator /(Point left, (int dx, int dy) scale) =>
    new Point(left.X / scale.dx, left.Y / scale.dy);
public static Point operator +(Point left, (int dx, int dy) scale) =>
    new Point(left.X + scale.dx, left.Y + scale.dy);
public static Point operator -(Point left, (int dx, int dy) scale) =>
    new Point(left.X - scale.dx, left.Y - scale.dy);
```

The preceding operator enables elegant tuple-based operations:

```csharp
Console.WriteLine("3. Discrete Operators using tuples (Point with (int, int))");
Console.WriteLine("------------------------------------------");

Point point = new Point(10, 8);
var offset = (3, -2);
var scale = (2, 3);
var divisor = (2, 4);

Console.WriteLine($"Original point: {point}");
Console.WriteLine($"Offset tuple: {offset}");
Console.WriteLine($"Scale tuple: {scale}");
Console.WriteLine($"Divisor tuple: {divisor}");
Console.WriteLine();

Console.WriteLine($"point + offset: {point + offset}");
Console.WriteLine($"point - offset: {point - offset}");
Console.WriteLine($"point * scale: {point * scale}");
Console.WriteLine($"point / divisor: {point / divisor}");
Console.WriteLine();
```

Your extensions can include multiple overloaded operators, as long as the operands are distinct.

## Migrate instance methods to extension members

Extension members also support instance methods. You don't have to change existing extension methods. The old and new forms are binary and source compatible. If you want to keep all your extensions in one container, you can. Migrating traditional extension methods to the new syntax maintains the same functionality.

### Traditional extension methods

The traditional approach uses the `this` parameter syntax:

```csharp
public static Vector2 ToVector(this Point point) =>
    new Vector2(point.X, point.Y);

public static void Translate(this Point point, int xDist, int yDist)
{
    point.X += xDist;
    point.Y += yDist;
}

public static void Scale(this Point point, int xScale, int yScale)
{
    point.X *= xScale;
    point.Y *= yScale;
}

public static void Rotate(this Point point, int angleInDegress)
{
    double theta = ((double)angleInDegress * Math.PI) / 180.0;
    double sinTheta = Math.Sin(theta);
    double cosTheta = Math.Cos(theta);
    double newX = (double)point.X * cosTheta - (double)point.Y * sinTheta;
    double newY = (double)point.X * sinTheta + (double)point.Y * cosTheta;
    point.X = (int)newX;
    point.Y = (int)newY;
}
```

Extension members use a different syntax but provide the same functionality. Add the following code to your new extension members class:

```csharp
public Vector2 ToVector() =>
    new Vector2(point.X, point.Y);

public void Translate(int xDist, int yDist)
{
    point.X += xDist;
    point.Y += yDist;
}

public void Scale(int xScale, int yScale)
{
    point.X *= xScale;
    point.Y *= yScale;
}

public void Rotate(int angleInDegrees)
{
    double theta = ((double)angleInDegrees * Math.PI) / 180.0;
    double sinTheta = Math.Sin(theta);
    double cosTheta = Math.Cos(theta);
    double newX = (double)point.X * cosTheta - (double)point.Y * sinTheta;
    double newY = (double)point.X * sinTheta + (double)point.Y * cosTheta;
    point.X = (int)newX;
    point.Y = (int)newY;
}
```

These methods extend an instance of the `Point` struct, not the `Point` type. The extension block names the receiver parameter so the method body can read that point. The sample uses `extension(ref Point point)` because `Translate`, `Scale`, and `Rotate` change the caller's `Point`. Without `ref`, those methods would update a copy of the struct, and the caller wouldn't see the change.

You can call these new instance methods exactly as you accessed traditional extension methods:

```csharp
Console.WriteLine("4. Instance Methods");
Console.WriteLine("------------------");

// ToVector demonstration
Point vectorPoint = new Point(12, 16);
Vector2 vector = vectorPoint.ToVector();
Console.WriteLine($"Point {vectorPoint} as Vector2: {vector}");
Console.WriteLine();

// Translate demonstration
Point translatePoint = new Point(5, 5);
Console.WriteLine($"Before Translate: {translatePoint}");
translatePoint.Translate(3, -2);
Console.WriteLine($"After Translate(3, -2): {translatePoint}");
Console.WriteLine();

// Scale demonstration
Point scalePoint = new Point(4, 6);
Console.WriteLine($"Before Scale: {scalePoint}");
scalePoint.Scale(2, 3);
Console.WriteLine($"After Scale(2, 3): {scalePoint}");
Console.WriteLine();

// Rotate demonstration
Point rotatePoint1 = new Point(10, 0);
Console.WriteLine($"Before Rotate: {rotatePoint1}");
rotatePoint1.Rotate(90);
Console.WriteLine($"After Rotate(90°): {rotatePoint1}");

Point rotatePoint2 = new Point(5, 5);
Console.WriteLine($"Before Rotate: {rotatePoint2}");
rotatePoint2.Rotate(45);
Console.WriteLine($"After Rotate(45°): {rotatePoint2}");

Point rotatePoint3 = new Point(3, 4);
Console.WriteLine($"Before Rotate: {rotatePoint3}");
rotatePoint3.Rotate(180);
Console.WriteLine($"After Rotate(180°): {rotatePoint3}");
Console.WriteLine();
```

The key difference is syntax: extension members use `extension (Type variableName)` instead of `this Type variableName`.

## Add extension indexers

C# 15 adds indexers to `extension` blocks. An indexer has no name. Code accesses it with `this[...]` in the declaration and with indexed syntax at the call site.

Imagine a path type that stores each step as a relative offset. When you ask for `path[i]`, you want the absolute point at that step. When you assign `path[i] = target`, you want the type to update the one offset that gets you there. Indexed access reads like "the point at this step" and keeps the offset-to-point math in one place.

Imagine that `Path` came from a library. If you don't own the type, you can't add an indexer to its source. Before C# 15, you could add methods, but you couldn't add `this[...]` indexed access to a type you don't control. This tutorial defines `Path` so the sample is runnable; think of it as standing in for that library type.

For this section, add a `Path` type. The type stores a sequence of `(dX, dY)` offsets. Each offset says how far to move from the previous point. The first offset starts at `Point.Origin`, the static extension property you added earlier.

Create a new file named `Path.cs` in the same project as the other sample files. Add the `Path` type to the `ExtensionMembers` namespace in that file. Keeping `Path` in this namespace makes it your sample type, not <xref:System.IO.Path>. The demo file uses a `using Path = ExtensionMembers.Path;` alias, so every `Path` in the demo means the sample path type.

```csharp
public sealed class Path
{
    private readonly List<(int dX, int dY)> offsets = [];

    public Path(IEnumerable<(int dX, int dY)> offsets)
    {
        this.offsets.AddRange(offsets);
    }

    public int Count => offsets.Count;

    internal (int dX, int dY) GetOffset(int index) => offsets[index];

    internal void SetOffset(int index, (int dX, int dY) offset) =>
        offsets[index] = offset;
}
```

Now add an indexer for `Path`. Put this code in the existing `PointExtensions` static class in `NewExtensionsMembers.cs`. Add it as a new `extension(Path path)` block, separate from the `extension(Point)` block for static members and operators and separate from the `extension(ref Point point)` block for instance methods:

```csharp
extension(Path path)
{
    public Point this[int index]
    {
        get
        {
            ValidatePathIndex(path, index);

            Point absolutePoint = Point.Origin;
            for (int current = 0; current <= index; current++)
            {
                var offset = path.GetOffset(current);
                absolutePoint += offset;
            }

            return absolutePoint;
        }
        set
        {
            ValidatePathIndex(path, index);

            Point previousPoint = Point.Origin;
            for (int current = 0; current < index; current++)
            {
                var offset = path.GetOffset(current);
                previousPoint += offset;
            }

            path.SetOffset(index, (value.X - previousPoint.X, value.Y - previousPoint.Y));
        }
    }
}

private static void ValidatePathIndex(Path path, int index)
{
    if (index < 0 || index >= path.Count)
    {
        throw new ArgumentOutOfRangeException(nameof(index), index,
            "Index must refer to an offset in the path.");
    }
}
```

Indexers are always instance members, so this new extension block must name the receiver: `extension(Path path)`. A block written as `extension(Path)` wouldn't provide a `path` variable for the indexer body.

`Path` is a class that owns a list of offsets. The indexer doesn't need a `ref` receiver because the setter changes the contents of that existing `Path` object.

The getter starts at `Point.Origin`, then adds the offsets from index `0` through the requested index. With offsets `(2, 3)`, `(1, 1)`, and `(-1, 4)`, the absolute points are `(2, 3)`, `(3, 4)`, and `(2, 8)`.

The setter receives a target absolute point. It leaves earlier offsets alone and changes only the offset at the requested index. The new offset is the target point minus the absolute point at the previous index. Later points shift because they remain relative to the changed offset.

Now, use the indexer to read and write points along the path:

```csharp
Console.WriteLine("5. Path Indexer");
Console.WriteLine("---------------");

Path path = new([(dX: 2, dY: 3), (dX: 1, dY: 1), (dX: -1, dY: 4)]);
Console.WriteLine($"First point: {path[0]}");
Console.WriteLine($"Second point: {path[1]}");
Console.WriteLine($"Third point: {path[2]}");

path[1] = new Point(10, 10);
Console.WriteLine("After setting the second point to {X=10,Y=10}:");
Console.WriteLine($"Second point: {path[1]}");
Console.WriteLine($"Third point: {path[2]}");
Console.WriteLine();
```

Both accessors share a small private `ValidatePathIndex` helper in the same `PointExtensions` class that bounds-checks the index and throws <xref:System.ArgumentOutOfRangeException> when it doesn't refer to an offset in the path.

## Completed sample

The final example shows the advantages when you combine static properties, operators, instance methods, and an indexer to create comprehensive type extensions.

Compare the extension member version:

```csharp
Console.WriteLine("6. Complex Scenarios");
Console.WriteLine("-------------------");

// Combining operators and methods
Console.WriteLine("Scenario 1: Building a rectangle using operators");
Point topLeft = Point.Origin;
Point bottomRight = topLeft + (10, 8);
Point topRight = new Point(bottomRight.X, topLeft.Y);
Point bottomLeft = new Point(topLeft.X, bottomRight.Y);

Console.WriteLine($"Rectangle corners:");
Console.WriteLine($"  Top-Left: {topLeft}");
Console.WriteLine($"  Top-Right: {topRight}");
Console.WriteLine($"  Bottom-Left: {bottomLeft}");
Console.WriteLine($"  Bottom-Right: {bottomRight}");
Console.WriteLine();

// Transformation chain
Console.WriteLine("Scenario 2: Transformation chain");
Point transformPoint = new Point(2, 3);
Console.WriteLine($"Starting point: {transformPoint}");

// Scale up
transformPoint.Scale(3, 2);
Console.WriteLine($"After scaling by (3, 2): {transformPoint}");

// Translate
transformPoint = transformPoint + (5, -3);
Console.WriteLine($"After translating by (5, -3): {transformPoint}");

// Rotate
transformPoint.Rotate(45);
Console.WriteLine($"After rotating 45°: {transformPoint}");

// Convert to vector
Vector2 finalVector = transformPoint.ToVector();
Console.WriteLine($"Final result as Vector2: {finalVector}");
Console.WriteLine();

// Distance calculation using operators
Console.WriteLine("Scenario 3: Distance calculation");
Point point1 = new Point(1, 1);
Point point2 = new Point(4, 5);
Point difference = point2 - point1;
Vector2 diffVector = difference.ToVector();
float distance = diffVector.Length();

Console.WriteLine($"Point 1: {point1}");
Console.WriteLine($"Point 2: {point2}");
Console.WriteLine($"Difference: {difference}");
Console.WriteLine($"Distance: {distance:F2}");
Console.WriteLine();

Console.WriteLine("Demonstration complete!");
```

With the previous version:

```csharp
// Combining operators and methods
Console.WriteLine("Scenario 1: Building a rectangle using inline operators");
Point topLeft = Point.Empty; // Inline equivalent of Point.Origin
Point bottomRight = new Point(topLeft.X + 10, topLeft.Y + 8); // Inline addition
Point topRight = new Point(bottomRight.X, topLeft.Y);
Point bottomLeft = new Point(topLeft.X, bottomRight.Y);

Console.WriteLine($"Rectangle corners:");
Console.WriteLine($"  Top-Left: {topLeft}");
Console.WriteLine($"  Top-Right: {topRight}");
Console.WriteLine($"  Bottom-Left: {bottomLeft}");
Console.WriteLine($"  Bottom-Right: {bottomRight}");
Console.WriteLine();

// Transformation chain
Console.WriteLine("Scenario 2: Transformation chain (mixed methods)");
Point transformPoint = new Point(2, 3);
Console.WriteLine($"Starting point: {transformPoint}");

// Scale up - using extension method
transformPoint.Scale(3, 2);
Console.WriteLine($"After scaling by (3, 2): {transformPoint}");

// Translate - using inline addition
transformPoint = new Point(transformPoint.X + 5, transformPoint.Y + (-3));
Console.WriteLine($"After translating by (5, -3): {transformPoint}");

// Rotate - using extension method
transformPoint.Rotate(45);
Console.WriteLine($"After rotating 45�: {transformPoint}");

// Convert to vector - using extension method
Vector2 finalVector = transformPoint.ToVector();
Console.WriteLine($"Final result as Vector2: {finalVector}");
Console.WriteLine();

// Distance calculation using inline operators and extension methods
Console.WriteLine("Scenario 3: Distance calculation (mixed methods)");
Point point1 = new Point(1, 1);
Point point2 = new Point(4, 5);
Point difference = new Point(point2.X - point1.X, point2.Y - point1.Y); // Inline subtraction
Vector2 diffVector = difference.ToVector(); // Extension method
float distance = diffVector.Length();

Console.WriteLine($"Point 1: {point1}");
Console.WriteLine($"Point 2: {point2}");
Console.WriteLine($"Difference: {difference}");
Console.WriteLine($"Distance: {distance:F2}");
Console.WriteLine();

Console.WriteLine("Traditional extension methods demonstration complete!");
```

This example demonstrates how extension members create a cohesive API that feels like part of the original type. You can:

- Use `Point.Origin` for a meaningful starting point
- Apply mathematical operators naturally (`point + offset`, `point * scale`)
- Chain transformations using both operators and methods
- Convert between related types (`ToVector()`)
- Read and update absolute points along a path with `path[index]`

### Migration benefits

When you migrate from traditional extension methods to extension members, you get:

1. **Static properties**: Add constants and computed values to types.
1. **Operators**: Enable natural mathematical and logical operations.
1. **Indexers**: Add C# 15 indexed access that can compute values from an existing type and update its stored state.
1. **Unified syntax**: All extension logic uses the same `extension` declaration.
1. **Type-level extensions**: Extend the type itself, not only instances.

Run the complete application to see both approaches side by side and observe how extension members provide a more integrated development experience.

## Related content

- [Extension methods (C# Programming Guide)](../../programming-guide/classes-and-structs/extension-methods.md)
- [What's new in C# 14](../csharp-14.md)
- [What's new in C# 15](../csharp-15.md)
- [`extension` keyword (C# reference)](../../language-reference/keywords/extension.md)
- [Extension indexers feature specification](~/_csharplang/proposals/csharp-15.0/extension-indexers.md)
- [Operator overloading (C# reference)](../../language-reference/operators/operator-overloading.md)
