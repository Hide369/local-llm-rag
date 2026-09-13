---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/advanced-topics/interop/example-com-class.md
title: Example COM Class
version: 0.0.0
fetched_at: 2026-09-13
---
# Example COM Class

The following code is an example of a class that you would expose as a COM object. After you place this code in a .cs file added to your project, set the **Register for COM Interop** property to **True**. For more information, see [How to: Register a Component for COM Interop](/previous-versions/visualstudio/visual-studio-2010/w29wacsy(v=vs.100)).

Exposing C# objects to COM requires declaring a class interface, an "events interface" if necessary, and the class itself. Class members must follow these rules to be visible to COM:

- The class must be public.
- Properties, methods, and events must be public.
- Properties and methods must be declared on the class interface.
- Events must be declared in the event interface.

Other public members in the class that you don't declare in these interfaces aren't visible to COM, but they're visible to other .NET objects. To expose properties and methods to COM, you must declare them on the class interface and mark them with a `DispId` attribute, and implement them in the class. The order in which you declare the members in the interface is the order used for the COM vtable. To expose events from your class, you must declare them on the events interface and mark them with a `DispId` attribute. The class shouldn't implement this interface.

The class implements the class interface; it can implement more than one interface, but the first implementation is the default class interface. Implement the methods and properties exposed to COM here. They must be public and must match the declarations in the class interface. Also, declare the events raised by the class here. They must be public and must match the declarations in the events interface.

## Example

:::code language="csharp" source="./snippets/ExampleCOMClass/ExampleCOM.cs":::

## See also

- [Interoperability](./index.md)
- [Build Page, Project Designer (C#)](/visualstudio/ide/reference/build-page-project-designer-csharp)
