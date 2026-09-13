---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/advanced-topics/interop/walkthrough-creating-and-using-dynamic-objects.md
title: Walkthrough: Creating and Using Dynamic Objects
version: 0.0.0
fetched_at: 2026-09-13
---
# Walkthrough: Creating and Using Dynamic Objects in C\#

Dynamic objects expose members such as properties and methods at run time, instead of at compile time. Dynamic objects enable you to create objects to work with structures that don't match a static type or format. For example, you can use a dynamic object to reference the HTML Document Object Model (DOM), which can contain any combination of valid HTML markup elements and attributes. Because each HTML document is unique, the members for a particular HTML document are determined at run time. A common method to reference an attribute of an HTML element is to pass the name of the attribute to the `GetProperty` method of the element. To reference the `id` attribute of the HTML element `<div id="Div1">`, you first obtain a reference to the `<div>` element, and then use `divElement.GetProperty("id")`. If you use a dynamic object, you can reference the `id` attribute as `divElement.id`.

 Dynamic objects also provide convenient access to dynamic languages such as IronPython and IronRuby. You can use a dynamic object to refer to a dynamic script interpreted at run time.

 You reference a dynamic object by using late binding. You specify the type of a late-bound object as `dynamic`.For more information, see [dynamic](../../language-reference/builtin-types/reference-types.md).

 You can create custom dynamic objects by using the classes in the <xref:System.Dynamic?displayProperty=nameWithType> namespace. For example, you can create an <xref:System.Dynamic.ExpandoObject> and specify the members of that object at run time. You can also create your own type that inherits the <xref:System.Dynamic.DynamicObject> class. You can then override the members of the <xref:System.Dynamic.DynamicObject> class to provide run-time dynamic functionality.

 This article contains two independent walkthroughs:

- Create a custom object that dynamically exposes the contents of a text file as properties of an object.
- Create a project that uses an `IronPython` library.

## Prerequisites

* [Visual Studio 2022 version 17.3 or a later version](https://visualstudio.microsoft.com/downloads/?utm_medium=microsoft&utm_source=learn.microsoft.com&utm_campaign=inline+link&utm_content=download+vs2019) with the **.NET desktop development** workload installed. The .NET 7 SDK is included when you select this workload.

[!INCLUDE[note_settings_general](~/includes/note-settings-general-md.md)]

* For the second walkthrough, install [IronPython](https://ironpython.net/) for .NET. Go to their [Download page](https://ironpython.net/download/) to obtain the latest version.

## Create a Custom Dynamic Object

The first walkthrough defines a custom dynamic object that searches the contents of a text file. A dynamic property specifies the text to search for. For example, if calling code specifies `dynamicFile.Sample`, the dynamic class returns a generic list of strings that contains all of the lines from the file that begin with "Sample". The search is case-insensitive. The dynamic class also supports two optional arguments. The first argument is a search option enum value that specifies that the dynamic class should search for matches at the start of the line, the end of the line, or anywhere in the line. The second argument specifies that the dynamic class should trim leading and trailing spaces from each line before searching. For example, if calling code specifies `dynamicFile.Sample(StringSearchOption.Contains)`, the dynamic class searches for "Sample" anywhere in a line. If calling code specifies `dynamicFile.Sample(StringSearchOption.StartsWith, false)`, the dynamic class searches for "Sample" at the start of each line, and doesn't remove leading and trailing spaces. The default behavior of the dynamic class is to search for a match at the start of each line and to remove leading and trailing spaces.

### Create a custom dynamic class

Start Visual Studio. Select **Create a new project**. In the **Create a new project** dialog, select C#, select **Console Application**, and then select **Next**. In the **Configure your new project** dialog, enter `DynamicSample` for the **Project name**, and then select **Next**. In the **Additional information** dialog, select **.NET 7.0 (Current)** for the **Target Framework**, and then select **Create**. In **Solution Explorer**, right-click the DynamicSample project and select **Add** > **Class**. In the **Name** box, type `ReadOnlyFile`, and then select **Add**. At the top of the *ReadOnlyFile.cs* or *ReadOnlyFile.vb* file, add the following code to import the <xref:System.IO?displayProperty=nameWithType> and <xref:System.Dynamic?displayProperty=nameWithType> namespaces.

```csharp
using System.IO;
using System.Dynamic;
```

The custom dynamic object uses an enum to determine the search criteria. Before the class statement, add the following enum definition.

```csharp
public enum StringSearchOption
{
    StartsWith,
    Contains,
    EndsWith
}
```

Update the class statement to inherit the `DynamicObject` class, as shown in the following code example.

```csharp
class ReadOnlyFile : DynamicObject
```

Add the following code to the `ReadOnlyFile` class to define a private field for the file path and a constructor for the `ReadOnlyFile` class.

```csharp
// Store the path to the file and the initial line count value.
private string p_filePath;

// Public constructor. Verify that file exists and store the path in
// the private variable.
public ReadOnlyFile(string filePath)
{
    if (!File.Exists(filePath))
    {
        throw new Exception("File path does not exist.");
    }

    p_filePath = filePath;
}
```

1. Add the following `GetPropertyValue` method to the `ReadOnlyFile` class. The `GetPropertyValue` method takes, as input, search criteria and returns the lines from a text file that match that search criteria. The dynamic methods provided by the `ReadOnlyFile` class call the `GetPropertyValue` method to retrieve their respective results.

```csharp
public List<string> GetPropertyValue(string propertyName,
                                     StringSearchOption StringSearchOption = StringSearchOption.StartsWith,
                                     bool trimSpaces = true)
{
    StreamReader sr = null;
    List<string> results = new List<string>();
    string line = "";
    string testLine = "";

    try
    {
        sr = new StreamReader(p_filePath);

        while (!sr.EndOfStream)
        {
            line = sr.ReadLine();

            // Perform a case-insensitive search by using the specified search options.
            testLine = line.ToUpper();
            if (trimSpaces) { testLine = testLine.Trim(); }

            switch (StringSearchOption)
            {
                case StringSearchOption.StartsWith:
                    if (testLine.StartsWith(propertyName.ToUpper())) { results.Add(line); }
                    break;
                case StringSearchOption.Contains:
                    if (testLine.Contains(propertyName.ToUpper())) { results.Add(line); }
                    break;
                case StringSearchOption.EndsWith:
                    if (testLine.EndsWith(propertyName.ToUpper())) { results.Add(line); }
                    break;
            }
        }
    }
    catch
    {
        // Trap any exception that occurs in reading the file and return null.
        results = null;
    }
    finally
    {
        if (sr != null) {sr.Close();}
    }

    return results;
}
```

After the `GetPropertyValue` method, add the following code to override the <xref:System.Dynamic.DynamicObject.TryGetMember*> method of the <xref:System.Dynamic.DynamicObject> class. The <xref:System.Dynamic.DynamicObject.TryGetMember*> method is called when a member of a dynamic class is requested and no arguments are specified. The `binder` argument contains information about the referenced member, and the `result` argument references the result returned for the specified member. The <xref:System.Dynamic.DynamicObject.TryGetMember*> method returns a Boolean value that returns `true` if the requested member exists; otherwise it returns `false`.

```csharp
// Implement the TryGetMember method of the DynamicObject class for dynamic member calls.
public override bool TryGetMember(GetMemberBinder binder,
                                  out object result)
{
    result = GetPropertyValue(binder.Name);
    return result == null ? false : true;
}
```

After the `TryGetMember` method, add the following code to override the <xref:System.Dynamic.DynamicObject.TryInvokeMember*> method of the <xref:System.Dynamic.DynamicObject> class. The <xref:System.Dynamic.DynamicObject.TryInvokeMember*> method is called when a member of a dynamic class is requested with arguments. The `binder` argument contains information about the referenced member, and the `result` argument references the result returned for the specified member. The `args` argument contains an array of the arguments that are passed to the member. The <xref:System.Dynamic.DynamicObject.TryInvokeMember*> method returns a Boolean value that returns `true` if the requested member exists; otherwise it returns `false`.

The custom version of the `TryInvokeMember` method expects the first argument to be a value from the `StringSearchOption` enum that you defined in a previous step. The `TryInvokeMember` method expects the second argument to be a Boolean value. If one or both arguments are valid values, they're passed to the `GetPropertyValue` method to retrieve the results.

```csharp
// Implement the TryInvokeMember method of the DynamicObject class for
// dynamic member calls that have arguments.
public override bool TryInvokeMember(InvokeMemberBinder binder,
                                     object[] args,
                                     out object result)
{
    StringSearchOption StringSearchOption = StringSearchOption.StartsWith;
    bool trimSpaces = true;

    try
    {
        if (args.Length > 0) { StringSearchOption = (StringSearchOption)args[0]; }
    }
    catch
    {
        throw new ArgumentException("StringSearchOption argument must be a StringSearchOption enum value.");
    }

    try
    {
        if (args.Length > 1) { trimSpaces = (bool)args[1]; }
    }
    catch
    {
        throw new ArgumentException("trimSpaces argument must be a Boolean value.");
    }

    result = GetPropertyValue(binder.Name, StringSearchOption, trimSpaces);

    return result == null ? false : true;
}
```

Save and close the file.

### Create a sample text file

In **Solution Explorer**, right-click the DynamicSample project and select **Add** > **New Item**. In the **Installed Templates** pane, select **General**, and then select the **Text File** template. Leave the default name of *TextFile1.txt* in the **Name** box, and then select **Add**. Copy the following text to the *TextFile1.txt* file.

```text
List of customers and suppliers

Supplier: Lucerne Publishing (https://www.lucernepublishing.com/)
Customer: Preston, Chris
Customer: Hines, Patrick
Customer: Cameron, Maria
Supplier: Graphic Design Institute (https://www.graphicdesigninstitute.com/)
Supplier: Fabrikam, Inc. (https://www.fabrikam.com/)
Customer: Seubert, Roxanne
Supplier: Proseware, Inc. (http://www.proseware.com/)
Customer: Adolphi, Stephan
Customer: Koch, Paul
```

Save and close the file.

### Create a sample application that uses the custom dynamic object

In **Solution Explorer**, double-click the *Program.cs* file. Add the following code to the `Main` procedure to create an instance of the `ReadOnlyFile` class for the *TextFile1.txt* file. The code uses late binding to call dynamic members and retrieve lines of text that contain the string "Customer".

```csharp
dynamic rFile = new ReadOnlyFile(@"..\..\..\TextFile1.txt");
foreach (string line in rFile.Customer)
{
    Console.WriteLine(line);
}
Console.WriteLine("----------------------------");
foreach (string line in rFile.Customer(StringSearchOption.Contains, true))
{
    Console.WriteLine(line);
}
```

Save the file and press <kbd>Ctrl</kbd>+<kbd>F5</kbd> to build and run the application.

## Call a dynamic language library

The following walkthrough creates a project that accesses a library written in the dynamic language IronPython.

### To create a custom dynamic class

In Visual Studio, select **File** > **New** > **Project**. In the **Create a new project** dialog, select C#, select **Console Application**, and then select **Next**. In the **Configure your new project** dialog, enter `DynamicIronPythonSample` for the **Project name**, and then select **Next**. In the **Additional information** dialog, select **.NET 7.0 (Current)** for the **Target Framework**, and then select **Create**. Install the [IronPython](https://www.nuget.org/packages/IronPython) NuGet package. Edit the *Program.cs* file. At the top of the file, add the following code to import the `Microsoft.Scripting.Hosting` and `IronPython.Hosting` namespaces from the IronPython libraries and the `System.Linq` namespace.

```csharp
using System.Linq;
using Microsoft.Scripting.Hosting;
using IronPython.Hosting;
```

In the Main method, add the following code to create a new `Microsoft.Scripting.Hosting.ScriptRuntime` object to host the IronPython libraries. The `ScriptRuntime` object loads the IronPython library module random.py.

```csharp
// Set the current directory to the IronPython libraries.
System.IO.Directory.SetCurrentDirectory(
   Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles) +
   @"\IronPython 2.7\Lib");

// Create an instance of the random.py IronPython library.
Console.WriteLine("Loading random.py");
ScriptRuntime py = Python.CreateRuntime();
dynamic random = py.UseFile("random.py");
Console.WriteLine("random.py loaded.");
```

After the code to load the random.py module, add the following code to create an array of integers. The array is passed to the `shuffle` method of the random.py module, which randomly sorts the values in the array.

```csharp
// Initialize an enumerable set of integers.
int[] items = Enumerable.Range(1, 7).ToArray();

// Randomly shuffle the array of integers by using IronPython.
for (int i = 0; i < 5; i++)
{
    random.shuffle(items);
    foreach (int item in items)
    {
        Console.WriteLine(item);
    }
    Console.WriteLine("-------------------");
}
```

Save the file and press <kbd>Ctrl</kbd>+<kbd>F5</kbd> to build and run the application.

## See also

- <xref:System.Dynamic?displayProperty=nameWithType>
- <xref:System.Dynamic.DynamicObject?displayProperty=nameWithType>
- [Using Type dynamic](./using-type-dynamic.md)
- [dynamic](../../language-reference/builtin-types/reference-types.md)
- [Implementing Dynamic Interfaces (downloadable PDF from Microsoft TechNet)](https://download.microsoft.com/download/5/4/B/54B83DFE-D7AA-4155-9687-B0CF58FF65D7/implementing-dynamic-interfaces.pdf)
