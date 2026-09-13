---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/statements/yield.md
title: yield statement - provide the next element in an iterator
version: 0.0.0
fetched_at: 2026-09-13
---
# yield statement - provide the next element

Use the `yield` statement in an [iterator](../../iterators.md) to provide the next value or signal the end of an iteration. The `yield` statement has the two following forms:

- `yield return`: to provide the next value in iteration, as the following example shows:

```csharp
foreach (int i in ProduceEvenNumbers(9))
{
    Console.Write(i);
    Console.Write(" ");
}
// Output: 0 2 4 6 8

IEnumerable<int> ProduceEvenNumbers(int upto)
{
    for (int i = 0; i <= upto; i += 2)
    {
        yield return i;
    }
}
```

- `yield break`: to explicitly signal the end of iteration, as the following example shows:

```csharp
Console.WriteLine(string.Join(" ", TakeWhilePositive(new int[] {2, 3, 4, 5, -1, 3, 4})));
// Output: 2 3 4 5

Console.WriteLine(string.Join(" ", TakeWhilePositive(new int[] {9, 8, 7})));
// Output: 9 8 7

IEnumerable<int> TakeWhilePositive(IEnumerable<int> numbers)
{
    foreach (int n in numbers)
    {
        if (n > 0)
        {
            yield return n;
        }
        else
        {
            yield break;
        }
    }
}
```

  Iteration also finishes when control reaches the end of an iterator.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

In the preceding examples, the return type of iterators is <xref:System.Collections.Generic.IEnumerable`1>. In nongeneric cases, use <xref:System.Collections.IEnumerable> as the return type of an iterator. You can also use <xref:System.Collections.Generic.IAsyncEnumerable`1> as the return type of an iterator. That makes an iterator async. Use the [`await foreach` statement](iteration-statements.md#await-foreach) to iterate over iterator's result, as the following example shows:

```csharp
await foreach (int n in GenerateNumbersAsync(5))
{
    Console.Write(n);
    Console.Write(" ");
}
// Output: 0 2 4 6 8

async IAsyncEnumerable<int> GenerateNumbersAsync(int count)
{
    for (int i = 0; i < count; i++)
    {
        yield return await ProduceNumberAsync(i);
    }
}

async Task<int> ProduceNumberAsync(int seed)
{
    await Task.Delay(1000);
    return 2 * seed;
}
```

<xref:System.Collections.Generic.IEnumerator`1> or <xref:System.Collections.IEnumerator> can also be the return type of an iterator. Use those return types when you implement the `GetEnumerator` method in the following scenarios:

- You design the type that implements <xref:System.Collections.Generic.IEnumerable`1> or <xref:System.Collections.IEnumerable> interface.
- You add an instance or [extension](../../programming-guide/classes-and-structs/extension-methods.md) `GetEnumerator` method to enable iteration over the type's instance with the [`foreach` statement](iteration-statements.md#the-foreach-statement), as the following example shows:

```csharp
public static void Example()
{
    var point = new Point(1, 2, 3);
    foreach (int coordinate in point)
    {
        Console.Write(coordinate);
        Console.Write(" ");
    }
    // Output: 1 2 3
}

public readonly record struct Point(int X, int Y, int Z)
{
    public IEnumerator<int> GetEnumerator()
    {
        yield return X;
        yield return Y;
        yield return Z;
    }
}
```

You can't use the `yield` statements in:

- methods with [in](../keywords/method-parameters.md#in-parameter-modifier), [ref](../keywords/ref.md), or [out](../keywords/method-parameters.md#out-parameter-modifier) parameters.
- [lambda expressions](../operators/lambda-expressions.md) and [anonymous methods](../operators/delegate-operator.md).
- [unsafe blocks](../keywords/unsafe.md). Before C# 13, `yield` was invalid in any method with an `unsafe` block. Beginning with C# 13, you can use `yield` in methods with `unsafe` blocks, but not in the `unsafe` block.
- `yield return` and `yield break` can't be used in [catch](../statements/exception-handling-statements.md) and [finally](../statements/exception-handling-statements.md) blocks, or in [try](../statements/exception-handling-statements.md) blocks with a corresponding `catch` block. The `yield return` and `yield break` statements can be used in a `try` block with no `catch` blocks, only a `finally` block.

## `using` statements in iterators

You can use [`using` statements](using.md) in iterator methods. Since `using` statements compile into `try` blocks with `finally` clauses (and no `catch` blocks), they work correctly with iterators. The disposable resources are properly managed throughout the iterator's execution:

```csharp
Console.WriteLine("=== Using in Iterator Example ===");

// Demonstrate that using statements work correctly in iterators
foreach (string line in ReadLinesFromResource())
{
    Console.WriteLine($"Read: {line}");
    // Simulate processing only first two items
    if (line == "Line 2") break;
}

Console.WriteLine("Iteration stopped early - resource should still be disposed.");

static IEnumerable<string> ReadLinesFromResource()
{
    Console.WriteLine("Opening resource...");
    using var resource = new StringWriter(); // Use StringWriter as a simple IDisposable
    resource.WriteLine("Resource initialized");

    // These lines would typically come from the resource (e.g., file, database)
    string[] lines = { "Line 1", "Line 2", "Line 3", "Line 4" };

    foreach (string line in lines)
    {
        Console.WriteLine($"About to yield: {line}");
        yield return line;
        Console.WriteLine($"Resumed after yielding: {line}");
    }

    Console.WriteLine("Iterator completed - using block will dispose resource.");
}
```

As the preceding example shows, the resource acquired in the `using` statement remains available throughout the iterator's execution, even when the iterator suspends and resumes execution at `yield return` statements. The resource is disposed when the iterator completes (either by reaching the end or via `yield break`) or when the iterator itself is disposed (for example, when the caller breaks out of enumeration early).

## Execution of an iterator

Calling an iterator doesn't execute it immediately, as the following example shows:

```csharp
var numbers = ProduceEvenNumbers(5);
Console.WriteLine("Caller: about to iterate.");
foreach (int i in numbers)
{
    Console.WriteLine($"Caller: {i}");
}

IEnumerable<int> ProduceEvenNumbers(int upto)
{
    Console.WriteLine("Iterator: start.");
    for (int i = 0; i <= upto; i += 2)
    {
        Console.WriteLine($"Iterator: about to yield {i}");
        yield return i;
        Console.WriteLine($"Iterator: yielded {i}");
    }
    Console.WriteLine("Iterator: end.");
}
// Output:
// Caller: about to iterate.
// Iterator: start.
// Iterator: about to yield 0
// Caller: 0
// Iterator: yielded 0
// Iterator: about to yield 2
// Caller: 2
// Iterator: yielded 2
// Iterator: about to yield 4
// Caller: 4
// Iterator: yielded 4
// Iterator: end.
```

As the preceding example shows, when you start to iterate over an iterator's result, the iterator executes until the first `yield return` statement is reached. Then, the execution of the iterator is suspended and the caller gets the first iteration value and processes it. On each subsequent iteration, the execution of the iterator resumes after the `yield return` statement that caused the previous suspension and continues until the next `yield return` statement is reached. The iteration completes when control reaches the end of an iterator or a `yield break` statement.

## C# language specification

For more information, see [The yield statement](~/_csharpstandard/standard/statements.md#1315-the-yield-statement) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [Iterators](../../iterators.md)
- [Iterate through collections in C#](../../programming-guide/concepts/iterators.md)
- [foreach](iteration-statements.md#the-foreach-statement)
- [await foreach](iteration-statements.md#await-foreach)
