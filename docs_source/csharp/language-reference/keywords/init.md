---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/init.md
title: The init keyword - init only properties
version: 0.0.0
fetched_at: 2026-09-13
---
# The `init` keyword (C# Reference)

The `init` keyword defines an *accessor* method in a property or indexer. An init-only setter assigns a value to the property or the indexer element **only** during object construction. An `init` enforces immutability, so that once the object is initialized, it can't be changed. An `init` accessor enables calling code to use an [object initializer](../../programming-guide/classes-and-structs/how-to-initialize-objects-by-using-an-object-initializer.md) to set the initial value. In contrast, an
 [automatically implemented property](../../programming-guide/classes-and-structs/auto-implemented-properties.md) with only a `get` accessor must be initialized by calling a constructor. A property with a `private set` accessor can be modified after construction, but only in the class.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following code demonstrates an `init` accessor in an automatically implemented property:

```csharp
class Person_InitExampleAutoProperty
{
    public int YearOfBirth { get; init; }
}
```

You might need to implement one of the accessors to provide parameter validation. You can do that validation by using the `field` keyword, introduced in C# 14. The `field` keyword accesses the compiler synthesized backing field for that property. The following example shows a property where the `init` accessor validates the range of the `value` parameter.

```csharp
class Person_InitExampleFieldProperty
{
    public int YearOfBirth
    {
        get;
        init
        {
            field = (value <= DateTime.Now.Year)
                ? value
                : throw new ArgumentOutOfRangeException(nameof(value), "Year of birth can't be in the future");
        }
    }
}
```

The `init` accessor can be used as an expression-bodied member. Example:

```csharp
class Person_InitExampleExpressionBodied
{
    private int _yearOfBirth;

    public int YearOfBirth
    {
        get => _yearOfBirth;
        init => _yearOfBirth = value;
    }
}
```

The following example defines both a `get` and an `init` accessor for a property named `YearOfBirth`. It uses a private field named `_yearOfBirth` to back the property value.

```csharp
class Person_InitExample
{
     private int _yearOfBirth;

     public int YearOfBirth
     {
         get { return _yearOfBirth; }
         init { _yearOfBirth = value; }
     }
}
```

An `init` accessor doesn't force callers to set the property. Instead, it allows callers to use an object initializer while prohibiting later modification. You can add the [`required`](required.md) modifier to force callers to set a property. The following example shows an `init` only property with a nullable value type as its backing field. If a caller doesn't initialize the `YearOfBirth` property, that property has the default `null` value:

```csharp
class Person_InitExampleNullability
{
    private int? _yearOfBirth;

    public int? YearOfBirth
    {
        get => _yearOfBirth;
        init => _yearOfBirth = value;
    }
}
```

To force callers to set an initial non-null value, add the `required` modifier, as shown in the following example:

```csharp
class Person_InitExampleNonNull
{
    private int _yearOfBirth;

    public required int YearOfBirth
    {
        get => _yearOfBirth;
        init => _yearOfBirth = value;
    }
}
```

The following example shows the distinction between a `private set`, read-only, and `init` property. Both the private set version and the read-only version require callers to use the added constructor to set the name property. The `private set` version allows a person to change their name after the instance is constructed. The `init` version doesn't require a constructor. Callers can initialize the properties by using an object initializer:

```csharp
class PersonPrivateSet
{
    public string FirstName { get; private set; }
    public string LastName { get; private set; }
    public PersonPrivateSet(string first, string last) => (FirstName, LastName) = (first, last);

    public void ChangeName(string first, string last) => (FirstName, LastName) = (first, last);
}

class PersonReadOnly
{
    public string FirstName { get; }
    public string LastName { get; }
    public PersonReadOnly(string first, string last) => (FirstName, LastName) = (first, last);
}

class PersonInit
{
    public string FirstName { get; init; }
    public string LastName { get; init; }
}
```

```csharp
PersonPrivateSet personPrivateSet = new("Bill", "Gates");
PersonReadOnly personReadOnly = new("Bill", "Gates");
PersonInit personInit = new() { FirstName = "Bill", LastName = "Gates" };
```

## C# language specification

[!INCLUDE[CSharplangspec](~/includes/csharplangspec-md.md)]

## See also

- [Properties](../../programming-guide/classes-and-structs/properties.md)
