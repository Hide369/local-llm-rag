---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/linq/how-to-extend-linq.md
title: Write your own extensions to LINQ
version: 0.0.0
fetched_at: 2026-09-13
---
# Write your own extensions to LINQ

All LINQ based methods follow one of two similar patterns. They take an enumerable sequence. They return either a different sequence or a single value. The consistency of the shape enables you to extend LINQ by writing methods with a similar shape. In fact, the .NET libraries gained new methods in many .NET releases since LINQ was first introduced. In this article, you see examples of extending LINQ by writing your own methods that follow the same pattern.

## Add custom methods for LINQ queries

Extend the set of methods that you use for LINQ queries by adding extension methods to the <xref:System.Collections.Generic.IEnumerable`1> interface. For example, in addition to the standard average or maximum operations, you create a custom aggregate method to compute a single value from a sequence of values. You also create a method that works as a custom filter or a specific data transform for a sequence of values and returns a new sequence. Examples of such methods are <xref:System.Linq.Enumerable.Distinct*>, <xref:System.Linq.Enumerable.Skip*>, and <xref:System.Linq.Enumerable.Reverse*>.

When you extend the <xref:System.Collections.Generic.IEnumerable`1> interface, you can apply your custom methods to any enumerable collection. For more information, see [Extension members](../programming-guide/classes-and-structs/extension-methods.md).

An *aggregate* method computes a single value from a set of values. LINQ provides several aggregate methods, including <xref:System.Linq.Enumerable.Average*>, <xref:System.Linq.Enumerable.Min*>, and <xref:System.Linq.Enumerable.Max*>. Create your own aggregate method by adding an extension method to the <xref:System.Collections.Generic.IEnumerable`1> interface.

Beginning in C# 14, you can declare an *extension block* to contain multiple extension members. Declare an extension block with the keyword `extension` followed by the receiver parameter in parentheses. The following code example shows how to create an extension method called `Median` in an extension block. The method computes a median for a sequence of numbers of type `double`.

```csharp
extension(IEnumerable<double>? source)
{
    public double Median()
    {
        if (source is null || !source.Any())
        {
            throw new InvalidOperationException("Cannot compute median for a null or empty set.");
        }

        var sortedList =
            source.OrderBy(number => number).ToList();

        int itemIndex = sortedList.Count / 2;

        if (sortedList.Count % 2 == 0)
        {
            // Even number of items.
            return (sortedList[itemIndex] + sortedList[itemIndex - 1]) / 2;
        }
        else
        {
            // Odd number of items.
            return sortedList[itemIndex];
        }
    }
}
```

You can also add the `this` modifier to a static method to declare an *extension method*. The following code shows the equivalent `Median` extension method:

```csharp
public static class EnumerableExtension
{
    public static double Median(this IEnumerable<double>? source)
    {
        if (source is null || !source.Any())
        {
            throw new InvalidOperationException("Cannot compute median for a null or empty set.");
        }

        var sortedList =
            source.OrderBy(number => number).ToList();

        int itemIndex = sortedList.Count / 2;

        if (sortedList.Count % 2 == 0)
        {
            // Even number of items.
            return (sortedList[itemIndex] + sortedList[itemIndex - 1]) / 2;
        }
        else
        {
            // Odd number of items.
            return sortedList[itemIndex];
        }
    }
}
```

Call either extension method for any enumerable collection in the same way you call other aggregate methods from the <xref:System.Collections.Generic.IEnumerable`1> interface.

The following code example shows how to use the `Median` method for an array of type `double`.

```csharp
double[] numbers = [1.9, 2, 8, 4, 5.7, 6, 7.2, 0];
var query = numbers.Median();

Console.WriteLine($"double: Median = {query}");
// This code produces the following output:
//     double: Median = 4.85
```

*Overload your aggregate method* so that it accepts sequences of various types. The standard approach is to create an overload for each type. Another approach is to create an overload that takes a generic type and convert it to a specific type by using a delegate. You can also combine both approaches.

Create a specific overload for each type that you want to support. The following code example shows an overload of the `Median` method for the `int` type.

```csharp
// int overload
public static double Median(this IEnumerable<int> source) =>
    (from number in source select (double)number).Median();
```

You can now call the `Median` overloads for both `integer` and `double` types, as shown in the following code:

```csharp
double[] numbers1 = [1.9, 2, 8, 4, 5.7, 6, 7.2, 0];
var query1 = numbers1.Median();

Console.WriteLine($"double: Median = {query1}");

int[] numbers2 = [1, 2, 3, 4, 5];
var query2 = numbers2.Median();

Console.WriteLine($"int: Median = {query2}");
// This code produces the following output:
//     double: Median = 4.85
//     int: Median = 3
```

You can also create an overload that accepts a *generic sequence* of objects. This overload takes a delegate as a parameter and uses it to convert a sequence of objects of a generic type to a specific type.

The following code shows an overload of the `Median` method that takes the <xref:System.Func`2> delegate as a parameter. This delegate takes an object of generic type T and returns an object of type `double`.

```csharp
// generic overload
public static double Median<T>(
    this IEnumerable<T> numbers, Func<T, double> selector) =>
    (from num in numbers select selector(num)).Median();
```

You can now call the `Median` method for a sequence of objects of any type. If the type doesn't have its own method overload, pass a delegate parameter. In C#, you can use a lambda expression for this purpose. Also, in Visual Basic only, if you use the `Aggregate` or `Group By` clause instead of the method call, you can pass any value or expression that's in the scope this clause.

The following example code shows how to call the `Median` method for an array of integers and an array of strings. For strings, the median for the lengths of strings in the array is calculated. The example shows how to pass the <xref:System.Func`2> delegate parameter to the `Median` method for each case.

```csharp
int[] numbers3 = [1, 2, 3, 4, 5];

/*
    You can use the num => num lambda expression as a parameter for the Median method
    so that the compiler will implicitly convert its value to double.
    If there is no implicit conversion, the compiler will display an error message.
*/
var query3 = numbers3.Median(num => num);

Console.WriteLine($"int: Median = {query3}");

string[] numbers4 = ["one", "two", "three", "four", "five"];

// With the generic overload, you can also use numeric properties of objects.
var query4 = numbers4.Median(str => str.Length);

Console.WriteLine($"string: Median = {query4}");
// This code produces the following output:
//     int: Median = 3
//     string: Median = 4
```

Extend the <xref:System.Collections.Generic.IEnumerable`1> interface with a custom query method that returns a *sequence of values*. In this case, the method must return a collection of type <xref:System.Collections.Generic.IEnumerable`1>. Such methods can be used to apply filters or data transforms to a sequence of values.

The following example shows how to create an extension method named `AlternateElements` that returns every other element in a collection, starting from the first element.

```csharp
// Extension method for the IEnumerable<T> interface.
// The method returns every other element of a sequence.
public static IEnumerable<T> AlternateElements<T>(this IEnumerable<T> source)
{
    int index = 0;
    foreach (T element in source)
    {
        if (index % 2 == 0)
        {
            yield return element;
        }

        index++;
    }
}
```

Call this extension method for any enumerable collection just as you would call other methods from the <xref:System.Collections.Generic.IEnumerable`1> interface, as shown in the following code:

```csharp
string[] strings = ["a", "b", "c", "d", "e"];

var query5 = strings.AlternateElements();

foreach (var element in query5)
{
    Console.WriteLine(element);
}
// This code produces the following output:
//     a
//     c
//     e
```

Each example shown in this article has a different *receiver*. That means you must declare each method in a different extension block that specifies the unique receiver. The following code example shows a single static class with three different extension blocks, each of which contains one of the methods defined in this article:

```csharp
public static class EnumerableExtension
{
    // <MedianExtensionMember>
    extension(IEnumerable<double>? source)
    {
        public double Median()
        {
            if (source is null || !source.Any())
            {
                throw new InvalidOperationException("Cannot compute median for a null or empty set.");
            }

            var sortedList =
                source.OrderBy(number => number).ToList();

            int itemIndex = sortedList.Count / 2;

            if (sortedList.Count % 2 == 0)
            {
                // Even number of items.
                return (sortedList[itemIndex] + sortedList[itemIndex - 1]) / 2;
            }
            else
            {
                // Odd number of items.
                return sortedList[itemIndex];
            }
        }
    }
```

The final extension block declares a generic extension block. The type parameter for the receiver is declared on the `extension` itself.

The preceding example declares one extension member in each extension block. In most cases, you create multiple extension members for the same receiver. In those cases, declare the extensions for those members in a single extension block.
