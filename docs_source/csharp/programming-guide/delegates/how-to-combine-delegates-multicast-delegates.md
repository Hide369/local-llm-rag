---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/delegates/how-to-combine-delegates-multicast-delegates.md
title: How to combine delegates (Multicast Delegates)
version: 0.0.0
fetched_at: 2026-09-13
---
# How to combine delegates (Multicast Delegates) (C# Programming Guide)

This example demonstrates how to create multicast delegates. A useful property of [delegate](../../language-reference/builtin-types/reference-types.md) objects is that you can assign multiple methods to one delegate instance by using the `+` operator. The multicast delegate contains a list of the assigned delegates. When you call the multicast delegate, it invokes the delegates in the list, in order. You can only combine delegates of the same type. You can use the `-` operator to remove a component delegate from a multicast delegate.

```csharp
using System;


namespace DelegateExamples;

// Define a custom delegate that has a string parameter and returns void.
delegate void CustomCallback(string s);

class TestClass
{
    // Define two methods that have the same signature as CustomCallback.
    static void Hello(string s)
    {
        Console.WriteLine($"  Hello, {s}!");
    }

    static void Goodbye(string s)
    {
        Console.WriteLine($"  Goodbye, {s}!");
    }

    static void Main()
    {
        // Declare instances of the custom delegate.
        CustomCallback hiDel, byeDel, multiDel, multiMinusHiDel;

        // In this example, you can omit the custom delegate if you
        // want to and use Action<string> instead.
        //Action<string> hiDel, byeDel, multiDel, multiMinusHiDel;

        // Initialize the delegate object hiDel that references the
        // method Hello.
        hiDel = Hello;

        // Initialize the delegate object byeDel that references the
        // method Goodbye.
        byeDel = Goodbye;

        // The two delegates, hiDel and byeDel, are combined to
        // form multiDel.
        multiDel = hiDel + byeDel;

        // Remove hiDel from the multicast delegate, leaving byeDel,
        // which calls only the method Goodbye.
        multiMinusHiDel = (multiDel - hiDel)!;

        Console.WriteLine("Invoking delegate hiDel:");
        hiDel("A");
        Console.WriteLine("Invoking delegate byeDel:");
        byeDel("B");
        Console.WriteLine("Invoking delegate multiDel:");
        multiDel("C");
        Console.WriteLine("Invoking delegate multiMinusHiDel:");
        multiMinusHiDel("D");
    }
}
/* Output:
Invoking delegate hiDel:
  Hello, A!
Invoking delegate byeDel:
  Goodbye, B!
Invoking delegate multiDel:
  Hello, C!
  Goodbye, C!
Invoking delegate multiMinusHiDel:
  Goodbye, D!
*/
```

> [!NOTE]
>
> You can add the same delegate to a multicast delegate multiple times. When you call the multicast delegate, it invokes all the delegates in the list, including duplicates. When you remove a delegate from a multicast delegate, it removes the rightmost matching entry, so only one instance is removed if there are multiple copies.

## See also

- <xref:System.MulticastDelegate>
- [Events](../events/index.md)
