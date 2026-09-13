---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/expressions/operators.md
title: C# arithmetic, comparison, logical, and assignment operators
version: 0.0.0
fetched_at: 2026-09-13
---

# C# operators

> [!TIP]
> This article is part of the **Fundamentals** section for developers who already know at least one programming language and are learning C#. If you're new to programming, start with the [Get started](../../tour-of-csharp/tutorials/index.md) tutorials first.
>
> **Coming from another language?** Most operators in this article (`+`, `-`, `*`, `/`, `%`, `&&`, `||`, `!`, `==`, `!=`, `<`, `>`, comparison operators, and `=`) work the same as in Java, C++, and JavaScript. The main surprises for newcomers are integer division behavior, the prefix/postfix distinction for `++`/`--`, and the way compound assignment converts back to the left-hand-side type.

An *operator* combines one or more *operands* into a single value. You already know about expressions and operator precedence from [C# expressions](index.md); this article goes deeper into the specific operators you'll use every day.

## Arithmetic operators

The five arithmetic operators perform numeric calculations.

| Operator | Name           | Example  | Result |
|----------|----------------|----------|--------|
| `+`      | Addition       | `10 + 3` | `13`   |
| `-`      | Subtraction    | `10 - 3` | `7`    |
| `*`      | Multiplication | `10 * 3` | `30`   |
| `/`      | Division       | `10 / 3` | `3`    |
| `%`      | Remainder      | `10 % 3` | `1`    |

```csharp
int apples = 10;
int oranges = 3;

Console.WriteLine(apples + oranges);  // => 13  (addition)
Console.WriteLine(apples - oranges);  // => 7   (subtraction)
Console.WriteLine(apples * oranges);  // => 30  (multiplication)
Console.WriteLine(apples / oranges);  // => 3   (integer division: truncates toward zero)
Console.WriteLine(apples % oranges);  // => 1   (remainder)

// Integer division always truncates toward zero — the fractional part is discarded
int result = 7 / 2;
Console.WriteLine(result); // => 3, not 3.5

// Truncation applies to negative results too: -7 / 2 is -3, not -4
int negResult = -7 / 2;
Console.WriteLine(negResult); // => -3

// To get a decimal result, at least one operand must be a double or float
double precise = 7.0 / 2;
Console.WriteLine(precise); // => 3.5

// Remainder with negative operands: the sign of the result matches the dividend
Console.WriteLine(-7 % 3);  // => -1  (-7 = 3 × -2 + (-1))
Console.WriteLine(7 % -3);  // => 1   ( 7 = -3 × -2 + 1)
```

**Integer division truncates toward zero.** When both operands are integers, `/` discards the fractional part: `7 / 2` is `3`, not `3.5`. Truncation is toward zero, not toward the smaller number: `-7 / 2` is `-3` (not `-4`). To get a decimal result, make at least one operand a floating-point type: `7.0 / 2` is `3.5`. This differs from some languages where `/` always produces a floating-point result.

**Remainder (`%`) returns what's left over** after integer division: `10 % 3` is `1` because `10 = 3 × 3 + 1`. It's useful for cycling through a fixed range (`index % length`), testing divisibility (`n % 2 == 0`), and extracting digits. With negative operands, the sign of the result matches the sign of the *dividend* (the left operand): `-7 % 3` is `-1` and `7 % -3` is `1`.

## Unary operators

Unary operators act on a single operand.

```csharp
int temperature = 20;
int windChill = -5;

int heatIndex = +temperature;   // unary +: value unchanged (rarely needed)
int coldFactor = -windChill;    // unary -: negates the value → 5

Console.WriteLine(heatIndex);   // => 20
Console.WriteLine(coldFactor);  // => 5

bool isRaining = false;
bool isSunny = !isRaining;     // logical NOT: flips true/false
Console.WriteLine(isSunny);    // => True
```

- `+x` (unary plus) — leaves the value unchanged; rarely written explicitly but valid.
- `-x` (unary minus) — negates the value.
- `!x` (logical NOT) — flips `true` to `false` and `false` to `true`. You'll use `!` often: `if (!list.Contains(item))`.

## Increment and decrement

`++` adds 1 and `--` subtracts 1. Both have a *prefix* form and a *postfix* form that differ in which value is returned:

```csharp
int counter = 5;

// Prefix: increment first, then use the new value
int a = ++counter;
Console.WriteLine(a);       // => 6
Console.WriteLine(counter); // => 6

// Postfix: use the current value first, then increment
int b = counter++;
Console.WriteLine(b);       // => 6  (value before increment)
Console.WriteLine(counter); // => 7  (incremented after)

// Decrement works the same way
int score = 10;
Console.WriteLine(score--); // => 10 (current value; score becomes 9)
Console.WriteLine(score);   // => 9
```

- **Prefix** (`++i`, `--i`): increments or decrements the variable first, then returns the *new* value.
- **Postfix** (`i++`, `i--`): returns the *current* value first, then increments or decrements the variable.

When `++` or `--` appears as a standalone statement (not part of a larger expression), prefix and postfix have the same effect. The distinction matters only when the result is used — for example, in an assignment or as a method argument.

## Relational operators

Relational operators compare two values and return a `bool`.

| Operator | Meaning               | Example         |
|----------|-----------------------|-----------------|
| `<`      | Less than             | `speed < limit` |
| `>`      | Greater than          | `speed > limit` |
| `<=`     | Less than or equal    | `score <= 100`  |
| `>=`     | Greater than or equal | `score >= 0`    |

```csharp
int speed = 75;
int limit = 60;

Console.WriteLine(speed > limit);   // => True   (greater than)
Console.WriteLine(speed < limit);   // => False  (less than)
Console.WriteLine(speed >= limit);  // => True   (greater than or equal)
Console.WriteLine(speed <= limit);  // => False  (less than or equal)

// Relational operators work on all numeric types and char
// char comparison uses the character's numeric Unicode code point, not alphabetical position
// 'B' (U+0042, value 66) is less than 'A' (U+0041, value 65)? No — 'A' (65) < 'B' (66)
char grade = 'B';
Console.WriteLine(grade >= 'A' && grade <= 'C'); // => True  ('A'=65 <= 'B'=66 <= 'C'=67)
```

Relational operators work on all numeric types and `char`. For `char`, comparison uses the character's numeric Unicode code point value, not any alphabetical or domain-specific ordering. In the grade example above, `'B'` is greater than or equal to `'A'` because `'B'` has Unicode value 66 and `'A'` has Unicode value 65 — the *numbers* determine the comparison, not the meaning of the letter grades.

## Equality operators

`==` and `!=` check whether two values are equal or not. `!=` is `true` when the operands are **not** equal, and `false` when they are.

```csharp
int expected = 42;
int actual = 42;

Console.WriteLine(actual == expected);  // => True   (values are equal)
Console.WriteLine(actual != expected);  // => False  (true when values are not equal)

string name = "Alice";
Console.WriteLine(name == "Alice");  // => True   (string content matches)
Console.WriteLine(name == "alice");  // => False  (case-sensitive)

int x = 5;
Console.WriteLine(x == 10);  // => False
```

For numeric types and `string`, equality tests the values. For reference types, the default is identity (whether two variables point to the same object), but many types including `string` and `record` override this to compare content. For the full picture — how equality works across value types, reference types, records, and structs — see [Equality comparisons](equality.md).

> [!NOTE]
> C# doesn't have a `===` operator. Writing `===` is a compile-time error:
>
> ```csharp
> // This does not compile — C# has no === operator
> bool same = (x === 10);
> ```
>
> If you're coming from JavaScript, use `==` for value comparison (C# `==` already compares by value for primitive types and strings). A common related bug is accidentally writing `=` (assignment) where you meant `==` (equality check). The compiler catches the most common forms, but double-check any `if` condition that contains `=`.

## Conditional-logical operators

`&&` (AND) and `||` (OR) combine `bool` expressions.

```csharp
int age = 20;
bool hasTicket = true;

// && (AND): both sides must be true
bool canEnter = age >= 18 && hasTicket;
Console.WriteLine(canEnter); // => True

// || (OR): at least one side must be true
bool freeEntry = age < 5 || age >= 65;
Console.WriteLine(freeEntry); // => False

// Short-circuit: right side is skipped when the result is already determined
// Here, items.Count is never called if items is null
List<string>? items = null;
bool hasItems = items != null && items.Count > 0;
Console.WriteLine(hasItems); // => False  (short-circuits; no NullReferenceException)
```

Both operators *short-circuit*: they skip evaluating the right operand when the result is already determined.

- `&&` returns `false` as soon as the left side is `false`. The right side is never evaluated.
- `||` returns `true` as soon as the left side is `true`. The right side is never evaluated.

Short-circuit behavior has a practical benefit: you can safely guard an operation on the right side with a null check on the left side, as the example above shows. If `items` is `null`, the `&&` stops there — `items.Count` is never called, so no `NullReferenceException` is thrown.

## Conditional operator `?:`

The conditional operator (also called the *ternary* operator) evaluates one of two expressions based on a condition:

```
condition ? value-when-true : value-when-false
```

```csharp
int temperature2 = 35;

// condition ? value-when-true : value-when-false
string weather = temperature2 > 30 ? "hot" : "comfortable";
Console.WriteLine(weather); // => hot

// Only the matching branch evaluates — the other branch is never run
int divisor = 0;
// The division 10 / divisor is never evaluated because divisor == 0 is true
int safe = divisor == 0 ? -1 : 10 / divisor;
Console.WriteLine(safe); // => -1
```

The `?:` operator always evaluates exactly one branch — the side that doesn't match the condition is never evaluated. This makes it safe to use an expression on one side that would fail for other inputs, as long as the condition properly guards it.

Use `?:` for simple, inline choices. For multi-way conditions or blocks of code, an `if`/`else` statement is usually clearer.

## Assignment operators

The simple assignment operator `=` stores a value in a variable:

```csharp
int level = 1;  // declaration + initialization
level = 5;      // reassignment
```

Assignment in C# is *right-associative*, which means `a = b = c = 0` evaluates right to left: `c` gets `0`, then `b` gets `0`, then `a` gets `0`.

### Compound assignment

Compound assignment operators combine a binary operation with assignment:

| Operator | Equivalent to |
|----------|---------------|
| `x += y` | `x = x + y`   |
| `x -= y` | `x = x - y`   |
| `x *= y` | `x = x * y`   |
| `x /= y` | `x = x / y`   |
| `x %= y` | `x = x % y`   |

```csharp
int level = 1;
level = 5;          // simple assignment: replaces the value
Console.WriteLine(level); // => 5

// Compound assignment: short form of binary operation + assignment
int hp = 100;
hp += 20;   // same as: hp = hp + 20
Console.WriteLine(hp); // => 120
hp -= 10;   // same as: hp = hp - 10
Console.WriteLine(hp); // => 110
hp *= 2;    // same as: hp = hp * 2
Console.WriteLine(hp); // => 220
hp /= 3;    // same as: hp = hp / 3 (integer division)
Console.WriteLine(hp); // => 73
hp %= 7;    // same as: hp = hp % 7
Console.WriteLine(hp); // => 3
```

Compound assignment is more than just a shorthand. It evaluates the left-hand side **exactly once** and then converts the result back to the left-hand-side type. This matters when the left side has side effects (like an array indexer), and it's why compound assignment on a `byte` variable compiles without an explicit cast while the expanded form does not:

```csharp
// Assignment is right-associative: evaluated right to left
int a2, b2, c2;
a2 = b2 = c2 = 0;     // c2 = 0 first, then b2 = 0, then a2 = 0
Console.WriteLine($"{a2} {b2} {c2}"); // => 0 0 0

// Compound assignment evaluates the left side once and converts back to the LHS type
byte small = 200;
small += 10;  // equivalent to: small = (byte)(small + 10); result is 210
Console.WriteLine(small); // => 210
```

`small += 10` compiles because the compiler inserts the narrowing conversion automatically — the result, `210`, fits within the `byte` range of 0–255. `small = small + 10` would require an explicit `(byte)` cast, because the arithmetic promotes both operands to `int`.

## Other C# operators

This article covers the operators you'll encounter most in everyday code. The C# language includes more operators useful in specific scenarios:

- **Shift operators** (`<<`, `>>`, `>>>`) — shift the bits of an integer value left or right by a specified number of positions. **Bitwise and integer logical operators** (`&`, `|`, `^`, `~`) — combine or invert integer values one bit at a time, useful in flags, masks, and low-level code: [Bitwise and shift operators](../../language-reference/operators/bitwise-and-shift-operators.md)
- **`checked` and `unchecked`** — control whether integer overflow throws an exception (`checked`) or wraps silently (`unchecked`): [Checked and unchecked](../../language-reference/statements/checked-and-unchecked.md)
- **Null operators** (`??`, `??=`, `?.`, `?[]`) — safely handle `null` values by providing defaults or short-circuiting member access: [Null operators](../null-safety/null-operators.md)
- **Type-test and conversion operators** (`is`, `as`, `typeof`, cast `(T)`) — check or convert a value's runtime type: [Type-testing and cast operators](../../language-reference/operators/type-testing-and-cast.md)
- **Range and index operators** (`..`, `^`) — create ranges and end-relative indexes for slicing arrays and spans: [Member access and null-conditional operators](../../language-reference/operators/member-access-operators.md)
- **Deconstruction assignment** — unpack a tuple or type into individual variables in a single expression: [Deconstructing tuples and other types](../../fundamentals/functional/deconstruct.md)

## See also

- [C# expressions](index.md) — how expressions form and how operator precedence works
- [Equality comparisons](equality.md) — how `==`, `!=`, and `Equals` work across different types
- [C# operators and expressions (language reference)](../../language-reference/operators/index.md) — full precedence table and every operator
