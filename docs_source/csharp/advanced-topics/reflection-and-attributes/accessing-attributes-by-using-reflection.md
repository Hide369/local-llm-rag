---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/advanced-topics/reflection-and-attributes/accessing-attributes-by-using-reflection.md
title: Access attributes using reflection
version: 0.0.0
fetched_at: 2026-09-13
---
# Access attributes using reflection

The fact that you can define custom attributes and place them in your source code would be of little value without some way of retrieving that information and acting on it. By using reflection, you can retrieve the information that was defined with custom attributes. The key method is `GetCustomAttributes`, which returns an array of objects that are the run-time equivalents of the source code attributes. This method has many overloaded versions. For more information, see <xref:System.Attribute>.

An attribute specification such as:

```csharp
[Author("P. Ackerman", Version = 1.1)]
class SampleClass { }
```

is conceptually equivalent to the following code:

```csharp
var anonymousAuthorObject = new Author("P. Ackerman")
{
    Version = 1.1
};
```

However, the code isn't executed until `SampleClass` is queried for attributes. Calling `GetCustomAttributes` on `SampleClass` causes an `Author` object to be constructed and initialized. If the class has other attributes, other attribute objects are constructed similarly. `GetCustomAttributes` then returns the `Author` object and any other attribute objects in an array. You can then iterate over this array, determine what attributes were applied based on the type of each array element, and extract information from the attribute objects.

Here's a complete example. A custom attribute is defined, applied to several entities, and retrieved via reflection.

```csharp
// Multiuse attribute.
// <DefineCustomAttribute>
[System.AttributeUsage(System.AttributeTargets.Class |
                       System.AttributeTargets.Struct,
                       AllowMultiple = true)  // Multiuse attribute.
]
public class AuthorAttribute : System.Attribute
{
    string Name;
    public string Version;

    public AuthorAttribute(string name)
    {
        Name = name;

        // Default value.
        Version = "1.0";
    }

    public string GetName() => Name;
}
```

## See also

- <xref:System.Reflection>
- <xref:System.Attribute>
- [Retrieving Information Stored in Attributes](../../../standard/attributes/retrieving-information-stored-in-attributes.md)
