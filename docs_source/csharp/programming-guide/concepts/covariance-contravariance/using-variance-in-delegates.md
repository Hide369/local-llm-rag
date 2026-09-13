---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/concepts/covariance-contravariance/using-variance-in-delegates.md
title: Using Variance in Delegates
version: 0.0.0
fetched_at: 2026-09-13
---
# Using Variance in Delegates (C#)

When you assign a method to a delegate, *covariance* and *contravariance* provide flexibility for matching a delegate type with a method signature. Covariance permits a method to have return type that is more derived than that defined in the delegate. Contravariance permits a method that has parameter types that are less derived than those in the delegate type.  
  
## Example 1: Covariance  
  
### Description  

 This example demonstrates how delegates can be used with methods that have return types that are derived from the return type in the delegate signature. The data type returned by `DogsHandler` is of type `Dogs`, which derives from the `Mammals` type that is defined in the delegate.  
  
### Code  
  
```csharp  
class Mammals {}  
class Dogs : Mammals {}  
  
class Program  
{  
    // Define the delegate.  
    public delegate Mammals HandlerMethod();  
  
    public static Mammals MammalsHandler()  
    {  
        return null;  
    }  
  
    public static Dogs DogsHandler()  
    {  
        return null;  
    }  
  
    static void Test()  
    {  
        HandlerMethod handlerMammals = MammalsHandler;  
  
        // Covariance enables this assignment.  
        HandlerMethod handlerDogs = DogsHandler;  
    }  
}  
```  
  
## Example 2: Contravariance  
  
### Description

This example demonstrates how delegates can be used with methods that have parameters whose types are base types of the delegate signature parameter type. With contravariance, you can use one event handler instead of separate handlers. The following example makes use of two delegates:

- A custom `KeyEventHandler` delegate that defines the signature of a key event. Its signature is:

   ```csharp
   public delegate void KeyEventHandler(object sender, KeyEventArgs e)
   ```

- A custom `MouseEventHandler` delegate that defines the signature of a mouse event. Its signature is:

   ```csharp
   public delegate void MouseEventHandler(object sender, MouseEventArgs e)
   ```

The example defines an event handler with an <xref:System.EventArgs> parameter and uses it to handle both key and mouse events. This works because <xref:System.EventArgs> is a base type of both the custom `KeyEventArgs` and `MouseEventArgs` classes defined in the example. Contravariance allows a method that accepts a base type parameter to be used for events that provide derived type parameters.

### How contravariance works in this example

When you subscribe to an event, the compiler checks if your event handler method is compatible with the event's delegate signature. With contravariance:

1. The `KeyDown` event expects a method that takes `KeyEventArgs`.
1. The `MouseClick` event expects a method that takes `MouseEventArgs`.  
1. Your `MultiHandler` method takes the base type `EventArgs`.
1. Since `KeyEventArgs` and `MouseEventArgs` both inherit from `EventArgs`, they can be safely passed to a method expecting `EventArgs`.
1. The compiler allows this assignment because it's safe - the `MultiHandler` can work with any `EventArgs` instance.

This is contravariance in action: you can use a method with a "less specific" (base type) parameter where a "more specific" (derived type) parameter is expected.
  
### Code  

```csharp
// Custom EventArgs classes to demonstrate the hierarchy
public class KeyEventArgs(string keyCode) : EventArgs
{
    public string KeyCode { get; set; } = keyCode;
}

public class MouseEventArgs(int x, int y) : EventArgs  
{
    public int X { get; set; } = x;
    public int Y { get; set; } = y;
}

// Define delegate types that match the Windows Forms pattern
public delegate void KeyEventHandler(object sender, KeyEventArgs e);
public delegate void MouseEventHandler(object sender, MouseEventArgs e);

// A simple class that demonstrates contravariance with events
public class Button
{
    // Events that expect specific EventArgs-derived types
    public event KeyEventHandler? KeyDown;
    public event MouseEventHandler? MouseClick;

    // Method to simulate key press
    public void SimulateKeyPress(string key)
    {
        Console.WriteLine($"Simulating key press: {key}");
        KeyDown?.Invoke(this, new KeyEventArgs(key));
    }

    // Method to simulate mouse click  
    public void SimulateMouseClick(int x, int y)
    {
        Console.WriteLine($"Simulating mouse click at ({x}, {y})");
        MouseClick?.Invoke(this, new MouseEventArgs(x, y));
    }
}

public class Form1
{
    private Button button1;

    public Form1()
    {
        button1 = new Button();

        // Event handler that accepts a parameter of the base EventArgs type.
        // This method can handle events that expect more specific EventArgs-derived types
        // due to contravariance in delegate parameters.

        // You can use a method that has an EventArgs parameter,
        // although the KeyDown event expects the KeyEventArgs parameter.
        button1.KeyDown += MultiHandler;

        // You can use the same method for an event that expects 
        // the MouseEventArgs parameter.
        button1.MouseClick += MultiHandler;
    }

    // Event handler that accepts a parameter of the base EventArgs type.
    // This works for both KeyDown and MouseClick events because:
    // - KeyDown expects KeyEventHandler(object sender, KeyEventArgs e)
    // - MouseClick expects MouseEventHandler(object sender, MouseEventArgs e)  
    // - Both KeyEventArgs and MouseEventArgs derive from EventArgs
    // - Contravariance allows a method with a base type parameter (EventArgs)
    //   to be used where a derived type parameter is expected
    private void MultiHandler(object sender, EventArgs e)
    {
        Console.WriteLine($"MultiHandler called at: {DateTime.Now:HH:mm:ss.fff}");

        // You can check the actual type of the event args if needed
        switch (e)
        {
            case KeyEventArgs keyArgs:
                Console.WriteLine($"  - Key event: {keyArgs.KeyCode}");
                break;
            case MouseEventArgs mouseArgs:
                Console.WriteLine($"  - Mouse event: ({mouseArgs.X}, {mouseArgs.Y})");
                break;
            default:
                Console.WriteLine($"  - Generic event: {e.GetType().Name}");
                break;
        }
    }

    public void DemonstrateEvents()
    {
        Console.WriteLine("Demonstrating contravariance in event handlers:");
        Console.WriteLine("Same MultiHandler method handles both events!\n");

        button1.SimulateKeyPress("Enter");
        button1.SimulateMouseClick(100, 200);
        button1.SimulateKeyPress("Escape");
        button1.SimulateMouseClick(50, 75);
    }
}
```

### Key points about contravariance

```csharp
// Demonstration of how contravariance works with delegates:
// 
// 1. KeyDown event signature: KeyEventHandler(object sender, KeyEventArgs e)
//    where KeyEventArgs derives from EventArgs
//
// 2. MouseClick event signature: MouseEventHandler(object sender, MouseEventArgs e)  
//    where MouseEventArgs derives from EventArgs
//
// 3. Our MultiHandler method signature: MultiHandler(object sender, EventArgs e)
//
// 4. Contravariance allows us to use MultiHandler (which expects EventArgs)
//    for events that provide more specific types (KeyEventArgs, MouseEventArgs)
//    because the more specific types can be safely treated as their base type.
//
// This is safe because:
// - The MultiHandler only uses members available on the base EventArgs type
// - KeyEventArgs and MouseEventArgs can be implicitly converted to EventArgs
// - The compiler knows that any EventArgs-derived type can be passed safely
```

When you run this example, you'll see that the same `MultiHandler` method successfully handles both key and mouse events, demonstrating how contravariance enables more flexible and reusable event handling code.  
  
## See also

- [Variance in Delegates (C#)](./variance-in-delegates.md)
- [Using Variance for Func and Action Generic Delegates (C#)](./using-variance-for-func-and-action-generic-delegates.md)
