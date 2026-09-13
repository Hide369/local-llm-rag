---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/classes-and-structs/how-to-create-a-new-method-for-an-enumeration.md
title: How to create a new method for an enumeration
version: 0.0.0
fetched_at: 2026-09-13
---
# How to create a new method for an enumeration (C# Programming Guide)

You can use extension methods to add functionality specific to a particular enum type. In the following example, the `Grades` enumeration represents the possible letter grades that a student might receive in a class. An extension method named `Passing` is added to the `Grades` type so that each instance of that type now "knows" whether it represents a passing grade or not.

```csharp
public enum Grades
{
    F = 0,
    D = 1,
    C = 2,
    B = 3,
    A = 4
};

// Define an extension method in a non-nested static class.
public static class Extensions
{
    public static bool Passing(this Grades grade, Grades minPassing = Grades.D) =>
        grade >= minPassing;
}
```

You can call the extension method as though it was declared on the `enum` type:

```csharp
Grades g1 = Grades.D;
Grades g2 = Grades.F;
Console.WriteLine($"First {(g1.Passing() ? "is" : "is not")} a passing grade.");
Console.WriteLine($"Second {(g2.Passing() ? "is" : "is not")} a passing grade.");

Console.WriteLine("\r\nRaising the bar!\r\n");
Console.WriteLine($"First {(g1.Passing(Grades.C) ? "is" : "is not")} a passing grade.");
Console.WriteLine($"Second {(g2.Passing(Grades.C) ? "is" : "is not")} a passing grade.");
/* Output:
    First is a passing grade.
    Second is not a passing grade.

    Raising the bar!

    First is not a passing grade.
    Second is not a passing grade.
*/
```

Beginning with C# 14, you can declare *extension members* in an extension block. The new syntax enables you to add *extension properties*. You can also add extension members that appear to be new static methods or properties. You're no longer limited to extensions that appear to be instance methods. The following example shows an extension block that adds an instance extension property for `Passing`, and a static extension property for `MinimumPassingGrade`:

```csharp
public static class EnumExtensions
{
    private static Grades minimumPassingGrade = Grades.D;

    extension(Grades grade)
    {
        public static Grades MinimumPassingGrade
        {
            get => minimumPassingGrade;
            set => minimumPassingGrade = value;
        }

        public bool Passing => grade >= minimumPassingGrade;
    }
}
```

You call these new extension properties as though they're declared on the extended type:

```csharp
Grades g1 = Grades.D;
Grades g2 = Grades.F;
Console.WriteLine($"First {(g1.Passing ? "is" : "is not")} a passing grade.");
Console.WriteLine($"Second {(g2.Passing ? "is" : "is not")} a passing grade.");

Grades.MinimumPassingGrade = Grades.C;
Console.WriteLine($"\r\nRaising the bar. Passing grade is now {Grades.MinimumPassingGrade}!\r\n");
Console.WriteLine($"First {(g1.Passing ? "is" : "is not")} a passing grade.");
Console.WriteLine($"Second {(g2.Passing ? "is" : "is not")} a passing grade.");
/* Output:
    First is a passing grade.
    Second is not a passing grade.

    Raising the bar!

    First is not a passing grade.
    Second is not a passing grade.
*/
```

You can learn more about the new extension members in the article on [extension members](./extension-methods.md) and in the language reference article on the [`extension` keyword](../../language-reference/keywords/extension.md).

## See also

- [Extension Methods](./extension-methods.md)
