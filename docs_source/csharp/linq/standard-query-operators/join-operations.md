---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/linq/standard-query-operators/join-operations.md
title: Join Operations
version: 0.0.0
fetched_at: 2026-09-13
---
# Join operations in LINQ

A *join* associates objects in one data source with objects that share a common attribute in another data source.

[!INCLUDE [Prerequisites](../includes/linq-syntax.md)]

Joining is an important operation in queries that target data sources whose relationships to each other you can't follow directly. In object-oriented programming, joining could mean a correlation between objects that isn't modeled, such as the backwards direction of a one-way relationship. An example of a one-way relationship is a `Student` class that has a property of type `Department` that represents the major, but the `Department` class doesn't have a property that is a collection of `Student` objects. If you have a list of `Department` objects and you want to find all the students in each department, you could use a join operation to find them.

The LINQ framework provides join methods: <xref:System.Linq.Enumerable.Join*> and <xref:System.Linq.Enumerable.GroupJoin*>. These methods perform equijoins, or joins that match two data sources based on equality of their keys. For comparison, Transact-SQL supports join operators other than `equals`, such as the `less than` operator. In relational database terms, <xref:System.Linq.Enumerable.Join*> implements an inner join, a type of join in which only those objects that have a match in the other data set are returned. The <xref:System.Linq.Enumerable.GroupJoin*> method has no direct equivalent in relational database terms, but it implements a superset of inner joins and left outer joins. A left outer join is a join that returns each element of the first (left) data source, even if it has no correlated elements in the other data source.

The following illustration shows a conceptual view of two sets and the elements within those sets that are included in either an inner join or a left outer join.

:::image type="content" source="./media/join-operations/join-method-overlapping-circles.png" alt-text="Two overlapping circles showing inner/outer.":::

## Methods

|Method Name|Description|C# Query Expression Syntax|More Information|
|-----------------|-----------------|---------------------------------|----------------------|
|Join|Joins two sequences based on key selector functions and extracts pairs of values.|`join … in … on … equals …`|<xref:System.Linq.Enumerable.Join*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.Join*?displayProperty=nameWithType>|
|GroupJoin|Joins two sequences based on key selector functions and groups the resulting matches for each element.|`join … in … on … equals … into …`|<xref:System.Linq.Enumerable.GroupJoin*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.GroupJoin*?displayProperty=nameWithType>|
|LeftJoin|Correlates the elements of two sequences based on matching keys.| N/A | <xref:System.Linq.Enumerable.LeftJoin*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.LeftJoin*?displayProperty=nameWithType>|
|RightJoin|Correlates the elements of two sequences based on matching keys.| N/A | <xref:System.Linq.Enumerable.RightJoin*?displayProperty=nameWithType><br /><br /> <xref:System.Linq.Queryable.RightJoin*?displayProperty=nameWithType>|

[!INCLUDE [Datasources](../includes/data-sources-definition.md)]

[!INCLUDE [Common Datasources reference](../includes/common-data-sources-reference.md)]

The following example uses the `join … in … on … equals …` clause to join two sequences based on a specific value:

```csharp
var query = from student in students
            join department in departments on student.DepartmentID equals department.ID
            select new { Name = $"{student.FirstName} {student.LastName}", DepartmentName = department.Name };

foreach (var item in query)
{
    Console.WriteLine($"{item.Name} - {item.DepartmentName}");
}
```

You can express the preceding query by using method syntax, as shown in the following code:

```csharp
var query = students.Join(departments,
    student => student.DepartmentID, department => department.ID,
    (student, department) => new { Name = $"{student.FirstName} {student.LastName}", DepartmentName = department.Name });

foreach (var item in query)
{
    Console.WriteLine($"{item.Name} - {item.DepartmentName}");
}
```

The following example uses the `join … in … on … equals … into …` clause to join two sequences based on a specific value and group the resulting matches for each element:

```csharp
IEnumerable<IEnumerable<Student>> studentGroups = from department in departments
                    join student in students on department.ID equals student.DepartmentID into studentGroup
                    select studentGroup;

foreach (IEnumerable<Student> studentGroup in studentGroups)
{
    Console.WriteLine("Group");
    foreach (Student student in studentGroup)
    {
        Console.WriteLine($"  - {student.FirstName}, {student.LastName}");
    }
}
```

You can express the preceding query by using method syntax, as shown in the following example:

```csharp
// Join department and student based on DepartmentId and grouping result
IEnumerable<IEnumerable<Student>> studentGroups = departments.GroupJoin(students,
    department => department.ID, student => student.DepartmentID,
    (department, studentGroup) => studentGroup);

foreach (IEnumerable<Student> studentGroup in studentGroups)
{
    Console.WriteLine("Group");
    foreach (Student student in studentGroup)
    {
        Console.WriteLine($"  - {student.FirstName}, {student.LastName}");
    }
}
```

## Perform inner joins

In relational database terms, an *inner join* produces a result set in which each element of the first collection appears one time for every matching element in the second collection. If an element in the first collection has no matching elements, it doesn't appear in the result set. The <xref:System.Linq.Enumerable.Join*> method, which the `join` clause in C# calls, implements an inner join. The following examples show you how to perform four variations of an inner join:

- A simple inner join that correlates elements from two data sources based on a simple key.
- An inner join that correlates elements from two data sources based on a *composite* key. A composite key, which is a key that consists of more than one value, enables you to correlate elements based on more than one property.
- A *multiple join* in which you append successive join operations to each other.
- An inner join that uses a group join.

### Single key join

The following example matches `Teacher` objects with `Department` objects whose `TeacherId` matches that `Teacher`. The `select` clause in C# defines how the resulting objects look. In the following example, the resulting objects are anonymous types that consist of the department name and the name of the teacher that leads the department.

```csharp
var query = from department in departments
            join teacher in teachers on department.TeacherID equals teacher.ID
            select new
            {
                DepartmentName = department.Name,
                TeacherName = $"{teacher.First} {teacher.Last}"
            };

foreach (var departmentAndTeacher in query)
{
    Console.WriteLine($"{departmentAndTeacher.DepartmentName} is managed by {departmentAndTeacher.TeacherName}");
}
```

You achieve the same results by using the <xref:System.Linq.Enumerable.Join*> method syntax:

```csharp
var query = teachers
    .Join(departments, teacher => teacher.ID, department => department.TeacherID,
        (teacher, department) =>
        new { DepartmentName = department.Name, TeacherName = $"{teacher.First} {teacher.Last}" });

foreach (var departmentAndTeacher in query)
{
    Console.WriteLine($"{departmentAndTeacher.DepartmentName} is managed by {departmentAndTeacher.TeacherName}");
}
```

Teachers who aren't department heads don't appear in the final results.

### Composite key join

Instead of correlating elements based on just one property, use a composite key to compare elements based on multiple properties. Specify the key selector function for each collection to return an anonymous type that consists of the properties you want to compare. If you label the properties, they must have the same label in each key's anonymous type. The properties must also appear in the same order.

The following example uses a list of `Teacher` objects and a list of `Student` objects to determine which teachers are also students. Both of these types have properties that represent the first and family name of each person. The functions that create the join keys from each list's elements return an anonymous type that consists of the properties. The join operation compares these composite keys for equality and returns pairs of objects from each list where both the first name and the family name match.

```csharp
// Join the two data sources based on a composite key consisting of first and last name,
// to determine which employees are also students.
IEnumerable<string> query =
    from teacher in teachers
    join student in students on new
    {
        FirstName = teacher.First,
        LastName = teacher.Last
    } equals new
    {
        student.FirstName,
        student.LastName
    }
    select teacher.First + " " + teacher.Last;

string result = "The following people are both teachers and students:\r\n";
foreach (string name in query)
{
    result += $"{name}\r\n";
}
Console.Write(result);
```

You can use the <xref:System.Linq.Enumerable.Join*> method, as shown in the following example:

```csharp
IEnumerable<string> query = teachers
    .Join(students,
        teacher => new { FirstName = teacher.First, LastName = teacher.Last },
        student => new { student.FirstName, student.LastName },
        (teacher, student) => $"{teacher.First} {teacher.Last}"
 );

Console.WriteLine("The following people are both teachers and students:");
foreach (string name in query)
{
    Console.WriteLine(name);
}
```

### Multiple join

You can append any number of join operations to perform a multiple join. Each `join` clause in C# correlates a specified data source with the results of the previous join.

The first `join` clause matches students and departments based on a `Student` object's `DepartmentID` matching a `Department` object's `ID`. It returns a sequence of anonymous types that contain the `Student` object and `Department` object.

The second `join` clause correlates the anonymous types returned by the first join with `Teacher` objects based on that teacher's ID matching the department head ID. It returns a sequence of anonymous types that contain the student's name, the department name, and the department leader's name. Because this operation is an inner join, the query returns only those objects from the first data source that have a match in the second data source.

```csharp
// The first join matches Department.ID and Student.DepartmentID from the list of students and
// departments, based on a common ID. The second join matches teachers who lead departments
// with the students studying in that department.
var query = from student in students
    join department in departments on student.DepartmentID equals department.ID
    join teacher in teachers on department.TeacherID equals teacher.ID
    select new {
        StudentName = $"{student.FirstName} {student.LastName}",
        DepartmentName = department.Name,
        TeacherName = $"{teacher.First} {teacher.Last}"
    };

foreach (var obj in query)
{
    Console.WriteLine($"""The student "{obj.StudentName}" studies in the department run by "{obj.TeacherName}".""");
}
```

The equivalent query that uses multiple <xref:System.Linq.Enumerable.Join*> methods uses the same approach with the anonymous type:

```csharp
var query = students
    .Join(departments, student => student.DepartmentID, department => department.ID,
        (student, department) => new { student, department })
    .Join(teachers, commonDepartment => commonDepartment.department.TeacherID, teacher => teacher.ID,
        (commonDepartment, teacher) => new
        {
            StudentName = $"{commonDepartment.student.FirstName} {commonDepartment.student.LastName}",
            DepartmentName = commonDepartment.department.Name,
            TeacherName = $"{teacher.First} {teacher.Last}"
        });

foreach (var obj in query)
{
    Console.WriteLine($"""The student "{obj.StudentName}" studies in the department run by "{obj.TeacherName}".""");
}
```

### Inner join by using grouped join

The following example shows how to implement an inner join by using a group join. The list of `Department` objects is group-joined to the list of `Student` objects based on the `Department.ID` matching the `Student.DepartmentID` property. The group join creates a collection of intermediate groups, where each group consists of a `Department` object and a sequence of matching `Student` objects. The second `from` clause combines (or flattens) this sequence of sequences into one longer sequence. The `select` clause specifies the type of elements in the final sequence. That type is an anonymous type that consists of the student's name and the matching department name.

```csharp
var query1 =
    from department in departments
    join student in students on department.ID equals student.DepartmentID into gj
    from subStudent in gj
    select new
    {
        DepartmentName = department.Name,
        StudentName = $"{subStudent.FirstName} {subStudent.LastName}"
    };
Console.WriteLine("Inner join using GroupJoin():");
foreach (var v in query1)
{
    Console.WriteLine($"{v.DepartmentName} - {v.StudentName}");
}
```

You can achieve the same results by using the <xref:System.Linq.Enumerable.GroupJoin*> method, as shown in the following example:

```csharp
var queryMethod1 = departments
    .GroupJoin(students, department => department.ID, student => student.DepartmentID,
        (department, gj) => new { department, gj })
    .SelectMany(departmentAndStudent => departmentAndStudent.gj,
        (departmentAndStudent, subStudent) => new
        {
            DepartmentName = departmentAndStudent.department.Name,
            StudentName = $"{subStudent.FirstName} {subStudent.LastName}"
        });

Console.WriteLine("Inner join using GroupJoin():");
foreach (var v in queryMethod1)
{
    Console.WriteLine($"{v.DepartmentName} - {v.StudentName}");
}
```

The result is equivalent to the result set obtained by using the `join` clause without the `into` clause to perform an inner join. The following code demonstrates this equivalent query:

```csharp
var query2 = from department in departments
    join student in students on department.ID equals student.DepartmentID
    select new
    {
        DepartmentName = department.Name,
        StudentName = $"{student.FirstName} {student.LastName}"
    };

Console.WriteLine("The equivalent operation using Join():");
foreach (var v in query2)
{
    Console.WriteLine($"{v.DepartmentName} - {v.StudentName}");
}
```

To avoid chaining, use the single <xref:System.Linq.Enumerable.Join*> method as presented here:

```csharp
var queryMethod2 = departments.Join(students, departments => departments.ID, student => student.DepartmentID,
    (department, student) => new
    {
        DepartmentName = department.Name,
        StudentName = $"{student.FirstName} {student.LastName}"
    });

Console.WriteLine("The equivalent operation using Join():");
foreach (var v in queryMethod2)
{
    Console.WriteLine($"{v.DepartmentName} - {v.StudentName}");
}
```

## Perform grouped joins

The group join is useful for producing hierarchical data structures. It pairs each element from the first collection with a set of correlated elements from the second collection.

> [!NOTE]
> Each element of the first collection appears in the result set of a group join regardless of whether correlated elements are found in the second collection. If no correlated elements are found, the sequence of correlated elements for that element is empty. The result selector therefore has access to every element of the first collection. This behavior differs from the result selector in a non-group join, which can't access elements from the first collection that have no match in the second collection.

> [!WARNING]
> <xref:System.Linq.Enumerable.GroupJoin*?displayProperty=nameWithType> has no direct equivalent in traditional relational database terms. However, this method does implement a superset of inner joins and left outer joins. Both of these operations can be written in terms of a grouped join. For more information, see [Entity Framework Core, GroupJoin](/ef/core/querying/complex-query-operators#groupjoin).

The first example in this article shows how to perform a group join. The second example shows how to use a group join to create XML elements.

### Group join

The following example performs a group join of objects of type `Department` and `Student` based on the `Department.ID` matching the `Student.DepartmentID` property. Unlike a non-group join, which produces a pair of elements for each match, the group join produces only one resulting object for each element of the first collection. In this example, the first collection is a `Department` object. The corresponding elements from the second collection, which in this example are `Student` objects, are grouped into a collection. Finally, the result selector function creates an anonymous type for each match that consists of `Department.Name` and a collection of `Student` objects.

```csharp
var query = from department in departments
    join student in students on department.ID equals student.DepartmentID into studentGroup
    select new
    {
        DepartmentName = department.Name,
        Students = studentGroup
    };

foreach (var v in query)
{
    // Output the department's name.
    Console.WriteLine($"{v.DepartmentName}:");

    // Output each of the students in that department.
    foreach (Student? student in v.Students)
    {
        Console.WriteLine($"  {student.FirstName} {student.LastName}");
    }
}
```

In the preceding example, the `query` variable contains the query that creates a list where each element is an anonymous type that contains the department's name and a collection of students that study in that department.

The equivalent query using method syntax is shown in the following code:

```csharp
var query = departments.GroupJoin(students, department => department.ID, student => student.DepartmentID,
    (department, Students) => new { DepartmentName = department.Name, Students });

foreach (var v in query)
{
    // Output the department's name.
    Console.WriteLine($"{v.DepartmentName}:");

    // Output each of the students in that department.
    foreach (Student? student in v.Students)
    {
        Console.WriteLine($"  {student.FirstName} {student.LastName}");
    }
}
```

### Group join to create XML

Group joins are ideal for creating XML by using LINQ to XML. The following example is similar to the previous example except that instead of creating anonymous types, the result selector function creates XML elements that represent the joined objects.

```csharp
XElement departmentsAndStudents = new("DepartmentEnrollment",
    from department in departments
    join student in students on department.ID equals student.DepartmentID into studentGroup
    select new XElement("Department",
        new XAttribute("Name", department.Name),
        from student in studentGroup
        select new XElement("Student",
            new XAttribute("FirstName", student.FirstName),
            new XAttribute("LastName", student.LastName)
        )
    )
);

Console.WriteLine(departmentsAndStudents);
```

The equivalent query using method syntax is shown in the following code:

```csharp
XElement departmentsAndStudents = new("DepartmentEnrollment",
    departments.GroupJoin(students, department => department.ID, student => student.DepartmentID,
        (department, Students) => new XElement("Department",
            new XAttribute("Name", department.Name),
            from student in Students
            select new XElement("Student",
                new XAttribute("FirstName", student.FirstName),
                new XAttribute("LastName", student.LastName)
            )
        )
    )
);

Console.WriteLine(departmentsAndStudents);
```

## Perform outer joins

.NET 10 includes [`LeftJoin`](/dotnet/api/?term=LeftJoin) and [`RightJoin`](/dotnet/api/?term=RightJoin) methods in the <xref:System.Linq.Enumerable?displayProperty=nameWithType> and <xref:System.Linq.Queryable?displayProperty=nameWithType> classes. These methods perform an *outer left equijoin*, and an *outer right equijoin*, respectively. An outer left equijoin is a join where every member of the first sequence is included in the output sequence, even if the second sequence doesn't include a match. An outer right equijoin is a join where every member of the second sequence is included in the output sequence, even if the first sequence doesn't include a match.

## Emulate a left outer join

Before .NET 10, use LINQ to perform a left outer join by calling the <xref:System.Linq.Enumerable.DefaultIfEmpty*> method on the results of a group join.

The following example demonstrates how to use the <xref:System.Linq.Enumerable.DefaultIfEmpty*> method on the results of a group join to perform a left outer join.

The first step in producing a left outer join of two collections is to perform an inner join by using a group join. (See [Perform inner joins](#perform-inner-joins) for an explanation of this process.) In this example, the list of `Department` objects is inner-joined to the list of `Student` objects based on a `Department` object's ID that matches the student's `DepartmentID`.

The second step is to include each element of the first (left) collection in the result set even if that element has no matches in the right collection. You accomplish this step by calling <xref:System.Linq.Enumerable.DefaultIfEmpty*> on each sequence of matching elements from the group join. In this example, you call <xref:System.Linq.Enumerable.DefaultIfEmpty*> on each sequence of matching `Student` objects. The method returns a collection that contains a single, default value if the sequence of matching `Student` objects is empty for any `Department` object, ensuring that each `Department` object is represented in the result collection.

> [!NOTE]
> The default value for a reference type is `null`; therefore, the example checks for a null reference before accessing each element of each `Student` collection.

```csharp
var query =
    from student in students
    join department in departments on student.DepartmentID equals department.ID into gj
    from subgroup in gj.DefaultIfEmpty()
    select new
    {
        student.FirstName,
        student.LastName,
        Department = subgroup?.Name ?? string.Empty
    };

foreach (var v in query)
{
    Console.WriteLine($"{v.FirstName:-15} {v.LastName:-15}: {v.Department}");
}
```

The equivalent query using method syntax is shown in the following code:

```csharp
var query = students
    .GroupJoin(
        departments,
        student => student.DepartmentID,
        department => department.ID,
        (student, departmentList) => new { student, subgroup = departmentList })
    .SelectMany(
        joinedSet => joinedSet.subgroup.DefaultIfEmpty(),
        (student, department) => new
        {
            student.student.FirstName,
            student.student.LastName,
            Department = department?.Name ?? string.Empty
        });

foreach (var v in query)
{
    Console.WriteLine($"{v.FirstName:-15} {v.LastName:-15}: {v.Department}");
}
```

## See also

- <xref:System.Linq.Enumerable.Join*>
- <xref:System.Linq.Enumerable.GroupJoin*>
- [Anonymous types](../../programming-guide/classes-and-structs/anonymous-types.md)
- [Formulate Joins and Cross-Product Queries](../../../framework/data/adonet/sql/linq/formulate-joins-and-cross-product-queries.md)
- [join clause](../../language-reference/keywords/join-clause.md)
- [group clause](../../language-reference/keywords/group-clause.md)
- [How to join content from dissimilar files (LINQ) (C#)](../how-to-query-files-and-directories.md)
- [How to populate object collections from multiple sources (LINQ) (C#)](../how-to-query-collections.md)
