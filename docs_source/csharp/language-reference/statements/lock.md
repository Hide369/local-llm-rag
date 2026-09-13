---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/statements/lock.md
title: The lock statement - synchronize access to shared resources
version: 0.0.0
fetched_at: 2026-09-13
---
# The lock statement - ensure exclusive access to a shared resource

The `lock` statement acquires the mutual-exclusion lock for a given object, executes a statement block, and then releases the lock. While a lock is held, the thread that holds the lock can acquire and release the lock multiple times. Any other thread is blocked from acquiring the lock and waits until the lock is released. The `lock` statement ensures that at most only one thread executes its body at any moment in time.

[!INCLUDE[csharp-version-note](../includes/initial-version.md)]

The `lock` statement takes the following form:

```csharp
lock (x)
{
    // Your code...
}
```

The variable `x` is an expression of <xref:System.Threading.Lock?displayProperty=fullName> type, or a [reference type](../keywords/reference-types.md). When the compiler knows that `x` is of the type <xref:System.Threading.Lock?displayProperty=fullName>, it's precisely equivalent to:

```csharp
using (x.EnterScope())
{
    // Your code...
}
```

The object returned by <xref:System.Threading.Lock.EnterScope?displayProperty=nameWithType> is a [`ref struct`](../builtin-types/ref-struct.md) that includes a `Dispose()` method. The generated [`using`](using.md) statement ensures the scope is released even if an exception is thrown within the body of the `lock` statement.

Otherwise, the `lock` statement is precisely equivalent to:

```csharp
object __lockObj = x;
bool __lockWasTaken = false;
try
{
    System.Threading.Monitor.Enter(__lockObj, ref __lockWasTaken);
    // Your code...
}
finally
{
    if (__lockWasTaken) System.Threading.Monitor.Exit(__lockObj);
}
```

Since the code uses a [`try-finally` statement](exception-handling-statements.md#the-try-finally-statement), the lock is released even if an exception is thrown within the body of a `lock` statement.

You can't use the [`await` expression](../operators/await.md) in the body of a `lock` statement.

## Guidelines

Starting with .NET 9 and C# 13, lock a dedicated object instance of the <xref:System.Threading.Lock?displayProperty=nameWithType> type for best performance. The compiler also issues a warning if you cast a known `Lock` object to another type and lock it. If you're using an older version of .NET and C#, lock on a dedicated object instance that isn't used for another purpose. Avoid using the same lock object instance for different shared resources, as it might result in deadlock or lock contention. In particular, avoid using the following instances as lock objects:

- `this`, as callers might also lock `this`.
- <xref:System.Type> instances, as they might be obtained by the [typeof](../operators/type-testing-and-cast.md#the-typeof-operator) operator or reflection.
- string instances, including string literals, as they might be [interned](/dotnet/api/system.string.intern#remarks).

Hold a lock for as short time as possible to reduce lock contention.

## Example

The following example defines an `Account` class that synchronizes access to its private `balance` field by locking on a dedicated `balanceLock` instance. Using the same instance for locking ensures that two different threads can't update the `balance` field by calling the `Debit` or `Credit` methods simultaneously. The sample uses C# 13 and the new `Lock` object. If you're using an older version of C# or an older .NET library, lock an instance of `object`.

```csharp
using System;
using System.Threading.Tasks;

public class Account
{
    // Use `object` in versions earlier than C# 13
    private readonly System.Threading.Lock _balanceLock = new();
    private decimal _balance;

    public Account(decimal initialBalance) => _balance = initialBalance;

    public decimal Debit(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "The debit amount cannot be negative.");
        }

        decimal appliedAmount = 0;
        lock (_balanceLock)
        {
            if (_balance >= amount)
            {
                _balance -= amount;
                appliedAmount = amount;
            }
        }
        return appliedAmount;
    }

    public void Credit(decimal amount)
    {
        if (amount < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amount), "The credit amount cannot be negative.");
        }

        lock (_balanceLock)
        {
            _balance += amount;
        }
    }

    public decimal GetBalance()
    {
        lock (_balanceLock)
        {
            return _balance;
        }
    }
}

class AccountTest
{
    static async Task Main()
    {
        var account = new Account(1000);
        var tasks = new Task[100];
        for (int i = 0; i < tasks.Length; i++)
        {
            tasks[i] = Task.Run(() => Update(account));
        }
        await Task.WhenAll(tasks);
        Console.WriteLine($"Account's balance is {account.GetBalance()}");
        // Output:
        // Account's balance is 2000
    }

    static void Update(Account account)
    {
        decimal[] amounts = [0, 2, -3, 6, -2, -1, 8, -5, 11, -6];
        foreach (var amount in amounts)
        {
            if (amount >= 0)
            {
                account.Credit(amount);
            }
            else
            {
                account.Debit(Math.Abs(amount));
            }
        }
    }
}
```

## C# language specification

For more information, see [The lock statement](~/_csharpstandard/standard/statements.md#1313-the-lock-statement) section of the [C# language specification](~/_csharpstandard/standard/README.md).

## See also

- <xref:System.Threading.Monitor?displayProperty=nameWithType>
- <xref:System.Threading.SpinLock?displayProperty=nameWithType>
- <xref:System.Threading.Interlocked?displayProperty=nameWithType>
- [Overview of synchronization primitives](../../../standard/threading/overview-of-synchronization-primitives.md)
- [Introduction to System.Threading.Channels](https://devblogs.microsoft.com/dotnet/an-introduction-to-system-threading-channels)
