---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/functional/discards.md
title: Discards - unassigned discardable variables
version: 0.0.0
fetched_at: 2026-09-13
---
# Discards - C# Fundamentals

Discards are placeholder variables that are intentionally unused in application code. Discards are equivalent to unassigned variables; they don't have a value. A discard communicates intent to the compiler and others that read your code: You intended to ignore the result of an expression. You may want to ignore the result of an expression, one or more members of a tuple expression, an `out` parameter to a method, or the target of a pattern matching expression.

Discards make the intent of your code clear. A discard indicates that our code never uses the variable. They enhance its readability and maintainability.

You indicate that a variable is a discard by assigning it the underscore (`_`) as its name. For example, the following method call returns a tuple in which the first and second values are discards. `area` is a previously declared variable set to the third component returned by `GetCityInformation`:

```csharp
(_, _, area) = city.GetCityInformation(cityName);
```

You can use discards to specify unused input parameters of a lambda expression. For more information, see the [Input parameters of a lambda expression](../../language-reference/operators/lambda-expressions.md#input-parameters-of-a-lambda-expression) section of the [Lambda expressions](../../language-reference/operators/lambda-expressions.md) article.

When `_` is a valid discard, attempting to retrieve its value or use it in an assignment operation generates compiler error CS0103, "The name '\_' doesn't exist in the current context". This error is because `_` isn't assigned a value, and may not even be assigned a storage location. If it were an actual variable, you couldn't discard more than one value, as the previous example did.

## Tuple and object deconstruction

Discards are useful in working with tuples when your application code uses some tuple elements but ignores others. For example, the following `QueryCityDataForYears` method returns a tuple with the name of a city, its area, a year, the city's population for that year, a second year, and the city's population for that second year. The example shows the change in population between those two years. Of the data available from the tuple, we're unconcerned with the city area, and we know the city name and the two dates at design-time. As a result, we're only interested in the two population values stored in the tuple, and can handle its remaining values as discards.

```csharp
var (_, _, _, pop1, _, pop2) = QueryCityDataForYears("New York City", 1960, 2010);

Console.WriteLine($"Population change, 1960 to 2010: {pop2 - pop1:N0}");

static (string, double, int, int, int, int) QueryCityDataForYears(string name, int year1, int year2)
{
    int population1 = 0, population2 = 0;
    double area = 0;

    if (name == "New York City")
    {
        area = 468.48;
        if (year1 == 1960)
        {
            population1 = 7781984;
        }
        if (year2 == 2010)
        {
            population2 = 8175133;
        }
        return (name, area, year1, population1, year2, population2);
    }

    return ("", 0, 0, 0, 0, 0);
}
// The example displays the following output:
//      Population change, 1960 to 2010: 393,149
```

For more information on deconstructing tuples with discards, see [Deconstructing tuples and other types](deconstruct.md#tuple-elements-with-discards).

The `Deconstruct` method of a class, structure, or interface also allows you to retrieve and deconstruct a specific set of data from an object. You can use discards when you're interested in working with only a subset of the deconstructed values. The following example deconstructs a `Person` object into four strings (the first and last names, the city, and the state), but discards the last name and the state.

```csharp
using System;

namespace Discards
{
    public class Person
    {
        public string FirstName { get; set; }
        public string MiddleName { get; set; }
        public string LastName { get; set; }
        public string City { get; set; }
        public string State { get; set; }

        public Person(string fname, string mname, string lname,
                      string cityName, string stateName)
        {
            FirstName = fname;
            MiddleName = mname;
            LastName = lname;
            City = cityName;
            State = stateName;
        }

        // Return the first and last name.
        public void Deconstruct(out string fname, out string lname)
        {
            fname = FirstName;
            lname = LastName;
        }

        public void Deconstruct(out string fname, out string mname, out string lname)
        {
            fname = FirstName;
            mname = MiddleName;
            lname = LastName;
        }

        public void Deconstruct(out string fname, out string lname,
                                out string city, out string state)
        {
            fname = FirstName;
            lname = LastName;
            city = City;
            state = State;
        }
    }
    class Example
    {
        public static void Main()
        {
            var p = new Person("John", "Quincy", "Adams", "Boston", "MA");

            // Deconstruct the person object.
            var (fName, _, city, _) = p;
            Console.WriteLine($"Hello {fName} of {city}!");
            // The example displays the following output:
            //      Hello John of Boston!
        }
    }
}
```

For more information on deconstructing user-defined types with discards, see [Deconstructing tuples and other types](deconstruct.md#user-defined-type-with-discards).

## Pattern matching with `switch`

The *discard pattern* can be used in pattern matching with the [switch expression](../../language-reference/operators/switch-expression.md). Every expression, including `null`,  always matches the discard pattern.

The following example defines a `ProvidesFormatInfo` method that uses a `switch` expression to determine whether an object provides an <xref:System.IFormatProvider> implementation and tests whether the object is `null`. It also uses the discard pattern to handle non-null objects of any other type.

```csharp
object?[] objects = [CultureInfo.CurrentCulture,
                   CultureInfo.CurrentCulture.DateTimeFormat,
                   CultureInfo.CurrentCulture.NumberFormat,
                   new ArgumentException(), null];
foreach (var obj in objects)
    ProvidesFormatInfo(obj);

static void ProvidesFormatInfo(object? obj) =>
    Console.WriteLine(obj switch
    {
        IFormatProvider fmt => $"{fmt.GetType()} object",
        null => "A null object reference: Its use could result in a NullReferenceException",
        _ => "Some object type without format information"
    });
// The example displays the following output:
//    System.Globalization.CultureInfo object
//    System.Globalization.DateTimeFormatInfo object
//    System.Globalization.NumberFormatInfo object
//    Some object type without format information
//    A null object reference: Its use could result in a NullReferenceException
```

## Calls to methods with `out` parameters

When calling the `Deconstruct` method to deconstruct a user-defined type (an instance of a class, structure, or interface), you can discard the values of individual `out` arguments. But you can also discard the value of `out` arguments when calling any method with an `out` parameter.

The following example calls the [DateTime.TryParse(String, out DateTime)](<xref:System.DateTime.TryParse(System.String,System.DateTime@)>) method to determine whether the string representation of a date is valid in the current culture. Because the example is concerned only with validating the date string and not with parsing it to extract the date, the `out` argument to the method is a discard.

```csharp
string[] dateStrings = ["05/01/2018 14:57:32.8", "2018-05-01 14:57:32.8",
                      "2018-05-01T14:57:32.8375298-04:00", "5/01/2018",
                      "5/01/2018 14:57:32.80 -07:00",
                      "1 May 2018 2:57:32.8 PM", "16-05-2018 1:00:32 PM",
                      "Fri, 15 May 2018 20:10:57 GMT"];
foreach (string dateString in dateStrings)
{
    if (DateTime.TryParse(dateString, out _))
        Console.WriteLine($"'{dateString}': valid");
    else
        Console.WriteLine($"'{dateString}': invalid");
}
// The example displays output like the following:
//       '05/01/2018 14:57:32.8': valid
//       '2018-05-01 14:57:32.8': valid
//       '2018-05-01T14:57:32.8375298-04:00': valid
//       '5/01/2018': valid
//       '5/01/2018 14:57:32.80 -07:00': valid
//       '1 May 2018 2:57:32.8 PM': valid
//       '16-05-2018 1:00:32 PM': invalid
//       'Fri, 15 May 2018 20:10:57 GMT': invalid
```

## A standalone discard

You can use a standalone discard to indicate any variable that you choose to ignore. One typical use is to use an assignment to ensure that an argument isn't null. The following code uses a discard to force an assignment. The right side of the assignment uses the [null coalescing operator](../../language-reference/operators/null-coalescing-operator.md) to throw an <xref:System.ArgumentNullException?displayProperty=nameWithType> when the argument is `null`. The code doesn't need the result of the assignment, so it's discarded. The expression forces a null check. The discard clarifies your intent: the result of the assignment isn't needed or used.

```csharp
public static void Method(string arg)
{
    _ = arg ?? throw new ArgumentNullException(paramName: nameof(arg), message: "arg can't be null");

    // Do work with arg.
}
```

The following example uses a standalone discard to ignore the <xref:System.Threading.Tasks.Task> object returned by an asynchronous operation. Assigning the task has the effect of suppressing the compiler warning about unobserved exceptions. It makes your intent clear: You want to discard the `Task`, and propagate any errors generated from that asynchronous operation to callers.

```csharp
private static async Task ExecuteAsyncMethods()
{
    Console.WriteLine("About to launch a task...");
    _ = Task.Run(() =>
    {
        var iterations = 0;
        for (int ctr = 0; ctr < int.MaxValue; ctr++)
            iterations++;
        Console.WriteLine("Completed looping operation...");
        throw new InvalidOperationException();
    });
    await Task.Delay(5000);
    Console.WriteLine("Exiting after 5 second delay");
}
// The example displays output like the following:
//       About to launch a task...
//       Completed looping operation...
//       Exiting after 5 second delay
```

Without assigning the task to a discard, the following code generates a compiler warning:

```csharp
private static async Task ExecuteAsyncMethods()
{
    Console.WriteLine("About to launch a task...");
    // CS4014: Because this call is not awaited, execution of the current method continues before the call is completed.
    // Consider applying the 'await' operator to the result of the call.
    Task.Run(() =>
    {
        var iterations = 0;
        for (int ctr = 0; ctr < int.MaxValue; ctr++)
            iterations++;
        Console.WriteLine("Completed looping operation...");
        throw new InvalidOperationException();
    });
    await Task.Delay(5000);
    Console.WriteLine("Exiting after 5 second delay");
```

> [!NOTE]
> If you run either of the preceding two samples using a debugger, the debugger will stop the program when the exception is thrown. Without a debugger attached, the exception is silently ignored in both cases.

`_` is also a valid identifier. When used outside of a supported context, `_` is treated not as a discard but as a valid variable. If an identifier named `_` is already in scope, the use of `_` as a standalone discard can result in:

- Accidental modification of the value of the in-scope `_` variable by assigning it the value of the intended discard. For example:
```csharp
private static void ShowValue(int _)
{
   byte[] arr = [0, 0, 1, 2];
   _ = BitConverter.ToInt32(arr, 0);
   Console.WriteLine(_);
}
 // The example displays the following output:
 //       33619968
```
- A compiler error for violating type safety. For example:
```csharp
private static bool RoundTrips(int _)
{
   string value = _.ToString();
   int newValue = 0;
   _ = Int32.TryParse(value, out newValue);
   return _ == newValue;
}
// The example displays the following compiler error:
//      error CS0029: Cannot implicitly convert type 'bool' to 'int'
```

## See also

- [Remove unnecessary expression value (style rule IDE0058)](../../../fundamentals/code-analysis/style-rules/ide0058.md)
- [Remove unnecessary value assignment (style rule IDE0059)](../../../fundamentals/code-analysis/style-rules/ide0059.md)
- [Remove unused parameter (style rule IDE0060)](../../../fundamentals/code-analysis/style-rules/ide0060.md)
- [Deconstructing tuples and other types](deconstruct.md)
- [`is` operator](../../language-reference/operators/is.md)
- [`switch` expression](../../language-reference/operators/switch-expression.md)
