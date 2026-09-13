---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/object-oriented/polymorphism.md
title: Polymorphism
version: 0.0.0
fetched_at: 2026-09-13
---
# Polymorphism

Polymorphism is often referred to as the third pillar of object-oriented programming, after encapsulation and inheritance. Polymorphism is a Greek word that means "many-shaped" and it has two distinct aspects:

- At run time, objects of a derived class can be treated as objects of a base class in places such as method parameters and collections or arrays. When this polymorphism occurs, the object's declared type is no longer identical to its run-time type.
- Base classes might define and implement [virtual](../../language-reference/keywords/virtual.md) *methods*, and derived classes can [override](../../language-reference/keywords/override.md) them, which means they provide their own definition and implementation. At run-time, when client code calls the method, the CLR looks up the run-time type of the object, and invokes that override of the virtual method. In your source code you can call a method on a base class, and cause a derived class's version of the method to be executed.

Virtual methods enable you to work with groups of related objects in a uniform way. For example, suppose you have a drawing application that enables a user to create various kinds of shapes on a drawing surface. You don't know at compile time which specific types of shapes the user will create. However, the application has to keep track of all the various types of shapes that are created, and it has to update them in response to user mouse actions. You can use polymorphism to solve this problem in two basic steps:

1. Create a class hierarchy in which each specific shape class derives from a common base class.
1. Use a virtual method to invoke the appropriate method on any derived class through a single call to the base class method.

First, create a base class called `Shape`, and derived classes such as `Rectangle`, `Circle`, and `Triangle`. Give the `Shape` class a virtual method called `Draw`, and override it in each derived class to draw the particular shape that the class represents. Create a `List<Shape>` object and add a `Circle`, `Triangle`, and `Rectangle` to it.

```csharp
public class Shape
{
    // A few example members
    public int X { get; init; }
    public int Y { get; init; }
    public int Height { get; init; }
    public int Width { get; init; }

    // Virtual method
    public virtual void Draw()
    {
        Console.WriteLine("Performing base class drawing tasks");
    }
}

public class Circle : Shape
{
    public override void Draw()
    {
        // Code to draw a circle...
        Console.WriteLine("Drawing a circle");
        base.Draw();
    }
}
public class Rectangle : Shape
{
    public override void Draw()
    {
        // Code to draw a rectangle...
        Console.WriteLine("Drawing a rectangle");
        base.Draw();
    }
}
public class Triangle : Shape
{
    public override void Draw()
    {
        // Code to draw a triangle...
        Console.WriteLine("Drawing a triangle");
        base.Draw();
    }
}
```

To update the drawing surface, use a [foreach](../../language-reference/statements/iteration-statements.md#the-foreach-statement) loop to iterate through the list and call the `Draw` method on each `Shape` object in the list. Even though each object in the list has a declared type of `Shape`, it's the run-time type (the overridden version of the method in each derived class) that will be invoked.

```csharp
// Polymorphism at work #1: a Rectangle, Triangle and Circle
// can all be used wherever a Shape is expected. No cast is
// required because an implicit conversion exists from a derived
// class to its base class.
List<Shape> shapes =
[
    new Rectangle(),
    new Triangle(),
    new Circle()
];

// Polymorphism at work #2: the virtual method Draw is
// invoked on each of the derived classes, not the base class.
foreach (var shape in shapes)
{
    shape.Draw();
}
/* Output:
    Drawing a rectangle
    Performing base class drawing tasks
    Drawing a triangle
    Performing base class drawing tasks
    Drawing a circle
    Performing base class drawing tasks
*/
```

In C#, every type is polymorphic because all types, including user-defined types, inherit from <xref:System.Object>.  

## Polymorphism overview

### Virtual members

When a derived class inherits from a base class, it includes all the members of the base class. All the behavior declared in the base class is part of the derived class. That enables objects of the derived class to be treated as objects of the base class. Access modifiers (`public`, `protected`, `private`, and so on) determine if those members are accessible from the derived class implementation. Virtual methods give the designer different choices for the behavior of the derived class:

- The derived class can override virtual members in the base class, defining new behavior.
- The derived class can inherit the closest base class method without overriding it, preserving the existing behavior but enabling further derived classes to override the method.
- The derived class can define new non-virtual implementation of those members that hide the base class implementations.

A derived class can override a base class member only if the base class member is declared as [virtual](../../language-reference/keywords/virtual.md) or [abstract](../../language-reference/keywords/abstract.md). The derived member must use the [override](../../language-reference/keywords/override.md) keyword to explicitly indicate that the method is intended to participate in virtual invocation. The following code provides an example:

```csharp
public class BaseClass
{
    public virtual void DoWork() { }
    public virtual int WorkProperty => 0;
}
public class DerivedClass : BaseClass
{
    public override void DoWork() { }
    public override int WorkProperty
    {
        get { return 0; }
    }
}
```

Fields can't be virtual; only methods, properties, events, and indexers can be virtual. When a derived class overrides a virtual member, that member is called even when an instance of that class is being accessed as an instance of the base class. The following code provides an example:

```csharp
DerivedClass B = new();
B.DoWork();  // Calls the new method.

BaseClass A = B;
A.DoWork();  // Also calls the new method.
```

Virtual methods and properties enable derived classes to extend a base class without needing to use the base class implementation of a method. For more information, see [Versioning with the Override and New Keywords](../../programming-guide/classes-and-structs/versioning-with-the-override-and-new-keywords.md). An interface provides another way to define a method or set of methods whose implementation is left to derived classes.

### Hide base class members with new members

If you want your derived class to have a member with the same name as a member in a base class, you can use the [new](../../language-reference/keywords/new-modifier.md) keyword to hide the base class member. The `new` keyword is put before the return type of a class member that's being replaced. The following code provides an example:

```csharp
public class BaseClass
{
    public void DoWork() { WorkField++; }
    public int WorkField;
    public int WorkProperty
    {
        get { return 0; }
    }
}

public class DerivedClass : BaseClass
{
    public new void DoWork() { WorkField++; }
    public new int WorkField;
    public new int WorkProperty
    {
        get { return 0; }
    }
}
```

When you use the `new` keyword, you're creating a method that *hides* the base class method rather than *overriding* it. This is different from virtual methods. With method hiding, the method that gets called depends on the compile-time type of the variable, not the run-time type of the object.

Hidden base class members can be accessed from client code by casting the instance of the derived class to an instance of the base class. For example:

```csharp
DerivedClass B = new();
B.DoWork();  // Calls the new method.

BaseClass A = (BaseClass)B;
A.DoWork();  // Calls the old method.
```

In this example, both variables refer to the same object instance, but the method that gets called depends on the variable's declared type: `DerivedClass.DoWork()` when accessed through the `DerivedClass` variable, and `BaseClass.DoWork()` when accessed through the `BaseClass` variable.

### Prevent derived classes from overriding virtual members  

Virtual members remain virtual, regardless of how many classes are declared between the virtual member and the class that originally declared it. If class `A` declares a virtual member, and class `B` derives from `A`, and class `C` derives from `B`, class `C` inherits the virtual member, and might override it, regardless of whether class `B` declared an override for that member. The following code provides an example:

:::code language="csharp" source="./snippets/inheritance/Hierarchy.cs" ID="SnippetFirstHierarchy":::

A derived class can stop virtual inheritance by declaring an override as [sealed](../../language-reference/keywords/sealed.md). Stopping inheritance requires putting the `sealed` keyword before the `override` keyword in the class member declaration. The following code provides an example:

:::code language="csharp" source="./snippets/inheritance/Hierarchy.cs" ID="SnippetSealedOverride":::

In the previous example, the method `DoWork` is no longer virtual to any class derived from `C`. It's still virtual for instances of `C`, even if they're cast to type `B` or type `A`. Sealed methods can be replaced by derived classes by using the `new` keyword, as the following example shows:

:::code language="csharp" source="./snippets/inheritance/Hierarchy.cs" ID="SnippetNewDeclaration":::

In this case, if `DoWork` is called on `D` using a variable of type `D`, the new `DoWork` is called. If a variable of type `C`, `B`, or `A` is used to access an instance of `D`, a call to `DoWork` follows the rules of virtual inheritance, routing those calls to the implementation of `DoWork` on class `C`.

### Access base class virtual members from derived classes

A derived class that replaces or overrides a method or property can still access the method or property on the base class using the `base` keyword. The following code provides an example:

```csharp
public class Base
{
    public virtual void DoWork() {/*...*/ }
}
public class Derived : Base
{
    public override void DoWork()
    {
        //Perform Derived's work here
        //...
        // Call DoWork on base class
        base.DoWork();
    }
}
```

For more information, see [base](../../language-reference/keywords/base.md).

> [!NOTE]
> It's recommended that virtual members use `base` to call the base class implementation of that member in their own implementation. Letting the base class behavior occur enables the derived class to concentrate on implementing behavior specific to the derived class. If the base class implementation isn't called, it's up to the derived class to make their behavior compatible with the behavior of the base class.
