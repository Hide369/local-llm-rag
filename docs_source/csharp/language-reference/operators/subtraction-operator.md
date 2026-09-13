---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/subtraction-operator.md
title: - and -= operators - subtraction (minus) operators
version: 0.0.0
fetched_at: 2026-09-13
---
# - and -= operators - subtraction (minus)

The built-in [delegate](../builtin-types/reference-types.md#the-delegate-type) types and [integral](../builtin-types/integral-numeric-types.md) and [floating-point](../builtin-types/floating-point-numeric-types.md) numeric types all support the `-` and `-=` operators.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

For information about the arithmetic `-` operator, see the [Unary plus and minus operators](arithmetic-operators.md#unary-plus-and-minus-operators) and [Subtraction operator -](arithmetic-operators.md#subtraction-operator--) sections of the [Arithmetic operators](arithmetic-operators.md) article.

## Delegate removal

For operands of the same [delegate](../builtin-types/reference-types.md#the-delegate-type) type, the `-` operator returns a delegate instance that's calculated as follows:

- If both operands are not `null` and the invocation list of the right-hand operand is a proper contiguous sublist of the invocation list of the left-hand operand, the result of the operation is a new invocation list that you get by removing the right-hand operand's entries from the invocation list of the left-hand operand. If the right-hand operand's list matches multiple contiguous sublists in the left-hand operand's list, the operation removes only the right-most matching sublist. If removal results in an empty list, the result is `null`.

```csharp
Action a = () => Console.Write("a");
Action b = () => Console.Write("b");

var abbaab = a + b + b + a + a + b;
abbaab();  // output: abbaab
Console.WriteLine();

var ab = a + b;
var abba = abbaab - ab;
abba();  // output: abba
Console.WriteLine();

var nihil = abbaab - abbaab;
Console.WriteLine(nihil is null);  // output: True
```

- If the invocation list of the right-hand operand isn't a proper contiguous sublist of the invocation list of the left-hand operand, the result of the operation is the left-hand operand. For example, removing a delegate that isn't part of the multicast delegate does nothing and results in the unchanged multicast delegate.

```csharp
Action a = () => Console.Write("a");
Action b = () => Console.Write("b");

var abbaab = a + b + b + a + a + b;
var aba = a + b + a;

var first = abbaab - aba;
first();  // output: abbaab
Console.WriteLine();
Console.WriteLine(object.ReferenceEquals(abbaab, first));  // output: True

Action a2 = () => Console.Write("a");
var changed = aba - a;
changed();  // output: ab
Console.WriteLine();
var unchanged = aba - a2;
unchanged();  // output: aba
Console.WriteLine();
Console.WriteLine(object.ReferenceEquals(aba, unchanged));  // output: True
```

  The preceding example also demonstrates that during delegate removal delegate instances are compared. For example, delegates that are produced from evaluation of identical [lambda expressions](lambda-expressions.md) aren't equal. For more information about delegate equality, see the [Delegate equality operators](~/_csharpstandard/standard/expressions.md#12159-delegate-equality-operators) section of the [C# language specification](~/_csharpstandard/standard/README.md).

- If the left-hand operand is `null`, the result of the operation is `null`. If the right-hand operand is `null`, the result of the operation is the left-hand operand.

```csharp
Action a = () => Console.Write("a");

var nothing = null - a;
Console.WriteLine(nothing is null);  // output: True

var first = a - null;
a();  // output: a
Console.WriteLine();
Console.WriteLine(object.ReferenceEquals(first, a));  // output: True
```

To combine delegates, use the [`+` operator](addition-operator.md#delegate-combination).

For more information about delegate types, see [Delegates](../../programming-guide/delegates/index.md).

## Subtraction assignment operator `-=`

An expression that uses the `-=` operator, such as

```csharp
x -= y
```

Is equivalent to

```csharp
x = x - y
```

Except that `x` is only evaluated once.

The following example demonstrates how to use the `-=` operator:

```csharp
int i = 5;
i -= 9;
Console.WriteLine(i);
// Output: -4

Action a = () => Console.Write("a");
Action b = () => Console.Write("b");
var printer = a + b + a;
printer();  // output: aba

Console.WriteLine();
printer -= a;
printer();  // output: ab
```

You also use the `-=` operator to specify an event handler method to remove when you unsubscribe from an [event](../keywords/event.md). For more information, see [How to subscribe to and unsubscribe from events](../../programming-guide/events/how-to-subscribe-to-and-unsubscribe-from-events.md).

## Operator overloadability

A user-defined type can [overload](operator-overloading.md) the `-` operator. When you overload a binary `-` operator, you also implicitly overload the `-=` operator. Starting with C# 14, a user-defined type can explicitly overload the `-=` operator to provide a more efficient implementation. Typically, a type overloads the `-=` operator because the value can be updated in place, rather than allocating a new instance to store the result of the subtraction. If a type doesn't provide an explicit overload, the compiler generates the implicit overload.

## C# language specification

For more information, see the [Unary minus operator](~/_csharpstandard/standard/expressions.md#1293-unary-minus-operator) and [Subtraction operator](~/_csharpstandard/standard/expressions.md#12136-subtraction-operator) sections of the [C# language specification](~/_csharpstandard/standard/README.md). For more information on overloading the compound assignment operators in C# 14 and later, see the [user defined compound assignment](~/_csharplang/proposals/csharp-14.0/user-defined-compound-assignment.md) feature specification.

## See also

- [C# operators and expressions](index.md)
- [Events](../../programming-guide/events/index.md)
- [Arithmetic operators](arithmetic-operators.md)
- [+ and += operators](addition-operator.md)
