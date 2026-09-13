---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/xmldoc/examples.md
title: Example XML documentation comments
version: 0.0.0
fetched_at: 2026-09-13
---
# Example XML documentation comments

This article contains three examples for adding XML documentation comments to most C# language elements. The first example shows how you document a class with different members. The second example shows how you can reuse explanations for a hierarchy of classes or interfaces. The third example shows tags to use for generic classes and members. The second and third examples use concepts that the first example covers.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

## Document a class, struct, or interface

The following example shows common language elements, and the tags you'll likely use to describe these elements.  The documentation comments describe the use of the tags, rather than the class itself.

```csharp
/// <summary>
/// Every class and member should have a one sentence
/// summary describing its purpose.
/// </summary>
/// <remarks>
/// You can expand on that one sentence summary to
/// provide more information for readers. In this case,
/// the <c>ExampleClass</c> provides different C#
/// elements to show how you would add documentation
///comments for most elements in a typical class.
/// <para>
/// The remarks can add multiple paragraphs, so you can
/// write detailed information for developers that use
/// your work. You should add everything needed for
/// readers to be successful. This class contains
/// examples for the following:
/// </para>
/// <list type="table">
/// <item>
/// <term>Summary</term>
/// <description>
/// This should provide a one sentence summary of the class or member.
/// </description>
/// </item>
/// <item>
/// <term>Remarks</term>
/// <description>
/// This is typically a more detailed description of the class or member
/// </description>
/// </item>
/// <item>
/// <term>para</term>
/// <description>
/// The para tag separates a section into multiple paragraphs
/// </description>
/// </item>
/// <item>
/// <term>list</term>
/// <description>
/// Provides a list of terms or elements
/// </description>
/// </item>
/// <item>
/// <term>returns, param</term>
/// <description>
/// Used to describe parameters and return values
/// </description>
/// </item>
/// <item>
/// <term>value</term>
/// <description>Used to describe properties</description>
/// </item>
/// <item>
/// <term>exception</term>
/// <description>
/// Used to describe exceptions that may be thrown
/// </description>
/// </item>
/// <item>
/// <term>c, cref, see, seealso</term>
/// <description>
/// These provide code style and links to other
/// documentation elements
/// </description>
/// </item>
/// <item>
/// <term>example, code</term>
/// <description>
/// These are used for code examples
/// </description>
/// </item>
/// </list>
/// <para>
/// The list above uses the "table" style. You could
/// also use the "bullet" or "number" style. Neither
/// would typically use the "term" element.
/// <br/>
/// Note: paragraphs are double spaced. Use the *br*
/// tag for single spaced lines.
/// </para>
/// </remarks>
public class ExampleClass
{
    /// <value>
    /// The <c>Label</c> property represents a label
    /// for this instance.
    /// </value>
    /// <remarks>
    /// The <see cref="Label"/> is a <see langword="string"/>
    /// that you use for a label.
    /// <para>
    /// Note that there isn't a way to provide a "cref" to
    /// each accessor, only to the property itself.
    /// </para>
    /// </remarks>
    public string? Label
    {
        get;
        set;
    }

    /// <summary>
    /// Adds two integers and returns the result.
    /// </summary>
    /// <returns>
    /// The sum of two integers.
    /// </returns>
    /// <param name="left">
    /// The left operand of the addition.
    /// </param>
    /// <param name="right">
    /// The right operand of the addition.
    /// </param>
    /// <example>
    /// <code>
    /// int c = Math.Add(4, 5);
    /// if (c > 10)
    /// {
    ///     Console.WriteLine(c);
    /// }
    /// </code>
    /// </example>
    /// <exception cref="System.OverflowException">
    /// Thrown when one parameter is
    /// <see cref="Int32.MaxValue">MaxValue</see> and the other is
    /// greater than 0.
    /// Note that here you can also use
    /// <see href="https://learn.microsoft.com/dotnet/api/system.int32.maxvalue"/>
    ///  to point a web page instead.
    /// </exception>
    /// <see cref="ExampleClass"/> for a list of all
    /// the tags in these examples.
    /// <seealso cref="ExampleClass.Label"/>
    public static int Add(int left, int right)
    {
        if ((left == int.MaxValue && right > 0) || (right == int.MaxValue && left > 0))
            throw new System.OverflowException();

        return left + right;
    }
}

/// <summary>
/// This is an example of a positional record.
/// </summary>
/// <remarks>
/// There isn't a way to add XML comments for properties
/// created for positional records, yet. The language
/// design team is still considering what tags should
/// be supported, and where. Currently, you can use
/// the "param" tag to describe the parameters to the
/// primary constructor.
/// </remarks>
/// <param name="FirstName">
/// This tag will apply to the primary constructor parameter.
/// </param>
/// <param name="LastName">
/// This tag will apply to the primary constructor parameter.
/// </param>
public record Person(string FirstName, string LastName);
```

Adding documentation can clutter your source code with large sets of comments intended for users of your library. Use the `<Include>` tag to separate your XML comments from your source. Your source code references an XML file by using the `<Include>` tag:

```csharp
/// <include file='xml_include_tag.xml' path='MyDocs/MyMembers[@name="test"]/*' />
class Test
{
    static void Main()
    {
    }
}

/// <include file='xml_include_tag.xml' path='MyDocs/MyMembers[@name="test2"]/*' />
class Test2
{
    public void Test()
    {
    }
}
```

The second file, *xml_include_tag.xml*, contains the documentation comments.

```xml
<MyDocs>
    <MyMembers name="test">
        <summary>
        The summary for this type.
        </summary>
    </MyMembers>
    <MyMembers name="test2">
        <summary>
        The summary for this other type.
        </summary>
    </MyMembers>
</MyDocs>
```

## Document a hierarchy of classes and interfaces

The `<inheritdoc>` element means a type or member *inherits* documentation comments from a base class or interface. You can also use the `<inheritdoc>` element with the `cref` attribute to inherit comments from a member of the same type. The following example shows ways to use this tag. When you add the `inheritdoc` attribute to a type, member comments are inherited. You can prevent the use of inherited comments by writing comments on the members in the derived type. The compiler chooses those comments over the inherited comments.

```csharp
/// <summary>
/// A summary about this class.
/// </summary>
/// <remarks>
/// These remarks would explain more about this class.
/// In this example, these comments also explain the
/// general information about the derived class.
/// </remarks>
public class MainClass
{
}

///<inheritdoc/>
public class DerivedClass : MainClass
{
}

/// <summary>
/// This interface would describe all the methods in
/// its contract.
/// </summary>
/// <remarks>
/// While elided for brevity, each method or property
/// in this interface would contain docs that you want
/// to duplicate in each implementing class.
/// </remarks>
public interface ITestInterface
{
    /// <summary>
    /// This method is part of the test interface.
    /// </summary>
    /// <remarks>
    /// This content would be inherited by classes
    /// that implement this interface when the
    /// implementing class uses "inheritdoc"
    /// </remarks>
    /// <returns>The value of <paramref name="arg" /> </returns>
    /// <param name="arg">The argument to the method</param>
    int Method(int arg);
}

///<inheritdoc cref="ITestInterface"/>
public class ImplementingClass : ITestInterface
{
    // doc comments are inherited here.
    public int Method(int arg) => arg;
}

/// <summary>
/// This class shows hows you can "inherit" the doc
/// comments from one method in another method.
/// </summary>
/// <remarks>
/// You can inherit all comments, or only a specific tag,
/// represented by an xpath expression.
/// </remarks>
public class InheritOnlyReturns
{
    /// <summary>
    /// In this example, this summary is only visible for this method.
    /// </summary>
    /// <returns>A boolean</returns>
    public static bool MyParentMethod(bool x) { return x; }

    /// <inheritdoc cref="MyParentMethod" path="/returns"/>
    public static bool MyChildMethod() { return false; }
}

/// <Summary>
/// This class shows an example ofsharing comments across methods.
/// </Summary>
public class InheritAllButRemarks
{
    /// <summary>
    /// In this example, this summary is visible on all the methods.
    /// </summary>
    /// <remarks>
    /// The remarks can be inherited by other methods
    /// using the xpath expression.
    /// </remarks>
    /// <returns>A boolean</returns>
    public static bool MyParentMethod(bool x) { return x; }

    /// <inheritdoc cref="MyParentMethod" path="//*[not(self::remarks)]"/>
    public static bool MyChildMethod() { return false; }
}
```

## Generic types

Use the `<typeparam>` tag to describe type parameters on generic types and methods. The value for the `cref` attribute requires new syntax to reference a generic method or class:

```csharp
/// <summary>
/// This is a generic class.
/// </summary>
/// <remarks>
/// This example shows how to specify the <see cref="GenericClass{T}"/>
/// type as a cref attribute.
/// In generic classes and methods, you'll often want to reference the
/// generic type, or the type parameter.
/// </remarks>
class GenericClass<T>
{
    // Fields and members.
}

/// <Summary>
/// This shows examples of typeparamref and typeparam tags
/// </Summary>
public class ParamsAndParamRefs
{
    /// <summary>
    /// The GetGenericValue method.
    /// </summary>
    /// <remarks>
    /// This sample shows how to specify the <see cref="GetGenericValue"/>
    /// method as a cref attribute.
    /// The parameter and return value are both of an arbitrary type,
    /// <typeparamref name="T"/>
    /// </remarks>
    public static T GetGenericValue<T>(T para)
    {
        return para;
    }
}
```

## Extension members

Add XML comments for `<summary>`, `<param>`, and, if necessary, `<typeparam>` to describe the receiver parameter on extension members:

```csharp
/// <summary>
/// This is an example of extension methods documentation.
/// </summary>
public static class Extensions
{
    /// <summary>
    /// Defines extensions for generic enumerable sequences.
    /// </summary>
    /// <param name="sequence">The receiver sequence</param>
    /// <typeparam name="TSequence">The type of the items in the sequence.</typeparam>
    extension<TSequence>(IEnumerable<TSequence> sequence)
    {
        /// <summary>
        /// Returns an enumerable collection containing the elements of the sequence in reverse order.
        /// </summary>
        /// <remarks>
        /// The returned sequence is evaluated lazily. Enumerating the result will consume all
        /// elements of the original sequence before yielding any items in reverse order.
        /// </remarks>
        /// <returns>
        /// An <see cref="IEnumerable{TSequence}"/> that enumerates the elements of the sequence from last to first.
        /// </returns>
        public IEnumerable<TSequence> ReverseSequence()
        {
            var stack = new Stack<TSequence>();
            foreach (var item in sequence)
            {
                stack.Push(item);
            }
            while (stack.Count > 0)
            {
                yield return stack.Pop();
            }
        }

        /// <summary>
        /// Generates a sequence of items using a generator function.
        /// </summary>
        /// <param name="count">The number of items.</param>
        /// <param name="generator">The generator function.</param>
        /// <returns>A new sequence of <paramref name="count"/> items.</returns>
        public static IEnumerable<TSequence> Generate(int count, Func<TSequence> generator)
        {
            for (int i = 0; i < count; i++)
            {
                yield return generator();
            }
        }

        /// <summary>
        /// Gets the element at the specified position in the sequence.
        /// </summary>
        /// <param name="index">The zero-based position of the element to retrieve.</param>
        /// <value>The element at the specified position.</value>
        public TSequence this[int index] => sequence.ElementAt(index);
    }
}
```

The C# compiler copies the XML nodes from the `extension` block to all members declared in that block.

For an extension indexer, `cref` syntax can reference the indexer and its accessors through the `extension` block that declares it, and it can reference the implementation methods on the containing class. The following examples show how to reference the `this[int]` indexer and its generated `get_Item` accessor from the preceding example:

```csharp
/// <seealso cref="Extensions.extension{TSequence}(System.Collections.Generic.IEnumerable{TSequence}).this[int]"/>
/// <seealso cref="Extensions.extension{TSequence}(System.Collections.Generic.IEnumerable{TSequence}).get_Item(int)"/>
```

## Math class example

The following code shows a realistic example of adding doc comments to a math library.

```csharp
namespace TaggedLibrary
{
    /*
        The main Math class
        Contains all methods for performing basic math functions
    */
    /// <summary>
    /// The main <c>Math</c> class.
    /// Contains all methods for performing basic math functions.
    /// <list type="bullet">
    /// <item>
    /// <term>Add</term>
    /// <description>Addition Operation</description>
    /// </item>
    /// <item>
    /// <term>Subtract</term>
    /// <description>Subtraction Operation</description>
    /// </item>
    /// <item>
    /// <term>Multiply</term>
    /// <description>Multiplication Operation</description>
    /// </item>
    /// <item>
    /// <term>Divide</term>
    /// <description>Division Operation</description>
    /// </item>
    /// </list>
    /// </summary>
    /// <remarks>
    /// <para>
    /// This class can add, subtract, multiply and divide.
    /// </para>
    /// <para>
    /// These operations can be performed on both
    /// integers and doubles.
    /// </para>
    /// </remarks>
    public class Math
    {
        // Adds two integers and returns the result
        /// <summary>
        /// Adds two integers <paramref name="a"/> and <paramref name="b"/>
        ///  and returns the result.
        /// </summary>
        /// <returns>
        /// The sum of two integers.
        /// </returns>
        /// <example>
        /// <code>
        /// int c = Math.Add(4, 5);
        /// if (c > 10)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// <exception cref="System.OverflowException">
        /// Thrown when one parameter is <see cref="Int32.MaxValue"/> and the other
        /// is greater than 0.
        /// </exception>
        /// See <see cref="Math.Add(double, double)"/> to add doubles.
        /// <seealso cref="Math.Subtract(int, int)"/>
        /// <seealso cref="Math.Multiply(int, int)"/>
        /// <seealso cref="Math.Divide(int, int)"/>
        /// <param name="a">An integer.</param>
        /// <param name="b">An integer.</param>
        public static int Add(int a, int b)
        {
            // If any parameter is equal to the max value of an integer
            // and the other is greater than zero
            if ((a == int.MaxValue && b > 0) || 
                (b == int.MaxValue && a > 0))
            {
                throw new System.OverflowException();
            }
            return a + b;
        }

        // Adds two doubles and returns the result
        /// <summary>
        /// Adds two doubles <paramref name="a"/> and <paramref name="b"/>
        /// and returns the result.
        /// </summary>
        /// <returns>
        /// The sum of two doubles.
        /// </returns>
        /// <example>
        /// <code>
        /// double c = Math.Add(4.5, 5.4);
        /// if (c > 10)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// <exception cref="System.OverflowException">
        /// Thrown when one parameter is max and the other
        /// is greater than 0.</exception>
        /// See <see cref="Math.Add(int, int)"/> to add integers.
        /// <seealso cref="Math.Subtract(double, double)"/>
        /// <seealso cref="Math.Multiply(double, double)"/>
        /// <seealso cref="Math.Divide(double, double)"/>
        /// <param name="a">A double precision number.</param>
        /// <param name="b">A double precision number.</param>
        public static double Add(double a, double b)
        {
            // If any parameter is equal to the max value of an integer
            // and the other is greater than zero
            if ((a == double.MaxValue && b > 0) 
                || (b == double.MaxValue && a > 0))
            {
                throw new System.OverflowException();
            }

            return a + b;
        }

        // Subtracts an integer from another and returns the result
        /// <summary>
        /// Subtracts <paramref name="b"/> from <paramref name="a"/>
        /// and returns the result.
        /// </summary>
        /// <returns>
        /// The difference between two integers.
        /// </returns>
        /// <example>
        /// <code>
        /// int c = Math.Subtract(4, 5);
        /// if (c > 1)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// See <see cref="Math.Subtract(double, double)"/> to subtract doubles.
        /// <seealso cref="Math.Add(int, int)"/>
        /// <seealso cref="Math.Multiply(int, int)"/>
        /// <seealso cref="Math.Divide(int, int)"/>
        /// <param name="a">An integer.</param>
        /// <param name="b">An integer.</param>
        public static int Subtract(int a, int b)
        {
            return a - b;
        }

        // Subtracts a double from another and returns the result
        /// <summary>
        /// Subtracts a double <paramref name="b"/> from another 
        /// double <paramref name="a"/> and returns the result.
        /// </summary>
        /// <returns>
        /// The difference between two doubles.
        /// </returns>
        /// <example>
        /// <code>
        /// double c = Math.Subtract(4.5, 5.4);
        /// if (c > 1)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// See <see cref="Math.Subtract(int, int)"/> to subtract integers.
        /// <seealso cref="Math.Add(double, double)"/>
        /// <seealso cref="Math.Multiply(double, double)"/>
        /// <seealso cref="Math.Divide(double, double)"/>
        /// <param name="a">A double precision number.</param>
        /// <param name="b">A double precision number.</param>
        public static double Subtract(double a, double b)
        {
            return a - b;
        }

        // Multiplies two integers and returns the result
        /// <summary>
        /// Multiplies two integers <paramref name="a"/> 
        /// and <paramref name="b"/> and returns the result.
        /// </summary>
        /// <returns>
        /// The product of two integers.
        /// </returns>
        /// <example>
        /// <code>
        /// int c = Math.Multiply(4, 5);
        /// if (c > 100)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// See <see cref="Math.Multiply(double, double)"/> to multiply doubles.
        /// <seealso cref="Math.Add(int, int)"/>
        /// <seealso cref="Math.Subtract(int, int)"/>
        /// <seealso cref="Math.Divide(int, int)"/>
        /// <param name="a">An integer.</param>
        /// <param name="b">An integer.</param>
        public static int Multiply(int a, int b)
        {
            return a * b;
        }

        // Multiplies two doubles and returns the result
        /// <summary>
        /// Multiplies two doubles <paramref name="a"/> and
        /// <paramref name="b"/> and returns the result.
        /// </summary>
        /// <returns>
        /// The product of two doubles.
        /// </returns>
        /// <example>
        /// <code>
        /// double c = Math.Multiply(4.5, 5.4);
        /// if (c > 100.0)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// See <see cref="Math.Multiply(int, int)"/> to multiply integers.
        /// <seealso cref="Math.Add(double, double)"/>
        /// <seealso cref="Math.Subtract(double, double)"/>
        /// <seealso cref="Math.Divide(double, double)"/>
        /// <param name="a">A double precision number.</param>
        /// <param name="b">A double precision number.</param>
        public static double Multiply(double a, double b)
        {
            return a * b;
        }

        // Divides an integer by another and returns the result
        /// <summary>
        /// Divides an integer <paramref name="a"/> by another
        /// integer <paramref name="b"/> and returns the result.
        /// </summary>
        /// <returns>
        /// The quotient of two integers.
        /// </returns>
        /// <example>
        /// <code>
        /// int c = Math.Divide(4, 5);
        /// if (c > 1)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// <exception cref="System.DivideByZeroException">
        /// Thrown when <paramref name="b"/> is equal to 0.
        /// </exception>
        /// See <see cref="Math.Divide(double, double)"/> to divide doubles.
        /// <seealso cref="Math.Add(int, int)"/>
        /// <seealso cref="Math.Subtract(int, int)"/>
        /// <seealso cref="Math.Multiply(int, int)"/>
        /// <param name="a">An integer dividend.</param>
        /// <param name="b">An integer divisor.</param>
        public static int Divide(int a, int b)
        {
            return a / b;
        }

        // Divides a double by another and returns the result
        /// <summary>
        /// Divides a double <paramref name="a"/> by another double
        /// <paramref name="b"/> and returns the result.
        /// </summary>
        /// <returns>
        /// The quotient of two doubles.
        /// </returns>
        /// <example>
        /// <code>
        /// double c = Math.Divide(4.5, 5.4);
        /// if (c > 1.0)
        /// {
        ///     Console.WriteLine(c);
        /// }
        /// </code>
        /// </example>
        /// <exception cref="System.DivideByZeroException">
        /// Thrown when <paramref name="b"/> is equal to 0.
        /// </exception>
        /// See <see cref="Math.Divide(int, int)"/> to divide integers.
        /// <seealso cref="Math.Add(double, double)"/>
        /// <seealso cref="Math.Subtract(double, double)"/>
        /// <seealso cref="Math.Multiply(double, double)"/>
        /// <param name="a">A double precision dividend.</param>
        /// <param name="b">A double precision divisor.</param>
        public static double Divide(double a, double b)
        {
            return a / b;
        }
    }
}
```

You might find that the code is obscured by all the comments. The final example shows how you adapt this library to use the `include` tag. You move all the documentation to an XML file:

```xml
<docs>
  <members name="math">
   <Math>
    <summary>
      The main <c>Math</c> class.
      Contains all methods for performing basic math functions.
      </summary>
      <remarks>
      <para>This class can add, subtract, multiply and divide.</para>
      <para>These operations can be performed on both integers and doubles.</para>
      </remarks>
    </Math>
    <AddInt>
      <summary>
      Adds two integers <paramref name="a"/> and <paramref name="b"/>
      and returns the result.
      </summary>
      <returns>
      The sum of two integers.
      </returns>
      <example>
      <code>
      int c = Math.Add(4, 5);
      if (c > 10)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      <exception cref="System.OverflowException">Thrown when one
      parameter is max 
      and the other is greater than 0.</exception>
      See <see cref="Math.Add(double, double)"/> to add doubles.
      <seealso cref="Math.Subtract(int, int)"/>
      <seealso cref="Math.Multiply(int, int)"/>
      <seealso cref="Math.Divide(int, int)"/>
      <param name="a">An integer.</param>
      <param name="b">An integer.</param>
    </AddInt>
    <AddDouble>
      <summary>
      Adds two doubles <paramref name="a"/> and <paramref name="b"/>
      and returns the result.
      </summary>
      <returns>
      The sum of two doubles.
      </returns>
      <example>
      <code>
      double c = Math.Add(4.5, 5.4);
      if (c > 10)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      <exception cref="System.OverflowException">Thrown when one parameter is max 
      and the other is greater than 0.</exception>
      See <see cref="Math.Add(int, int)"/> to add integers.
      <seealso cref="Math.Subtract(double, double)"/>
      <seealso cref="Math.Multiply(double, double)"/>
      <seealso cref="Math.Divide(double, double)"/>
      <param name="a">A double precision number.</param>
      <param name="b">A double precision number.</param>
    </AddDouble>
    <SubtractInt>
      <summary>
      Subtracts <paramref name="b"/> from <paramref name="a"/> and
      returns the result.
      </summary>
      <returns>
      The difference between two integers.
      </returns>
      <example>
      <code>
      int c = Math.Subtract(4, 5);
      if (c > 1)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      See <see cref="Math.Subtract(double, double)"/> to subtract doubles.
      <seealso cref="Math.Add(int, int)"/>
      <seealso cref="Math.Multiply(int, int)"/>
      <seealso cref="Math.Divide(int, int)"/>
      <param name="a">An integer.</param>
      <param name="b">An integer.</param>
    </SubtractInt>
    <SubtractDouble>
      <summary>
      Subtracts a double <paramref name="b"/> from another
      double <paramref name="a"/> and returns the result.
      </summary>
      <returns>
      The difference between two doubles.
      </returns>
      <example>
      <code>
      double c = Math.Subtract(4.5, 5.4);
      if (c > 1)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      See <see cref="Math.Subtract(int, int)"/> to subtract integers.
      <seealso cref="Math.Add(double, double)"/>
      <seealso cref="Math.Multiply(double, double)"/>
      <seealso cref="Math.Divide(double, double)"/>
      <param name="a">A double precision number.</param>
      <param name="b">A double precision number.</param>
    </SubtractDouble>
    <MultiplyInt>
      <summary>
      Multiplies two integers <paramref name="a"/> and
      <paramref name="b"/> and returns the result.
      </summary>
      <returns>
      The product of two integers.
      </returns>
      <example>
      <code>
      int c = Math.Multiply(4, 5);
      if (c > 100)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      See <see cref="Math.Multiply(double, double)"/> to multiply doubles.
      <seealso cref="Math.Add(int, int)"/>
      <seealso cref="Math.Subtract(int, int)"/>
      <seealso cref="Math.Divide(int, int)"/>
      <param name="a">An integer.</param>
      <param name="b">An integer.</param>
    </MultiplyInt>
    <MultiplyDouble>
      <summary>
      Multiplies two doubles <paramref name="a"/> and
      <paramref name="b"/> and returns the result.
      </summary>
      <returns>
      The product of two doubles.
      </returns>
      <example>
      <code>
      double c = Math.Multiply(4.5, 5.4);
      if (c > 100.0)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      See <see cref="Math.Multiply(int, int)"/> to multiply integers.
      <seealso cref="Math.Add(double, double)"/>
      <seealso cref="Math.Subtract(double, double)"/>
      <seealso cref="Math.Divide(double, double)"/>
      <param name="a">A double precision number.</param>
      <param name="b">A double precision number.</param>
    </MultiplyDouble>
    <DivideInt>
      <summary>
      Divides an integer <paramref name="a"/> by another integer
      <paramref name="b"/> and returns the result.
      </summary>
      <returns>
      The quotient of two integers.
      </returns>
      <example>
      <code>
      int c = Math.Divide(4, 5);
      if (c > 1)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      <exception cref="System.DivideByZeroException">
      Thrown when <paramref name="b"/> is equal to 0.
      </exception>
      See <see cref="Math.Divide(double, double)"/> to divide doubles.
      <seealso cref="Math.Add(int, int)"/>
      <seealso cref="Math.Subtract(int, int)"/>
      <seealso cref="Math.Multiply(int, int)"/>
      <param name="a">An integer dividend.</param>
      <param name="b">An integer divisor.</param>
    </DivideInt>
    <DivideDouble>
      <summary>
      Divides a double <paramref name="a"/> by another
      double <paramref name="b"/> and returns the result.
      </summary>
      <returns>
      The quotient of two doubles.
      </returns>
      <example>
      <code>
      double c = Math.Divide(4.5, 5.4);
      if (c > 1.0)
      {
        Console.WriteLine(c);
      }
      </code>
      </example>
      <exception cref="System.DivideByZeroException">Thrown when <paramref name="b"/> is equal to 0.</exception>
      See <see cref="Math.Divide(int, int)"/> to divide integers.
      <seealso cref="Math.Add(double, double)"/>
      <seealso cref="Math.Subtract(double, double)"/>
      <seealso cref="Math.Multiply(double, double)"/>
      <param name="a">A double precision dividend.</param>
      <param name="b">A double precision divisor.</param>
    </DivideDouble>
  </members>
</docs>
```

In the preceding XML, each member's documentation comments appear directly inside a tag named after what they do. You can choose your own strategy.
The code uses the `<include>` tag to reference the appropriate element in the XML file:

```csharp
namespace IncludeTag
{

    /*
        The main Math class
        Contains all methods for performing basic math functions
    */
    /// <include file='include.xml' path='docs/members[@name="math"]/Math/*'/>
    public class Math
    {
        // Adds two integers and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/AddInt/*'/>
        public static int Add(int a, int b)
        {
            // If any parameter is equal to the max value of an integer
            // and the other is greater than zero
            if ((a == int.MaxValue && b > 0) || (b == int.MaxValue && a > 0))
                throw new System.OverflowException();

            return a + b;
        }

        // Adds two doubles and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/AddDouble/*'/>
        public static double Add(double a, double b)
        {
            // If any parameter is equal to the max value of an integer
            // and the other is greater than zero
            if ((a == double.MaxValue && b > 0) || (b == double.MaxValue && a > 0))
                throw new System.OverflowException();

            return a + b;
        }

        // Subtracts an integer from another and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/SubtractInt/*'/>
        public static int Subtract(int a, int b)
        {
            return a - b;
        }

        // Subtracts a double from another and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/SubtractDouble/*'/>
        public static double Subtract(double a, double b)
        {
            return a - b;
        }

        // Multiplies two integers and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/MultiplyInt/*'/>
        public static int Multiply(int a, int b)
        {
            return a * b;
        }

        // Multiplies two doubles and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/MultiplyDouble/*'/>
        public static double Multiply(double a, double b)
        {
            return a * b;
        }

        // Divides an integer by another and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/DivideInt/*'/>
        public static int Divide(int a, int b)
        {
            return a / b;
        }

        // Divides a double by another and returns the result
        /// <include file='include.xml' path='docs/members[@name="math"]/DivideDouble/*'/>
        public static double Divide(double a, double b)
        {
            return a / b;
        }
    }
}
```

- The `file` attribute is the name of the XML file containing the documentation.
- The `path` attribute is an [XPath](../../../standard/data/xml/xpath-queries-and-namespaces.md) query to the tag name present in the specified file.
- The `name` attribute is the name specifier in the tag that precedes the comments.
- The `id` attribute, which you can use in place of `name`, is the ID for the tag that precedes the comments.
