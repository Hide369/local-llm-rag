---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/classes-and-structs/how-to-write-a-copy-constructor.md
title: How to write a copy constructor
version: 0.0.0
fetched_at: 2026-09-13
---
# How to write a copy constructor (C# Programming Guide)

C# [records](../../fundamentals/types/records.md) provide a copy constructor for objects, but for classes you have to write one yourself.

> [!IMPORTANT]
> Writing copy constructors that work for all derived types in a class hierarchy can be difficult. If your class isn't `sealed`, you should strongly consider creating a hierarchy of `record class` types to use the compiler-synthesized copy constructor.

## Example

In the following example, the `Person` [class](../../language-reference/keywords/class.md) defines a copy constructor that takes, as its argument, an instance of `Person`. The values of the properties of the argument are assigned to the properties of the new instance of `Person`. The code contains an alternative copy constructor that sends the `Name` and `Age` properties of the instance that you want to copy to the instance constructor of the class. The `Person` class is `sealed`, so no derived types can be declared that could introduce errors by copying only the base class.

```csharp
public sealed class Person
{
    // Copy constructor.
    public Person(Person previousPerson)
    {
        Name = previousPerson.Name;
        Age = previousPerson.Age;
    }

    //// Alternate copy constructor calls the instance constructor.
    //public Person(Person previousPerson)
    //    : this(previousPerson.Name, previousPerson.Age)
    //{
    //}

    // Instance constructor.
    public Person(string name, int age)
    {
        Name = name;
        Age = age;
    }

    public int Age { get; set; }

    public string Name { get; set; }

    public string Details()
    {
        return Name + " is " + Age.ToString();
    }
}

class TestPerson
{
    static void Main()
    {
        // Create a Person object by using the instance constructor.
        Person person1 = new Person("George", 40);

        // Create another Person object, copying person1.
        Person person2 = new Person(person1);

        // Change each person's age.
        person1.Age = 39;
        person2.Age = 41;

        // Change person2's name.
        person2.Name = "Charles";

        // Show details to verify that the name and age fields are distinct.
        Console.WriteLine(person1.Details());
        Console.WriteLine(person2.Details());

        // Keep the console window open in debug mode.
        Console.WriteLine("Press any key to exit.");
        Console.ReadKey();
    }
}
// Output:
// George is 39
// Charles is 41
```

## See also

- <xref:System.ICloneable>
- [Records](../../fundamentals/types/records.md)
- [The C# type system](../../fundamentals/types/index.md)
- [Constructors](./constructors.md)
- [Finalizers](./finalizers.md)
