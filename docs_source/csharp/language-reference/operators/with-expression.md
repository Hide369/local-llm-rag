---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/with-expression.md
title: The with expression - create new objects that are modified copies of existing objects
version: 0.0.0
fetched_at: 2026-09-13
---
# The `with` expression - Nondestructive mutation creates a new object with modified properties

A `with` expression creates a copy of its operand with the specified properties and fields modified. Use the [object initializer](../../programming-guide/classes-and-structs/object-and-collection-initializers.md) syntax to specify which members to modify and their new values:

```csharp
using System;

public class WithExpressionBasicExample
{
    public record NamedPoint(string Name, int X, int Y);

    public static void Main()
    {
        var p1 = new NamedPoint("A", 0, 0);
        Console.WriteLine($"{nameof(p1)}: {p1}");  // output: p1: NamedPoint { Name = A, X = 0, Y = 0 }
        
        var p2 = p1 with { Name = "B", X = 5 };
        Console.WriteLine($"{nameof(p2)}: {p2}");  // output: p2: NamedPoint { Name = B, X = 5, Y = 0 }
        
        var p3 = p1 with 
            { 
                Name = "C", 
                Y = 4 
            };
        Console.WriteLine($"{nameof(p3)}: {p3}");  // output: p3: NamedPoint { Name = C, X = 0, Y = 4 }

        Console.WriteLine($"{nameof(p1)}: {p1}");  // output: p1: NamedPoint { Name = A, X = 0, Y = 0 }

        var apples = new { Item = "Apples", Price = 1.19m };
        Console.WriteLine($"Original: {apples}");  // output: Original: { Item = Apples, Price = 1.19 }
        var saleApples = apples with { Price = 0.79m };
        Console.WriteLine($"Sale: {saleApples}");  // output: Sale: { Item = Apples, Price = 0.79 }
    }
}
```

The left-hand operand of a `with` expression can be a [record type](../builtin-types/record.md). It can also be a [structure type](../builtin-types/struct.md), a [tuple](../builtin-types/value-tuples.md), or an [anonymous type](../../programming-guide/classes-and-structs/anonymous-types.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The result of a `with` expression has the same run-time type as the expression's operand, as the following example shows:

```csharp
using System;

public class InheritanceExample
{
    public record Point(int X, int Y);
    public record NamedPoint(string Name, int X, int Y) : Point(X, Y);

    public static void Main()
    {
        Point p1 = new NamedPoint("A", 0, 0);
        Point p2 = p1 with { X = 5, Y = 3 };
        Console.WriteLine(p2 is NamedPoint);  // output: True
        Console.WriteLine(p2);  // output: NamedPoint { X = 5, Y = 3, Name = A }
    }
}
```

When a member is a reference type, copying that member copies only the reference to that member instance. Both the copy and original operand access the same reference-type instance. The following example demonstrates that behavior:

```csharp
using System;
using System.Collections.Generic;

public class ExampleWithReferenceType
{
    public record TaggedNumber(int Number, List<string> Tags)
    {
        public string PrintTags() => string.Join(", ", Tags);
    }

    public static void Main()
    {
        var original = new TaggedNumber(1, new List<string> { "A", "B" });

        var copy = original with { Number = 2 };
        Console.WriteLine($"Tags of {nameof(copy)}: {copy.PrintTags()}");
        // output: Tags of copy: A, B

        original.Tags.Add("C");
        Console.WriteLine($"Tags of {nameof(copy)}: {copy.PrintTags()}");
        // output: Tags of copy: A, B, C
    }
}
```

## Custom copy semantics

Every record class type has a *copy constructor*. A *copy constructor* is a constructor with a single parameter of the containing record type. It copies the state of its argument to a new record instance. When you evaluate a `with` expression, it calls the copy constructor to create a new record instance based on an original record. Then, it updates the new instance with the specified modifications. By default, the compiler synthesizes the copy constructor. To customize the record copy semantics, explicitly declare a copy constructor with the desired behavior. The following example updates the preceding example with an explicit copy constructor. The new copy behavior copies list items instead of a list reference when a record is copied:

```csharp
using System;
using System.Collections.Generic;

public class UserDefinedCopyConstructorExample
{
    public record TaggedNumber(int Number, List<string> Tags)
    {
        protected TaggedNumber(TaggedNumber original)
        {
            Number = original.Number;
            Tags = new List<string>(original.Tags);
        }

        public string PrintTags() => string.Join(", ", Tags);
    }

    public static void Main()
    {
        var original = new TaggedNumber(1, new List<string> { "A", "B" });

        var copy = original with { Number = 2 };
        Console.WriteLine($"Tags of {nameof(copy)}: {copy.PrintTags()}");
        // output: Tags of copy: A, B

        original.Tags.Add("C");
        Console.WriteLine($"Tags of {nameof(copy)}: {copy.PrintTags()}");
        // output: Tags of copy: A, B
    }
}
```

You can't customize the copy semantics for structure types.

> [!IMPORTANT]
> In the preceding examples, all properties are independent. None of the properties are computed from other property values. A `with` expression first copies the existing record instance, then modifies any properties or fields specified in the `with` expression. Computed properties in `record` types should be computed on access, not initialized when the instance is created. Otherwise, a property might return the computed value based on the original instance, not the modified copy. For more information, see the language reference article on [`record` types](../builtin-types/record.md#nondestructive-mutation).

## C# language specification

For more information, see the following sections of the [C# language specification](~/_csharpstandard/standard/README.md):

- [`with` expression](~/_csharpstandard/standard/expressions.md#1210-with-expressions)
- [Copy and Clone members](~/_csharpstandard/standard/classes.md#151644-copy-and-clone-members)

## See also

- [C# operators and expressions](index.md)
- [Records](../builtin-types/record.md)
- [Structure types](../builtin-types/struct.md)
