---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/by.md
title: by contextual keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# by (C# Reference)

Use the `by` contextual keyword in the `group` clause of a query expression to specify how to group the returned items. For more information, see [group clause](./group-clause.md).

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows how to use the `by` contextual keyword in a `group` clause to group students by the first letter of each student's last name.

```csharp
var query = from student in students
            group student by student.LastName[0];
```

## See also

- [LINQ in C#](../../linq/index.md)
