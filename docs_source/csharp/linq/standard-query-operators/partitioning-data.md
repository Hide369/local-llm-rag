---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/linq/standard-query-operators/partitioning-data.md
title: Partitioning data
version: 0.0.0
fetched_at: 2026-09-13
---
# Partitioning data (C#)

Partitioning in LINQ refers to the operation of dividing an input sequence into two sections, without rearranging the elements, and then returning one of the sections.

[!INCLUDE [Prerequisites](../includes/linq-syntax.md)]

The following illustration shows the results of three different partitioning operations on a sequence of characters. The first operation returns the first three elements in the sequence. The second operation skips the first three elements and returns the remaining elements. The third operation skips the first two elements in the sequence and returns the next three elements.

:::image type="content" source="./media/partitioning-data/linq-partitioning-operations.png" alt-text="Illustration that shows three LINQ partitioning operations.":::

The standard query operator methods that partition sequences are listed in the following section.

## Operators

| Method names | Description | C# query expression syntax | More information |
|--|--|--|--|
| Skip | Skips elements up to a specified position in a sequence. | Not applicable. | <xref:System.Linq.Enumerable.Skip*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Skip*?displayProperty=nameWithType> |
| SkipWhile | Skips elements based on a predicate function until an element doesn't satisfy the condition. | Not applicable. | <xref:System.Linq.Enumerable.SkipWhile*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.SkipWhile*?displayProperty=nameWithType> |
| Take | Takes elements up to a specified position in a sequence. | Not applicable. | <xref:System.Linq.Enumerable.Take*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Take*?displayProperty=nameWithType> |
| TakeWhile | Takes elements based on a predicate function until an element doesn't satisfy the condition. | Not applicable. | <xref:System.Linq.Enumerable.TakeWhile*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.TakeWhile*?displayProperty=nameWithType> |
| Chunk | Splits the elements of a sequence into chunks of a specified maximum size. | Not applicable. | <xref:System.Linq.Enumerable.Chunk*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Chunk*?displayProperty=nameWithType> |

All the following examples use <xref:System.Linq.Enumerable.Range(System.Int32,System.Int32)?displayProperty=nameWithType> to generate a sequence of numbers from 0 through 7.

[!INCLUDE [Common Datasources reference](../includes/common-data-sources-reference.md)]

You use the `Take` method to take only the first elements in a sequence:

```csharp
foreach (int number in Enumerable.Range(0, 8).Take(3))
{
    Console.WriteLine(number);
}
// This code produces the following output:
// 0
// 1
// 2
```

You use the `Skip` method to skip the first elements in a sequence, and use the remaining elements:

```csharp
foreach (int number in Enumerable.Range(0, 8).Skip(3))
{
    Console.WriteLine(number);
}
// This code produces the following output:
// 3
// 4
// 5
// 6
// 7
```

The `TakeWhile` and `SkipWhile` methods also take and skip elements in a sequence. However, instead of a set number of elements, these methods skip or take elements based on a condition. `TakeWhile` takes the elements of a sequence until an element doesn't match the condition.

```csharp
foreach (int number in Enumerable.Range(0, 8).TakeWhile(n => n < 5))
{
    Console.WriteLine(number);
}
// This code produces the following output:
// 0
// 1
// 2
// 3
// 4
```

`SkipWhile` skips the first elements, as long as the condition is true. The first element not matching the condition, and all subsequent elements, are returned.

```csharp
foreach (int number in Enumerable.Range(0, 8).SkipWhile(n => n < 5))
{
    Console.WriteLine(number);
}
// This code produces the following output:
// 5
// 6
// 7
```

The `Chunk` operator is used to split elements of a sequence based on a given `size`.

```csharp
int chunkNumber = 1;
foreach (int[] chunk in Enumerable.Range(0, 8).Chunk(3))
{
    Console.WriteLine($"Chunk {chunkNumber++}:");
    foreach (int item in chunk)
    {
        Console.WriteLine($"    {item}");
    }

    Console.WriteLine();
}
// This code produces the following output:
// Chunk 1:
//    0
//    1
//    2
//
//Chunk 2:
//    3
//    4
//    5
//
//Chunk 3:
//    6
//    7
```

The preceding C# code:

- Relies on <xref:System.Linq.Enumerable.Range(System.Int32,System.Int32)?displayProperty=nameWithType> to generate a sequence of numbers.
- Applies the `Chunk` operator, splitting the sequence into chunks with a max size of three.

## See also

- <xref:System.Linq>
