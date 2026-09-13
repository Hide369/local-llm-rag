---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/advanced-topics/expression-trees/expression-trees-building.md
title: Building Expression Trees
version: 0.0.0
fetched_at: 2026-09-13
---
# Build expression trees

The C# compiler created all the expression trees you've seen so far. You created a lambda expression assigned to a variable typed as an `Expression<Func<T>>` or some similar type. For many scenarios, you build an expression in memory at run time.

Expression trees are immutable. Being immutable means that you must build the tree from the leaves up to the root. The APIs you use to build expression trees reflect this fact: The methods you use to build a node take all its children as arguments. Let's walk through a few examples to show you the techniques.

## Create nodes

You start with the addition expression you've been working with throughout these sections:

```csharp
Expression<Func<int>> sum = () => 1 + 2;
```

To construct that expression tree, you first construct the leaf nodes. The leaf nodes are constants. Use the <xref:System.Linq.Expressions.Expression.Constant*> method to create the nodes:

```csharp
var one = Expression.Constant(1, typeof(int));
var two = Expression.Constant(2, typeof(int));
```

Next, build the addition expression:

```csharp
var addition = Expression.Add(one, two);
```

Once you've built the addition expression, you create the lambda expression:

```csharp
var lambda = Expression.Lambda(addition);
```

This lambda expression contains no arguments. Later in this section, you see how to map arguments to parameters and build more complicated expressions.

For expressions like this one, you may combine all the calls into a single statement:

```csharp
var lambda2 = Expression.Lambda(
    Expression.Add(
        Expression.Constant(1, typeof(int)),
        Expression.Constant(2, typeof(int))
    )
);
```

## Build a tree

The previous section showed the basics of building an expression tree in memory. More complex trees generally mean more node types, and more nodes in the tree. Let's run through one more example and show two more node types that you typically build when you create expression trees: the argument nodes, and method call nodes. Let's build an expression tree to create this expression:

```csharp
Expression<Func<double, double, double>> distanceCalc =
    (x, y) => Math.Sqrt(x * x + y * y);
```

You start by creating parameter expressions for `x` and `y`:

```csharp
var xParameter = Expression.Parameter(typeof(double), "x");
var yParameter = Expression.Parameter(typeof(double), "y");
```

Creating the multiplication and addition expressions follows the pattern you've already seen:

```csharp
var xSquared = Expression.Multiply(xParameter, xParameter);
var ySquared = Expression.Multiply(yParameter, yParameter);
var sum = Expression.Add(xSquared, ySquared);
```

Next, you need to create a method call expression for the call to `Math.Sqrt`.

```csharp
var sqrtMethod = typeof(Math).GetMethod("Sqrt", new[] { typeof(double) }) ?? throw new InvalidOperationException("Math.Sqrt not found!");
var distance = Expression.Call(sqrtMethod, sum);
```

The `GetMethod` call could return `null` if the method isn't found. Most likely that's because you've misspelled the method name. Otherwise, it could mean the required assembly isn't loaded. Finally, you put the method call into a lambda expression, and make sure to define the arguments to the lambda expression:

```csharp
var distanceLambda = Expression.Lambda(
    distance,
    xParameter,
    yParameter);
```

In this more complicated example, you see a couple more techniques that you often need to create expression trees.

First, you need to create the objects that represent parameters or local variables before you use them. Once you've created those objects, you can use them in your expression tree wherever you need.

Second, you need to use a subset of the Reflection APIs to create a <xref:System.Reflection.MethodInfo?displayProperty=nameWithType> object so that you can create an expression tree to access that method. You must limit yourself to the subset of the Reflection APIs that are available on the .NET Core platform. Again, these techniques extend to other expression trees.

## Build code in depth

You aren't limited in what you can build using these APIs. However, the more complicated expression tree that you want to build, the more difficult the code is to manage and to read.

Let's build an expression tree that is the equivalent of this code:

```csharp
Func<int, int> factorialFunc = (n) =>
{
    var res = 1;
    while (n > 1)
    {
        res = res * n;
        n--;
    }
    return res;
};
```

The preceding code didn't build the expression tree, but simply the delegate. Using the `Expression` class, you can't build statement lambdas. Here's the code that is required to build the same functionality. There isn't an API for building a `while` loop, instead you need to build a loop that contains a conditional test, and a label target to break out of the loop.

```csharp
var nArgument = Expression.Parameter(typeof(int), "n");
var result = Expression.Variable(typeof(int), "result");

// Creating a label that represents the return value
LabelTarget label = Expression.Label(typeof(int));

var initializeResult = Expression.Assign(result, Expression.Constant(1));

// This is the inner block that performs the multiplication,
// and decrements the value of 'n'
var block = Expression.Block(
    Expression.Assign(result,
        Expression.Multiply(result, nArgument)),
    Expression.PostDecrementAssign(nArgument)
);

// Creating a method body.
BlockExpression body = Expression.Block(
    new[] { result },
    initializeResult,
    Expression.Loop(
        Expression.IfThenElse(
            Expression.GreaterThan(nArgument, Expression.Constant(1)),
            block,
            Expression.Break(label, result)
        ),
        label
    )
);
```

The code to build the expression tree for the factorial function is quite a bit longer, more complicated, and it's riddled with labels and break statements and other elements you'd like to avoid in our everyday coding tasks.

For this section, you wrote code to visit every node in this expression tree and write out information about the nodes that are created in this sample. You can [view or download the sample code](https://github.com/dotnet/samples/tree/main/csharp/expression-trees) at the dotnet/docs GitHub repository. Experiment for yourself by building and running the samples.

## Map code constructs to expressions

The following code example demonstrates an expression tree that represents the lambda expression `num => num < 5` by using the API.

```csharp
// Manually build the expression tree for
// the lambda expression num => num < 5.
ParameterExpression numParam = Expression.Parameter(typeof(int), "num");
ConstantExpression five = Expression.Constant(5, typeof(int));
BinaryExpression numLessThanFive = Expression.LessThan(numParam, five);
Expression<Func<int, bool>> lambda1 =
    Expression.Lambda<Func<int, bool>>(
        numLessThanFive,
        new ParameterExpression[] { numParam });
```

The expression trees API also supports assignments and control flow expressions such as loops, conditional blocks, and `try-catch` blocks. By using the API, you can create expression trees that are more complex than those that can be created from lambda expressions by the C# compiler. The following example demonstrates how to create an expression tree that calculates the factorial of a number.

```csharp
// Creating a parameter expression.
ParameterExpression value = Expression.Parameter(typeof(int), "value");

// Creating an expression to hold a local variable.
ParameterExpression result = Expression.Parameter(typeof(int), "result");

// Creating a label to jump to from a loop.
LabelTarget label = Expression.Label(typeof(int));

// Creating a method body.
BlockExpression block = Expression.Block(
    // Adding a local variable.
    new[] { result },
    // Assigning a constant to a local variable: result = 1
    Expression.Assign(result, Expression.Constant(1)),
        // Adding a loop.
        Expression.Loop(
           // Adding a conditional block into the loop.
           Expression.IfThenElse(
               // Condition: value > 1
               Expression.GreaterThan(value, Expression.Constant(1)),
               // If true: result *= value --
               Expression.MultiplyAssign(result,
                   Expression.PostDecrementAssign(value)),
               // If false, exit the loop and go to the label.
               Expression.Break(label, result)
           ),
       // Label to jump to.
       label
    )
);

// Compile and execute an expression tree.
int factorial = Expression.Lambda<Func<int, int>>(block, value).Compile()(5);

Console.WriteLine(factorial);
// Prints 120.
```

For more information, see [Generating Dynamic Methods with Expression Trees in Visual Studio 2010](https://devblogs.microsoft.com/csharpfaq/generating-dynamic-methods-with-expression-trees-in-visual-studio-2010/), which also applies to later versions of Visual Studio.
