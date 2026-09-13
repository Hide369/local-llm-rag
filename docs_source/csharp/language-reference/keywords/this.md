---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/this.md
title: The this keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# The this keyword

The `this` keyword refers to the current instance of the class. It also serves as a modifier for the first parameter of an extension method.

> [!NOTE]
> This article discusses the use of `this` to refer to the receiver instance in the current member. For more information about its use in extension methods, see the [`extension`](./extension.md) keyword.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

Common uses of `this` include:

- Qualifying members hidden by similar names, such as:
```csharp
public class Employee
{
    private string alias;
    private string name;

    public Employee(string name, string alias)
    {
        // Use this to qualify the members of the class
        // instead of the constructor parameters.
        this.name = name;
        this.alias = alias;
    }
}
```
- Passing an object as a parameter to other methods.

  ```csharp
  CalcTax(this);
  ```

- Declaring [indexers](../../programming-guide/indexers/index.md), such as:
```csharp
public int this[int param]
{
    get => array[param];
    set => array[param] = value;
}
```

Static member functions exist at the class level and not as part of an object. They don't have a `this` pointer. Referring to `this` in a static method is an error.

In the following example, the parameters `name` and `alias` hide fields with the same names. The `this` keyword qualifies those variables as `Employee` class members. The `this` keyword also specifies the object for the method `CalcTax`, which belongs to another class.

```csharp
class Employee
{
    private string name;
    private string alias;

    // Constructor:
    public Employee(string name, string alias)
    {
        // Use this to qualify the fields, name and alias:
        this.name = name;
        this.alias = alias;
    }

    // Printing method:
    public void printEmployee()
    {
        Console.WriteLine($"""
        Name: {name}
        Alias: {alias}
        """);
        // Passing the object to the CalcTax method by using this:
        Console.WriteLine($"Taxes: {Tax.CalcTax(this):C}");
    }

    public decimal Salary { get; } = 3000.00m;
}

class Tax
{
    public static decimal CalcTax(Employee E)=> 0.08m * E.Salary;
}

class Program
{
    static void Main()
    {
        // Create objects:
        Employee E1 = new Employee("Mingda Pan", "mpan");

        // Display results:
        E1.printEmployee();
    }
}
/*
Output:
    Name: Mingda Pan
    Alias: mpan
    Taxes: $240.00
 */
```

## C# language specification

[!INCLUDE[CSharplangspec](~/includes/csharplangspec-md.md)]

## See also

- [Member-access qualification preferences (IDE0003 and IDE0009)](../../../fundamentals/code-analysis/style-rules/ide0003-ide0009.md)
- [C# Keywords](index.md)
- [base](base.md)
- [Methods](../../programming-guide/classes-and-structs/methods.md)
