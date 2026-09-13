---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/from-clause.md
title: from clause
version: 0.0.0
fetched_at: 2026-09-13
---
# from clause (C# Reference)

A query expression must begin with a `from` clause. Additionally, a query expression can contain subqueries, which also begin with a `from` clause. The `from` clause specifies the following:

- The data source on which the query or subquery runs.
- A local *range variable* that represents each element in the source sequence.

Both the range variable and the data source are strongly typed. The data source referenced in the `from` clause must have a type of <xref:System.Collections.IEnumerable>, <xref:System.Collections.Generic.IEnumerable`1>, or a derived type such as <xref:System.Linq.IQueryable`1>.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

In the following example, `numbers` is the data source and `num` is the range variable. Note that both variables are strongly typed even though the [var](../statements//declarations.md#implicitly-typed-local-variables) keyword is used.

:::code language="csharp" source="./snippets/from.cs" id="1":::

## The range variable

The compiler infers the type of the range variable when the data source implements <xref:System.Collections.Generic.IEnumerable`1>. For example, if the source has a type of `IEnumerable<Customer>`, then the range variable is inferred to be `Customer`. You must specify the type explicitly only when the source is a non-generic `IEnumerable` type such as <xref:System.Collections.ArrayList>. For more information, see [How to query an ArrayList with LINQ](../../linq/how-to-query-collections.md).

In the previous example, `num` is inferred to be of type `int`. Because the range variable is strongly typed, you can call methods on it or use it in other operations. For example, instead of writing `select num`, you could write `select num.ToString()` to cause the query expression to return a sequence of strings instead of integers. Or you could write `select num + 10` to cause the expression to return the sequence 14, 11, 13, 12, 10. For more information, see [select clause](select-clause.md).

The range variable is like an iteration variable in a [foreach](../statements/iteration-statements.md#the-foreach-statement) statement except for one very important difference: a range variable never actually stores data from the source. It's just a syntactic convenience that enables the query to describe what occurs when the query is executed. For more information, see [Introduction to LINQ Queries (C#)](../../linq/get-started/introduction-to-linq-queries.md).

## Compound from clauses

In some cases, each element in the source sequence might itself be either a sequence or contain a sequence. For example, your data source might be an `IEnumerable<Student>` where each student object in the sequence contains a list of test scores. To access the inner list within each `Student` element, you can use compound `from` clauses. The technique is like using nested [foreach](../statements/iteration-statements.md#the-foreach-statement) statements. You can add [where](partial-member.md) or [orderby](orderby-clause.md) clauses to either `from` clause to filter the results. The following example shows a sequence of `Student` objects, each of which contains an inner `List` of integers representing test scores. To access the inner list, use a compound `from` clause. You can insert clauses between the two `from` clauses if necessary.

```csharp
class CompoundFrom
{
    // The element type of the data source.
    public class Student
    {
        public required string LastName { get; init; }
        public required List<int> Scores {get; init;}
    }

    static void Main()
    {

        // Use a collection initializer to create the data source. Note that
        // each element in the list contains an inner sequence of scores.
        List<Student> students =
        [
           new Student {LastName="Omelchenko", Scores= [97, 72, 81, 60]},
           new Student {LastName="O'Donnell", Scores= [75, 84, 91, 39]},
           new Student {LastName="Mortensen", Scores= [88, 94, 65, 85]},
           new Student {LastName="Garcia", Scores= [97, 89, 85, 82]},
           new Student {LastName="Beebe", Scores= [35, 72, 91, 70]}
        ];

        // Use a compound from to access the inner sequence within each element.
        // Note the similarity to a nested foreach statement.
        var scoreQuery = from student in students
                         from score in student.Scores
                            where score > 90
                            select new { Last = student.LastName, score };

        // Execute the queries.
        Console.WriteLine("scoreQuery:");
        // Rest the mouse pointer on scoreQuery in the following line to
        // see its type. The type is IEnumerable<'a>, where 'a is an
        // anonymous type defined as new {string Last, int score}. That is,
        // each instance of this anonymous type has two members, a string
        // (Last) and an int (score).
        foreach (var student in scoreQuery)
        {
            Console.WriteLine($"{student.Last} Score: {student.score}");
        }
    }
}
/*
scoreQuery:
Omelchenko Score: 97
O'Donnell Score: 91
Mortensen Score: 94
Garcia Score: 97
Beebe Score: 91
*/
```

## Using multiple from clauses to perform joins

Use a compound `from` clause to access inner collections in a single data source. However, a query can also contain multiple `from` clauses that generate supplemental queries from independent data sources. By using this technique, you can perform certain types of join operations that aren't possible by using the [join clause](join-clause.md).

The following example shows how two `from` clauses form a complete cross join of two data sources.

:::code language="csharp" source="./snippets/from.cs" id="3":::

For more information about join operations that use multiple `from` clauses, see [Perform left outer joins](../../linq/standard-query-operators/join-operations.md).

## See also

- [Query Keywords (LINQ)](query-keywords.md)
- [Language Integrated Query (LINQ)](../../linq/index.md)
