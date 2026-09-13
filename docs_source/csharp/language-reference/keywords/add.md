---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/keywords/add.md
title: The `add` keyword
version: 0.0.0
fetched_at: 2026-09-13
---
# The `add` contextual keyword (C# Reference)

Use the `add` contextual keyword to define a custom event accessor that's invoked when client code subscribes to your [event](./event.md). If you supply a custom `add` accessor, you must also supply a [remove](./remove.md) accessor.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The following example shows an event that has custom `add` and [remove](./remove.md) accessors. For the full example, see [How to implement interface events](../../programming-guide/events/how-to-implement-interface-events.md).

```csharp
class Events : IDrawingObject
{
    event EventHandler PreDrawEvent;

    event EventHandler IDrawingObject.OnDraw
    {
        add => PreDrawEvent += value;
        remove => PreDrawEvent -= value;
    }
}
```

You don't typically need to provide your own custom event accessors. The automatically generated accessors when you declare an event are sufficient for most scenarios. Starting with C# 14, you can declare [`partial`](./partial-member.md) events. The implementing declaration of a partial event must declare the `add` and `remove` handlers.

## See also

- [Events](../../programming-guide/events/index.md)
