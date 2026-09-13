---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/bitwise-and-shift-operators.md
title: Bitwise and shift operators - perform boolean (AND, NOT, OR, XOR) and shift operations on individual bits in integral types
version: 0.0.0
fetched_at: 2026-09-13
---
# Bitwise and shift operators (C# reference)

The bitwise and shift operators include unary bitwise complement, binary left and right shift, unsigned right shift, and the binary logical AND, OR, and exclusive OR operators. These operators take operands of the [integral numeric types](../builtin-types/integral-numeric-types.md) or the [char](../builtin-types/char.md) type.

- Unary [`~` (bitwise complement)](#bitwise-complement-operator-) operator
- Binary [`<<` (left shift)](#left-shift-operator-), [`>>` (right shift)](#right-shift-operator-), and [`>>>` (unsigned right shift)](#unsigned-right-shift-operator-) operators
- Binary [`&` (logical AND)](#logical-and-operator-), [`|` (logical OR)](#logical-or-operator-), and [`^` (logical exclusive OR)](#logical-exclusive-or-operator-) operators

You can use these operators with the `int`, `uint`, `long`, `ulong`, `nint`, and `nuint` types. When both operands are of other integral types (`sbyte`, `byte`, `short`, `ushort`, or `char`), their values are converted to the `int` type, which is also the result type of an operation. When operands are of different integral types, their values are converted to the closest containing integral type. For more information, see the [Numeric promotions](~/_csharpstandard/standard/expressions.md#1247-numeric-promotions) section of the [C# language specification](~/_csharpstandard/standard/README.md). The compound operators (such as `>>=`) don't convert their arguments to `int` or have the result type as `int`.

The `&`, `|`, and `^` operators also work with operands of the `bool` type. For more information, see [Boolean logical operators](boolean-logical-operators.md).

Bitwise and shift operations never cause overflow and produce the same results in [checked and unchecked](../statements/checked-and-unchecked.md) contexts.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

## Bitwise complement operator ~

The `~` operator produces a bitwise complement of its operand by reversing each bit:

```csharp
uint a = 0b_0000_1111_0000_1111_0000_1111_0000_1100;
uint b = ~a;
Console.WriteLine(Convert.ToString(b, toBase: 2));
// Output:
// 11110000111100001111000011110011
```

You can also use the `~` symbol to declare finalizers. For more information, see [Finalizers](../../programming-guide/classes-and-structs/finalizers.md).

## Left-shift operator \<\<

The `<<` operator shifts its left-hand operand to the left by the number of bits specified by its right-hand operand. For more information about how the right-hand operand defines the shift count, see the [Shift count of the shift operators](#shift-count-of-the-shift-operators) section.

The left-shift operation discards the high-order bits that fall outside the range of the result type. It sets the low-order empty bit positions to zero, as the following example shows:

```csharp
uint x = 0b_1100_1001_0000_0000_0000_0000_0001_0001;
Console.WriteLine($"Before: {Convert.ToString(x, toBase: 2)}");

uint y = x << 4;
Console.WriteLine($"After:  {Convert.ToString(y, toBase: 2)}");
// Output:
// Before: 11001001000000000000000000010001
// After:  10010000000000000000000100010000
```

Because the shift operators are defined only for the `int`, `uint`, `long`, and `ulong` types, the result of an operation always contains at least 32 bits. If the left-hand operand uses another integral type (`sbyte`, `byte`, `short`, `ushort`, or `char`), the operation converts its value to the `int` type, as the following example shows:

```csharp
byte a = 0b_1111_0001;

var b = a << 8;
Console.WriteLine(b.GetType());
Console.WriteLine($"Shifted byte: {Convert.ToString(b, toBase: 2)}");
// Output:
// System.Int32
// Shifted byte: 1111000100000000
```

## Right-shift operator >>

The `>>` operator shifts its left-hand operand right by the number of bits defined by its right-hand operand. For information about how the right-hand operand defines the shift count, see the [Shift count of the shift operators](#shift-count-of-the-shift-operators) section.

The right-shift operation discards the low-order bits, as the following example shows:

```csharp
uint x = 0b_1001;
Console.WriteLine($"Before: {Convert.ToString(x, toBase: 2), 4}");

uint y = x >> 2;
Console.WriteLine($"After:  {Convert.ToString(y, toBase: 2).PadLeft(4, '0'), 4}");
// Output:
// Before: 1001
// After:  0010
```

The high-order empty bit positions are set based on the type of the left-hand operand as follows:

- If the left-hand operand is of type `int` or `long`, the right-shift operator performs an *arithmetic* shift: the value of the most significant bit (the sign bit) of the left-hand operand is propagated to the high-order empty bit positions. That is, the high-order empty bit positions are set to zero if the left-hand operand is non-negative and set to one if it's negative.

```csharp
int a = int.MinValue;
Console.WriteLine($"Before: {Convert.ToString(a, toBase: 2)}");

int b = a >> 3;
Console.WriteLine($"After:  {Convert.ToString(b, toBase: 2)}");
// Output:
// Before: 10000000000000000000000000000000
// After:  11110000000000000000000000000000
```

- If the left-hand operand is of type `uint` or `ulong`, the right-shift operator performs a *logical* shift: the high-order empty bit positions are always set to zero.

```csharp
uint c = 0b_1000_0000_0000_0000_0000_0000_0000_0000;
Console.WriteLine($"Before: {Convert.ToString(c, toBase: 2), 32}");

uint d = c >> 3;
Console.WriteLine($"After:  {Convert.ToString(d, toBase: 2).PadLeft(32, '0'), 32}");
// Output:
// Before: 10000000000000000000000000000000
// After:  00010000000000000000000000000000
```

> [!NOTE]
> Use the [unsigned right-shift operator](#unsigned-right-shift-operator-) to perform a *logical* shift on operands of signed integer types. The logical shift is preferred. Avoid casting the left-hand operand to an unsigned type and then casting the result of a shift operation back to a signed type.

## Unsigned right-shift operator >>>

The `>>>` operator shifts its left-hand operand right by the number of bits defined by its right-hand operand. For information about how the right-hand operand defines the shift count, see the [Shift count of the shift operators](#shift-count-of-the-shift-operators) section.

The `>>>` operator always performs a *logical* shift. That is, the high-order empty bit positions are always set to zero, regardless of the type of the left-hand operand. The [`>>` operator](#right-shift-operator-) performs an *arithmetic* shift (that is, the value of the most significant bit is propagated to the high-order empty bit positions) if the left-hand operand is of a signed type. The following example demonstrates the difference between `>>` and `>>>` operators for a negative left-hand operand:

```csharp
int x = -8;
Console.WriteLine($"Before:    {x,11}, hex: {x,8:x}, binary: {Convert.ToString(x, toBase: 2), 32}");

int y = x >> 2;
Console.WriteLine($"After  >>: {y,11}, hex: {y,8:x}, binary: {Convert.ToString(y, toBase: 2), 32}");

int z = x >>> 2;
Console.WriteLine($"After >>>: {z,11}, hex: {z,8:x}, binary: {Convert.ToString(z, toBase: 2).PadLeft(32, '0'), 32}");
// Output:
// Before:             -8, hex: fffffff8, binary: 11111111111111111111111111111000
// After  >>:          -2, hex: fffffffe, binary: 11111111111111111111111111111110
// After >>>:  1073741822, hex: 3ffffffe, binary: 00111111111111111111111111111110
```

## <a name="logical-and-operator-"></a> Logical AND operator `&`

The `&` operator computes the bitwise logical AND of its integral operands:

```csharp
uint a = 0b_1111_1000;
uint b = 0b_1001_1101;
uint c = a & b;
Console.WriteLine(Convert.ToString(c, toBase: 2));
// Output:
// 10011000
```

For `bool` operands, the `&` operator computes the [logical AND](boolean-logical-operators.md#logical-and-operator-) of its operands. The unary `&` operator is the [address-of operator](pointer-related-operators.md#address-of-operator-).

## Logical exclusive OR operator ^

The `^` operator computes the bitwise logical exclusive OR, also known as the bitwise logical XOR, of its integral operands:

```csharp
uint a = 0b_1111_1000;
uint b = 0b_0001_1100;
uint c = a ^ b;
Console.WriteLine(Convert.ToString(c, toBase: 2));
// Output:
// 11100100
```

For `bool` operands, the `^` operator computes the [logical exclusive OR](boolean-logical-operators.md#logical-exclusive-or-operator-) of its operands.

## Logical OR operator |

The `|` operator computes the bitwise logical OR of its integral operands:

```csharp
uint a = 0b_1010_0000;
uint b = 0b_1001_0001;
uint c = a | b;
Console.WriteLine(Convert.ToString(c, toBase: 2));
// Output:
// 10110001
```

For `bool` operands, the `|` operator computes the [logical OR](boolean-logical-operators.md#logical-or-operator-) of its operands.

## Compound assignment

For a binary operator `op`, a compound assignment expression of the form

```csharp
x op= y
```

Is equivalent to

```csharp
x = x op y
```

Except that `x` is only evaluated once.

The following example demonstrates the usage of compound assignment with bitwise and shift operators:

```csharp
uint INITIAL_VALUE = 0b_1111_1000;

uint a = INITIAL_VALUE;
a &= 0b_1001_1101; 
Display(a);  // output: 10011000

a = INITIAL_VALUE;
a |= 0b_0011_0001; 
Display(a);  // output: 11111001

a = INITIAL_VALUE;
a ^= 0b_1000_0000;
Display(a);  // output: 01111000

a = INITIAL_VALUE;
a <<= 2;
Display(a);  // output: 1111100000

a = INITIAL_VALUE;
a >>= 4;
Display(a);  // output: 00001111

a = INITIAL_VALUE;
a >>>= 4;
Display(a);  // output: 00001111

void Display(uint x) => Console.WriteLine($"{Convert.ToString(x, toBase: 2).PadLeft(8, '0'), 8}");
```

Because of [numeric promotions](~/_csharpstandard/standard/expressions.md#1247-numeric-promotions), the result of the `op` operation might not be implicitly convertible to the type `T` of `x`. In such a case, if `op` is a predefined operator and the result of the operation is explicitly convertible to the type `T` of `x`, a compound assignment expression of the form `x op= y` is equivalent to `x = (T)(x op y)`, except that the  `x` is evaluated only once. The following example demonstrates that behavior:

```csharp
byte x = 0b_1111_0001;

int b = x << 8;
Console.WriteLine($"{Convert.ToString(b, toBase: 2)}");  // output: 1111000100000000

x <<= 8;
Console.WriteLine(x);  // output: 0
```

## Operator precedence

The following list orders bitwise and shift operators in groups from highest precedence to lowest precedence:

- ([Unary](./index.md#operator-precedence)) operators: Bitwise complement operator `~`.
- ([Shift](./index.md#operator-precedence)) operators: Shift operators `<<`, `>>`, and `>>>`.
- ([Bitwise logical AND](./index.md#operator-precedence)) operators: `&`.
- ([Bitwise logical XOR](./index.md#operator-precedence)) operators: Logical exclusive OR `^`.
- ([Bitwise logical OR](./index.md#operator-precedence)) operators: `|`.

Use parentheses, `()`, to change the order of evaluation from the default operator precedence:

```csharp
uint a = 0b_1101;
uint b = 0b_1001;
uint c = 0b_1010;

uint d1 = a | b & c;
Display(d1);  // output: 1101

uint d2 = (a | b) & c;
Display(d2);  // output: 1000

void Display(uint x) => Console.WriteLine($"{Convert.ToString(x, toBase: 2), 4}");
```

For the complete list of C# operators ordered by precedence level, see the [Operator precedence](index.md#operator-precedence) section of the [C# operators](index.md) article.

## Shift count of the shift operators

For the `x << count`, `x >> count`, and `x >>> count` expressions, the actual shift count depends on the type of `x` as follows:

- If the type of `x` is `int` or `uint`, the low-order *five* bits of the right-hand operand define the shift count. That is, the shift count is computed from `count & 0x1F` (or `count & 0b_1_1111`).

- If the type of `x` is `long` or `ulong`, the low-order *six* bits of the right-hand operand define the shift count. That is, the shift count is computed from `count & 0x3F` (or `count & 0b_11_1111`).

The following example demonstrates that behavior:

```csharp
int count1 = 0b_0000_0001;
int count2 = 0b_1110_0001;

int a = 0b_0001;
Console.WriteLine($"{a} << {count1} is {a << count1}; {a} << {count2} is {a << count2}");
// Output:
// 1 << 1 is 2; 1 << 225 is 2

int b = 0b_0100;
Console.WriteLine($"{b} >> {count1} is {b >> count1}; {b} >> {count2} is {b >> count2}");
// Output:
// 4 >> 1 is 2; 4 >> 225 is 2

int count = -31;
int c = 0b_0001;
Console.WriteLine($"{c} << {count} is {c << count}");
// Output:
// 1 << -31 is 2
```

> [!NOTE]
> As the preceding example shows, the result of a shift operation can be non-zero even if the value of the right-hand operand is greater than the number of bits in the left-hand operand.

## Enumeration logical operators

Every [enumeration](../builtin-types/enum.md) type supports the `~`, `&`, `|`, and `^` operators. For operands of the same enumeration type, a logical operation is performed on the corresponding values of the underlying integral type. For example, for any `x` and `y` of an enumeration type `T` with an underlying type `U`, the `x & y` expression produces the same result as the `(T)((U)x & (U)y)` expression.

You typically use bitwise logical operators with an enumeration type that is defined with the [Flags](xref:System.FlagsAttribute) attribute. For more information, see the [Enumeration types as bit flags](../builtin-types/enum.md#enumeration-types-as-bit-flags) section of the [Enumeration types](../builtin-types/enum.md) article.

## Operator overloadability

A user-defined type can [overload](operator-overloading.md) the `~`, `<<`, `>>`, `>>>`, `&`, `|`, and `^` operators. When you overload a binary operator, you also implicitly overload the corresponding compound assignment operator. Beginning with C# 14, a user-defined type can explicitly overload the compound assignment operators to provide a more efficient implementation. Typically, a type overloads these operators because the value can be updated in place, rather than allocating a new instance to store the result of the binary operation. If a type doesn't provide an explicit overload, the compiler generates the implicit overload.

If a user-defined type `T` overloads the `<<`, `>>`, or `>>>` operator, the type of the left-hand operand must be `T`. In C# 10 and earlier, the type of the right-hand operand must be `int`; the type of the right-hand operand of an overloaded shift operator can be any.

## C# language specification

For more information, see the following sections of the [C# language specification](~/_csharpstandard/standard/README.md):

- [Bitwise complement operator](~/_csharpstandard/standard/expressions.md#1295-bitwise-complement-operator)
- [Shift operators](~/_csharpstandard/standard/expressions.md#1214-shift-operators)
- [Logical operators](~/_csharpstandard/standard/expressions.md#1216-logical-operators)
- [Compound assignment](~/_csharpstandard/standard/expressions.md#12245-compound-assignment)
- [Numeric promotions](~/_csharpstandard/standard/expressions.md#1247-numeric-promotions)
- [User defined compound assignment](~/_csharplang/proposals/csharp-14.0/user-defined-compound-assignment.md)

## See also

- [C# operators and expressions](index.md)
- [Boolean logical operators](boolean-logical-operators.md)
