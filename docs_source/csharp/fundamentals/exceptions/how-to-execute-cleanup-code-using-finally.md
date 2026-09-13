---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/exceptions/how-to-execute-cleanup-code-using-finally.md
title: How to execute cleanup code using finally
version: 0.0.0
fetched_at: 2026-09-13
---
# How to execute cleanup code using finally

The purpose of a `finally` statement is to ensure that the necessary cleanup of objects, usually objects that are holding external resources, occurs immediately, even if an exception is thrown. One example of such cleanup is calling <xref:System.IO.Stream.Close*> on a <xref:System.IO.FileStream> immediately after use instead of waiting for the object to be garbage collected by the common language runtime, as follows:

```csharp
static void CodeWithoutCleanup()
{
    FileStream? file = null;
    FileInfo fileInfo = new FileInfo("./file.txt");

    file = fileInfo.OpenWrite();
    file.WriteByte(0xF);

    file.Close();
}
```

## Example

To turn the previous code into a `try-catch-finally` statement, the cleanup code is separated from the working code, as follows.

```csharp
static void CodeWithCleanup()
{
    FileStream? file = null;
    FileInfo? fileInfo = null;

    try
    {
        fileInfo = new FileInfo("./file.txt");

        file = fileInfo.OpenWrite();
        file.WriteByte(0xF);
    }
    catch (UnauthorizedAccessException e)
    {
        Console.WriteLine(e.Message);
    }
    finally
    {
        file?.Close();
    }
}
```

Because an exception can occur at any time within the `try` block before the `OpenWrite()` call, or the `OpenWrite()` call itself could fail, we aren't guaranteed that the file is open when we try to close it. The `finally` block adds a check to make sure that the <xref:System.IO.FileStream> object isn't `null` before you call the <xref:System.IO.Stream.Close*> method. Without the `null` check, the `finally` block could throw its own <xref:System.NullReferenceException>, but throwing exceptions in `finally` blocks should be avoided if it's possible.

A database connection is another good candidate for being closed in a `finally` block. Because the number of connections allowed to a database server is sometimes limited, you should close database connections as quickly as possible. If an exception is thrown before you can close your connection, using the `finally` block is better than waiting for garbage collection.

## See also

- [using statement](../../language-reference/statements/using.md)
- [Exception-handling statements](../../language-reference/statements/exception-handling-statements.md)
