---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/fundamentals/tutorials/xml-documentation.md
title: Generate XML documentation from your source code
version: 0.0.0
fetched_at: 2026-09-13
---
# Tutorial: Create XML documentation

In this tutorial, you take an existing object‑oriented sample (from the preceding [tutorial](oop.md)) and enhance it with XML documentation comments. XML documentation comments provide helpful IntelliSense tooltips, and can participate in generated API reference docs. You learn which elements deserve comments, how to use core tags like `<summary>`, `<param>`, `<returns>`, `<value>`, `<remarks>`, `<example>`, `<seealso>`, `<exception>`, and `<inheritdoc>`, and how consistent, purposeful commenting improves maintainability, discoverability, and collaboration—without adding noise. By the end, you annotated the public surface of the sample, built the project to emit the XML documentation file, and seen how those comments flow directly into the developer experience and downstream documentation tooling.

In this tutorial, you:

> [!div class="checklist"]
>
> * Enable XML documentation output in your C# project.
> * Add and structure XML documentation comments to types and members.
> * Build the project and inspect the generated XML documentation file.

## Prerequisites

- The [.NET SDK](https://dot.net)
- Either [Visual Studio](https://visualstudio.com) or [Visual Studio Code](https://visualstudio.com/vscode) with the [C# Dev Kit](https://marketplace.visualstudio.com/items?itemName=ms-dotnettools.csdevkit).

## Enable XML documentation

Load the project you built in the preceding [object-oriented tutorial](oop.md). If you prefer to start fresh, clone the sample from the `dotnet/docs` repository under the [`snippets/object-oriented-programming`](https://github.com/dotnet/docs/tree/main/docs/csharp/fundamentals/tutorials/snippets/object-oriented-programming) folder.

Next, enable XML documentation output so the compiler emits a `.xml` file alongside your assembly. Edit the project file and add (or confirm) the following property inside a `<PropertyGroup>` element:

```xml
<GenerateDocumentationFile>True</GenerateDocumentationFile>
```

If you're using Visual Studio, you can enable this using the "build" property page.

Build the project. The compiler produces an XML file that aggregates all the `///` comments from publicly visible types and members. That file feeds IntelliSense tooltips, static analysis tools, and downstream documentation generation systems.

Build the project now. You see warnings for any public members that are missing `<summary>` comments. Treat those warnings as a to-do list that helps you provide complete, intentional documentation. Open the generated XML file (it's next to your build output) and inspect the initial structure. At first, the `<members>` section is empty because you didn't add comments yet:

```xml
<?xml version="1.0"?>
<doc>
    <assembly>
        <name>oo-programming</name>
    </assembly>
    <members>
    </members>
</doc>
```

With the file in place, start adding targeted XML comments and immediately verify how each one appears in the generated output. Start with the `Transaction` record type:

```csharp
namespace OOProgramming;

/// <summary>
/// Represents an immutable financial transaction with an amount, date, and descriptive notes.
/// </summary>
/// <param name="Amount">The transaction amount. Positive values represent credits/deposits, negative values represent debits/withdrawals.</param>
/// <param name="Date">The date and time when the transaction occurred.</param>
/// <param name="Notes">Descriptive notes or memo text associated with the transaction.</param>
public record Transaction(decimal Amount, DateTime Date, string Notes);
```

## Add documentation comments

You now cycle through the build warnings to add concise, useful documentation to the `BankAccount` type. Each warning pinpoints a public member that lacks a `<summary>` (or other required) element. Treat the warning list as a checklist. Avoid adding noise: focus on describing intent, invariants, and important usage constraints—skip restating obvious type names or parameter types.

1. Build the project again. In Visual Studio or Visual Studio Code, open the Error List / Problems panel and filter for documentation warnings (CS1591). At the command line, run a build and review the warnings emitted to the console.
1. Navigate to the first warning (the `BankAccount` class). On the line above the declaration, type `///`. The editor scaffolds a `<summary>` element. Replace the placeholder with a single, action‑focused sentence. The sentence explains the role of the account in the domain. For example,  it tracks transactions and enforces a minimum balance.
1. Add `<remarks>` only if you need to explain behavior. Examples include how minimum balance enforcement works or how account numbers are generated. Keep remarks short.
1. For each property (`Number`, `Owner`, `Balance`), type `///` and write a `<summary>` that states what the value represents—not how a trivial getter returns it. If a property calculates a value (like `Balance`), add a `<value>` element that clarifies the calculation.
1. For each constructor, add `<summary>` plus `<param>` elements describing the meaning of each argument, not just restating the parameter name. If one overload delegates to another, add a concise `<remarks>` element.
1. For methods that can throw, add `<exception>` tags for each intentional exception type. Describe the condition that triggers it. Don't document exceptions thrown by argument validation helpers unless they're part of the public contract.
1. For methods that return a value, add `<returns>` with a short description of what callers receive. Avoid repeating the method name or managed type.
1. Work with the `BankAccount` base class first.

Your version should look something like the following code:

```csharp
namespace OOProgramming;

/// <summary>
/// Represents a bank account with basic banking operations including deposits, withdrawals, and transaction history.
/// Supports minimum balance constraints and provides extensible month-end processing capabilities.
/// </summary>
public class BankAccount
{
    /// <summary>
    /// Gets the unique account number for this bank account.
    /// </summary>
    /// <value>A string representation of the account number, generated sequentially.</value>
    public string Number { get; }
    
    /// <summary>
    /// Gets or sets the name of the account owner.
    /// </summary>
    /// <value>The full name of the person who owns this account.</value>
    public string Owner { get; set; }
    
    /// <summary>
    /// Gets the current balance of the account by calculating the sum of all transactions.
    /// </summary>
    /// <value>The current account balance as a decimal value.</value>
    public decimal Balance => _allTransactions.Sum(i => i.Amount);

    private static int s_accountNumberSeed = 1234567890;

    private readonly decimal _minimumBalance;

    /// <summary>
    /// Initializes a new instance of the BankAccount class with the specified owner name and initial balance.
    /// Uses a default minimum balance of 0.
    /// </summary>
    /// <param name="name">The name of the account owner.</param>
    /// <param name="initialBalance">The initial deposit amount for the account.</param>
    /// <remarks>
    /// This constructor is a convenience overload that calls the main constructor with a minimum balance of 0.
    /// If the initial balance is greater than 0, it will be recorded as the first transaction with the note "Initial balance".
    /// The account number is automatically generated using a static seed value that increments for each new account.
    /// </remarks>
    public BankAccount(string name, decimal initialBalance) : this(name, initialBalance, 0) { }

    /// <summary>
    /// Initializes a new instance of the BankAccount class with the specified owner name, initial balance, and minimum balance constraint.
    /// </summary>
    /// <param name="name">The name of the account owner.</param>
    /// <param name="initialBalance">The initial deposit amount for the account.</param>
    /// <param name="minimumBalance">The minimum balance that must be maintained in the account.</param>
    /// <remarks>
    /// This is the primary constructor that sets up all account properties. The account number is generated automatically
    /// using a static seed value. If an initial balance is provided and is greater than 0, it will be added as the first
    /// transaction. The minimum balance constraint will be enforced on all future withdrawal operations through the
    /// <see cref="CheckWithdrawalLimit"/> method.
    /// </remarks>
    public BankAccount(string name, decimal initialBalance, decimal minimumBalance)
    {
        Number = s_accountNumberSeed.ToString();
        s_accountNumberSeed++;

        Owner = name;
        _minimumBalance = minimumBalance;
        if (initialBalance > 0)
            MakeDeposit(initialBalance, DateTime.Now, "Initial balance");
    }

    private readonly List<Transaction> _allTransactions = [];

    /// <summary>
    /// Makes a deposit to the account by adding a positive transaction.
    /// </summary>
    /// <param name="amount">The amount to deposit. Must be positive.</param>
    /// <param name="date">The date when the deposit is made.</param>
    /// <param name="note">A descriptive note about the deposit transaction.</param>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when the deposit amount is zero or negative.</exception>
    /// <remarks>
    /// This method creates a new <see cref="Transaction"/> object with the specified amount, date, and note,
    /// then adds it to the internal transaction list. The transaction amount must be positive - negative amounts
    /// are not allowed for deposits. The account balance is automatically updated through the Balance property
    /// which calculates the sum of all transactions. There are no limits or restrictions on deposit amounts.
    /// </remarks>
    public void MakeDeposit(decimal amount, DateTime date, string note)
    {
        if (amount <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Amount of deposit must be positive");
        }
        var deposit = new Transaction(amount, date, note);
        _allTransactions.Add(deposit);
    }

    /// <summary>
    /// Makes a withdrawal from the account by adding a negative transaction.
    /// Checks withdrawal limits and minimum balance constraints before processing.
    /// </summary>
    /// <param name="amount">The amount to withdraw. Must be positive.</param>
    /// <param name="date">The date when the withdrawal is made.</param>
    /// <param name="note">A descriptive note about the withdrawal transaction.</param>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when the withdrawal amount is zero or negative.</exception>
    /// <exception cref="InvalidOperationException">Thrown when the withdrawal would cause the balance to fall below the minimum balance.</exception>
    /// <remarks>
    /// This method first validates that the withdrawal amount is positive, then checks if the withdrawal would
    /// violate the minimum balance constraint by calling <see cref="CheckWithdrawalLimit"/>. The withdrawal is
    /// recorded as a negative transaction amount. If the withdrawal limit check returns an overdraft transaction
    /// (such as a fee), that transaction is also added to the account. The method enforces business rules through
    /// the virtual CheckWithdrawalLimit method, allowing derived classes to implement different withdrawal policies.
    /// </remarks>
    public void MakeWithdrawal(decimal amount, DateTime date, string note)
    {
        if (amount <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "Amount of withdrawal must be positive");
        }
        Transaction? overdraftTransaction = CheckWithdrawalLimit(Balance - amount < _minimumBalance);
        Transaction? withdrawal = new(-amount, date, note);
        _allTransactions.Add(withdrawal);
        if (overdraftTransaction != null)
            _allTransactions.Add(overdraftTransaction);
    }

    /// <summary>
    /// Checks whether a withdrawal would violate the account's minimum balance constraint.
    /// This method can be overridden in derived classes to implement different withdrawal limit policies.
    /// </summary>
    /// <param name="isOverdrawn">True if the withdrawal would cause the balance to fall below the minimum balance.</param>
    /// <returns>A Transaction object representing any overdraft fees or penalties, or null if no additional charges apply.</returns>
    /// <exception cref="InvalidOperationException">Thrown when the withdrawal would cause an overdraft and the account type doesn't allow it.</exception>
    protected virtual Transaction? CheckWithdrawalLimit(bool isOverdrawn)
    {
        if (isOverdrawn)
        {
            throw new InvalidOperationException("Not sufficient funds for this withdrawal");
        }
        else
        {
            return default;
        }
    }

    /// <summary>
    /// Generates a detailed account history report showing all transactions with running balance calculations.
    /// </summary>
    /// <returns>A formatted string containing the complete transaction history with dates, amounts, running balances, and notes.</returns>
    /// <remarks>
    /// This method creates a formatted report that includes a header row followed by all transactions in chronological order.
    /// Each row shows the transaction date (in short date format), the transaction amount, the running balance after that
    /// transaction, and any notes associated with the transaction. The running balance is calculated by iterating through
    /// all transactions and maintaining a cumulative total. The report uses tab characters for column separation and
    /// is suitable for display in console applications or simple text outputs.
    /// </remarks>
    public string GetAccountHistory()
    {
        var report = new System.Text.StringBuilder();

        decimal balance = 0;
        report.AppendLine("Date\t\tAmount\tBalance\tNote");
        foreach (var item in _allTransactions)
        {
            balance += item.Amount;
            report.AppendLine($"{item.Date.ToShortDateString()}\t{item.Amount}\t{balance}\t{item.Notes}");
        }

        return report.ToString();
    }

    /// <summary>
    /// Performs month-end processing for the account. This virtual method can be overridden in derived classes
    /// to implement specific month-end behaviors such as interest calculations, fee assessments, or statement generation.
    /// </summary>
    /// <remarks>
    /// The base implementation of this method does nothing, providing a safe default for basic bank accounts.
    /// Derived classes such as savings accounts or checking accounts can override this method to implement
    /// account-specific month-end processing. Examples include calculating and applying interest payments,
    /// assessing monthly maintenance fees, generating account statements, or performing regulatory compliance checks.
    /// This method is typically called by banking systems at the end of each month as part of batch processing operations.
    /// </remarks>
    public virtual void PerformMonthEndTransactions() { }
}
```

When you're done, open the regenerated XML file and confirm that each member appears with your new elements. A trimmed portion might look like this:

```xml
<member name="T:OOProgramming.BankAccount">
  <summary>Represents a bank account that records transactions and enforces an optional minimum balance.</summary>
  <remarks>Account numbers are generated sequentially when each instance is constructed.</remarks>
</member>
<member name="P:OOProgramming.BankAccount.Balance">
  <summary>Gets the current balance based on all recorded transactions.</summary>
  <value>The net sum of deposits and withdrawals.</value>
</member>
```

> [!TIP]
> Keep summaries to a single sentence. If you need more than one, move secondary context into `<remarks>`.

## Use `<inheritdoc/>` in derived classes

If you derive from `BankAccount` (for example, a `SavingsAccount` that applies interest), you can inherit base documentation instead of copying it. Add a self-closing `<inheritdoc/>` element inside the derived member's documentation block. You can still append more elements (such as extra `<remarks>` details) after `<inheritdoc/>` to document the specialized behavior:

```csharp
/// <inheritdoc/>
/// <remarks>
/// An interest-earning account is a specialized savings account that rewards customers for maintaining higher balances.
/// Interest is only earned when the account balance exceeds $500, encouraging customers to maintain substantial deposits.
/// The annual interest rate of 2% is applied monthly to qualifying balances, providing a simple savings incentive.
/// This account type uses the standard minimum balance of $0 from the base <see cref="BankAccount"/> class.
/// </remarks>
public class InterestEarningAccount : BankAccount
```

> [!NOTE]
> `<inheritdoc/>` reduces duplication and helps maintain consistency when you update base type documentation later.

After you finish documenting the public surface, build one final time to confirm there are no remaining CS1591 warnings. Your project now produces useful IntelliSense and a structured XML file ready for publishing workflows.

You can see the full annotated sample in [the source folder](https://github.com/dotnet/docs/tree/main/docs/csharp/fundamentals/tutorials/snippets/xml-documentation) of the [dotnet/docs](https://github.com/dotnet/docs) repository on GitHub.

## Build output from comments

You can explore more by trying any of these tools to create output from XML comments:

- [DocFX](https://dotnet.github.io/docfx/): *DocFX* is an API documentation generator for .NET, which currently supports C#, Visual Basic, and F#. It also allows you to customize the generated reference documentation. DocFX builds a static HTML website from your source code and Markdown files. Also, DocFX provides you with the flexibility to customize the layout and style of your website through templates. You can also create custom templates.
- [Sandcastle](https://github.com/EWSoftware/SHFB): The *Sandcastle tools* create help files for managed class libraries containing both conceptual and API reference pages. The Sandcastle tools are command-line based and have no GUI front-end, project management features, or automated build process. The Sandcastle Help File Builder provides standalone GUI and command-line-based tools to build a help file in an automated fashion. A Visual Studio integration package is also available for it so that help projects can be created and managed entirely from within Visual Studio.
- [Doxygen](https://github.com/doxygen/doxygen): *Doxygen* generates an online documentation browser (in HTML) or an offline reference manual (in LaTeX) from a set of documented source files. There's also support for generating output in RTF (MS Word), PostScript, hyperlinked PDF, compressed HTML, DocBook, and Unix manual pages. You can configure Doxygen to extract the code structure from undocumented source files.

## Related content

- [XML Doc language reference](../../language-reference/xmldoc/index.md)
- [Recommended XML tags](../../language-reference/xmldoc/recommended-tags.md)
- [XML Documentation examples](../../language-reference/xmldoc/examples.md)
