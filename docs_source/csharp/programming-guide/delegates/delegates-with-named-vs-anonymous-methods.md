---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/delegates/delegates-with-named-vs-anonymous-methods.md
title: Delegates with Named vs. Anonymous Methods
version: 0.0.0
fetched_at: 2026-09-13
---
# Delegates with Named vs. Anonymous Methods (C# Programming Guide)

A [delegate](../../language-reference/builtin-types/reference-types.md) can be associated with a named method. When you instantiate a delegate by using a named method, the method is passed as a parameter, for example:

```csharp
// Declare a delegate.
delegate void WorkCallback(int x);

// Define a named method.
void DoWork(int k) { /* ... */ }

// Instantiate the delegate using the method as a parameter.
WorkCallback d = obj.DoWork;
```

The preceding example uses a named method. Delegates constructed with a named method can encapsulate either a [static](../../language-reference/keywords/static.md) method or an instance method. Named methods are the only way to instantiate a delegate in earlier versions of C#. C# enables you to instantiate a delegate and immediately specify a code block that the delegate processes when called. The block can contain either a [lambda expression](../../language-reference/operators/lambda-expressions.md) or an [anonymous method](../../language-reference/operators/delegate-operator.md), as shown in the following example:

```csharp
// Declare a delegate.
delegate void WorkCallback(int x);

// Instantiate the delegate using an anonymous method.
WorkCallback d = (int k) => { /* ... */ };
```

The method that you pass as a delegate parameter must have the same signature as the delegate declaration. A delegate instance can encapsulate either static or instance method.

> [!NOTE]
> Although the delegate can use an [out](../../language-reference/keywords/method-parameters.md#out-parameter-modifier) parameter, we do not recommend its use with multicast event delegates because you cannot know which delegate will be called.

Method groups with a single overload have a *natural type*. The compiler can infer the return type and parameter types for the delegate type:

```csharp
var read = Console.Read; // Just one overload; Func<int> inferred
var write = Console.Write; // ERROR: Multiple overloads, can't choose
```

## Examples

The following example is a simple example of declaring and using a delegate. Notice that both the delegate, `MultiplyCallback`, and the associated method, `MultiplyNumbers`, have the same signature

```csharp
// Declare a delegate
delegate void MultiplyCallback(int i, double j);

class MathClass
{
    static void Main()
    {
        MathClass m = new MathClass();

        // Delegate instantiation using "MultiplyNumbers"
        MultiplyCallback d = m.MultiplyNumbers;

        // Invoke the delegate object.
        Console.WriteLine("Invoking the delegate using 'MultiplyNumbers':");
        for (int i = 1; i <= 5; i++)
        {
            d(i, 2);
        }

        // Keep the console window open in debug mode.
        Console.WriteLine("Press any key to exit.");
        Console.ReadKey();
    }

    // Declare the associated method.
    void MultiplyNumbers(int m, double n)
    {
        Console.Write(m * n + " ");
    }
}
/* Output:
    Invoking the delegate using 'MultiplyNumbers':
    2 4 6 8 10
*/
```

In the following example, one delegate is mapped to both static and instance methods and returns specific information from each.

```csharp
// Declare a delegate
delegate void Callback();

class SampleClass
{
    public void InstanceMethod()
    {
        Console.WriteLine("A message from the instance method.");
    }

    static public void StaticMethod()
    {
        Console.WriteLine("A message from the static method.");
    }
}

class TestSampleClass
{
    static void Main()
    {
        var sc = new SampleClass();

        // Map the delegate to the instance method:
        Callback d = sc.InstanceMethod;
        d();

        // Map to the static method:
        d = SampleClass.StaticMethod;
        d();
    }
}
/* Output:
    A message from the instance method.
    A message from the static method.
*/
```

## See also

- [Delegates](./index.md)
- [How to combine delegates (Multicast Delegates)](./how-to-combine-delegates-multicast-delegates.md)
- [Events](../events/index.md)
