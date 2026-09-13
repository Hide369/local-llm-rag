---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/in-generic-modifier.md
title: in (Generic Modifier)
version: 0.0.0
fetched_at: 2026-09-13
---
# `in` (Generic Modifier) (C# Reference)

For generic type parameters, use the `in` keyword to allow contravariant type arguments. Use the `in` keyword in generic interfaces and delegates.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

Contravariance enables you to use a less derived type than the type specified by the generic parameter. This feature allows for implicit conversion of classes that implement contravariant interfaces and implicit conversion of delegate types. Reference types support covariance and contravariance in generic type parameters, but value types don't support these features.

You can declare a type as contravariant in a generic interface or delegate only if it defines the type of a method's parameters and not the method's return type. `In`, `ref`, and `out` parameters must be invariant, meaning they're neither covariant nor contravariant.

An interface that has a contravariant type parameter allows its methods to accept arguments of less derived types than those specified by the interface type parameter. For example, in the <xref:System.Collections.Generic.IComparer`1> interface, type T is contravariant. You can assign an object of the `IComparer<Person>` type to an object of the `IComparer<Employee>` type without using any special conversion methods if `Employee` inherits `Person`.

You can assign a contravariant delegate to another delegate of the same type, but with a less derived generic type parameter.

For more information, see [Covariance and Contravariance](../../programming-guide/concepts/covariance-contravariance/index.md).

## Contravariant generic interface

The following example shows how to declare, extend, and implement a contravariant generic interface. It also shows how you can use implicit conversion for classes that implement this interface.

```csharp
// Contravariant interface.
interface IContravariant<in A> { }

// Extending contravariant interface.
interface IExtContravariant<in A> : IContravariant<A> { }

// Implementing contravariant interface.
class Sample<A> : IContravariant<A> { }

class Program
{
    static void Test()
    {
        IContravariant<Object> iobj = new Sample<Object>();
        IContravariant<String> istr = new Sample<String>();

        // You can assign iobj to istr because
        // the IContravariant interface is contravariant.
        istr = iobj;
    }
}
```

## Contravariant generic delegate

The following example shows how to declare, instantiate, and invoke a contravariant generic delegate. It also shows how you can implicitly convert a delegate type.

```csharp
// Contravariant delegate.
public delegate void DContravariant<in A>(A argument);

// Methods that match the delegate signature.
public static void SampleControl(Control control)
{ }
public static void SampleButton(Button button)
{ }

public void Test()
{

    // Instantiating the delegates with the methods.
    DContravariant<Control> dControl = SampleControl;
    DContravariant<Button> dButton = SampleButton;

    // You can assign dControl to dButton
    // because the DContravariant delegate is contravariant.
    dButton = dControl;

    // Invoke the delegate.
    dButton(new Button());
}
```

## C# language specification

[!INCLUDE[CSharplangspec](~/includes/csharplangspec-md.md)]

## See also

- [out](out-generic-modifier.md)
- [Covariance and Contravariance](../../programming-guide/concepts/covariance-contravariance/index.md)
- [Modifiers](index.md)
