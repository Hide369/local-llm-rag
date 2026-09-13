---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/whats-new/tutorials/primary-constructors.md
title: Declare C# primary constructors – classes, structs
version: 0.0.0
fetched_at: 2026-09-13
---
# Declare primary constructors for classes and structs

C# 12 introduces [primary constructors](../../programming-guide/classes-and-structs/instance-constructors.md#primary-constructors), which provide a concise syntax to declare constructors whose parameters are available anywhere in the body of the type.

This article describes how to declare a primary constructor on your type and recognize where to store primary constructor parameters. You can call primary constructors from other constructors and use primary constructor parameters in members of the type.

## Prerequisites

[!INCLUDE [Prerequisites](../../../../includes/prerequisites-basic.md)]

## Understand rules for primary constructors

You can add parameters to a `struct` or `class` declaration to create a *primary constructor*. Primary constructor parameters are in scope throughout the class definition. It's important to view primary constructor parameters as *parameters* even though they are in scope throughout the class definition.

Several rules clarify that these constructors are parameters:

- Primary constructor parameters might not be stored if they aren't needed.
- Primary constructor parameters aren't members of the class. For example, a primary constructor parameter named `param` can't be accessed as `this.param`.
- Primary constructor parameters can be assigned to.
- Primary constructor parameters don't become properties, except in [record](../../language-reference/builtin-types/record.md) types.

These rules are the same rules already defined for parameters to any method, including other constructor declarations.

Here are the most common uses for a primary constructor parameter:

- Pass as an argument to a `base()` constructor invocation
- Initialize a member field or property
- Reference the constructor parameter in an instance member

Every other constructor for a class **must** call the primary constructor, directly or indirectly, through a `this()` constructor invocation. This rule ensures that primary constructor parameters are assigned everywhere in the body of the type.

## Initialize immutable properties or fields

The following code initializes two readonly (immutable) properties that are computed from primary constructor parameters:

```csharp
public readonly struct Distance(double dx, double dy)
{
    public readonly double Magnitude { get; } = Math.Sqrt(dx * dx + dy * dy);
    public readonly double Direction { get; } = Math.Atan2(dy, dx);
}
```

This example uses a primary constructor to initialize calculated readonly properties. The field initializers for the `Magnitude` and `Direction` properties use the primary constructor parameters. The primary constructor parameters aren't used anywhere else in the struct. The code creates a struct as if it were written in the following manner:

```csharp
public readonly struct Distance
{
    public readonly double Magnitude { get; }

    public readonly double Direction { get; }

    public Distance(double dx, double dy)
    {
        Magnitude = Math.Sqrt(dx * dx + dy * dy);
        Direction = Math.Atan2(dy, dx);
    }
}
```

This feature makes it easier to use field initializers when you need arguments to initialize a field or property.

## Create mutable state

The previous examples use primary constructor parameters to initialize readonly properties. You can also use primary constructors for properties that aren't readonly.

Consider the following code:

```csharp
public struct Distance(double dx, double dy)
{
    public readonly double Magnitude => Math.Sqrt(dx * dx + dy * dy);
    public readonly double Direction => Math.Atan2(dy, dx);

    public void Translate(double deltaX, double deltaY)
    {
        dx += deltaX;
        dy += deltaY;
    }

    public Distance() : this(0,0) { }
}
```

In this example, the `Translate` method changes the `dx` and `dy` components, which requires the `Magnitude` and `Direction` properties be computed when accessed. The lambda operator (`=>`) designates an expression-bodied `get` accessor, whereas the equal-to operator (`=`) designates an initializer.

This version of the code adds a parameterless constructor to the struct. The parameterless constructor must invoke the primary constructor, which ensures all primary constructor parameters are initialized. The primary constructor properties are accessed in a method, and the compiler creates hidden fields to represent each parameter.

The following code demonstrates an approximation of what the compiler generates. The actual field names are valid Common Intermediate Language (CIL) identifiers, but not valid C# identifiers.

```csharp
public struct Distance
{
    private double __unspeakable_dx;
    private double __unspeakable_dy;

    public readonly double Magnitude => Math.Sqrt(__unspeakable_dx * __unspeakable_dx + __unspeakable_dy * __unspeakable_dy);
    public readonly double Direction => Math.Atan2(__unspeakable_dy, __unspeakable_dx);

    public void Translate(double deltaX, double deltaY)
    {
        __unspeakable_dx += deltaX;
        __unspeakable_dy += deltaY;
    }

    public Distance(double dx, double dy)
    {
        __unspeakable_dx = dx;
        __unspeakable_dy = dy;
    }
    public Distance() : this(0, 0) { }
}
```

### Compiler-created storage

For the first example in this section, the compiler didn't need to create a field to store the value of the primary constructor parameters. However, in  the second example, the primary constructor parameter is used inside a method, so the compiler must create storage for the parameters.

The compiler creates storage for any primary constructors only when the parameter is accessed in the body of a member of your type. Otherwise, the primary constructor parameters aren't stored in the object.

## Use dependency injection

Another common use for primary constructors is to specify parameters for dependency injection. The following code creates a simple controller that requires a service interface for its use:

```csharp
public interface IService
{
    Distance GetDistance();
}

public class ExampleController(IService service) : ControllerBase
{
    [HttpGet]
    public ActionResult<Distance> Get()
    {
        return service.GetDistance();
    }
}
```

The primary constructor clearly indicates the parameters needed in the class. You use the primary constructor parameters as you would any other variable in the class.

## Initialize base class

You can invoke the primary constructor for a base class from the primary constructor of derived class. This approach is the easiest way to write a derived class that must invoke a primary constructor in the base class. Consider a hierarchy of classes that represent different account types as a bank. The following code shows what the base class might look like:

```csharp
public class BankAccount(string accountID, string owner)
{
    public string AccountID { get; } = accountID;
    public string Owner { get; } = owner;

    public override string ToString() => $"Account ID: {AccountID}, Owner: {Owner}";
}
```

All bank accounts, regardless of the type, have properties for the account number and owner. In the completed application, you can add other common functionality to the base class.

Many types require more specific validation on constructor parameters. For example, the `BankAccount` class has specific requirements for the `owner` and `accountID` parameters. The `owner` parameter must not be `null` or whitespace, and the `accountID` parameter must be a string containing 10 digits. You can add this validation when you assign the corresponding properties:

```csharp
public class BankAccount(string accountID, string owner)
{
    public string AccountID { get; } = ValidAccountNumber(accountID) 
        ? accountID 
        : throw new ArgumentException("Invalid account number", nameof(accountID));

    public string Owner { get; } = string.IsNullOrWhiteSpace(owner) 
        ? throw new ArgumentException("Owner name cannot be empty", nameof(owner)) 
        : owner;

    public override string ToString() => $"Account ID: {AccountID}, Owner: {Owner}";

    public static bool ValidAccountNumber(string accountID) => 
    accountID?.Length == 10 && accountID.All(c => char.IsDigit(c));
}
```

This example shows how to validate the constructor parameters before you assign them to the properties. You can use built-in methods like <xref:System.String.IsNullOrWhiteSpace(System.String)?displayProperty=nameWithType> or your own validation method, such as `ValidAccountNumber`. In the example, any exceptions are thrown from the constructor, when it invokes the initializers. If a constructor parameter isn't used to assign a field, any exceptions are thrown when the constructor parameter is first accessed.

One derived class might represent a checking account:

```csharp
public class CheckingAccount(string accountID, string owner, decimal overdraftLimit = 0) : BankAccount(accountID, owner)
{
    public decimal CurrentBalance { get; private set; } = 0;

    public void Deposit(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Deposit amount must be positive");
        }
        CurrentBalance += amount;
    }

    public void Withdrawal(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Withdrawal amount must be positive");
        }
        if (CurrentBalance - amount < -overdraftLimit)
        {
            throw new InvalidOperationException("Insufficient funds for withdrawal");
        }
        CurrentBalance -= amount;
    }

    public override string ToString() => $"Account ID: {AccountID}, Owner: {Owner}, Balance: {CurrentBalance}";
}
```

The derived `CheckingAccount` class has a primary constructor that takes all the parameters needed in the base class, and another parameter with a default value. The primary constructor calls the base constructor with the `: BankAccount(accountID, owner)` syntax. This expression specifies both the type for the base class and the arguments for the primary constructor.

Your derived class isn't required to use a primary constructor. You can create a constructor in the derived class that invokes the primary constructor for the base class, as shown in the following example:

```csharp
public class LineOfCreditAccount : BankAccount
{
    private readonly decimal _creditLimit;
    public LineOfCreditAccount(string accountID, string owner, decimal creditLimit) : base(accountID, owner)
    {
        _creditLimit = creditLimit;
    }
    public decimal CurrentBalance { get; private set; } = 0;

    public void Deposit(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Deposit amount must be positive");
        }
        CurrentBalance += amount;
    }

    public void Withdrawal(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Withdrawal amount must be positive");
        }
        if (CurrentBalance - amount < -_creditLimit)
        {
            throw new InvalidOperationException("Insufficient funds for withdrawal");
        }
        CurrentBalance -= amount;
    }

    public override string ToString() => $"{base.ToString()}, Balance: {CurrentBalance}";
}
```

There's one potential concern with class hierarchies and primary constructors. It's possible to create multiple copies of a primary constructor parameter because the parameter is used in both derived and base classes. The following code creates two copies each of the `owner` and `accountID` parameters:

```csharp
public class SavingsAccount(string accountID, string owner, decimal interestRate) : BankAccount(accountID, owner)
{
    public SavingsAccount() : this("default", "default", 0.01m) { }
    public decimal CurrentBalance { get; private set; } = 0;

    public void Deposit(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Deposit amount must be positive");
        }
        CurrentBalance += amount;
    }

    public void Withdrawal(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Withdrawal amount must be positive");
        }
        if (CurrentBalance - amount < 0)
        {
            throw new InvalidOperationException("Insufficient funds for withdrawal");
        }
        CurrentBalance -= amount;
    }

    public void ApplyInterest()
    {
        CurrentBalance *= 1 + interestRate;
    }

    public override string ToString() => $"Account ID: {accountID}, Owner: {owner}, Balance: {CurrentBalance}";
}
```

The highlighted line in this example shows that the `ToString` method uses the *primary constructor parameters* (`owner` and `accountID`) rather than the *base class properties* (`Owner` and `AccountID`). The result is that the derived class, `SavingsAccount`, creates storage for the parameter copies. The copy in the derived class is different than the property in the base class. If the base class property can be modified, the instance of the derived class doesn't see the modification. The compiler issues a warning for primary constructor parameters that are used in a derived class and passed to a base class constructor. In this instance, the fix is to use the properties of the base class.

## Related content

- [Parameterless constructors (C# programming guide)](../../programming-guide/classes-and-structs/instance-constructors.md#parameterless-constructors)
- [Primary constructors (§15.11.6)](~/_csharpstandard/standard/classes.md#15116-primary-constructors)
