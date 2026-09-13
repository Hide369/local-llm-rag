---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/linq/standard-query-operators/quantifier-operations.md
title: Quantifier Operations
version: 0.0.0
fetched_at: 2026-09-13
---
# Quantifier operations in LINQ (C#)

Quantifier operations return a <xref:System.Boolean> value that indicates whether some or all of the elements in a sequence satisfy a condition.

[!INCLUDE [Prerequisites](../includes/linq-syntax.md)]

The following illustration depicts two different quantifier operations on two different source sequences. The first operation asks if any of the elements are the character 'A'. The second operation asks if all the elements are the character 'A'. Both methods return `true` in this example.

:::image type="content" source="./media/quantifier-operations/linq-quantifier-operations.png" alt-text="LINQ Quantifier Operations":::

|Method Name|Description|C# Query Expression Syntax|More Information|
|-----------------|-----------------|---------------------------------|----------------------|
|All|Determines whether all the elements in a sequence satisfy a condition.|Not applicable.|<xref:System.Linq.Enumerable.All*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.All*?displayProperty=nameWithType>|
|Any|Determines whether any elements in a sequence satisfy a condition.|Not applicable.|<xref:System.Linq.Enumerable.Any*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Any*?displayProperty=nameWithType>|
|Contains|Determines whether a sequence contains a specified element.|Not applicable.|<xref:System.Linq.Enumerable.Contains*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Contains*?displayProperty=nameWithType>|

## All

The following example uses the `All` to find students that scored above 70 on all exams.

[!INCLUDE [Common Datasources reference](../includes/common-data-sources-reference.md)]

```csharp
IEnumerable<string> names = from student in students
                            where student.Scores.All(score => score > 70)
                            select $"{student.FirstName} {student.LastName}: {string.Join(", ", student.Scores.Select(s => s.ToString()))}";

foreach (string name in names)
{
    Console.WriteLine($"{name}");
}

// This code produces the following output:
//
// Cesar Garcia: 71, 86, 77, 97
// Nancy Engström: 75, 73, 78, 83
// Ifunanya Ugomma: 84, 82, 96, 80
```

## Any

The following example uses the `Any` to find students that scored greater than 95 on any exam.

```csharp
IEnumerable<string> names = from student in students
                            where student.Scores.Any(score => score > 95)
                            select $"{student.FirstName} {student.LastName}: {student.Scores.Max()}";

foreach (string name in names)
{
    Console.WriteLine($"{name}");
}

// This code produces the following output:
//
// Svetlana Omelchenko: 97
// Cesar Garcia: 97
// Debra Garcia: 96
// Ifeanacho Jamuike: 98
// Ifunanya Ugomma: 96
// Michelle Caruana: 97
// Nwanneka Ifeoma: 98
// Martina Mattsson: 96
// Anastasiya Sazonova: 96
// Jesper Jakobsson: 98
// Max Lindgren: 96
```

## Contains

The following example uses the `Contains` to find students that scored exactly 95 on an exam.

```csharp
IEnumerable<string> names = from student in students
                            where student.Scores.Contains(95)
                            select $"{student.FirstName} {student.LastName}: {string.Join(", ", student.Scores.Select(s => s.ToString()))}";

foreach (string name in names)
{
    Console.WriteLine($"{name}");
}

// This code produces the following output:
//
// Claire O'Donnell: 56, 78, 95, 95
// Donald Urquhart: 92, 90, 95, 57
```

## See also

- <xref:System.Linq>
- [Dynamically specify predicate filters at run time](../get-started/write-linq-queries.md)
- [How to query for sentences that contain a specified set of words (LINQ) (C#)](../how-to-query-strings.md)
