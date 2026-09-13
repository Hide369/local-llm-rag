---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/linq/standard-query-operators/set-operations.md
title: Set operations
version: 0.0.0
fetched_at: 2026-09-13
---
# Set operations (C#)

Set operations in LINQ refer to query operations that produce a result set based on the presence or absence of equivalent elements within the same or separate collections.

[!INCLUDE [Prerequisites](../includes/linq-syntax.md)]

| Method names | Description | C# query expression syntax | More information |
|--|--|--|--|
| `Distinct` or `DistinctBy` | Removes duplicate values from a collection. | Not applicable. | <xref:System.Linq.Enumerable.Distinct*?displayProperty=nameWithType><br /><xref:System.Linq.Enumerable.DistinctBy*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Distinct*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.DistinctBy*?displayProperty=nameWithType> |
| `Except` or `ExceptBy` | Returns the set difference, which means the elements of one collection that don't appear in a second collection. | Not applicable. | <xref:System.Linq.Enumerable.Except*?displayProperty=nameWithType><br /><xref:System.Linq.Enumerable.ExceptBy*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Except*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.ExceptBy*?displayProperty=nameWithType> |
| `Intersect` or `IntersectBy` | Returns the set intersection, which means elements that appear in each of two collections. | Not applicable. | <xref:System.Linq.Enumerable.Intersect*?displayProperty=nameWithType><br /><xref:System.Linq.Enumerable.IntersectBy*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Intersect*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.IntersectBy*?displayProperty=nameWithType> |
| `Union` or `UnionBy` | Returns the set union, which means unique elements that appear in either of two collections. | Not applicable. | <xref:System.Linq.Enumerable.Union*?displayProperty=nameWithType><br /><xref:System.Linq.Enumerable.UnionBy*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.Union*?displayProperty=nameWithType><br /><xref:System.Linq.Queryable.UnionBy*?displayProperty=nameWithType> |

## `Distinct` and `DistinctBy`

The following example depicts the behavior of the <xref:System.Linq.Enumerable.Distinct*?displayProperty=nameWithType> method on a sequence of strings. The returned sequence contains the unique elements from the input sequence.

:::image type="content" source="./media/set-operations/distinct-method-behavior.png" alt-text="Graphic showing the behavior of Distinct()":::

```csharp
string[] words = ["the", "quick", "brown", "fox", "jumped", "over", "the", "lazy", "dog"];

IEnumerable<string> query = from word in words.Distinct()
                            select word;

foreach (var str in query)
{
    Console.WriteLine(str);
}

/* This code produces the following output:
 *
 * the
 * quick
 * brown
 * fox
 * jumped
 * over
 * lazy
 * dog
 */
```

The [`DistinctBy`](xref:System.Linq.Enumerable.DistinctBy*?displayProperty=nameWithType) is an alternative approach to `Distinct` that takes a `keySelector`. The `keySelector` is used as the comparative discriminator of the source type. In the following code, words are discriminated based on their `Length`, and the first word of each length is displayed:

```csharp
string[] words = ["the", "quick", "brown", "fox", "jumped", "over", "the", "lazy", "dog"];

foreach (string word in words.DistinctBy(p => p.Length))
{
    Console.WriteLine(word);
}

// This code produces the following output:
//     the
//     quick
//     jumped
//     over
```

## `Except` and `ExceptBy`

The following example depicts the behavior of <xref:System.Linq.Enumerable.Except*?displayProperty=nameWithType>. The returned sequence contains only the elements from the first input sequence that aren't in the second input sequence.

:::image type="content" source="./media/set-operations/except-behavior-graphic.png" alt-text="Graphic showing the action of Except()":::

[!INCLUDE [Datasources](../includes/data-sources-definition.md)]

[!INCLUDE [Common Datasources reference](../includes/common-data-sources-reference.md)]

```csharp
string[] words1 = ["the", "quick", "brown", "fox"];
string[] words2 = ["jumped", "over", "the", "lazy", "dog"];

IEnumerable<string> query = from word in words1.Except(words2)
                            select word;

foreach (var str in query)
{
    Console.WriteLine(str);
}

/* This code produces the following output:
 *
 * quick
 * brown
 * fox
 */
```

The <xref:System.Linq.Enumerable.ExceptBy*> method is an alternative approach to `Except` that takes two sequences of possibly heterogenous types and a `keySelector`. The `keySelector` is the same type as the first collection's type. Consider the following `Teacher` array and teacher IDs to exclude. To find teachers in the first collection that aren't in the second collection, you can project the teacher's ID onto the second collection:

```csharp
int[] teachersToExclude =
[
    901,    // English
    965,    // Mathematics
    932,    // Engineering
    945,    // Economics
    987,    // Physics
    901     // Chemistry
];

foreach (Teacher teacher in
    teachers.ExceptBy(
        teachersToExclude, teacher => teacher.ID))
{
    Console.WriteLine($"{teacher.First} {teacher.Last}");
}
```

In the preceding C# code:

- The `teachers` array is filtered to only those teachers that aren't in the `teachersToExclude` array.
- The `teachersToExclude` array contains the `ID` value for all department heads.
- The call to `ExceptBy` results in a new set of values that are written to the console.

The new set of values is of type `Teacher`, which is the type of the first collection. Each `teacher` in the `teachers` array that doesn't have a corresponding ID value in the `teachersToExclude` array is written to the console.

## `Intersect` and `IntersectBy`

The following example depicts the behavior of <xref:System.Linq.Enumerable.Intersect*?displayProperty=nameWithType>. The returned sequence contains the elements that are common to both of the input sequences.

:::image type="content" source="./media/set-operations/intersection-two-sequences.png" alt-text="Graphic showing the intersection of two sequences":::

```csharp
string[] words1 = ["the", "quick", "brown", "fox"];
string[] words2 = ["jumped", "over", "the", "lazy", "dog"];

IEnumerable<string> query = from word in words1.Intersect(words2)
                            select word;

foreach (var str in query)
{
    Console.WriteLine(str);
}

/* This code produces the following output:
 *
 * the
 */
```

The <xref:System.Linq.Enumerable.IntersectBy*> method is an alternative approach to `Intersect` that takes two sequences of possibly heterogenous types and a `keySelector`. The `keySelector` is used as the comparative discriminator of the second collection's type. Consider the following student and teacher arrays. The query matches items in each sequence by name to find those students who are also teachers:

```csharp
foreach (Student person in
    students.IntersectBy(
        teachers.Select(t => (t.First, t.Last)), s => (s.FirstName, s.LastName)))
{
    Console.WriteLine($"{person.FirstName} {person.LastName}");
}
```

In the preceding C# code:

- The query produces the intersection of the `Teacher` and `Student` by comparing names.
- Only people that are found in both arrays are present in the resulting sequence.
- The resulting `Student` instances are written to the console.

## `Union` and `UnionBy`

The following example depicts a union operation on two sequences of strings. The returned sequence contains the unique elements from both input sequences.

:::image type="content" source="./media/set-operations/union-operation-two-sequences.png" alt-text="Graphic showing the union of two sequences.":::

```csharp
string[] words1 = ["the", "quick", "brown", "fox"];
string[] words2 = ["jumped", "over", "the", "lazy", "dog"];

IEnumerable<string> query = from word in words1.Union(words2)
                            select word;

foreach (var str in query)
{
    Console.WriteLine(str);
}

/* This code produces the following output:
 *
 * the
 * quick
 * brown
 * fox
 * jumped
 * over
 * lazy
 * dog
*/
```

The <xref:System.Linq.Enumerable.UnionBy*> method is an alternative approach to `Union` that takes two sequences of the same type and a `keySelector`. The `keySelector` is used as the comparative discriminator of the source type. The following query produces the list of all people that are either students or teachers. Students who are also teachers are added to the union set only once:

```csharp
foreach (var person in
    students.Select(s => (s.FirstName, s.LastName)).UnionBy(
        teachers.Select(t => (FirstName: t.First, LastName: t.Last)), s => (s.FirstName, s.LastName)))
{
    Console.WriteLine($"{person.FirstName} {person.LastName}");
}
```

In the preceding C# code:

- The `teachers` and `students` arrays are woven together using their names as the key selector.
- The resulting names are written to the console.

## See also

- <xref:System.Linq>
- [How to find the set difference between two lists (LINQ) (C#)](../how-to-query-collections.md)
