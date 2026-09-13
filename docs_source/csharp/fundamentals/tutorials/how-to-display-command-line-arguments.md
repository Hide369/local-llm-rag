---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/tutorials/how-to-display-command-line-arguments.md
title: How to display command-line arguments
version: 0.0.0
fetched_at: 2026-09-13
---
# How to display command-line arguments

Arguments provided to an executable on the command line are accessible in [top-level statements](../program-structure/top-level-statements.md) or through an optional parameter to `Main`. The arguments are provided in the form of an array of strings. Each element of the array contains one argument. White-space between arguments is removed. For example, consider these command-line invocations of a fictitious executable:  
  
|Input on command line|Array of strings passed to Main|  
|----------------------------|-------------------------------------|  
|**executable.exe a b c**|"a"<br /><br /> "b"<br /><br /> "c"|  
|**executable.exe one two**|"one"<br /><br /> "two"|  
|**executable.exe "one two" three**|"one two"<br /><br /> "three"|  
  
> [!NOTE]
> When you are running an application in Visual Studio, you can specify command-line arguments in the [Debug Page, Project Designer](/visualstudio/ide/reference/debug-page-project-designer).
  
## Example  

 This example displays the command-line arguments passed to a command-line application. The output shown is for the first entry in the table above.  
  
```csharp
// The Length property provides the number of array elements.
Console.WriteLine($"parameter count = {args.Length}");

for (int i = 0; i < args.Length; i++)
{
    Console.WriteLine($"Arg[{i}] = [{args[i]}]");
}

/* Output (assumes 3 cmd line args):
    parameter count = 3
    Arg[0] = [a]
    Arg[1] = [b]
    Arg[2] = [c]
*/
```

## See also

* [System.CommandLine overview](../../../standard/commandline/index.md)
* [Tutorial: Get started with System.CommandLine](../../../standard/commandline/get-started-tutorial.md)
