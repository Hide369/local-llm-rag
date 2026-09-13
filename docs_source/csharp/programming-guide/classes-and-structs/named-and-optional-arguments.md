---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/classes-and-structs/named-and-optional-arguments.md
title: Named and Optional Arguments
version: 0.0.0
fetched_at: 2026-09-13
---
# Named and Optional Arguments (C# Programming Guide)

*Named arguments* enable you to specify an argument for a parameter by matching the argument with its name rather than with its position in the parameter list. *Optional arguments* enable you to omit arguments for some parameters. Both techniques can be used with methods, indexers, constructors, and delegates.

When you use named and optional arguments, the arguments are evaluated in the order in which they appear in the argument list, not the parameter list.

Named and optional parameters enable you to supply arguments for selected parameters. This capability greatly eases calls to COM interfaces such as the Microsoft Office Automation APIs.

## Named arguments

Named arguments free you from matching the order of arguments to the order of parameters in the parameter lists of called methods. The argument for each parameter is specified by parameter name. For example, a function that prints order details (such as seller name, order number, and product name) is called by sending arguments by position, in the order defined by the function.

```csharp
PrintOrderDetails("Gift Shop", 31, "Red Mug");
```

If you don't remember the order of the parameters but know their names, you can send the arguments in any order.

```csharp
PrintOrderDetails(orderNum: 31, productName: "Red Mug", sellerName: "Gift Shop");
PrintOrderDetails(productName: "Red Mug", sellerName: "Gift Shop", orderNum: 31);
```

Named arguments also improve the readability of your code by identifying what each argument represents. In the following example method, the `sellerName` can't be null or white space. As both `sellerName` and `productName` are string types, instead of sending arguments by position, it makes sense to use named arguments to disambiguate the two and reduce confusion for anyone reading the code.

Named arguments, when used with positional arguments, are valid as long as

- they're not followed by any positional arguments, or

    ```csharp
    PrintOrderDetails("Gift Shop", 31, productName: "Red Mug");
    ```

- they're used in the correct position. In the following example, the parameter `orderNum` is in the correct position but isn't explicitly named.

    ```csharp
    PrintOrderDetails(sellerName: "Gift Shop", 31, productName: "Red Mug");
    ```

Positional arguments that follow any out-of-order named arguments are invalid.

```csharp
// This generates CS1738: Named argument specifications must appear after all fixed arguments have been specified.
PrintOrderDetails(productName: "Red Mug", 31, "Gift Shop");
```

### Example

The following code implements the examples from this section along with some extra ones.

```csharp
class NamedExample
{
    static void Main(string[] args)
    {
        // The method can be called in the normal way, by using positional arguments.
        PrintOrderDetails("Gift Shop", 31, "Red Mug");

        // Named arguments can be supplied for the parameters in any order.
        PrintOrderDetails(orderNum: 31, productName: "Red Mug", sellerName: "Gift Shop");
        PrintOrderDetails(productName: "Red Mug", sellerName: "Gift Shop", orderNum: 31);

        // Named arguments mixed with positional arguments are valid
        // as long as they are used in their correct position.
        PrintOrderDetails("Gift Shop", 31, productName: "Red Mug");
        PrintOrderDetails(sellerName: "Gift Shop", 31, productName: "Red Mug"); 
        PrintOrderDetails("Gift Shop", orderNum: 31, "Red Mug");

        // However, mixed arguments are invalid if used out-of-order.
        // The following statements will cause a compiler error.
        // PrintOrderDetails(productName: "Red Mug", 31, "Gift Shop");
        // PrintOrderDetails(31, sellerName: "Gift Shop", "Red Mug");
        // PrintOrderDetails(31, "Red Mug", sellerName: "Gift Shop");
    }

    static void PrintOrderDetails(string sellerName, int orderNum, string productName)
    {
        if (string.IsNullOrWhiteSpace(sellerName))
        {
            throw new ArgumentException(message: "Seller name cannot be null or empty.", paramName: nameof(sellerName));
        }

        Console.WriteLine($"Seller: {sellerName}, Order #: {orderNum}, Product: {productName}");
    }
}
```

## Optional arguments

The definition of a method, constructor, indexer, or delegate can specify its parameters are required or optional. Any call must provide arguments for all required parameters, but can omit arguments for optional parameters. A nullable reference type (`T?`) allows arguments to be explicitly `null` but doesn't inherently make a parameter optional.

Each optional parameter has a default value as part of its definition. If no argument is sent for that parameter, the default value is used. A default value must be one of the following types of expressions:

- a constant expression;
- an expression of the form `new ValType()`, where `ValType` is a value type, such as an [enum](../../language-reference/builtin-types/enum.md) or a [struct](../../language-reference/builtin-types/struct.md);
- an expression of the form [default(ValType)](../../language-reference/operators/default.md),  where `ValType` is a value type.

Optional parameters are defined at the end of the parameter list, after any required parameters. The caller must provide arguments for all required parameters and any optional parameters preceding those it specifies. Comma-separated gaps in the argument list aren't supported. For example, in the following code, instance method `ExampleMethod` is defined with one required and two optional parameters.

```csharp
public void ExampleMethod(int required, string optionalstr = "default string",
    int optionalint = 10)
```

The following call to `ExampleMethod` causes a compiler error, because an argument is provided for the third parameter but not for the second.

```csharp
// anExample.ExampleMethod(3, ,4);
```

However, if you know the name of the third parameter, you can use a named argument to accomplish the task.

```csharp
anExample.ExampleMethod(3, optionalint: 4);
```

IntelliSense uses brackets to indicate optional parameters, as shown in the following illustration:

![Screenshot showing IntelliSense quick info for the ExampleMethod method.](./media/named-and-optional-arguments/optional-examplemethod-parameters.png)

> [!NOTE]
> You can also declare optional parameters by using the .NET <xref:System.Runtime.InteropServices.OptionalAttribute> class. `OptionalAttribute` parameters don't require a default value. However, if a default value is desired, take a look at <xref:System.Runtime.InteropServices.DefaultParameterValueAttribute> class.

### Example

In the following example, the constructor for `ExampleClass` has one parameter, which is optional. Instance method `ExampleMethod` has one required parameter, `required`, and two optional parameters, `optionalstr` and `optionalint`. The code in `Main` shows the different ways in which the constructor and method can be invoked.

```csharp
namespace OptionalNamespace
{
    class OptionalExample
    {
        static void Main(string[] args)
        {
            // Instance anExample does not send an argument for the constructor's
            // optional parameter.
            ExampleClass anExample = new ExampleClass();
            anExample.ExampleMethod(1, "One", 1);
            anExample.ExampleMethod(2, "Two");
            anExample.ExampleMethod(3);

            // Instance anotherExample sends an argument for the constructor's
            // optional parameter.
            ExampleClass anotherExample = new ExampleClass("Provided name");
            anotherExample.ExampleMethod(1, "One", 1);
            anotherExample.ExampleMethod(2, "Two");
            anotherExample.ExampleMethod(3);

            // The following statements produce compiler errors.

            // An argument must be supplied for the first parameter, and it
            // must be an integer.
            //anExample.ExampleMethod("One", 1);
            //anExample.ExampleMethod();

            // You cannot leave a gap in the provided arguments.
            //anExample.ExampleMethod(3, ,4);
            //anExample.ExampleMethod(3, 4);

            // You can use a named parameter to make the previous
            // statement work.
            anExample.ExampleMethod(3, optionalint: 4);
        }
    }

    class ExampleClass
    {
        private string _name;

        // Because the parameter for the constructor, name, has a default
        // value assigned to it, it is optional.
        public ExampleClass(string name = "Default name")
        {
            _name = name;
        }

        // The first parameter, required, has no default value assigned
        // to it. Therefore, it is not optional. Both optionalstr and
        // optionalint have default values assigned to them. They are optional.
        //<Snippet15>
        public void ExampleMethod(int required, string optionalstr = "default string",
            int optionalint = 10)
```

The preceding code illustrates several cases where optional parameters are used correctly and incorrectly. Arguments must be supplied for all required parameters. Gaps in optional arguments must be filled with named parameters.

## Caller information attributes

[Caller information attributes](../../language-reference/attributes/caller-information.md), such as <xref:System.Runtime.CompilerServices.CallerFilePathAttribute>, <xref:System.Runtime.CompilerServices.CallerLineNumberAttribute>, <xref:System.Runtime.CompilerServices.CallerMemberNameAttribute>, and <xref:System.Runtime.CompilerServices.CallerArgumentExpressionAttribute>, are used to obtain information about the caller to a method. These attributes are especially useful when you're debugging or when you need to log information about method calls.

These attributes are optional parameters with default values provided by the compiler. The caller shouldn't explicitly provide a value for these parameters.

## COM interfaces

Named and optional arguments, along with support for dynamic objects, greatly improve interoperability with COM APIs, such as Office Automation APIs.

For example, the <xref:Microsoft.Office.Interop.Excel.Range.AutoFormat*> method in the Microsoft Office Excel <xref:Microsoft.Office.Interop.Excel.Range> interface has seven parameters, all of which are optional. These parameters are shown in the following illustration:

![Screenshot showing IntelliSense quick info for the AutoFormat method.](./media/named-and-optional-arguments/autoformat-method-parameters.png)

However, you can greatly simplify the call to `AutoFormat` by using named and optional arguments. Named and optional arguments enable you to omit the argument for an optional parameter if you don't want to change the parameter's default value. In the following call, a value is specified for only one of the seven parameters.

```csharp
var excelApp = new Microsoft.Office.Interop.Excel.Application();
excelApp.Workbooks.Add();
excelApp.Visible = true;

var myFormat =
    Microsoft.Office.Interop.Excel.XlRangeAutoFormat.xlRangeAutoFormatAccounting1;

excelApp.Range["A1", "B4"].AutoFormat( Format: myFormat );
```

For more information and examples, see [How to use named and optional arguments in Office programming](../../advanced-topics/interop/how-to-use-named-and-optional-arguments-in-office-programming.md) and [How to access Office interop objects by using C# features](../../advanced-topics/interop/how-to-access-office-interop-objects.md).

## Overload resolution

Use of named and optional arguments affects overload resolution in the following ways:

- A method, indexer, or constructor is a candidate for execution if each of its parameters either is optional or corresponds, by name or by position, to a single argument in the calling statement, and that argument can be converted to the type of the parameter.
- If more than one candidate is found, overload resolution rules for preferred conversions are applied to the arguments that are explicitly specified. Omitted arguments for optional parameters are ignored.
- If two candidates are judged to be equally good, preference goes to a candidate that doesn't have optional parameters for which arguments were omitted in the call. Overload resolution generally prefers candidates that have fewer parameters.

## C# language specification

[!INCLUDE[CSharplangspec](~/includes/csharplangspec-md.md)]
