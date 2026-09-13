---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/operators/namespace-alias-qualifier.md
title: Namespace alias operator - the `::` is used to access a member of an aliased namespace.
version: 0.0.0
fetched_at: 2026-09-13
---
# :: operator - the namespace alias operator

Use the namespace alias qualifier `::` to access a member of an aliased namespace. You can use the `::` qualifier only between two identifiers. The left-hand identifier can be one of a namespace alias, an extern alias, or the `global` alias.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

For example:

- A namespace alias created with a [using alias directive](../keywords/using-directive.md):

  ```csharp
  using forwinforms = System.Drawing;
  using forwpf = System.Windows;
  
  public class Converters
  {
      public static forwpf::Point Convert(forwinforms::Point point) => new forwpf::Point(point.X, point.Y);
  }
  ```

- An [extern alias](../keywords/extern-alias.md).
- The `global` alias, which is the global namespace alias. The global namespace is the namespace that contains namespaces and types that aren't declared inside a named namespace. When used with the `::` qualifier, the `global` alias always references the global namespace, even if there's the user-defined `global` namespace alias.

  The following example uses the `global` alias to access the .NET <xref:System> namespace, which is a member of the global namespace. Without the `global` alias, the user-defined `System` namespace, which is a member of the `MyCompany.MyProduct` namespace, would be accessed:

  ```csharp
  namespace MyCompany.MyProduct.System
  {
      class Program
      {
          static void Main() => global::System.Console.WriteLine("Using global alias");
      }

      class Console
      {
          string Suggestion => "Consider renaming this class";
      }
  }
  ```

  > [!NOTE]
  > The `global` keyword is the global namespace alias only when it's the left-hand identifier of the `::` qualifier.

You can also use the [`.` token](member-access-operators.md#member-access-expression-) to access a member of an aliased namespace. However, the `.` token is also used to access a type member. The `::` qualifier ensures that its left-hand identifier always references a namespace alias, even if there exists a type or namespace with the same name.

## C# language specification

For more information, see the [Namespace alias qualifiers](~/_csharpstandard/standard/namespaces.md#149-qualified-alias-member) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- [C# operators and expressions](index.md)
