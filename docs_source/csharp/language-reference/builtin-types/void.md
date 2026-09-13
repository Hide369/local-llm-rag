---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/builtin-types/void.md
title: void
version: 0.0.0
fetched_at: 2026-09-13
---
# void (C# reference)

Use `void` as the return type of a [method](../../programming-guide/classes-and-structs/methods.md) or a [local function](../../programming-guide/classes-and-structs/local-functions.md) to specify that the method doesn't return a value.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

```csharp
public static void Display(IEnumerable<int> numbers)
{
    if (numbers is null)
    {
        return;
    }

    Console.WriteLine(string.Join(" ", numbers));
}
```

You can also use `void` as a referent type to declare a pointer to an unknown type. For more information, see [Pointer types](../unsafe-code.md#pointer-types).

You can't use `void` as the type of a variable.

## See also

- <xref:System.Void?displayProperty=nameWithType>
