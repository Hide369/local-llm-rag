---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/types/generics.md
title: Generic types and methods
version: 0.0.0
fetched_at: 2026-09-13
---
# Generic types and methods

> [!TIP]
> **New to developing software?** Start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first. You'll encounter generics as soon as you use collections like `List<T>`.
>
> **Experienced in another language?** C# generics are similar to generics in Java or templates in C++, but with full runtime type information and no type erasure. Skim the [collection expressions](#collection-expressions) and [covariance and contravariance](#covariance-and-contravariance) sections for C#-specific patterns.

*Generics* let you write code that works with any type while keeping full type safety. Instead of writing separate classes or methods for `int`, `string`, and every other type you need, write one version with one or more *type parameters* (such as `T`, or `TKey` and `TValue`) and specify the actual types when you use it. The compiler checks types at compile time, so you don't need runtime casts or risk `InvalidCastException`.

You encounter generics constantly in everyday C#. Collections, async return types, delegates, and LINQ all rely on generic types:

```csharp
List<int> scores = [95, 87, 72, 91];
Dictionary<string, decimal> prices = new()
{
    ["Widget"] = 19.99m,
    ["Gadget"] = 29.99m
};
Task<string> greeting = Task.FromResult("Hello, generics!");
Func<int, bool> isPositive = n => n > 0;

Console.WriteLine($"First score: {scores[0]}");
Console.WriteLine($"Widget price: {prices["Widget"]:C}");
Console.WriteLine($"Greeting: {await greeting}");
Console.WriteLine($"Is 5 positive? {isPositive(5)}");
```

In each case, the type argument in angle brackets (`<int>`, `<string>`, `<decimal>`) tells the generic type what kind of data it holds or operates on. The compiler enforces type safety. You can't accidentally add a `string` to a `List<int>`.

## Consuming generic types

More often, you *consume* generic types from the .NET class library rather than creating your own. The following sections show the most common generic types you'll use.

### Generic collections

The <xref:System.Collections.Generic> namespace provides type-safe collection classes. Always use these collections instead of nongeneric collections like <xref:System.Collections.ArrayList>:

```csharp
// A strongly typed list of strings
List<string> names = ["Alice", "Bob", "Carol"];
names.Add("Dave");
// names.Add(42); // Compile-time error: can't add an int to List<string>

// A dictionary mapping string keys to int values
var inventory = new Dictionary<string, int>
{
    ["Apples"] = 50,
    ["Oranges"] = 30
};
inventory["Bananas"] = 25;

// A set that prevents duplicates
HashSet<int> uniqueIds = [1, 2, 3, 1, 2];
Console.WriteLine($"Unique count: {uniqueIds.Count}"); // 3

// A FIFO queue
Queue<string> tasks = new();
tasks.Enqueue("Build");
tasks.Enqueue("Test");
Console.WriteLine($"Next task: {tasks.Dequeue()}"); // Build
```

Generic collections prevent type errors at runtime because the errors surface at compile time instead. These collections also avoid boxing for value types, which improves performance.

### Generic methods

A generic method declares its own type parameter. The compiler often *infers* the type argument from the values you pass, so you don't need to specify it explicitly:

```csharp
static void Print<T>(T value) =>
    Console.WriteLine($"Value: {value}");

Print(42);        // Compiler infers T as int
Print("hello");   // Compiler infers T as string
Print(3.14);      // Compiler infers T as double
```

In the call `Print(42)`, the compiler infers `T` as `int` from the argument. You can write `Print<int>(42)` explicitly, but type inference keeps the code cleaner.

## Collection expressions

Collection expressions (C# 12) provide a concise syntax for creating collections. Use square brackets instead of constructor calls or initializer syntax:

```csharp
// Create a list with a collection expression
List<string> fruits = ["Apple", "Banana", "Cherry"];

// Create an array
int[] numbers = [1, 2, 3, 4, 5];

// Works with any supported collection type
IReadOnlyList<double> temperatures = [72.0, 68.5, 75.3];

Console.WriteLine($"Fruits: {string.Join(", ", fruits)}");
Console.WriteLine($"Numbers: {string.Join(", ", numbers)}");
Console.WriteLine($"Temps: {string.Join(", ", temperatures)}");
```

The *spread operator* (`..`) inlines the elements of one collection into another, which is useful for combining sequences:

```csharp
List<int> first = [1, 2, 3];
List<int> second = [4, 5, 6];

// Spread both lists into a new combined list
List<int> combined = [.. first, .. second];
Console.WriteLine(string.Join(", ", combined));
// Output: 1, 2, 3, 4, 5, 6

// Add extra elements alongside spreads
List<int> withExtras = [0, .. first, 99, .. second];
Console.WriteLine(string.Join(", ", withExtras));
// Output: 0, 1, 2, 3, 99, 4, 5, 6
```

Collection expressions work with arrays, `List<T>`, `Span<T>`, `ImmutableArray<T>`, and any type that supports the collection builder pattern. For the complete syntax reference, see [Collection expressions](../../language-reference/operators/collection-expressions.md).

## Dictionary initialization

You can initialize dictionaries concisely with indexer initializers. This syntax uses square brackets to set key-value pairs:

```csharp
Dictionary<string, int> scores = new()
{
    ["Alice"] = 95,
    ["Bob"] = 87,
    ["Carol"] = 92
};

foreach (var (name, score) in scores)
{
    Console.WriteLine($"{name}: {score}");
}
```

You can merge dictionaries by copying one and applying overrides:

```csharp
Dictionary<string, int> defaults = new()
{
    ["Timeout"] = 30,
    ["Retries"] = 3
};
Dictionary<string, int> overrides = new()
{
    ["Timeout"] = 60
};

// Merge defaults and overrides into a new dictionary
Dictionary<string, int> config = new(defaults);
foreach (var (key, value) in overrides)
{
    config[key] = value;
}

Console.WriteLine($"Timeout: {config["Timeout"]}");  // 60
Console.WriteLine($"Retries: {config["Retries"]}");   // 3
```

## Type constraints

*Constraints* restrict which type arguments a generic type or method accepts. Constraints let you call methods or access properties on the type parameter that wouldn't be available on `object` alone:

```csharp
static T Max<T>(T a, T b) where T : IComparable<T> =>
    a.CompareTo(b) >= 0 ? a : b;

Console.WriteLine(Max(3, 7));          // 7
Console.WriteLine(Max("apple", "banana")); // banana

static T CreateDefault<T>() where T : new() => new T();

var list = CreateDefault<List<int>>(); // Creates an empty List<int>
Console.WriteLine($"Empty list count: {list.Count}"); // 0
```

The most common constraints are:

| Constraint | Meaning |
|---|---|
| `where T : class` | `T` must be a reference type |
| `where T : struct` | `T` must be a non-nullable value type |
| `where T : new()` | `T` must have a public parameterless constructor |
| `where T : BaseClass` | `T` must derive from `BaseClass` |
| `where T : IInterface` | `T` must implement `IInterface` |

You can combine constraints: `where T : class, IComparable<T>, new()`. Less common constraints include `where T : System.Enum`, `where T : System.Delegate`, and `where T : unmanaged` for specialized scenarios. For the complete list, see [Constraints on type parameters](../../programming-guide/generics/constraints-on-type-parameters.md).

## Covariance and contravariance

*Covariance* and *contravariance* describe how generic types behave with inheritance. They determine whether you can use a more derived or less derived type argument than originally specified:

```csharp
// Covariance: IEnumerable<Dog> can be used as IEnumerable<Animal>
// because IEnumerable<out T> is covariant
List<Dog> dogs = [new("Rex"), new("Buddy")];
IEnumerable<Animal> animals = dogs; // Allowed because Dog derives from Animal

foreach (var animal in animals)
{
    Console.WriteLine(animal.Name);
}

// Contravariance: Action<Animal> can be used as Action<Dog>
// because Action<in T> is contravariant
Action<Animal> printAnimal = a => Console.WriteLine($"Animal: {a.Name}");
Action<Dog> printDog = printAnimal; // Allowed because any Animal handler can handle Dog

printDog(new Dog("Spot"));
```

- **Covariance** (`out T`): An `IEnumerable<Dog>` can be used where `IEnumerable<Animal>` is expected because `Dog` derives from `Animal`. The `out` keyword on the type parameter enables this. Covariant type parameters can only appear in output positions (return types).
- **Contravariance** (`in T`): An `Action<Animal>` can be used where `Action<Dog>` is expected because any action that handles `Animal` can also handle `Dog`. The `in` keyword enables this. Contravariant type parameters can only appear in input positions (parameters).

Many built-in interfaces and delegates are already variant: `IEnumerable<out T>`, `IReadOnlyList<out T>`, `Func<out TResult>`, and `Action<in T>`. You benefit from variance automatically when working with these types. For an in-depth treatment of designing variant interfaces and delegates, see [Covariance and contravariance](../../programming-guide/concepts/covariance-contravariance/index.md).

## Create your own generic types

You can define your own generic classes, structs, interfaces, and methods. The following example shows a simple generic linked list for illustration. In practice, use <xref:System.Collections.Generic.List`1> or another built-in collection:

```csharp
public class GenericList<T>
{
    private class Node(T data)
    {
        public T Data { get; set; } = data;
        public Node? Next { get; set; }
    }

    private Node? head;

    public void AddHead(T data)
    {
        var node = new Node(data) { Next = head };
        head = node;
    }

    public IEnumerator<T> GetEnumerator()
    {
        var current = head;
        while (current is not null)
        {
            yield return current.Data;
            current = current.Next;
        }
    }
}
```

```csharp
var list = new GenericList<int>();
for (var i = 0; i < 5; i++)
{
    list.AddHead(i);
}

foreach (var item in list)
{
    Console.Write($"{item} ");
}
Console.WriteLine();
// Output: 4 3 2 1 0
```

Generic types aren't limited to classes. You can define generic `interface`, `struct`, and `record` types. For more information about designing generic algorithms and complex constraint combinations, see [Generics in .NET](../../../standard/generics/index.md).

## See also

- [Generics in .NET](../../../standard/generics/index.md)
- [Collection expressions](../../language-reference/operators/collection-expressions.md)
- [Constraints on type parameters](../../programming-guide/generics/constraints-on-type-parameters.md)
- [Covariance and contravariance](../../programming-guide/concepts/covariance-contravariance/index.md)
- <xref:System.Collections.Generic>
