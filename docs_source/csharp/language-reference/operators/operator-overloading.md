---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/operator-overloading.md
title: Operator overloading - Define unary, arithmetic, equality, and comparison operators.
version: 0.0.0
fetched_at: 2026-09-13
---
# Operator overloading - predefined unary, arithmetic, equality, and comparison operators

You can overload a predefined C# operator in a user-defined type. By overloading an operator, you provide a custom implementation for the operation when one or both operands are of that type. See the [Overloadable operators](#overloadable-operators) section for a list of C# operators that you can overload.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

Use the `operator` keyword to declare an operator. An operator declaration must satisfy the following rules:

- It includes a `public` modifier.
- A unary operator has one input parameter. A binary operator has two input parameters. In each case, at least one parameter must have type `T` or `T?` where `T` is the type that contains the operator declaration.
- It includes the `static` modifier, except for the compound assignment operators, such as `+=`.
- The increment (`++`) and decrement (`--`) operators can be implemented as either static or instance methods. Instance method operators are a new feature introduced in C# 14.

The following example defines a simplified structure to represent a rational number. The structure overloads some of the [arithmetic operators](arithmetic-operators.md):

```csharp
public struct Fraction
{
    private int numerator;
    private int denominator;

    public Fraction(int numerator, int denominator)
    {
        if (denominator == 0)
        {
            throw new ArgumentException("Denominator cannot be zero.", nameof(denominator));
        }
        this.numerator = numerator;
        this.denominator = denominator;
    }

    public static Fraction operator +(Fraction operand) => operand;
    public static Fraction operator -(Fraction operand) => new Fraction(-operand.numerator, operand.denominator);

    public static Fraction operator +(Fraction left, Fraction right)
        => new Fraction(left.numerator * right.denominator + right.numerator * left.denominator, left.denominator * right.denominator);

    public static Fraction operator -(Fraction left, Fraction right)
        => left + (-right);

    public static Fraction operator *(Fraction left, Fraction right)
        => new Fraction(left.numerator * right.numerator, left.denominator * right.denominator);

    public static Fraction operator /(Fraction left, Fraction right)
    {
        if (right.numerator == 0)
        {
            throw new DivideByZeroException();
        }
        return new Fraction(left.numerator * right.denominator, left.denominator * right.numerator);
    }

    // Define increment and decrement to add 1/den, rather than 1/1.
    public static Fraction operator ++(Fraction operand)
        => new Fraction(operand.numerator + 1, operand.denominator);

    public static Fraction operator --(Fraction operand) =>
        new Fraction(operand.numerator - 1, operand.denominator);

    public override string ToString() => $"{numerator} / {denominator}";

    // New operators allowed in C# 14:
    public void operator +=(Fraction operand) =>
        (numerator, denominator ) =
        (
            numerator * operand.denominator + operand.numerator * denominator,
            denominator * operand.denominator
        );

    public void operator -=(Fraction operand) =>
        (numerator, denominator) =
        (
            numerator * operand.denominator - operand.numerator * denominator,
            denominator * operand.denominator
        );

    public void operator *=(Fraction operand) =>
        (numerator, denominator) =
        (
            numerator * operand.numerator,
            denominator * operand.denominator
        );

    public void operator /=(Fraction operand)
    {
        if (operand.numerator == 0)
        {
            throw new DivideByZeroException();
        }
        (numerator, denominator) =
        (
            numerator * operand.denominator,
            denominator * operand.numerator
        );
    }

    public void operator ++() => numerator++;

    public void operator --() => numerator--;
}

public static class OperatorOverloading
{
    public static void Main()
    {
        var a = new Fraction(5, 4);
        var b = new Fraction(1, 2);
        Console.WriteLine(-a);   // output: -5 / 4
        Console.WriteLine(a + b);  // output: 14 / 8
        Console.WriteLine(a - b);  // output: 6 / 8
        Console.WriteLine(a * b);  // output: 5 / 8
        Console.WriteLine(a / b);  // output: 10 / 4
    }
}
```

You could extend the preceding example by [defining an implicit conversion](user-defined-conversion-operators.md) from `int` to `Fraction`. Then, overloaded operators would support arguments of those two types. That is, it would become possible to add an integer to a fraction and obtain a fraction as a result.

You also use the `operator` keyword to define a custom type conversion. For more information, see [User-defined conversion operators](user-defined-conversion-operators.md).

## Overloadable operators

The following table shows the operators that can be overloaded:

<!--markdownlint-disable MD056 -->

| Operators | Notes |
| :--------------------: | ------------- |
|[`+x`](arithmetic-operators.md#unary-plus-and-minus-operators), [`-x`](arithmetic-operators.md#unary-plus-and-minus-operators), [`!x`](boolean-logical-operators.md#logical-negation-operator-), [`~x`](bitwise-and-shift-operators.md#bitwise-complement-operator-), [`++`](arithmetic-operators.md#increment-operator-), [`--`](arithmetic-operators.md#decrement-operator---), [`true`](true-false-operators.md), [`false`](true-false-operators.md)|The `true` and `false` operators must be overloaded together.|
|[`x + y`](arithmetic-operators.md#addition-operator-), [`x - y`](arithmetic-operators.md#subtraction-operator--), [`x * y`](arithmetic-operators.md#multiplication-operator-), [`x / y`](arithmetic-operators.md#division-operator-), [`x % y`](arithmetic-operators.md#remainder-operator-), <br /> [`x & y`](boolean-logical-operators.md#logical-and-operator-), [<code>x &#124; y</code>](boolean-logical-operators.md#logical-or-operator-), [`x ^ y`](boolean-logical-operators.md#logical-exclusive-or-operator-), <br /> [`x << y`](bitwise-and-shift-operators.md#left-shift-operator-), [`x >> y`](bitwise-and-shift-operators.md#right-shift-operator-), [`x >>> y`](bitwise-and-shift-operators.md#unsigned-right-shift-operator-) | |
|[`x == y`](equality-operators.md#equality-operator-), [`x != y`](equality-operators.md#inequality-operator-), [`x < y`](comparison-operators.md#less-than-operator-), [`x > y`](comparison-operators.md#greater-than-operator-), [`x <= y`](comparison-operators.md#less-than-or-equal-operator-), [`x >= y`](comparison-operators.md#greater-than-or-equal-operator-)|Must be overloaded in pairs as follows:  `==` and `!=`, `<` and `>`, `<=` and `>=`.|
|[`+=`](arithmetic-operators.md#compound-assignment), [`-=`](arithmetic-operators.md#compound-assignment), [`*=`](arithmetic-operators.md#compound-assignment), [`/=`](arithmetic-operators.md#compound-assignment), [`%=`](arithmetic-operators.md#compound-assignment), [`&=`](boolean-logical-operators.md#compound-assignment), [`|=`](boolean-logical-operators.md#compound-assignment), [`^=`](boolean-logical-operators.md#compound-assignment), [`<<=`](bitwise-and-shift-operators.md#compound-assignment), [`>>=`](bitwise-and-shift-operators.md#compound-assignment), [`>>>=`](bitwise-and-shift-operators.md#compound-assignment)|The compound assignment operators can be overloaded in C# 14 and later.|

<!--markdownlint-enable MD056 -->

A compound assignment overloaded operator must follow these rules:

- It must include the `public` modifier.
- It can't include the `static` modifier.
- The return type must be `void`.
- The declaration must include one parameter, which represents the right hand side of the compound assignment.

Starting in C# 14, you can overload the increment (`++`) and decrement (`--`) operators as instance members. Instance operators can improve performance by avoiding the creation of a new instance. An instance operator must follow these rules:

- It must include the `public` modifier.
- It can't include the `static` modifier.
- The return type must be `void`.
- It can't declare any parameters, even if those parameters have a default value.

## Non overloadable operators

The following table shows the operators that can't be overloaded:

| Operators | Alternatives |
| :---------: | --------------- |
|[`x && y`](boolean-logical-operators.md#conditional-logical-and-operator-), [<code>x &#124;&#124; y</code>](boolean-logical-operators.md#conditional-logical-or-operator-)| Overload both the [`true`](true-false-operators.md) and [`false`](true-false-operators.md) operators and the [`&`](boolean-logical-operators.md#logical-and-operator-) or [<code>&#124;</code>](boolean-logical-operators.md#logical-or-operator-) operators. For more information, see [User-defined conditional logical operators](~/_csharpstandard/standard/expressions.md#12173-user-defined-conditional-logical-operators).|
|[<code>a&#91;i&#93;</code>](member-access-operators.md#indexer-operator-), [`a?[i]`](member-access-operators.md#null-conditional-operators--and-)|Define an [indexer](../../programming-guide/indexers/index.md).|
|[`(T)x`](type-testing-and-cast.md#cast-expression)|Define custom type conversions performed by a cast expression. For more information, see [User-defined conversion operators](user-defined-conversion-operators.md).|
|[`^x`](member-access-operators.md#index-from-end-operator-), [`x = y`](assignment-operator.md), [`x.y`](member-access-operators.md#member-access-expression-), [`x?.y`](member-access-operators.md#null-conditional-operators--and-), [`c ? t : f`](conditional-operator.md), [`x ?? y`](null-coalescing-operator.md), [`??= y`](null-coalescing-operator.md),<br />[`x..y`](member-access-operators.md#range-operator-), [`x->y`](pointer-related-operators.md#pointer-member-access-operator--), [`=>`](lambda-operator.md), [`f(x)`](member-access-operators.md#invocation-expression-), [`as`](type-testing-and-cast.md#the-as-operator), [`await`](await.md), [`checked`](../statements/checked-and-unchecked.md), [`unchecked`](../statements/checked-and-unchecked.md), [`default`](default.md), [`delegate`](delegate-operator.md), [`is`](type-testing-and-cast.md#the-is-operator), [`nameof`](nameof.md), [`new`](new-operator.md), <br />[`sizeof`](sizeof.md), [`stackalloc`](stackalloc.md), [`switch`](switch-expression.md), [`typeof`](type-testing-and-cast.md#the-typeof-operator), [`with`](with-expression.md)|None.|

Before C# 14, the compound operators can't be overloaded. Overloading the corresponding binary operator implicitly overloads the corresponding compound assignment operator.

## Operator overload resolution

> [!IMPORTANT]
> This section applies to C# 14 and later. Before C# 14, user-defined compound assignment operators and instance increment and decrement operators aren't allowed.

If `x` is classified as a variable in a compound assignment expression such as `x «op»= y`, instance operators take precedence over any static operator for `«op»`. If the type of `x` doesn't declare an overloaded `«op»=` operator or `x` isn't classified as a variable, the static operators are used.

For the postfix operator `++`, if `x` isn't classified as a variable *or* the expression `x++` is used, the instance `operator++` is ignored. Otherwise, preference is given to the instance `operator ++`. For example,

```csharp
x++; // Instance operator++ preferred.
y = x++; // instance operator++ isn't considered.
```

The reason for this rule is that `y` should be assigned to the value of `x` *before* it's incremented. The compiler can't determine that for a user-defined implementation in a reference type.

For the prefix operator `++`, if `x` is classified as a variable in `++x`, the instance operator is preferred over a static unary operator.

## C# language specification

For more information, see the following sections of the [C# language specification](~/_csharpstandard/standard/README.md):

- [Operator overloading](~/_csharpstandard/standard/expressions.md#1243-operator-overloading)
- [Operators](~/_csharpstandard/standard/classes.md#1510-operators)

## See also

- [C# operators and expressions](index.md)
- [User-defined conversion operators](user-defined-conversion-operators.md)
- [Design guidelines - Operator overloads](../../../standard/design-guidelines/operator-overloads.md)
- [Design guidelines - Equality operators](../../../standard/design-guidelines/equality-operators.md)
