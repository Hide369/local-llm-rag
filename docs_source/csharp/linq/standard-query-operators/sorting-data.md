---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/linq/standard-query-operators/sorting-data.md
title: Sorting Data
version: 0.0.0
fetched_at: 2026-09-13
---
# Sorting Data (C#)

A sorting operation orders the elements of a sequence based on one or more attributes. The first sort criterion performs a primary sort on the elements. By specifying a second sort criterion, you can sort the elements within each primary sort group.

[!INCLUDE [Prerequisites](../includes/linq-syntax.md)]

The following illustration shows the results of an alphabetical sort operation on a sequence of characters:

:::image type="content" source="./media/sorting-data/alphabetical-sort-operation.png" alt-text="Graphic that shows an alphabetical sort operation.":::

The standard query operator methods that sort data are listed in the following section.

## Methods

|Method Name|Description|C# Query Expression Syntax|More Information|
|-----------------|-----------------|---------------------------------|----------------------|
|OrderBy|Sorts values in ascending order.|`orderby`|<xref:System.Linq.Enumerable.OrderBy*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.OrderBy*?displayProperty=nameWithType>|
|OrderByDescending|Sorts values in descending order.|`orderby … descending`|<xref:System.Linq.Enumerable.OrderByDescending*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.OrderByDescending*?displayProperty=nameWithType>|
|ThenBy|Performs a secondary sort in ascending order.|`orderby …, …`|<xref:System.Linq.Enumerable.ThenBy*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.ThenBy*?displayProperty=nameWithType>|
|ThenByDescending|Performs a secondary sort in descending order.|`orderby …, … descending`|<xref:System.Linq.Enumerable.ThenByDescending*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.ThenByDescending*?displayProperty=nameWithType>|
|Reverse|Reverses the order of the elements in a collection.|Not applicable.|<xref:System.Linq.Enumerable.Reverse*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.Reverse*?displayProperty=nameWithType>|

[!INCLUDE [Datasources](../includes/data-sources-definition.md)]

[!INCLUDE [Common Datasources reference](../includes/common-data-sources-reference.md)]

## Primary Ascending Sort

The following example demonstrates how to use the `orderby` clause in a LINQ query to sort the array of teachers by family name, in ascending order.

```csharp
IEnumerable<string> query = from teacher in teachers
                            orderby teacher.Last
                            select teacher.Last;

foreach (string str in query)
{
    Console.WriteLine(str);
}
```

The equivalent query written using method syntax is shown in the following code:

```csharp
IEnumerable<string> query = teachers
    .OrderBy(teacher => teacher.Last)
    .Select(teacher => teacher.Last);

foreach (string str in query)
{
    Console.WriteLine(str);
}
```

## Primary Descending Sort

The next example demonstrates how to use the `orderby descending` clause in a LINQ query to sort the teachers by family name, in descending order.

```csharp
IEnumerable<string> query = from teacher in teachers
                            orderby teacher.Last descending
                            select teacher.Last;

foreach (string str in query)
{
    Console.WriteLine(str);
}
```

The equivalent query written using method syntax is shown in the following code:

```csharp
IEnumerable<string> query = teachers
    .OrderByDescending(teacher => teacher.Last)
    .Select(teacher => teacher.Last);

foreach (string str in query)
{
    Console.WriteLine(str);
}
```

## Secondary Ascending Sort

The following example demonstrates how to use the `orderby` clause in a LINQ query to perform a primary and secondary sort. The teachers are sorted primarily by city and secondarily by their family name, both in ascending order.

```csharp
IEnumerable<(string, string)> query = from teacher in teachers
                            orderby teacher.City, teacher.Last
                            select (teacher.Last, teacher.City);

foreach ((string last, string city) in query)
{
    Console.WriteLine($"City: {city}, Last Name: {last}");
}
```

The equivalent query written using method syntax is shown in the following code:

```csharp
IEnumerable<(string, string)> query = teachers
    .OrderBy(teacher => teacher.City)
    .ThenBy(teacher => teacher.Last)
    .Select(teacher => (teacher.Last, teacher.City));

foreach ((string last, string city) in query)
{
    Console.WriteLine($"City: {city}, Last Name: {last}");
}
```

## Secondary Descending Sort

The next example demonstrates how to use the `orderby descending` clause in a LINQ query to perform a primary sort, in ascending order, and a secondary sort, in descending order. The teachers are sorted primarily by city and secondarily by their family name.

```csharp
IEnumerable<(string, string)> query = from teacher in teachers
                            orderby teacher.City, teacher.Last descending
                            select (teacher.Last, teacher.City);

foreach ((string last, string city) in query)
{
    Console.WriteLine($"City: {city}, Last Name: {last}");
}
```

The equivalent query written using method syntax is shown in the following code:

```csharp
IEnumerable<(string, string)> query = teachers
    .OrderBy(teacher => teacher.City)
    .ThenByDescending(teacher => teacher.Last)
    .Select(teacher => (teacher.Last, teacher.City));

foreach ((string last, string city) in query)
{
    Console.WriteLine($"City: {city}, Last Name: {last}");
}
```

## See also

- <xref:System.Linq>
- [orderby clause](../../language-reference/keywords/orderby-clause.md)
- [How to sort or filter text data by any word or field (LINQ) (C#)](../how-to-query-strings.md)
