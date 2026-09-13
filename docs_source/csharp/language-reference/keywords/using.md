---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/using.md
title: using keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# using (C# reference)

The `using` keyword has two major uses:

- The [`using` statement](../statements/using.md) defines a scope at the end of which an object is disposed:
```csharp
string filePath = "example.txt";
string textToWrite = "Hello, this is a test message!";

// Use the using statement to ensure the StreamWriter is properly disposed of
using (StreamWriter writer = new StreamWriter(filePath))
{
    writer.WriteLine(textToWrite);
}
```
- The [`using` directive](using-directive.md) creates an alias for a namespace or imports types defined in other namespaces:
```csharp
using System;
using System.IO;
```

## See also

- [C# keywords](index.md)
