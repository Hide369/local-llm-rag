---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/statements/using.md
title: using statement - ensure the correct use of disposable objects
version: 0.0.0
fetched_at: 2026-09-13
---
# using statement - ensure the correct use of disposable objects

The `using` statement ensures the correct use of an <xref:System.IDisposable> instance:

```csharp
var numbers = new List<int>();
using (StreamReader reader = File.OpenText("numbers.txt"))
{
    string line;
    while ((line = reader.ReadLine()) is not null)
    {
        if (int.TryParse(line, out int number))
        {
            numbers.Add(number);
        }
    }
}
```

When control leaves the block of the `using` statement, the acquired <xref:System.IDisposable> instance is disposed. In particular, the `using` statement ensures that a disposable instance is disposed even if an exception occurs within the block of the `using` statement. In the preceding example, an opened file is closed after all lines are processed.

Use the `await using` statement to correctly use an <xref:System.IAsyncDisposable> instance:

```csharp
await using (var resource = new AsyncDisposableExample())
{
    // Use the resource
}
```

For more information about using <xref:System.IAsyncDisposable> instances, see the [Using async disposable](../../../standard/garbage-collection/implementing-disposeasync.md#using-async-disposable) section of the [Implement a DisposeAsync method](../../../standard/garbage-collection/implementing-disposeasync.md) article.

You can also use a `using` *declaration* that doesn't require braces:

```csharp
static IEnumerable<int> LoadNumbers(string filePath)
{
    using StreamReader reader = File.OpenText(filePath);

    var numbers = new List<int>();
    string line;
    while ((line = reader.ReadLine()) is not null)
    {
        if (int.TryParse(line, out int number))
        {
            numbers.Add(number);
        }
    }
    return numbers;
}
```

When declared in a `using` declaration, a local variable is disposed at the end of the scope in which it's declared. In the preceding example, disposal happens at the end of a method.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

A variable declared by the `using` statement or declaration is readonly. You can't reassign it or pass it as a [`ref`](../keywords/ref.md) or [`out`](../keywords/method-parameters.md#out-parameter-modifier) parameter.

You can declare several instances of the same type in one `using` statement, as the following example shows:

```csharp
using (StreamReader numbersFile = File.OpenText("numbers.txt"), wordsFile = File.OpenText("words.txt"))
{
    // Process both files
}
```

When you declare several instances in one `using` statement, they are disposed in reverse order of declaration.

You can also use the `using` statement and declaration with an instance of a [ref struct](../builtin-types/ref-struct.md) that fits the disposable pattern. That is, it has an instance `Dispose` method that's accessible, parameterless, and has a `void` return type.

A `return` inside a `using` block still guarantees disposal. The compiler rewrites it into a `try/finally`, so the resource’s `Dispose` is always called before the method actually returns.

The `using` statement can also be of the following form:

```csharp
using (expression)
{
    // ...
}
```

where `expression` produces a disposable instance. The following example demonstrates that form:

```csharp
StreamReader reader = File.OpenText(filePath);

using (reader)
{
    // Process file content
}
```

> [!WARNING]
> In the preceding example, after control leaves the `using` statement, a disposable instance remains in scope while it's already disposed. If you use that instance further, you might encounter an exception, for example, <xref:System.ObjectDisposedException>. That's why you should declare a disposable variable within the `using` statement or with the `using` declaration.

## C# language specification

For more information, see [The using statement](~/_csharpstandard/standard/statements.md#1314-the-using-statement) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- <xref:System.IDisposable?displayProperty=nameWithType>
- <xref:System.IAsyncDisposable?displayProperty=nameWithType>
- [Using objects that implement IDisposable](../../../standard/garbage-collection/using-objects.md)
- [Implement a Dispose method](../../../standard/garbage-collection/implementing-dispose.md)
- [Implement a DisposeAsync method](../../../standard/garbage-collection/implementing-disposeasync.md)
- [Use simple 'using' statement (style rule IDE0063)](../../../fundamentals/code-analysis/style-rules/ide0063.md)
- [`using` directive](../keywords/using-directive.md)
