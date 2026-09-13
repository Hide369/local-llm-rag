---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/advanced-topics/interop/how-to-access-office-interop-objects.md
title: How to access Office interop objects
version: 0.0.0
fetched_at: 2026-09-13
---
# How to access Office interop objects

C# has features that simplify access to Office API objects. The new features include named and optional arguments, a new type called `dynamic`, and the ability to pass arguments to reference parameters in COM methods as if they were value parameters.

In this article, you use the new features to write code that creates and displays a Microsoft Office Excel worksheet. You write code to add an Office Word document that contains an icon that is linked to the Excel worksheet.

To complete this walkthrough, you must have Microsoft Office Excel 2007 and Microsoft Office Word 2007, or later versions, installed on your computer.

[!INCLUDE[note_settings_general](~/includes/note-settings-general-md.md)]

[!INCLUDE[vsto_framework](../../includes/vsto-framework.md)]

## To create a new console application

1. Start Visual Studio.
1. On the **File** menu, point to **New**, and then select **Project**. The **New Project** dialog box appears.
1. In the **Installed Templates** pane, expand **C#**, and then select **Windows**.
1. Look at the top of the **New Project** dialog box to make sure to select **.NET Framework 4** (or later version) as a target framework.
1. In the **Templates** pane, select **Console Application**.
1. Type a name for your project in the **Name** field.
1. Select **OK**.

The new project appears in **Solution Explorer**.

## To add references

1. In **Solution Explorer**, right-click your project's name and then select **Add Reference**. The **Add Reference** dialog box appears.
1. On the **Assemblies**  page, select **Microsoft.Office.Interop.Word** in the **Component Name** list, and then hold down the CTRL key and select **Microsoft.Office.Interop.Excel**.  If you don't see the assemblies, you may need to install them. See [How to: Install Office Primary Interop Assemblies](/visualstudio/vsto/how-to-install-office-primary-interop-assemblies).
1. Select **OK**.

## To add necessary using directives

In **Solution Explorer**, right-click the *Program.cs* file and then select **View Code**. Add the following `using` directives to the top of the code file:

```csharp
using Excel = Microsoft.Office.Interop.Excel;
using Word = Microsoft.Office.Interop.Word;
```

## To create a list of bank accounts

Paste the following class definition into **Program.cs**, under the `Program` class.

```csharp
public class Account
{
    public int ID { get; set; }
    public double Balance { get; set; }
}
```

Add the following code to the `Main` method to create a `bankAccounts` list that contains two accounts.

```csharp
// Create a list of accounts.
var bankAccounts = new List<Account> {
    new Account {
                  ID = 345678,
                  Balance = 541.27
                },
    new Account {
                  ID = 1230221,
                  Balance = -127.44
                }
};
```

## To declare a method that exports account information to Excel

1. Add the following method to the `Program` class to set up an Excel worksheet. Method <xref:Microsoft.Office.Interop.Excel.Workbooks.Add*> has an optional parameter for specifying a particular template. Optional parameters enable you to omit the argument for that parameter if you want to use the parameter's default value. Because you didn't supply an argument, `Add` uses the default template and creates a new workbook. The equivalent statement in earlier versions of C# requires a placeholder argument: `ExcelApp.Workbooks.Add(Type.Missing)`.

```csharp
static void DisplayInExcel(IEnumerable<Account> accounts)
{
    var excelApp = new Excel.Application();
    // Make the object visible.
    excelApp.Visible = true;

    // Create a new, empty workbook and add it to the collection returned
    // by property Workbooks. The new workbook becomes the active workbook.
    // Add has an optional parameter for specifying a particular template.
    // Because no argument is sent in this example, Add creates a new workbook.
    excelApp.Workbooks.Add();

    // This example uses a single workSheet. The explicit type casting is
    // removed in a later procedure.
    Excel._Worksheet workSheet = (Excel.Worksheet)excelApp.ActiveSheet;
}
```

Add the following code at the end of `DisplayInExcel`. The code inserts values into the first two columns of the first row of the worksheet.

```csharp
// Establish column headings in cells A1 and B1.
workSheet.Cells[1, "A"] = "ID Number";
workSheet.Cells[1, "B"] = "Current Balance";
```

Add the following code at the end of `DisplayInExcel`. The `foreach` loop puts the information from the list of accounts into the first two columns of successive rows of the worksheet.

```csharp
var row = 1;
foreach (var acct in accounts)
{
    row++;
    workSheet.Cells[row, "A"] = acct.ID;
    workSheet.Cells[row, "B"] = acct.Balance;
}
```

Add the following code at the end of `DisplayInExcel` to adjust the column widths to fit the content.

```csharp
workSheet.Columns[1].AutoFit();
workSheet.Columns[2].AutoFit();
```

Earlier versions of C# require explicit casting for these operations because `ExcelApp.Columns[1]` returns an `Object`, and `AutoFit` is an Excel <xref:Microsoft.Office.Interop.Excel.Range> method. The following lines show the casting.

```csharp
((Excel.Range)workSheet.Columns[1]).AutoFit();
((Excel.Range)workSheet.Columns[2]).AutoFit();
```

C# converts the returned `Object` to `dynamic` automatically if the assembly is referenced by the [**EmbedInteropTypes**](../../language-reference/compiler-options/inputs.md#embedinteroptypes) compiler option or, equivalently, if the Excel **Embed Interop Types** property is true. True is the default value for this property.

## To run the project

Add the following line at the end of `Main`.

```csharp
// Display the list in an Excel spreadsheet.
DisplayInExcel(bankAccounts);
```

Press CTRL+F5. An Excel worksheet appears that contains the data from the two accounts.

## To add a Word document

The following code opens a Word application and creates an icon that links to the Excel worksheet. Paste method `CreateIconInWordDoc`, provided later in this step, into the `Program` class. `CreateIconInWordDoc` uses named and optional arguments to reduce the complexity of the method calls to <xref:Microsoft.Office.Interop.Word.Documents.Add*> and <xref:Microsoft.Office.Interop.Word.Selection.PasteSpecial*>. These calls incorporate two other features that simplify calls to COM methods that have reference parameters. First, you can send arguments to the reference parameters as if they were value parameters. That is, you can send values directly, without creating a variable for each reference parameter. The compiler generates temporary variables to hold the argument values, and discards the variables when you return from the call. Second, you can omit the `ref` keyword in the argument list.

The `Add` method has four reference parameters, all of which are optional. You can omit arguments for any or all of the parameters if you want to use their default values.

The `PasteSpecial` method inserts the contents of the Clipboard. The method has seven reference parameters, all of which are optional. The following code specifies arguments for two of them: `Link`, to create a link to the source of the Clipboard contents, and `DisplayAsIcon`, to display the link as an icon. You can use named arguments for those two arguments and omit the others. Although these arguments are reference parameters, you don't have to use the `ref` keyword, or to create variables to send in as arguments. You can send the values directly.

```csharp
static void CreateIconInWordDoc()
{
    var wordApp = new Word.Application();
    wordApp.Visible = true;

    // The Add method has four reference parameters, all of which are
    // optional. Visual C# allows you to omit arguments for them if
    // the default values are what you want.
    wordApp.Documents.Add();

    // PasteSpecial has seven reference parameters, all of which are
    // optional. This example uses named arguments to specify values
    // for two of the parameters. Although these are reference
    // parameters, you do not need to use the ref keyword, or to create
    // variables to send in as arguments. You can send the values directly.
    wordApp.Selection.PasteSpecial( Link: true, DisplayAsIcon: true);
}
```

Add the following statement at the end of `Main`.

```csharp
// Create a Word document that contains an icon that links to
// the spreadsheet.
CreateIconInWordDoc();
```

Add the following statement at the end of `DisplayInExcel`. The `Copy` method adds the worksheet to the Clipboard.

```csharp
// Put the spreadsheet contents on the clipboard. The Copy method has one
// optional parameter for specifying a destination. Because no argument
// is sent, the destination is the Clipboard.
workSheet.Range["A1:B3"].Copy();
```

Press CTRL+F5. A Word document appears that contains an icon. Double-click the icon to bring the worksheet to the foreground.

## To set the Embed Interop Types property

More enhancements are possible when you call a COM type that doesn't require a primary interop assembly (PIA) at run time. Removing the dependency on PIAs results in version independence and easier deployment. For more information about the advantages of programming without PIAs, see [Walkthrough: Embedding Types from Managed Assemblies](../../../standard/assembly/embed-types-visual-studio.md).

In addition, programming is easier because the `dynamic` type represents the required and returned types declared in COM methods. Variables that have type `dynamic` aren't evaluated until run time, which eliminates the need for explicit casting. For more information, see [Using Type dynamic](using-type-dynamic.md).

Embedding type information instead of using PIAs is default behavior. Because of that default, several of the previous examples are simplified. You don't need any explicit casting. For example, the declaration of `worksheet` in `DisplayInExcel` is written as `Excel._Worksheet workSheet = excelApp.ActiveSheet` rather than `Excel._Worksheet workSheet = (Excel.Worksheet)excelApp.ActiveSheet`. The calls to `AutoFit` in the same method also would require explicit casting without the default, because `ExcelApp.Columns[1]` returns an `Object`, and `AutoFit` is an Excel  method. The following code shows the casting.

```csharp
((Excel.Range)workSheet.Columns[1]).AutoFit();
((Excel.Range)workSheet.Columns[2]).AutoFit();
```

To change the default and use PIAs instead of embedding type information, expand the References node in Solution Explorer, and then select **Microsoft.Office.Interop.Excel** or **Microsoft.Office.Interop.Word**. If you can't see the **Properties** window, press **F4**. Find **Embed Interop Types** in the list of properties, and change its value to **False**. Equivalently, you can compile by using the [**References**](../../language-reference/compiler-options/inputs.md#references) compiler option instead of [**EmbedInteropTypes**](../../language-reference/compiler-options/inputs.md#embedinteroptypes) at a command prompt.

## To add additional formatting to the table

Replace the two calls to `AutoFit` in `DisplayInExcel` with the following statement.

```csharp
// Call to AutoFormat in Visual C# 2010.
workSheet.Range["A1", "B3"].AutoFormat(
    Excel.XlRangeAutoFormat.xlRangeAutoFormatClassic2);
```

The <xref:Microsoft.Office.Interop.Excel.Range.AutoFormat*> method has seven value parameters, all of which are optional. Named and optional arguments enable you to provide arguments for none, some, or all of them. In the previous statement, you supply an argument for only one of the parameters, `Format`. Because `Format` is the first parameter in the parameter list, you don't have to provide the parameter name. However, the statement might be easier to understand if you include the parameter name, as shown in the following code.

```csharp
// Call to AutoFormat in Visual C# 2010.
workSheet.Range["A1", "B3"].AutoFormat(Format:
    Excel.XlRangeAutoFormat.xlRangeAutoFormatClassic2);
```

Press CTRL+F5 to see the result. You can find other formats in the listed in the <xref:Microsoft.Office.Interop.Excel.XlRangeAutoFormat> enumeration.

## Example

The following code shows the complete example.

```csharp
using System.Collections.Generic;
using Excel = Microsoft.Office.Interop.Excel;
using Word = Microsoft.Office.Interop.Word;

namespace OfficeProgrammingWalkthruComplete
{
    class Walkthrough
    {
        static void Main(string[] args)
        {
            // Create a list of accounts.
            var bankAccounts = new List<Account>
            {
                new Account {
                              ID = 345678,
                              Balance = 541.27
                            },
                new Account {
                              ID = 1230221,
                              Balance = -127.44
                            }
            };

            // Display the list in an Excel spreadsheet.
            DisplayInExcel(bankAccounts);

            // Create a Word document that contains an icon that links to
            // the spreadsheet.
            CreateIconInWordDoc();
        }

        static void DisplayInExcel(IEnumerable<Account> accounts)
        {
            var excelApp = new Excel.Application();
            // Make the object visible.
            excelApp.Visible = true;

            // Create a new, empty workbook and add it to the collection returned
            // by property Workbooks. The new workbook becomes the active workbook.
            // Add has an optional parameter for specifying a particular template.
            // Because no argument is sent in this example, Add creates a new workbook.
            excelApp.Workbooks.Add();

            // This example uses a single workSheet.
            Excel._Worksheet workSheet = excelApp.ActiveSheet;

            // Earlier versions of C# require explicit casting.
            //Excel._Worksheet workSheet = (Excel.Worksheet)excelApp.ActiveSheet;

            // Establish column headings in cells A1 and B1.
            workSheet.Cells[1, "A"] = "ID Number";
            workSheet.Cells[1, "B"] = "Current Balance";

            var row = 1;
            foreach (var acct in accounts)
            {
                row++;
                workSheet.Cells[row, "A"] = acct.ID;
                workSheet.Cells[row, "B"] = acct.Balance;
            }

            workSheet.Columns[1].AutoFit();
            workSheet.Columns[2].AutoFit();

            // Call to AutoFormat in Visual C#. This statement replaces the
            // two calls to AutoFit.
            workSheet.Range["A1", "B3"].AutoFormat(
                Excel.XlRangeAutoFormat.xlRangeAutoFormatClassic2);

            // Put the spreadsheet contents on the clipboard. The Copy method has one
            // optional parameter for specifying a destination. Because no argument
            // is sent, the destination is the Clipboard.
            workSheet.Range["A1:B3"].Copy();
        }

        static void CreateIconInWordDoc()
        {
            var wordApp = new Word.Application();
            wordApp.Visible = true;

            // The Add method has four reference parameters, all of which are
            // optional. Visual C# allows you to omit arguments for them if
            // the default values are what you want.
            wordApp.Documents.Add();

            // PasteSpecial has seven reference parameters, all of which are
            // optional. This example uses named arguments to specify values
            // for two of the parameters. Although these are reference
            // parameters, you do not need to use the ref keyword, or to create
            // variables to send in as arguments. You can send the values directly.
            wordApp.Selection.PasteSpecial(Link: true, DisplayAsIcon: true);
        }
    }

    public class Account
    {
        public int ID { get; set; }
        public double Balance { get; set; }
    }
}
```

## See also

- <xref:System.Type.Missing?displayProperty=nameWithType>
- [dynamic](../../language-reference/builtin-types/reference-types.md)
- [Named and Optional Arguments](../../programming-guide/classes-and-structs/named-and-optional-arguments.md)
- [How to use named and optional arguments in Office programming](how-to-use-named-and-optional-arguments-in-office-programming.md)
