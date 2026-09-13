---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/statements/iteration.md
title: Iteration statements in C#
version: 0.0.0
fetched_at: 2026-09-13
---

# Iteration statements

> [!TIP]
> This article is part of the **Fundamentals** section for developers who already know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first. For the complete syntax, see [iteration statements](../../language-reference/statements/iteration-statements.md) in the language reference.
>
> **Coming from another language?** All four C# loops (`foreach`, `while`, `do`-`while`, and `for`) have direct equivalents in Java, C++, and JavaScript. You use `foreach` most often. It iterates a collection without an index, like Java's enhanced `for` or JavaScript's `for...of`.

Iteration statements run a block of code repeatedly. Each pass through the block is an *iteration*, and a repeating block is a *loop*. C# provides four loops. Start with `foreach` for collections, use `while` and `do`-`while` when a condition controls the repetition, and use `for` when you need an explicit index.

## Iterate a collection with `foreach`

The `foreach` statement runs its body once for each element in a collection, in order. It's the most common choice for reading a collection because you don't manage an index or a bounds check. The `foreach` statement prevents typical off-by-one errors:

```csharp
string[] names = ["Ana", "Ben", "Cleo"];

// foreach reads each element in order. It's the default loop for
// collections: no index to manage and no off-by-one mistakes.
foreach (string name in names)
{
    Console.WriteLine(name); // => Ana, then Ben, then Cleo
}
```

`foreach` works with any type that C# recognizes as a sequence, including arrays, <xref:System.Collections.Generic.List`1>, and <xref:System.Collections.Generic.Dictionary`2>. The iteration variable (`name` in the previous example) is read-only, so you can't reassign it inside the loop.

The body of a loop is a single *statement*, such as an assignment or a method call. A *block statement* is itself a single statement that encloses zero or more statements in braces (`{ }`).

Many coding standards recommend that you enclose the loop body in braces, even for a single statement. Braces make the scope explicit. It prevents a common mistake: adding a second line later that you expect to run each iteration, but that runs once after the loop instead. Only the braces decide which statements belong to the loop. C# doesn't treat whitespace as significant, so indentation alone never does. Braces are legal even around one line: the block is the single statement that the loop repeats. Indent your code for readability, but rely on braces to define the block.

## Repeat while a condition holds with `while`

A `while` loop checks its Boolean condition *before* each iteration. If the condition is `false` at the start, the body never runs, so a `while` loop runs zero or more times:

```csharp
int countdown = 3;

// A while loop checks its condition before each iteration, so the body
// runs zero or more times.
while (countdown > 0)
{
    Console.WriteLine(countdown); // => 3, then 2, then 1
    countdown--;
}
```

Make sure something inside the loop changes the condition. In the previous example, `countdown--` eventually makes the condition `false`. A loop whose condition never becomes `false` runs forever.

## Run the body at least once with `do`-`while`

A `do`-`while` loop checks its condition *after* each iteration, so the body always runs at least once. Use it when the first pass must happen before you can evaluate the condition, such as prompting for input and then validating it:

```csharp
int attempts = 0;

// A do-while loop runs its body once, then checks the condition. Use it
// when the body must run at least one time.
do
{
    attempts++;
    Console.WriteLine($"Attempt {attempts}"); // => Attempt 1, then Attempt 2, then Attempt 3
}
while (attempts < 3);
```

## Count with `for`

A `for` loop statement contains three parts: an *initializer* that runs once before the loop, a *condition* that's checked before each iteration, and an *iterator* that runs after each iteration. Use `for` when you need the index itself, not just the elements. Typically, you need the index when you want to modify the element rather than reading its value.

```csharp
// A for loop fits when you need an explicit index. The three parts are
// the initializer, the condition, and the iterator.
for (int i = 0; i < 3; i++)
{
    Console.WriteLine(i); // => 0, then 1, then 2
}
```

When you only read the elements, when you don't use the positions or assign new values, prefer `foreach`. It states the intent more clearly and avoids index arithmetic.

## Exit or skip with `break` and `continue`

Two jump statements give you finer control inside any loop. The `break` statement exits the loop immediately, skipping any remaining iterations:

```csharp
int[] numbers = [2, 4, 7, 8];

// break stops the loop immediately, skipping any remaining elements.
foreach (int number in numbers)
{
    if (number % 2 != 0)
    {
        Console.WriteLine($"First odd number: {number}"); // => First odd number: 7
        break;
    }
}
```

The `continue` statement skips the rest of the current iteration and moves on to the next one:

```csharp
int[] values = [1, 2, 3, 4, 5];

// continue skips the rest of the current iteration and moves to the next.
foreach (int value in values)
{
    if (value % 2 == 0)
    {
        continue; // skip even numbers
    }

    Console.WriteLine(value); // => 1, then 3, then 5
}
```

## Iterate an asynchronous stream with `await foreach`

An *asynchronous stream* is a reader that uses an asynchronous task to produce each next element. C# represents it with the <xref:System.Collections.Generic.IAsyncEnumerable`1> interface. Data that arrives over time, such as pages from a web API or rows from a database, fits this model: retrieving the next element is an awaitable operation instead of an immediate return.

To consume an asynchronous stream, put the `await` keyword before `foreach`. Each iteration awaits the next element, so the loop suspends while that element is produced instead of blocking the thread:

```csharp
private static async Task AwaitForeachExample()
{
    // await foreach consumes an asynchronous stream. Each iteration can
    // suspend while the next element is produced.
    await foreach (int value in GenerateAsync())
    {
        Console.WriteLine(value); // => 0, then 1, then 2
    }
}

private static async IAsyncEnumerable<int> GenerateAsync()
{
    for (int i = 0; i < 3; i++)
    {
        await Task.Delay(1); // stand-in for real asynchronous work
        yield return i;
    }
}
```

Asynchronous streams build on `async` and `await`. For a full walkthrough, see [Generate and consume asynchronous streams](../../asynchronous-programming/generate-consume-asynchronous-stream.md).

## See also

- [Selection statements](selection.md)
- [Iteration statements (language reference)](../../language-reference/statements/iteration-statements.md)
- [Generate and consume asynchronous streams](../../asynchronous-programming/generate-consume-asynchronous-stream.md)
