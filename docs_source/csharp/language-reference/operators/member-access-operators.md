---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/member-access-operators.md
title: Member access and null-conditional operators and expressions:
version: 0.0.0
fetched_at: 2026-09-13
---
# Member access operators and expressions - the dot, indexer, and invocation operators

You use several operators and expressions to access a type member. Member access operators include member access (`.`), array element, or indexer access (`[]`), index-from-end (`^`), range (`..`), null-conditional operators (`?.` and `?[]`), and method invocation (`()`). These operators include the *null-conditional* member access (`?.`), and indexer access (`?[]`) operators.

- [`.` (member access)](#member-access-expression-): Access a member of a namespace or a type.
- [`[]` (array element or indexer access)](#indexer-operator-): Access an array element or a type indexer.
- [`?.` and `?[]` (null-conditional operators)](#null-conditional-operators--and-): Perform a member or element access operation only if an operand is non-null.
- [`()` (invocation)](#invocation-expression-): Call an accessed method or invoke a delegate.
- [`^` (index from end)](#index-from-end-operator-): Indicate that the element position is from the end of a sequence.
- [`..` (range)](#range-operator-): Specify a range of indices that you can use to obtain a range of sequence elements.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

## Member access expression `.`

Use the `.` token to access a member of a namespace or a type, as the following examples demonstrate:

- Use `.` to access a nested namespace within a namespace, as the following example of a [`using` directive](../keywords/using-directive.md) shows:

```csharp
using System.Collections.Generic;
```

- Use `.` to form a *qualified name* to access a type within a namespace, as the following code shows:

```csharp
System.Collections.Generic.IEnumerable<int> numbers = [1, 2, 3];
```

  Use a [`using` directive](../keywords/using-directive.md) to make the use of qualified names optional.

- Use `.` to access [type members](../../fundamentals/object-oriented/index.md#members), static and nonstatic, as the following code shows:

```csharp
List<double> constants =
[
    Math.PI,
    Math.E
];
Console.WriteLine($"{constants.Count} values to show:");
Console.WriteLine(string.Join(", ", constants));
// Output:
// 2 values to show:
// 3.14159265358979, 2.71828182845905
```

You can also use `.` to access an [extension member](../../programming-guide/classes-and-structs/extension-methods.md).

## Indexer operator []

Square brackets, `[]`, typically access array, indexer, or pointer elements. Beginning with C# 12, `[]` encloses a [collection expression](./collection-expressions.md).

### Array access

The following example demonstrates how to access array elements:

```csharp
int[] fib = new int[10];
fib[0] = fib[1] = 1;
for (int i = 2; i < fib.Length; i++)
{
    fib[i] = fib[i - 1] + fib[i - 2];
}
Console.WriteLine(fib[fib.Length - 1]);  // output: 55

double[,] matrix = new double[2,2];
matrix[0,0] = 1.0;
matrix[0,1] = 2.0;
matrix[1,0] = matrix[1,1] = 3.0;
var determinant = matrix[0,0] * matrix[1,1] - matrix[1,0] * matrix[0,1];
Console.WriteLine(determinant);  // output: -3
```

If an array index is outside the bounds of the corresponding dimension of an array, the runtime throws an <xref:System.IndexOutOfRangeException>.

As the preceding example shows, you also use square brackets when you declare an array type or instantiate an array instance.

For more information about arrays, see [Arrays](../builtin-types/arrays.md).

### Indexer access

The following example uses the .NET <xref:System.Collections.Generic.Dictionary`2> type to demonstrate indexer access:

```csharp
var dict = new Dictionary<string, double>();
dict["one"] = 1;
dict["pi"] = Math.PI;
Console.WriteLine(dict["one"] + dict["pi"]);  // output: 4.14159265358979
```

Indexers allow you to index instances of a user-defined type in a similar way as array indexing. Unlike array indices, which must be integer, the indexer parameters can be declared to be of any type.

For more information about indexers, see [Indexers](../../programming-guide/indexers/index.md).

### Other usages of []

For information about pointer element access, see the [Pointer element access operator []](pointer-related-operators.md#pointer-element-access-operator-) section of the [Pointer related operators](pointer-related-operators.md) article. For information about collection expressions, see the [collection expressions](./collection-expressions.md) article.

You also use square brackets to specify [attributes](/dotnet/csharp/advanced-topics/reflection-and-attributes):

```csharp
[System.Diagnostics.Conditional("DEBUG")]
void TraceMethod() {}
```

Additionally, use square brackets to designate [list patterns](../../fundamentals/functional/pattern-matching.md) for use in pattern matching or testing.

```csharp
arr is ([1, 2, ..])
//Specifies that an array starts with (1, 2)
```

## Null-conditional operators `?.` and `?[]`

A null-conditional operator applies a [member access](#member-access-expression-) (`?.`) or [element access](#indexer-operator-) (`?[]`) operation to its operand only if that operand evaluates to non-null. Otherwise, it returns `null`. In other words:

- If `a` evaluates to `null`, the result of `a?.x` or `a?[x]` is `null`.
- If `a` evaluates to non-null, the result of `a?.x` or `a?[x]` is the same as the result of `a.x` or `a[x]`, respectively.

  > [!NOTE]
  > If `a.x` or `a[x]` throws an exception, `a?.x` or `a?[x]` throws the same exception for non-null `a`. For example, if `a` is a non-null array instance and `x` is outside the bounds of `a`, `a?[x]` throws an <xref:System.IndexOutOfRangeException>.

The null-conditional operators are short-circuiting. That is, if one operation in a chain of conditional member or element access operations returns `null`, the rest of the chain doesn't execute. In the following example, `B` isn't evaluated if `A` evaluates to `null` and `C` isn't evaluated if `A` or `B` evaluates to `null`:

```csharp
A?.B?.Do(C);
A?.B?[C];
```

If `A` might be null but `B` and `C` wouldn't be null if A isn't null, you only need to apply the null-conditional operator to `A`:

```csharp
A?.B.C();
```

In the preceding example, `B` isn't evaluated and `C()` isn't called if `A` is null. However, if the chained member access is interrupted, for example by parentheses as in `(A?.B).C()`, short-circuiting doesn't happen.

The following examples demonstrate the usage of the `?.` and `?[]` operators:

```csharp
double SumNumbers(List<double[]> setsOfNumbers, int indexOfSetToSum)
{
    return setsOfNumbers?[indexOfSetToSum]?.Sum() ?? double.NaN;
}

var sum1 = SumNumbers(null, 0);
Console.WriteLine(sum1);  // output: NaN

List<double[]?> numberSets =
[
    [1.0, 2.0, 3.0],
    null
];

var sum2 = SumNumbers(numberSets, 0);
Console.WriteLine(sum2);  // output: 6

var sum3 = SumNumbers(numberSets, 1);
Console.WriteLine(sum3);  // output: NaN
```
```csharp
namespace MemberAccessOperators2;

public static class NullConditionalShortCircuiting
{
    public static void Main()
    {
        Person? person = null;
        person?.Name.Write(); // no output: Write() is not called due to short-circuit.
        try
        {
            (person?.Name).Write();
        }
        catch (NullReferenceException)
        {
            Console.WriteLine("NullReferenceException");
        }; // output: NullReferenceException
    }
}

public class Person
{
    public required FullName Name { get; set; }
}

public class FullName
{
    public required string FirstName { get; set; }
    public required string LastName { get; set; }
    public void Write() => Console.WriteLine($"{FirstName} {LastName}");
}
```

The first preceding example also uses the [null-coalescing operator `??`](null-coalescing-operator.md) to specify an alternative expression to evaluate in case the result of a null-conditional operation is `null`.

If `a.x` or `a[x]` is of a non-nullable value type `T`, `a?.x` or `a?[x]` is of the corresponding [nullable value type](../builtin-types/nullable-value-types.md) `T?`. If you need an expression of type `T`, apply the null-coalescing operator `??` to a null-conditional expression, as the following example shows:

```csharp
int GetSumOfFirstTwoOrDefault(int[]? numbers)
{
    if ((numbers?.Length ?? 0) < 2)
    {
        return 0;
    }
    return numbers[0] + numbers[1];
}

Console.WriteLine(GetSumOfFirstTwoOrDefault(null));  // output: 0
Console.WriteLine(GetSumOfFirstTwoOrDefault([]));  // output: 0
Console.WriteLine(GetSumOfFirstTwoOrDefault([3, 4, 5]));  // output: 7
```

In the preceding example, if you don't use the `??` operator, `numbers?.Length < 2` evaluates to `false` when `numbers` is `null`.

> [!NOTE]
> The `?.` operator evaluates its left-hand operand no more than once, guaranteeing that it can't be changed to `null` after being verified as non-null.

Beginning in C# 14, assignment is permissible with a null conditional access expression (`?.` and `?[]`) on reference types. For example, see the following method:

```csharp
person?.FirstName = "Scott";
messages?[5] = "five";
```

The preceding example shows assignment to a property and an indexed element on a reference type that might be null. An important behavior for this assignment is that the expression on the right-hand side of the `=` is evaluated only when the left-hand side is known to be non-null. For example, in the following code, the function `GenerateNextIndex` is called only when the `values` array isn't null. If the `values` array is null, `GenerateNextIndex` isn't called:

```csharp
values?[2] = GenerateNextIndex();
int GenerateNextIndex() => index++;
```

In other words, the preceding code is equivalent to the following code using an `if` statement for the null check:

```csharp
if (values is not null)
{
    values[2] = GenerateNextIndex();
}
```

In addition to assignment, any form of [compound assignment](./assignment-operator.md#compound-assignment), such as `+=` or `-=`, is allowed. However, increment (`++`) and decrement (`--`) aren't allowed.

This enhancement doesn't classify a null conditional expression as a variable. It can't be `ref` assigned, nor can it be assigned to a `ref` variable or passed to a method as a `ref` or `out` argument.

### Thread-safe delegate invocation

Use the `?.` operator to check if a delegate isn't null and invoke it in a thread-safe way (for example, when you [raise an event](../../../standard/events/how-to-raise-and-consume-events.md)), as the following code shows:

```csharp
PropertyChanged?.Invoke(…)
```

That code is equivalent to the following code:

```csharp
var handler = this.PropertyChanged;
if (handler != null)
{
    handler(…);
}
```

The preceding example is a thread-safe way to ensure that only a non-null `handler` is invoked. Because delegate instances are immutable, no thread can change the object referenced by the `handler` local variable. In particular, if the code executed by another thread unsubscribes from the `PropertyChanged` event and `PropertyChanged` becomes `null` before `handler` is invoked, the object referenced by `handler` remains unaffected.

## Invocation expression ()

Use parentheses, `()`, to call a [method](../../programming-guide/classes-and-structs/methods.md) or invoke a [delegate](../../programming-guide/delegates/index.md).

The following code demonstrates how to call a method, with or without arguments, and invoke a delegate:

```csharp
Action<int> display = s => Console.WriteLine(s);

List<int> numbers =
[
    10,
    17
];
display(numbers.Count);   // output: 2

numbers.Clear();
display(numbers.Count);   // output: 0
```

You also use parentheses when you invoke a [constructor](../../programming-guide/classes-and-structs/constructors.md) by using the [`new`](new-operator.md) operator.

### Other usages of ()

You also use parentheses to adjust the order in which to evaluate operations in an expression. For more information, see [C# operators](index.md).

[Cast expressions](type-testing-and-cast.md#cast-expression), which perform explicit type conversions, also use parentheses.

## Index from end operator ^

You can use index and range operators with a type that is *countable*. A *countable* type has an `int` property named either `Count` or `Length` with an accessible `get` accessor. [Collection expressions](./collection-expressions.md) also rely on *countable* types.

> [!NOTE]
> Single dimensional arrays are *countable*. Multidimensional arrays aren't. You can't use the `^` and `..` (range) operators in multidimensional arrays.

The `^` operator indicates the element position from the end of a sequence. For a sequence of length `length`, `^n` points to the element with offset `length - n` from the start of a sequence. For example, `^1` points to the last element of a sequence and `^length` points to the first element of a sequence.

```csharp
int[] xs = [0, 10, 20, 30, 40];
int last = xs[^1];
Console.WriteLine(last);  // output: 40

List<string> lines = ["one", "two", "three", "four"];
string prelast = lines[^2];
Console.WriteLine(prelast);  // output: three

string word = "Twenty";
Index toFirst = ^word.Length;
char first = word[toFirst];
Console.WriteLine(first);  // output: T
```

As the preceding example shows, expression `^e` is of the <xref:System.Index?displayProperty=nameWithType> type. In expression `^e`, the result of `e` must be implicitly convertible to `int`.

You can also use the `^` operator with the [range operator](#range-operator-) to create a range of indices. For more information, see [Indices and ranges](../../tutorials/ranges-indexes.md).

Starting with C# 13, you can use the Index from the end operator, `^`, in an object initializer.

## Range operator `..`

The `..` operator specifies the start and end of a range of indices as its operands. The left-hand operand is an *inclusive* start of a range. The right-hand operand is an *exclusive* end of a range. Either operand can be an index from the start or from the end of a sequence, as the following example shows:

```csharp
int[] numbers = [0, 10, 20, 30, 40, 50];
int start = 1;
int amountToTake = 3;
int[] subset = numbers[start..(start + amountToTake)];
Display(subset);  // output: 10 20 30

int margin = 1;
int[] inner = numbers[margin..^margin];
Display(inner);  // output: 10 20 30 40

string line = "one two three";
int amountToTakeFromEnd = 5;
Range endIndices = ^amountToTakeFromEnd..^0;
string end = line[endIndices];
Console.WriteLine(end);  // output: three

void Display<T>(IEnumerable<T> xs) => Console.WriteLine(string.Join(" ", xs));
```

As the preceding example shows, expression `a..b` is of the <xref:System.Range?displayProperty=nameWithType> type. In expression `a..b`, the results of `a` and `b` must be implicitly convertible to <xref:System.Int32> or <xref:System.Index>.

> [!IMPORTANT]
> Implicit conversions from `int` to `Index` throw an <xref:System.ArgumentOutOfRangeException> when the value is negative.

You can omit any of the operands of the `..` operator to obtain an open-ended range:

- `a..` is equivalent to `a..^0`
- `..b` is equivalent to `0..b`
- `..` is equivalent to `0..^0`

```csharp
int[] numbers = [0, 10, 20, 30, 40, 50];
int amountToDrop = numbers.Length / 2;

int[] rightHalf = numbers[amountToDrop..];
Display(rightHalf);  // output: 30 40 50

int[] leftHalf = numbers[..^amountToDrop];
Display(leftHalf);  // output: 0 10 20

int[] all = numbers[..];
Display(all);  // output: 0 10 20 30 40 50

void Display<T>(IEnumerable<T> xs) => Console.WriteLine(string.Join(" ", xs));
```

The following table shows various ways to express collection ranges:

| Range operator expression | Description                                                                      |
|---------------------------|----------------------------------------------------------------------------------|
| `..`                      | All values in the collection.                                                    |
| `..end`                   | Values from the start to the `end` exclusively.                                  |
| `start..`                 | Values from the `start` inclusively to the end.                                  |
| `start..end`              | Values from the `start` inclusively to the `end` exclusively.                    |
| `^start..`                | Values from the `start` inclusively to the end counting from the end.            |
| `..^end`                  | Values from the start to the `end` exclusively counting from the end.            |
| `start..^end`             | Values from `start` inclusively to `end` exclusively counting from the end.      |
| `^start..^end`            | Values from `start` inclusively to `end` exclusively both counting from the end. |

The following example demonstrates the effect of using all the ranges presented in the preceding table:

```csharp
int[] oneThroughTen =
[
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10
];

Write(oneThroughTen, ..);
Write(oneThroughTen, ..3);
Write(oneThroughTen, 2..);
Write(oneThroughTen, 3..5);
Write(oneThroughTen, ^2..);
Write(oneThroughTen, ..^3);
Write(oneThroughTen, 3..^4);
Write(oneThroughTen, ^4..^2);

static void Write(int[] values, Range range) =>
    Console.WriteLine($"{range}:\t{string.Join(", ", values[range])}");
// Sample output:
//      0..^0:      1, 2, 3, 4, 5, 6, 7, 8, 9, 10
//      0..3:       1, 2, 3
//      2..^0:      3, 4, 5, 6, 7, 8, 9, 10
//      3..5:       4, 5
//      ^2..^0:     9, 10
//      0..^3:      1, 2, 3, 4, 5, 6, 7
//      3..^4:      4, 5, 6
//      ^4..^2:     7, 8
```

For more information, see [Indices and ranges](../../tutorials/ranges-indexes.md).

The `..` token is also used for the [spread element](./collection-expressions.md#spread-element) in a collection expression.

## Operator overloadability

You can't overload the `.`, `()`, `^`, and `..` operators. The `[]` operator is also a non-overloadable operator. Use [indexers](../../programming-guide/indexers/index.md) to support indexing with user-defined types.

## C# language specification

For more information, see the following sections of the [C# language specification](~/_csharpstandard/standard/README.md):

- [Member access](~/_csharpstandard/standard/expressions.md#1287-member-access)
- [Element access](~/_csharpstandard/standard/expressions.md#12812-element-access)
- [Null-conditional member access](~/_csharpstandard/standard/expressions.md#1288-null-conditional-member-access)
- [Invocation expressions](~/_csharpstandard/standard/expressions.md#12810-invocation-expressions)

For more information about indices and ranges, see the [feature proposal note](~/_csharpstandard/standard/ranges.md).

## See also

- [Use index operator (style rule IDE0056)](../../../fundamentals/code-analysis/style-rules/ide0056.md)
- [Use range operator (style rule IDE0057)](../../../fundamentals/code-analysis/style-rules/ide0057.md)
- [Use conditional delegate call (style rule IDE1005)](../../../fundamentals/code-analysis/style-rules/ide1005.md)
- [C# operators and expressions](index.md)
- [?? (null-coalescing operator)](null-coalescing-operator.md)
- [:: operator](namespace-alias-qualifier.md)
