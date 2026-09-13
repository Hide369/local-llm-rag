---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/equality-operators.md
title: Equality operators - test if two objects are equal or not equal
version: 0.0.0
fetched_at: 2026-09-13
---
# Equality operators - test if two objects are equal or not

The [`==` (equality)](#equality-operator-) and [`!=` (inequality)](#inequality-operator-) operators check if their operands are equal or not. Value types are equal when their contents are equal. Reference types are equal when the two variables refer to the same storage.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

You can use the [`is`](./is.md) pattern matching operator as an alternative to an `==` test when you test against a [constant value](./patterns.md#constant-pattern). The `is` operator uses the default equality semantics for all value and reference types.

## Equality operator ==

The equality operator `==` returns `true` if its operands are equal, `false` otherwise.

### Value types equality

Operands of the [built-in value types](../builtin-types/value-types.md#built-in-value-types) are equal if their values are equal:

```csharp
int a = 1 + 2 + 3;
int b = 6;
Console.WriteLine(a == b);  // output: True

char c1 = 'a';
char c2 = 'A';
Console.WriteLine(c1 == c2);  // output: False
Console.WriteLine(c1 == char.ToLower(c2));  // output: True
```

> [!NOTE]
> For the `==`, [`<`, `>`, `<=`, and `>=`](comparison-operators.md) operators, if any of the operands isn't a number (<xref:System.Double.NaN?displayProperty=nameWithType> or <xref:System.Single.NaN?displayProperty=nameWithType>), the result of operation is `false`. That condition means that the `NaN` value isn't greater than, less than, or equal to any other `double` (or `float`) value, including `NaN`. For more information and examples, see the <xref:System.Double.NaN?displayProperty=nameWithType> or <xref:System.Single.NaN?displayProperty=nameWithType> reference article.

Two operands of the same [enum](../builtin-types/enum.md) type are equal if the corresponding values of the underlying integral type are equal.

User-defined [struct](../builtin-types/struct.md) types don't support the `==` operator by default. To support the `==` operator, a user-defined struct must [overload](operator-overloading.md) it.

C# [tuples](../builtin-types/value-tuples.md) have built-in support for the `==` and `!=` operators. For more information, see the [Tuple equality](../builtin-types/value-tuples.md#tuple-equality) section of the [Tuple types](../builtin-types/value-tuples.md) article.

### Reference types equality

By default, reference-type operands, excluding records, are equal if they refer to the same object:

```csharp
public class ReferenceTypesEquality
{
    public class MyClass
    {
        private int id;

        public MyClass(int id) => this.id = id;
    }

    public static void Main()
    {
        var a = new MyClass(1);
        var b = new MyClass(1);
        var c = a;
        Console.WriteLine(a == b);  // output: False
        Console.WriteLine(a == c);  // output: True
    }
}
```

As the preceding example shows, user-defined reference types support the `==` operator by default. However, a reference type can overload the `==` operator. If a reference type overloads the `==` operator, use the <xref:System.Object.ReferenceEquals*?displayProperty=nameWithType> method to check if two references of that type refer to the same object.

### Record types equality

[Record types](../builtin-types/record.md) support the `==` and `!=` operators that by default provide value equality semantics. That is, two record operands are equal when both of them are `null` or corresponding values of all fields and automatically implemented properties are equal.

```csharp
public class RecordTypesEquality
{
    public record Point(int X, int Y, string Name);
    public record TaggedNumber(int Number, List<string> Tags);

    public static void Main()
    {
        var p1 = new Point(2, 3, "A");
        var p2 = new Point(1, 3, "B");
        var p3 = new Point(2, 3, "A");

        Console.WriteLine(p1 == p2);  // output: False
        Console.WriteLine(p1 == p3);  // output: True

        var n1 = new TaggedNumber(2, new List<string>() { "A" });
        var n2 = new TaggedNumber(2, new List<string>() { "A" });
        Console.WriteLine(n1 == n2);  // output: False
    }
}
```

As the preceding example shows, the equality of reference-type members is compared using their specific equality implementations.

### String equality

Two [string](../builtin-types/reference-types.md#the-string-type) operands are equal when both of them are `null` or both string instances are of the same length and have identical characters in each character position:

```csharp
string s1 = "hello!";
string s2 = "HeLLo!";
Console.WriteLine(s1 == s2.ToLower());  // output: True

string s3 = "Hello!";
Console.WriteLine(s1 == s3);  // output: False
```

String equality comparisons are case-sensitive ordinal comparisons. For more information about string comparison, see [How to compare strings in C#](../../fundamentals/strings/common-tasks/compare.md).

### Delegate equality

Two [delegate](../../programming-guide/delegates/index.md) operands of the same run-time type are equal when both of them are `null` or their invocation lists are the same length and have equal entries in each position:

```csharp
Action a = () => Console.WriteLine("a");

Action b = a + a;
Action c = a + a;
Console.WriteLine(object.ReferenceEquals(b, c));  // output: False
Console.WriteLine(b == c);  // output: True
```

> [!IMPORTANT]
> Equal entries in an invocation list include all fixed parameters in the invocation, including the receiver. The receiver is the instance of an object represented by `this` when the entry is invoked.

```csharp
var o1 = new object();
var o2 = new object();
var d1 = o1.ToString;
var d2 = o2.ToString;
Console.WriteLine(object.ReferenceEquals(d1, d2));  // output: False
Console.WriteLine(d1 == d2);  // output: False (different receivers)
```

For more information, see the [Delegate equality operators](~/_csharpstandard/standard/expressions.md#12159-delegate-equality-operators) section of the [C# language specification](~/_csharpstandard/standard/README.md).

Delegates that come from evaluating semantically identical [lambda expressions](lambda-expressions.md) aren't equal, as the following example shows:

```csharp
Action a = () => Console.WriteLine("a");
Action b = () => Console.WriteLine("a");

Console.WriteLine(a == b);  // output: False
Console.WriteLine(a + b == a + b);  // output: True
Console.WriteLine(b + a == a + b);  // output: False
```

## Inequality operator `!=`

The inequality operator `!=` returns `true` if its operands aren't equal, and `false` otherwise. For the operands of the [built-in types](../builtin-types/built-in-types.md), the expression `x != y` produces the same result as the expression `!(x == y)`. For more information about type equality, see the [Equality operator](#equality-operator-) section.

The following example demonstrates how to use the `!=` operator:

```csharp
int a = 1 + 1 + 2 + 3;
int b = 6;
Console.WriteLine(a != b);  // output: True

string s1 = "Hello";
string s2 = "Hello";
Console.WriteLine(s1 != s2);  // output: False

object o1 = 1;
object o2 = 1;
Console.WriteLine(o1 != o2);  // output: True
```

## Equality in class hierarchies

Records handle inheritance correctly without manual work. The compiler-generated equality checks both runtime type and all declared properties, so it automatically satisfies the symmetry and transitivity requirements. Prefer `record` over a manual unsealed hierarchy when value equality is the goal.

> [!IMPORTANT]
> Use `record` whenever possible — the compiler generates all required equality members for you. Manual implementation is only needed when your type must derive from a non-record class or has other constraints that prevent `record`.

### Implement equality yourself when a type can't be a record

Here is a minimal manual implementation for a value type that can't be a record:

```csharp
class Color : IEquatable<Color>
{
    public Color(int r, int g, int b)
    {
        R = r;
        G = g;
        B = b;
    }

    public int R { get; }
    public int G { get; }
    public int B { get; }

    public bool Equals(Color? other) =>
        other is not null && R == other.R && G == other.G && B == other.B;

    public override bool Equals(object? obj) => obj is Color other && Equals(other);
    public override int GetHashCode() => HashCode.Combine(R, G, B);
}
```

The implementation provides three required members: `Equals(T?)` as the core comparison, `override Equals(object?)` for object-level calls, and `override GetHashCode()` so hash-based collections work correctly. `HashCode.Combine` is a library helper that builds one hash from the same values used by `Equals`. Implementing <xref:System.IEquatable`1> (the `Equals(T?)` overload) is optional but avoids boxing when callers already have the concrete type.

When you also define `==` and `!=`, the language requires them as a pair; warnings [CS0660](../../language-reference/compiler-messages/overloaded-operator-errors.md#equality-operators) and [CS0661](../../language-reference/compiler-messages/overloaded-operator-errors.md#equality-operators) remind you to keep all four members consistent.

With the three members above in place, `Equals` reflects value equality, but `==` still tests identity because no `==` operator has been declared yet:

```csharp
var red1 = new Color(255, 0, 0);
var red2 = new Color(255, 0, 0);

Console.WriteLine(red1.Equals(red2)); // => True
Console.WriteLine(red1 == red2);      // => False  (no == overload; identity check)
```

A correct implementation must also satisfy the *equivalence contract* (assume `x`, `y`, and `z` are non-null):

1. **Reflexive**: `x.Equals(x)` returns `true`.
2. **Symmetric**: `x.Equals(y)` returns the same value as `y.Equals(x)`.
3. **Transitive**: if `x.Equals(y)` and `y.Equals(z)` are both `true`, then `x.Equals(z)` must be `true`.
4. **Consistent**: successive calls to `x.Equals(y)` return the same value as long as neither object changes.
5. **Null behavior**: `x.Equals(null)` returns `false`; `x.Equals(y)` must not throw when called on a non-null `x`.

Value equality in an unsealed class hierarchy requires more care than in a sealed class to satisfy the symmetric and transitive rules. The hazard is that `IEquatable<T>.Equals(T? other)` dispatch follows the *declared type* (the type written in the variable declaration) of the variable, not its runtime type. If `Shape` declares a non-`virtual` `Equals(Shape? other)`, a variable typed as `Shape` that holds a `Circle` at runtime invokes `Shape.Equals`—silently ignoring `Circle`-specific fields. Two `Circle` objects with different radii can compare as equal when accessed through a `Shape` variable.

The correct pattern requires two cooperating requirements: make the typed `Equals` method `virtual` so each derived class can extend the comparison, and add a `GetType() == other.GetType()` guard in the base-class implementation so objects of different runtime types are never considered equal.

### Base class implementation

```csharp
// Shape is an unsealed base class. Making Equals virtual and guarding with GetType()
// ensures a derived instance is never equal to an instance of a different runtime type.
class Shape : IEquatable<Shape>
{
    public string Color { get; }
    public Shape(string color) => Color = color;

    public override bool Equals(object? obj) => Equals(obj as Shape);

    // virtual so derived classes can override and augment the comparison
    public virtual bool Equals(Shape? other) =>
        other is not null &&
        GetType() == other.GetType() &&   // reject different runtime types
        Color == other.Color;

    // GetType() is included because equality requires matching runtime types
    public override int GetHashCode() => HashCode.Combine(GetType(), Color);

    public static bool operator ==(Shape? l, Shape? r) => l?.Equals(r) ?? r is null;
    public static bool operator !=(Shape? l, Shape? r) => !(l == r);
}
```

Key points:

- **`virtual` typed `Equals`**: each derived class overrides this method to augment the comparison with its own fields.
- **`GetType()` guard**: `GetType() == other.GetType()` prevents a `Circle` from equaling a `Shape` with the same color, and prevents objects of different derived types from equaling each other.
- **`GetHashCode` includes `GetType()`**: because two objects are equal only when their runtime types match, `GetHashCode` must hash the runtime type as well as the data fields. Omitting `GetType()` here causes incorrect behavior in `Dictionary<TKey,TValue>` and `HashSet<T>`.
- **`==` delegates to `Equals`**: keeps operator and method equality consistent.

### Derived class implementation

A derived class that adds fields overrides the typed `Equals`, casts to its own type, calls `base.Equals`, then compares its own fields:

```csharp
class Circle : Shape
{
    public double Radius { get; }
    public Circle(string color, double radius) : base(color) => Radius = radius;

    public override bool Equals(object? obj) => Equals(obj as Shape);

    // Calls base.Equals to verify Color and runtime type, then adds Radius
    public override bool Equals(Shape? other) =>
        other is Circle c && base.Equals(c) && Radius == c.Radius;

    public override int GetHashCode() => HashCode.Combine(GetType(), Color, Radius);
}
```

`base.Equals(c)` enforces the `GetType()` guard and checks the shared fields. The cast via `other is Circle c` fails fast when the argument is a `Shape` of any other derived type.

### Usage through a base-type variable

```csharp
Shape circle1 = new Circle("red", 5.0);
Shape circle2 = new Circle("red", 7.0);
Shape circle3 = new Circle("red", 5.0);
Shape shape1  = new Shape("red");

Console.WriteLine(circle1.Equals(circle2)); // => False  (Radius differs)
Console.WriteLine(circle1.Equals(circle3)); // => True
Console.WriteLine(circle1.Equals(shape1));  // => False  (different runtime types)
```

### Sealed classes are simpler

You can't subclass a `sealed` class, so compile-time and runtime types always agree. You don't need the `GetType()` guard or `virtual` dispatch. The `IEquatable<T>` pattern shown in [Implement equality yourself when a type can't be a record](#implement-equality-yourself-when-a-type-cant-be-a-record) is correct and complete for a sealed class.

## Operator overloadability

You can [overload](operator-overloading.md) the `==` and `!=` operators in a user-defined type. If you overload one of these two operators, you must also overload the other operator.

You can't explicitly overload the `==` and `!=` operators in a record type. To change the behavior of the `==` and `!=` operators for record type `T`, implement the <xref:System.IEquatable`1.Equals*?displayProperty=nameWithType> method with the following signature:

```csharp
public virtual bool Equals(T? other);
```

## C# language specification

For more information, see the [Relational and type-testing operators](~/_csharpstandard/standard/expressions.md#1215-relational-and-type-testing-operators) section of the [C# language specification](~/_csharpstandard/standard/README.md).

For more information about equality of record types, see the [Equality members](~/_csharpstandard/standard/classes.md#151643-equality-members) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
- <xref:System.IEquatable`1?displayProperty=nameWithType>
- <xref:System.Object.Equals*?displayProperty=nameWithType>
- <xref:System.Object.ReferenceEquals*?displayProperty=nameWithType>
- [Equality comparisons](../../fundamentals/expressions/equality.md)
- [Comparison operators](comparison-operators.md)
