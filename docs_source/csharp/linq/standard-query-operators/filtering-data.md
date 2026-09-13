---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/linq/standard-query-operators/filtering-data.md
title: Filtering Data with LINQ
version: 0.0.0
fetched_at: 2026-09-13
---
# Filtering Data in C# with LINQ

Filtering refers to the operation of restricting the result set to contain only those elements that satisfy a specified condition. It's also referred to as *selecting* elements that match the specified condition.

[!INCLUDE [Prerequisites](../includes/linq-syntax.md)]

The following illustration shows the results of filtering a sequence of characters. The predicate for the filtering operation specifies that the character must be 'A'.

:::image type="content" source="./media/filtering-data/linq-filter-operation.png" alt-text="Diagram that shows a LINQ filtering operation":::

The standard query operator methods that perform selection are listed in the following table:

|Method Name|Description|C# Query Expression Syntax|More Information|
|-----------------|-----------------|---------------------------------|----------------------|
|OfType|Selects values, depending on their ability to be cast to a specified type.|Not applicable.|<xref:System.Linq.Enumerable.OfType*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.OfType*?displayProperty=nameWithType>|
|Where|Selects values that are based on a predicate function.|`where`|<xref:System.Linq.Enumerable.Where*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.Where*?displayProperty=nameWithType>|

The following example uses the `where` clause to filter from an array those strings that have a specific length.

[!INCLUDE [Common Datasources reference](../includes/common-data-sources-reference.md)]

```csharp
string[] words = ["the", "quick", "brown", "fox", "jumps"];

IEnumerable<string> query = from word in words
                            where word.Length == 3
                            select word;

foreach (string str in query)
{
    Console.WriteLine(str);
}

/* This code produces the following output:

    the
    fox
*/
```

The equivalent query using method syntax is shown in the following code:

```csharp
string[] words = ["the", "quick", "brown", "fox", "jumps"];

IEnumerable<string> query =
    words.Where(word => word.Length == 3);

foreach (string str in query)
{
    Console.WriteLine(str);
}

/* This code produces the following output:

    the
    fox
*/
```

## See also

- <xref:System.Linq>
- [where clause](../../language-reference/keywords/where-clause.md)
- [How to query an assembly's metadata with Reflection (LINQ) (C#)](../../advanced-topics/reflection-and-attributes/how-to-query-assembly-metadata-with-reflection-linq.md)
- [How to query for files with a specified attribute or name (C#)](../how-to-query-files-and-directories.md)
- [How to sort or filter text data by any word or field (LINQ) (C#)](../how-to-query-strings.md)
