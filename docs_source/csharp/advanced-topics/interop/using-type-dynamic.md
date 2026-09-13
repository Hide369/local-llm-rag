---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/advanced-topics/interop/using-type-dynamic.md
title: Using type dynamic
version: 0.0.0
fetched_at: 2026-09-13
---
# Using type dynamic

The `dynamic` type is a static type, but an object of type `dynamic` bypasses static type checking. In most cases, it functions like it has type `object`. The compiler assumes a `dynamic` element supports any operation. Therefore, you don't have to determine whether the object gets its value from a COM API, from a dynamic language such as IronPython, from the HTML Document Object Model (DOM), from reflection, or from somewhere else in the program. However, if the code isn't valid, errors surface at run time.

For example, if instance method `exampleMethod1` in the following code has only one parameter, the compiler recognizes that the first call to the method, `ec.exampleMethod1(10, 4)`, isn't valid because it contains two arguments. The call causes a compiler error. The compiler doesn't check the second call to the method, `dynamic_ec.exampleMethod1(10, 4)`, because the type of `dynamic_ec` is `dynamic`. Therefore, no compiler error is reported. However, the error doesn't escape notice indefinitely. It appears at run time and causes a run-time exception.

```csharp
static void Main(string[] args)
{
    ExampleClass ec = new ExampleClass();
    // The following call to exampleMethod1 causes a compiler error
    // if exampleMethod1 has only one parameter. Uncomment the line
    // to see the error.
    // ec.exampleMethod1(10, 4);

    dynamic dynamic_ec = new ExampleClass();
    // The following line is not identified as an error by the
    // compiler, but it causes a run-time exception.
    dynamic_ec.exampleMethod1(10, 4);

    // The following calls also do not cause compiler errors, whether
    // appropriate methods exist or not.
    dynamic_ec.someMethod("some argument", 7, null);
    dynamic_ec.nonexistentMethod();
}
```

```csharp
class ExampleClass
{
    public ExampleClass() { }
    public ExampleClass(int v) { }

    public void exampleMethod1(int i) { }

    public void exampleMethod2(string str) { }
}
```

The role of the compiler in these examples is to package together information about what each statement is proposing to do to the `dynamic` object or expression. The runtime examines the stored information and any statement that isn't valid causes a run-time exception.

The result of most dynamic operations is itself `dynamic`. For example, if you rest the mouse pointer over the use of `testSum` in the following example, IntelliSense displays the type **(local variable) dynamic testSum**.

```csharp
dynamic d = 1;
var testSum = d + 3;
// Rest the mouse pointer over testSum in the following statement.
System.Console.WriteLine(testSum);
```

Operations in which the result isn't `dynamic` include:

* Conversions from `dynamic` to another type.
* Constructor calls that include arguments of type `dynamic`.

For example, the type of `testInstance` in the following declaration is `ExampleClass`, not `dynamic`:

```csharp
var testInstance = new ExampleClass(d);
```

## Conversions

Conversions between dynamic objects and other types are easy. Conversions enable the developer to switch between dynamic and non-dynamic behavior.

You can convert any to `dynamic` implicitly, as shown in the following examples.

```csharp
dynamic d1 = 7;
dynamic d2 = "a string";
dynamic d3 = System.DateTime.Today;
dynamic d4 = System.Diagnostics.Process.GetProcesses();
```

Conversely, you can dynamically apply any implicit conversion to any expression of type `dynamic`.

```csharp
int i = d1;
string str = d2;
DateTime dt = d3;
System.Diagnostics.Process[] procs = d4;
```

## Overload resolution with arguments of type dynamic

Overload resolution occurs at run time instead of at compile time if one or more of the arguments in a method call have the type `dynamic`, or if the receiver of the method call is of type `dynamic`. In the following example, if the only accessible `exampleMethod2` method takes a string argument, sending `d1` as the argument doesn't cause a compiler error, but it does cause a run-time exception. Overload resolution fails at run time because the run-time type of `d1` is `int`, and `exampleMethod2` requires a string.

```csharp
// Valid.
ec.exampleMethod2("a string");

// The following statement does not cause a compiler error, even though ec is not
// dynamic. A run-time exception is raised because the run-time type of d1 is int.
ec.exampleMethod2(d1);

// The following statement does cause a compiler error.
// Uncomment the line to see the error.
// ec.exampleMethod2(7);
```

## Dynamic language runtime

The dynamic language runtime (DLR) provides the infrastructure that supports the `dynamic` type in C#, and also the implementation of dynamic programming languages such as IronPython and IronRuby. For more information about the DLR, see [Dynamic Language Runtime Overview](../../../framework/reflection-and-codedom/dynamic-language-runtime-overview.md).

## COM interop

Many COM methods allow for variation in argument types and return type by designating the types as `object`. COM interop necessitates explicit casting of the values to coordinate with strongly typed variables in C#. If you compile by using the [**EmbedInteropTypes** (C# Compiler Options)](../../language-reference/compiler-options/inputs.md#embedinteroptypes) option, the introduction of the `dynamic` type enables you to treat the occurrences of `object` in COM signatures as if they were of type `dynamic`, and thereby to avoid much of the casting. For more information on using the `dynamic` type with COM objects, see the article on [How to access Office interop objects by using C# features](./how-to-access-office-interop-objects.md).

## Related articles

|Title|Description|
|-----------|-----------------|
|[dynamic](../../language-reference/builtin-types/reference-types.md#the-dynamic-type)|Describes the usage of the `dynamic` keyword.|
|[Dynamic Language Runtime Overview](../../../framework/reflection-and-codedom/dynamic-language-runtime-overview.md)|Provides an overview of the DLR, which is a runtime environment that adds a set of services for dynamic languages to the common language runtime (CLR).|
|[Walkthrough: Creating and Using Dynamic Objects](walkthrough-creating-and-using-dynamic-objects.md)|Provides step-by-step instructions for creating a custom dynamic object and for creating a project that accesses an `IronPython` library.|
