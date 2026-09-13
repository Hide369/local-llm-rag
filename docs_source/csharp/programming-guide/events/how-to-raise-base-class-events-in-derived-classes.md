---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/events/how-to-raise-base-class-events-in-derived-classes.md
title: How to raise base class events in derived classes
version: 0.0.0
fetched_at: 2026-09-13
---
# How to raise base class events in derived classes (C# Programming Guide)

The following simple example shows the standard way to declare events in a base class so that they can also be raised from derived classes. This pattern is used extensively in Windows Forms classes in the .NET class libraries.  
  
 When you create a class that can be used as a base class for other classes, you should consider the fact that events are a special type of delegate that can only be invoked from within the class that declared them. Derived classes cannot directly invoke events that are declared within the base class. Although sometimes you may want an event that can only be raised by the base class, most of the time, you should enable the derived class to invoke base class events. To do this, you can create a protected invoking method in the base class that wraps the event. By calling or overriding this invoking method, derived classes can invoke the event indirectly.  
  
> [!NOTE]
> Do not declare virtual events in a base class and override them in a derived class. The C# compiler does not handle these correctly and it is unpredictable whether a subscriber to the derived event will actually be subscribing to the base class event.  
  
## Example  

 [!code-csharp[csProgGuideEvents#1](~/samples/snippets/csharp/VS_Snippets_VBCSharp/csProgGuideEvents/CS/Events.cs#1)]  
  
## See also

- [Events](./index.md)
- [Delegates](../delegates/index.md)
- [Access Modifiers](../classes-and-structs/access-modifiers.md)
- [Creating Event Handlers in Windows Forms](/dotnet/desktop/winforms/creating-event-handlers-in-windows-forms)
