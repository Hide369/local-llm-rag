---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/null-coalescing-operator.md
title: ?? and ??= operators - null-coalescing operators
version: 0.0.0
fetched_at: 2026-09-13
---
# `??` and `??=` operators - the null-coalescing operators

The null-coalescing operator `??` returns the value of its left-hand operand if it's not `null`. Otherwise, it evaluates the right-hand operand and returns its result. The `??` operator doesn't evaluate its right-hand operand if the left-hand operand evaluates to non-null. The null-coalescing assignment operator `??=` assigns the value of its right-hand operand to its left-hand operand only if the left-hand operand evaluates to `null`. The `??=` operator doesn't evaluate its right-hand operand if the left-hand operand evaluates to non-null.

```csharp
List<int>? numbers = null;
int? a = null;

Console.WriteLine((numbers is null)); // expected: true
// if numbers is null, initialize it. Then, add 5 to numbers
(numbers ??= new List<int>()).Add(5);
Console.WriteLine(string.Join(" ", numbers));  // output: 5
Console.WriteLine((numbers is null)); // expected: false        


Console.WriteLine((a is null)); // expected: true
Console.WriteLine((a ?? 3)); // expected: 3 since a is still null 
// if a is null then assign 0 to a and add a to the list
numbers.Add(a ??= 0);
Console.WriteLine((a is null)); // expected: false        
Console.WriteLine(string.Join(" ", numbers));  // output: 5 0
Console.WriteLine(a);  // output: 0	        
```

The left-hand operand of the `??=` operator must be a variable, a [property](../../programming-guide/classes-and-structs/properties.md), or an [indexer](../../programming-guide/indexers/index.md) element.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The type of the left-hand operand of the `??` and `??=` operators can't be a non-nullable value type. In particular, you can use the null-coalescing operators with unconstrained type parameters:

```csharp
private static void Display<T>(T a, T backup)
{
    Console.WriteLine(a ?? backup);
}
```

The null-coalescing operators are right-associative. That is, expressions of the form

```csharp
a ?? b ?? c
d ??= e ??= f
```

are evaluated as

```csharp
a ?? (b ?? c)
d ??= (e ??= f)
```

## Examples

The `??` and `??=` operators are useful in the following scenarios:

- In expressions that use the [null-conditional operators `?.` and `?[]`](member-access-operators.md#null-conditional-operators--and-), use the `??` operator to provide an alternative expression to evaluate if the result of the expression with null-conditional operations is `null`:

```csharp
double SumNumbers(List<double[]> setsOfNumbers, int indexOfSetToSum)
{
    return setsOfNumbers?[indexOfSetToSum]?.Sum() ?? double.NaN;
}

var sum = SumNumbers(null, 0);
Console.WriteLine(sum);  // output: NaN
```

- When you work with [nullable value types](../builtin-types/nullable-value-types.md) and need to provide a value of an underlying value type, use the `??` operator to specify the value to provide if a nullable type value is `null`:

```csharp
int? a = null;
int b = a ?? -1;
Console.WriteLine(b);  // output: -1
```

  Use the <xref:System.Nullable`1.GetValueOrDefault?displayProperty=nameWithType> method if the value to use when a nullable type value is `null` should be the default value of the underlying value type.

- To make the argument-checking code more concise, use a [`throw` expression](../statements/exception-handling-statements.md#the-throw-expression) as the right-hand operand of the `??` operator:

```csharp
public string Name
{
    get => name;
    set => name = value ?? throw new ArgumentNullException(nameof(value), "Name cannot be null");
}
```

  The preceding example also demonstrates how to use [expression-bodied members](lambda-operator.md#expression-body-definition) to define a property.

- Use the `??=` operator to replace code of the following form:

  ```csharp
  if (variable is null)
  {
      variable = expression;
  }
  ```

  Use the following code:

  ```csharp
  variable ??= expression;
  ```

## Operator overloadability

You can't overload the `??` and `??=` operators.

## C# language specification

For more information about the `??` operator, see [The null coalescing operator](~/_csharpstandard/standard/expressions.md#1218-the-null-coalescing-operator) section of the [C# language specification](~/_csharpstandard/standard/README.md).

For more information about the `??=` operator, see the [Compound assignment](~/_csharpstandard/standard/expressions.md#12245-compound-assignment) section of the C# language specification.

## See also

- [Null check can be simplified (IDE0029, IDE0030, and IDE0270)](../../../fundamentals/code-analysis/style-rules/ide0029-ide0030-ide0270.md)
- [C# operators and expressions](index.md)
- [?. and ?[] operators](member-access-operators.md#null-conditional-operators--and-)
- [?: operator](conditional-operator.md)
