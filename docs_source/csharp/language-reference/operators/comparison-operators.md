---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/comparison-operators.md
title: Comparison operators - order items using the greater than and less than operators
version: 0.0.0
fetched_at: 2026-09-13
---
# Comparison operators (C# reference)

The [`<` (less than)](#less-than-operator-), [`>` (greater than)](#greater-than-operator-), [`<=` (less than or equal)](#less-than-or-equal-operator-), and [`>=` (greater than or equal)](#greater-than-or-equal-operator-) comparison, also known as relational, operators compare their operands. All [integral](../builtin-types/integral-numeric-types.md) and [floating-point](../builtin-types/floating-point-numeric-types.md) numeric types support those operators.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

> [!NOTE]
> For the `==`, `<`, `>`, `<=`, and `>=` operators, if any of the operands isn't a number (<xref:System.Double.NaN?displayProperty=nameWithType> or <xref:System.Single.NaN?displayProperty=nameWithType>), the result of operation is `false`. This behavior means that the `NaN` value is neither greater than, less than, nor equal to any other `double` (or `float`) value, including `NaN`. For more information and examples, see the <xref:System.Double.NaN?displayProperty=nameWithType> or <xref:System.Single.NaN?displayProperty=nameWithType> reference article.

The [char](../builtin-types/char.md) type also supports comparison operators. When you use `char` operands, the corresponding character codes are compared.

Enumeration types also support comparison operators. For operands of the same [enum](../builtin-types/enum.md) type, the corresponding values of the underlying integral type are compared.

The [`==` and `!=` operators](equality-operators.md) check if their operands are equal or not.

## Less than operator \<

The `<` operator returns `true` if its left-hand operand is less than its right-hand operand, `false` otherwise:

```csharp
Console.WriteLine(7.0 < 5.1);   // output: False
Console.WriteLine(5.1 < 5.1);   // output: False
Console.WriteLine(0.0 < 5.1);   // output: True

Console.WriteLine(double.NaN < 5.1);   // output: False
Console.WriteLine(double.NaN >= 5.1);  // output: False
```

## Greater than operator >

The `>` operator returns `true` if its left-hand operand is greater than its right-hand operand, `false` otherwise:

```csharp
Console.WriteLine(7.0 > 5.1);   // output: True
Console.WriteLine(5.1 > 5.1);   // output: False
Console.WriteLine(0.0 > 5.1);   // output: False

Console.WriteLine(double.NaN > 5.1);   // output: False
Console.WriteLine(double.NaN <= 5.1);  // output: False
```

## Less than or equal operator `<=`

The `<=` operator returns `true` if its left-hand operand is less than or equal to its right-hand operand. Otherwise, it returns `false`:

```csharp
Console.WriteLine(7.0 <= 5.1);   // output: False
Console.WriteLine(5.1 <= 5.1);   // output: True
Console.WriteLine(0.0 <= 5.1);   // output: True

Console.WriteLine(double.NaN > 5.1);   // output: False
Console.WriteLine(double.NaN <= 5.1);  // output: False
```

## Greater than or equal operator `>=`

The `>=` operator returns `true` if its left-hand operand is greater than or equal to its right-hand operand. Otherwise, it returns `false`:

```csharp
Console.WriteLine(7.0 >= 5.1);   // output: True
Console.WriteLine(5.1 >= 5.1);   // output: True
Console.WriteLine(0.0 >= 5.1);   // output: False

Console.WriteLine(double.NaN < 5.1);   // output: False
Console.WriteLine(double.NaN >= 5.1);  // output: False
```

## Operator overloadability

You can [overload](operator-overloading.md) the `<`, `>`, `<=`, and `>=` operators in a user-defined type.

If you overload one of the `<` or `>` operators, you must overload both `<` and `>`. If you overload one of the `<=` or `>=` operators, you must overload both `<=` and `>=`.

## C# language specification

For more information, see the [Relational and type-testing operators](~/_csharpstandard/standard/expressions.md#1215-relational-and-type-testing-operators) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
- <xref:System.IComparable`1?displayProperty=nameWithType>
- [Equality operators](equality-operators.md)
