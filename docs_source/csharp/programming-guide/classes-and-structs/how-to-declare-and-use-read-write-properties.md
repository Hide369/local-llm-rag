---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/classes-and-structs/how-to-declare-and-use-read-write-properties.md
title: How to declare and use read write properties
version: 0.0.0
fetched_at: 2026-09-13
---
# How to declare and use read write properties (C# Programming Guide)

Properties provide the convenience of public data members without the risks that come with unprotected, uncontrolled, and unverified access to an object's data. Properties declare *accessors*: special methods that assign and retrieve values from the underlying data member. The [set](../../language-reference/keywords/set.md) accessor enables data members to be assigned, and the [get](../../language-reference/keywords/get.md) accessor retrieves data member values.

This sample shows a `Person` class that has two properties: `Name` (string) and `Age` (int). Both properties provide `get` and `set` accessors, so they're considered read/write properties.

## Example

```csharp
class Person
{
    private string _name = "N/A";
    private int _age = 0;

    // Declare a Name property of type string:
    public string Name
    {
        get
        {
            return _name;
        }
        set
        {
            //<Snippet4>
            _name = value;
```
  
## Robust Programming

In the previous example, the `Name` and `Age` properties are [public](../../language-reference/keywords/public.md) and include both a `get` and a `set` accessor. Public accessors allow any object to read and write these properties. It's sometimes desirable, however, to exclude one of the accessors. You can omit the `set` accessor to make the property read-only:

```csharp
public string Name
{
    get
    {
        return _name;
    }
    private set
    {
        //<Snippet4>
        _name = value;
```

Alternatively, you can expose one accessor publicly but make the other private or protected. For more information, see [Asymmetric Accessor Accessibility](./restricting-accessor-accessibility.md).

Once the properties are declared, they can be used as fields of the class. Properties allow for a natural syntax when both getting and setting the value of a property, as in the following statements:

```csharp
person.Name = "Joe";
person.Age = 99;
```

In a property `set` method a special `value` variable is available. This variable contains the value that the user specified, for example:

```csharp
_name = value;
```

Notice the clean syntax for incrementing the `Age` property on a `Person` object:

```csharp
person.Age += 1;
```

If separate `set` and `get` methods were used to model properties, the equivalent code might look like this:

```csharp
person.SetAge(person.GetAge() + 1);
```

The `ToString` method is overridden in this example:

```csharp
public override string ToString()
{
    return "Name = " + Name + ", Age = " + Age;
}
```

Notice that `ToString` isn't explicitly used in the program. It's invoked by default by the `WriteLine` calls.

## See also

- [Properties](./properties.md)
- [The C# type system](../../fundamentals/types/index.md)
