---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/delegates/how-to-declare-instantiate-and-use-a-delegate.md
title: How to declare, instantiate, and use a delegate
version: 0.0.0
fetched_at: 2026-09-13
---
# How to declare, instantiate, and use a Delegate (C# Programming Guide)

You can declare delegates using any of the following methods:

- Declare a delegate type and declare a method with a matching signature:

```csharp
// Declare a delegate.
delegate void NotifyCallback(string str);

// Declare a method with the same signature as the delegate.
static void Notify(string name)
{
    Console.WriteLine($"Notification received for: {name}");
}
```

```csharp
// Create an instance of the delegate.
NotifyCallback del1 = new NotifyCallback(Notify);
```

- Assign a method group to a delegate type:

```csharp
NotifyCallback del2 = Notify;
```

- Declare an anonymous method

```csharp
// Instantiate NotifyCallback by using an anonymous method.
NotifyCallback del3 = delegate (string name)
{
    Console.WriteLine($"Notification received for: {name}");
};
```

- Use a lambda expression:

```csharp
// Instantiate NotifyCallback by using a lambda expression.
NotifyCallback del4 = name => Console.WriteLine($"Notification received for: {name}");
```

For more information, see [Lambda Expressions](../../language-reference/operators/lambda-expressions.md).

The following example illustrates declaring, instantiating, and using a delegate. The `BookDB` class encapsulates a bookstore database that maintains a database of books. It exposes a method, `ProcessPaperbackBooks`, which finds all paperback books in the database and calls a delegate for each one. The `delegate` type is named `ProcessBookCallback`. The `Test` class uses this class to print the titles and average price of the paperback books.

The use of delegates promotes good separation of functionality between the bookstore database and the client code. The client code has no knowledge of how the books are stored or how the bookstore code finds paperback books. The bookstore code has no knowledge of what processing is performed on the paperback books after it finds them.

```csharp
using System;
using System.Collections.Generic;

// A set of classes for handling a bookstore:
namespace Bookstore;

// Describes a book in the book list:
public record struct Book(string Title, string Author, decimal Price, bool Paperback);

// Declare a delegate type for processing a book:
public delegate void ProcessBookCallback(Book book);

// Maintains a book database.
public class BookDB
{
    // List of all books in the database:
    List<Book> list = new();

    // Add a book to the database:
    public void AddBook(string title, string author, decimal price, bool paperBack) =>
        list.Add(new Book(title, author, price, paperBack));

    // Call a passed-in delegate on each paperback book to process it:
    public void ProcessPaperbackBooks(ProcessBookCallback processBook)
    {
        foreach (Book b in list)
        {
            if (b.Paperback)
            {
                // Calling the delegate:
                processBook(b);
            }
        }
    }
}

// Using the Bookstore classes:

// Class to total and average prices of books:
class PriceTotaller
{
    private int countBooks = 0;
    private decimal priceBooks = 0.0m;

    internal void AddBookToTotal(Book book)
    {
        countBooks += 1;
        priceBooks += book.Price;
    }

    internal decimal AveragePrice() => priceBooks / countBooks;
}

// Class to test the book database:
class Test
{
    // Print the title of the book.
    static void PrintTitle(Book b) => Console.WriteLine($"   {b.Title}");

    // Execution starts here.
    static void Main()
    {
        BookDB bookDB = new BookDB();

        // Initialize the database with some books:
        AddBooks(bookDB);

        // Print all the titles of paperbacks:
        Console.WriteLine("Paperback Book Titles:");

        // Create a new delegate object associated with the static
        // method Test.PrintTitle:
        bookDB.ProcessPaperbackBooks(PrintTitle);

        // Get the average price of a paperback by using
        // a PriceTotaller object:
        PriceTotaller totaller = new PriceTotaller();

        // Create a new delegate object associated with the nonstatic
        // method AddBookToTotal on the object totaller:
        bookDB.ProcessPaperbackBooks(totaller.AddBookToTotal);

        Console.WriteLine($"Average Paperback Book Price: ${totaller.AveragePrice():#.##}");
    }

    // Initialize the book database with some test books:
    static void AddBooks(BookDB bookDB)
    {
        bookDB.AddBook("The C Programming Language", "Brian W. Kernighan and Dennis M. Ritchie", 19.95m, true);
        bookDB.AddBook("The Unicode Standard 2.0", "The Unicode Consortium", 39.95m, true);
        bookDB.AddBook("The MS-DOS Encyclopedia", "Ray Duncan", 129.95m, false);
        bookDB.AddBook("Dogbert's Clues for the Clueless", "Scott Adams", 12.00m, true);
    }
}
/* Output:
Paperback Book Titles:
   The C Programming Language
   The Unicode Standard 2.0
   Dogbert's Clues for the Clueless
Average Paperback Book Price: $23.97
*/
```

## See also

- [Events](../events/index.md)
- [Delegates](./index.md)
