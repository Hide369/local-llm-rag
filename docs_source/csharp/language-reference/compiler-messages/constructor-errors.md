---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/language-reference/compiler-messages/constructor-errors.md
title: Resolve errors related to constructor declarations and module initializers
version: 0.0.0
fetched_at: 2026-09-13
---
# Resolve errors and warnings for constructor declarations and module initializers

This article covers the following compiler errors:

<!-- The text in this list generates issues for Acrolinx, because they don't use contractions.
That's by design. The text closely matches the text of the compiler error / warning for SEO purposes.
 -->
- [**CS0132**](#static-constructors): *'constructor': a static constructor must be parameterless.*
- [**CS0514**](#static-constructors): *static constructor cannot have an explicit 'this' or 'base' constructor call.*
- [**CS0515**](#static-constructors): *access modifiers are not allowed on static constructors.*
- [**CS0516**](#constructor-calls-with-base-and-this): *Constructor 'constructor' cannot call itself.*
- [**CS0517**](#constructor-calls-with-base-and-this): *'class' has no base class and cannot call a base constructor.*
- [**CS0522**](#constructor-calls-with-base-and-this): *structs cannot call base class constructors.*
- [**CS0526**](#constructor-declaration): *Interfaces cannot contain instance constructors.*
- [**CS0568**](#constructors-in-struct-types): *Structs cannot contain explicit parameterless constructors.*
- [**CS0573**](#constructors-in-struct-types): *'field declaration': cannot have instance field initializers in structs.*
- [**CS0710**](#constructor-declaration): *Static classes cannot have instance constructors.*
- [**CS0768**](#constructor-calls-with-base-and-this): *Constructor cannot call itself through another constructor.*
- [**CS1018**](#constructor-calls-with-base-and-this): *Keyword 'this' or 'base' expected.*
- [**CS8054**](#constructor-declaration): *Enums cannot contain explicit parameterless constructors.*
- [**CS8091**](#constructor-declaration): *cannot be extern and have a constructor initializer.*
- [**CS8760**](#constructor-declaration): *'event': extern event cannot have initializer.*
- [**CS8358**](#constructor-declaration): *Cannot use attribute constructor because it has 'in' or 'ref readonly' parameters.*
- [**CS8813**](#module-initializer-declarations): *A module initializer must be an ordinary member method*
- [**CS8814**](#module-initializer-declarations): *Module initializer method 'method' must be accessible at the module level*
- [**CS8815**](#module-initializer-declarations): *Module initializer method 'method' must be static, and non-virtual, must have no parameters, and must return 'void'*
- [**CS8816**](#module-initializer-declarations): *Module initializer method 'method' must not be generic and must not be contained in a generic type*
- [**CS8861**](#primary-constructor-declaration): *Unexpected argument list.*
- [**CS8862**](#primary-constructor-declaration): *A constructor declared in a type with parameter list must have 'this' constructor initializer.*
- [**CS8867**](#records-and-copy-constructors): *No accessible copy constructor found in base type '{0}'.*
- [**CS8868**](#records-and-copy-constructors): *A copy constructor in a record must call a copy constructor of the base, or a parameterless object constructor if the record inherits from object.*
- [**CS8878**](#records-and-copy-constructors): *A copy constructor '{0}' must be public or protected because the record is not sealed.*
- [**CS8900**](#module-initializer-declarations): *Module initializer cannot be attributed with 'UnmanagedCallersOnly'.*
- [**CS8901**](#module-initializer-declarations): *'method' is attributed with 'UnmanagedCallersOnly' and cannot be called directly. Obtain a function pointer to this method.*
- [**CS8902**](#module-initializer-declarations): *'method' is attributed with 'UnmanagedCallersOnly' and cannot be converted to a delegate type. Obtain a function pointer to this method.*
- [**CS8910**](#records-and-copy-constructors): *The primary constructor conflicts with the synthesized copy constructor.*
- [**CS8958**](#constructors-in-struct-types): *The parameterless struct constructor must be 'public'.*
- [**CS8982**](#constructors-in-struct-types): *A constructor declared in a 'struct' with parameter list must have a 'this' initializer that calls the primary constructor or an explicitly declared constructor.*
- [**CS8983**](#constructors-in-struct-types): *A 'struct' with field initializers must include an explicitly declared constructor.*
- [**CS9105**](#primary-constructor-declaration): *Cannot use primary constructor parameter in this context.*
- [**CS9106**](#primary-constructor-declaration): *Identifier is ambiguous between type and parameter in this context.*
- [**CS9108**](#primary-constructor-declaration): *Cannot use parameter that has ref-like type inside an anonymous method, lambda expression, query expression, or local function.*
- [**CS9109**](#primary-constructor-declaration): *Cannot use `ref`, `out`, or `in` primary constructor parameter inside an instance member.*
- [**CS9110**](#primary-constructor-declaration): *Cannot use primary constructor parameter that has ref-like type inside an instance member.*
- [**CS9111**](#primary-constructor-declaration): *Anonymous methods, lambda expressions, query expressions, and local functions inside an instance member of a struct cannot access primary constructor parameter.*
- [**CS9112**](#primary-constructor-declaration): *Anonymous methods, lambda expressions, query expressions, and local functions inside a struct cannot access primary constructor parameter also used inside an instance member.*
- [**CS9114**](#primary-constructor-declaration): *A primary constructor parameter of a readonly type cannot be assigned to (except in init-only setter of the type or a variable initializer).*
- [**CS9115**](#primary-constructor-declaration): *A primary constructor parameter of a readonly type cannot be returned by writable reference.*
- [**CS9116**](#primary-constructor-declaration): *A primary constructor parameter of a readonly type cannot be used as a ref or out value (except in init-only setter of the type or a variable initializer).*
- [**CS9117**](#primary-constructor-declaration): *Members of primary constructor parameter of a readonly type cannot be modified (except in init-only setter of the type or a variable initializer).*
- [**CS9118**](#primary-constructor-declaration): *Members of primary constructor parameter of a readonly type cannot be returned by writable reference.*
- [**CS9119**](#primary-constructor-declaration): *Members of primary constructor parameter of a readonly type cannot be used as a `ref` or `out` value (except in init-only setter of the type or a variable initializer).*
- [**CS9120**](#primary-constructor-declaration): *Cannot return primary constructor parameter by reference.*
- [**CS9121**](#primary-constructor-declaration): *Struct primary constructor parameter of type causes a cycle in the struct layout.*
- [**CS9122**](#primary-constructor-declaration): *Unexpected parameter list.*
- [**CS9136**](#primary-constructor-declaration): *Cannot use primary constructor parameter of type inside an instance member.*

In addition, the following warnings are covered in this article:

- [**CS0824**](#constructor-declaration): *Constructor 'name' is marked external.*
- [**CS9107**](#primary-constructor-declaration): *Parameter is captured into the state of the enclosing type and its value is also passed to the base constructor. The value might be captured by the base class as well.*
- [**CS9113**](#primary-constructor-declaration): *Parameter is unread.*
- [**CS9124**](#primary-constructor-declaration): *Parameter is captured into the state of the enclosing type and its value is also used to initialize a field, property, or event.*
- [**CS9179**](#primary-constructor-declaration): *Primary constructor parameter is shadowed by a member from base*
- [**CS9018**](#constructors-in-struct-types): *Auto-implemented property is read before being explicitly assigned, causing a preceding implicit assignment of 'default'.*
- [**CS9019**](#constructors-in-struct-types): *Field is read before being explicitly assigned, causing a preceding implicit assignment of 'default'.*
- [**CS9020**](#constructors-in-struct-types): *The 'this' object is read before all of its fields are assigned, causing preceding implicit assignments of 'default' to non-explicitly assigned fields.*
- [**CS9021**](#constructors-in-struct-types): *Control is returned to caller before auto-implemented property is explicitly assigned, causing a preceding implicit assignment of 'default'.*
- [**CS9022**](#constructors-in-struct-types): *Control is returned to caller before field is explicitly assigned, causing a preceding implicit assignment of 'default'.*

## Static constructors

- **CS0132**: *'constructor': a static constructor must be parameterless.*
- **CS0514**: *Static constructor cannot have an explicit 'this' or 'base' constructor call.*
- **CS0515**: *Access modifiers are not allowed on static constructors.*

Static constructors initialize static data for a type. For more information, see [Static constructors](../../programming-guide/classes-and-structs/static-constructors.md).

To correct these errors, ensure your static constructor declaration follows these rules:

- Remove any parameters from the static constructor declaration, because a static constructor must be parameterless (**CS0132**). If you need to pass initialization values, consider using static fields or properties that you set before the static constructor runs.
- Remove any access modifiers such as `public`, `protected`, `private`, or `internal` from the static constructor, because the runtime controls when the static constructor executes and access modifiers aren't meaningful (**CS0515**).
- Remove any `: base()` or `: this()` constructor initializer calls from the static constructor, because static constructors can't chain to other constructors (**CS0514**). The runtime automatically invokes the base class static constructor if one exists.

## Constructor declaration

- **CS0526**: *Interfaces cannot contain instance constructors.*
- **CS0710**: *Static classes cannot have instance constructors.*
- **CS8054**: *Enums cannot contain explicit parameterless constructors.*
- **CS8358**: *Cannot use attribute constructor because it has 'in' or 'ref readonly' parameters.*
- **CS8091**: *A constructor cannot be extern and have a constructor initializer.*
- **CS8760**: *'event': extern event cannot have initializer.*

You can declare constructors only in `class` and `struct` types, including `record class` and `record struct` types. For more information, see [Instance constructors](../../programming-guide/classes-and-structs/instance-constructors.md).

To fix these errors, try the following suggestions:

- Move the constructor to a `class` or `struct` type, because you can't declare constructors in `interface` or `enum` types (**CS0526**, **CS8054**). Interfaces define contracts but don't provide initialization logic, and enum types have their values defined at compile time.
- Remove instance constructors from static classes, because static classes can't be instantiated and therefore can't have instance constructors (**CS0710**). If you need initialization logic, use a static constructor instead.
- Change `in` or `ref readonly` parameters to pass-by-value parameters in attribute constructors, because attribute constructors don't support `in` or `ref readonly` parameter modifiers (**CS8358**). The runtime instantiates attributes by using reflection, which doesn't support the `in` or `ref readonly` modifier.
- Remove the `: base()` or `: this()` constructor initializer from an `extern` constructor, because extern constructors can't chain to other constructors (**CS8091**). The implementation of an extern constructor is provided externally, so constructor chaining isn't possible.
- Remove the initializer from an `extern` event declaration (**CS8760**). Extern events have their add and remove accessors provided by external code, so a field initializer in the source has no effect and isn't permitted by the compiler.

The following warning can be generated for constructor declarations:

- **CS0824**: *Constructor is marked external.*

When a constructor is marked `extern`, the compiler can't verify that an implementation exists. To suppress this warning, either provide a non-extern implementation or ensure the external implementation is correctly linked.

## Constructors in struct types

- **CS0568**: *Structs cannot contain explicit parameterless constructors.*
- **CS0573**: *'field declaration': cannot have instance field initializers in structs.*
- **CS8958**: *The parameterless struct constructor must be 'public'.*
- **CS8982**: *A constructor declared in a 'struct' with parameter list must have a 'this' initializer that calls the primary constructor or an explicitly declared constructor.*
- **CS8983**: *A 'struct' with field initializers must include an explicitly declared constructor.*

Struct types have specific rules for constructors and field initialization. For more information, see the [Struct initialization and default values](../builtin-types/struct.md#struct-initialization-and-default-values) section of the [Structure types](../builtin-types/struct.md) article.

To fix these errors, try the following suggestions:

- Upgrade to C# 10 or later if you encounter **CS0568** or **CS0573**, because these errors occur only in older versions of C#. Modern C# allows explicit parameterless constructors and field initializers in structs.
- Add the `public` access modifier to any parameterless struct constructor, because parameterless struct constructors must be public to ensure the `default` expression and array allocation can properly initialize struct instances (**CS8958**).
- Add a `: this(...)` initializer to explicitly declared constructors in a struct that has a primary constructor, because all non-parameterless constructors must chain to the primary constructor or another explicitly declared constructor to ensure consistent initialization (**CS8982**).
- Declare an explicit constructor when your struct uses field initializers, because the compiler requires an explicit constructor to ensure field initializers are invoked (**CS8983**). This constructor can be a parameterless constructor with an empty body.

The following warnings indicate that a field or property isn't explicitly assigned before being read or before control returns to the caller:

- **CS9018**: *Auto-implemented property is read before being explicitly assigned, causing a preceding implicit assignment of 'default'.*
- **CS9019**: *Field is read before being explicitly assigned, causing a preceding implicit assignment of 'default'.*
- **CS9020**: *The 'this' object is read before all of its fields are assigned, causing preceding implicit assignments of 'default' to non-explicitly assigned fields.*
- **CS9021**: *Control is returned to caller before auto-implemented property is explicitly assigned, causing a preceding implicit assignment of 'default'.*
- **CS9022**: *Control is returned to caller before field is explicitly assigned, causing a preceding implicit assignment of 'default'.*

To silence these warnings, explicitly assign all fields and auto-implemented properties before reading them or before control returns from the constructor (**CS9018**, **CS9019**, **CS9020**, **CS9021**, **CS9022**). When unassigned members are read, the compiler implicitly assigns `default` to them, which might not be the intended behavior.

## Constructor calls with `base` and `this`

- **CS0516**: *Constructor cannot call itself.*
- **CS0517**: *'class' has no base class and cannot call a base constructor.*
- **CS0522**: *Structs cannot call base class constructors.*
- **CS0768**: *Constructor cannot call itself through another constructor.*
- **CS1018**: *Keyword 'this' or 'base' expected.*

By using constructor initializers, one constructor can call another constructor by using `: this()` or `: base()`. For more information, see [Using constructors](../../programming-guide/classes-and-structs/using-constructors.md).

To fix these errors, try the following suggestions:

- Break any circular constructor call chains, because a constructor can't call itself either directly or indirectly through another constructor (**CS0516**, **CS0768**). Make sure that constructor chaining eventually ends at a constructor that doesn't call another constructor in the same type.
- Remove the `: base()` initializer from constructors in struct types or from constructors in <xref:System.Object?displayProperty=nameWithType>, because these types don't have a base class constructor to call (**CS0517**, **CS0522**). Struct types implicitly inherit from <xref:System.ValueType?displayProperty=nameWithType>, but you can't explicitly call its constructor.
- Complete the constructor initializer or remove the colon (`:`) from the constructor declaration, because when a colon follows a constructor signature, the compiler expects either `this()` or `base()` (**CS1018**). Either add the appropriate constructor call or remove the colon entirely if no chaining is intended.

## Records and copy constructors

- **CS8867**: *No accessible copy constructor found in base type.*
- **CS8868**: *A copy constructor in a record must call a copy constructor of the base, or a parameterless object constructor if the record inherits from object.*
- **CS8878**: *A copy constructor must be public or protected because the record is not sealed.*
- **CS8910**: *The primary constructor conflicts with the synthesized copy constructor.*

In a derived record type, your explicit copy constructor must call the base type's copy constructor by using the `: this()` initializer. If the record directly inherits from <xref:System.Object?displayProperty=nameWithType>, it can call the parameterless object constructor instead (**CS8868**).

[Records](../builtin-types/record.md) include a compiler-synthesized [copy constructor](../builtin-types/record.md#nondestructive-mutation). You can write an explicit copy constructor, but it must meet specific requirements. The compiler generates errors when record copy constructors violate these requirements:

- The base type must have an accessible copy constructor. All `record` types have a copy constructor. Ensure the base type is a `record`, or add an accessible copy constructor to it (**CS8867**).
- In a derived record type, your explicit copy constructor must call the base type's copy constructor by using the `: base()` initializer. If the record directly inherits from <xref:System.Object?displayProperty=nameWithType>, it can call the parameterless object constructor instead (**CS8868**).
- Copy constructors must be `public` or `protected` unless the record type is [`sealed`](../keywords/sealed.md). Add the appropriate access modifier to the copy constructor (**CS8878**).
- If your explicit copy constructor has the same signature as the synthesized copy constructor, the definitions conflict. Remove your explicit copy constructor or modify its signature (**CS8910**).

## Module initializer declarations

- **CS8813**: *A module initializer must be an ordinary member method.*
- **CS8814**: *Module initializer method 'method' must be accessible at the module level.*
- **CS8815**: *Module initializer method 'method' must be static, and non-virtual, must have no parameters, and must return 'void'.*
- **CS8816**: *Module initializer method 'method' must not be generic and must not be contained in a generic type.*
- **CS8900**: *Module initializer cannot be attributed with 'UnmanagedCallersOnly'.*
- **CS8901**: *'method' is attributed with 'UnmanagedCallersOnly' and cannot be called directly. Obtain a function pointer to this method.*
- **CS8902**: *'method' is attributed with 'UnmanagedCallersOnly' and cannot be converted to a delegate type. Obtain a function pointer to this method.*

These errors enforce the requirements for methods marked with <xref:System.Runtime.CompilerServices.ModuleInitializerAttribute>. Module initializers run automatically when an assembly is first loaded, before any other code in the module executes. For the full rules, see [Module initializers](../attributes/general.md#moduleinitializer-attribute).

To correct these errors, apply one of the following changes based on the specific diagnostic:

- Ensure the method marked with `[ModuleInitializer]` is an ordinary method, not a property accessor, event accessor, local function, lambda, constructor, destructor, or operator (**CS8813**). The compiler can only treat an ordinary method declaration as a valid target for module initializer infrastructure.
- Make the module initializer method and all its containing types `internal` or `public` so the method is accessible outside the top-level type (**CS8814**). The runtime needs to call the method from generated module-level code, which requires accessibility at the module level.
- Declare the module initializer method as `static`, non-virtual, with no parameters, and with a `void` return type (**CS8815**). The runtime calls module initializers without any arguments and discards the result, so the method signature must match these constraints exactly.
- Remove generic type parameters from the module initializer method and move the method out of any generic containing type (**CS8816**). The runtime can't determine which type arguments to supply when invoking the initializer, so generic methods and methods in generic types aren't permitted.
- Remove the <xref:System.Runtime.InteropServices.UnmanagedCallersOnlyAttribute> from the module initializer method (**CS8900**). Module initializers are called by managed runtime infrastructure, so they can't be restricted to unmanaged callers only.
- Obtain a function pointer instead of calling a method marked with `[UnmanagedCallersOnly]` directly (**CS8901**). Methods attributed with <xref:System.Runtime.InteropServices.UnmanagedCallersOnlyAttribute> can't be called from managed code. Use the `&` operator to get a function pointer (`delegate* unmanaged<...>`) in an `unsafe` context, and pass the pointer to unmanaged code. If your project doesn't already allow unsafe code, enable `AllowUnsafeBlocks`.
- Obtain a function pointer instead of converting a method marked with `[UnmanagedCallersOnly]` to a delegate type (**CS8902**). Methods attributed with <xref:System.Runtime.InteropServices.UnmanagedCallersOnlyAttribute> can't be represented as managed delegates because the calling convention is incompatible. Use function pointers (`delegate* unmanaged<...>`) in an `unsafe` context instead. If your project doesn't already allow unsafe code, enable `AllowUnsafeBlocks`.

For more information, see <xref:System.Runtime.CompilerServices.ModuleInitializerAttribute> and <xref:System.Runtime.InteropServices.UnmanagedCallersOnlyAttribute>.

## Primary constructor declaration

[Primary constructors](../../programming-guide/classes-and-structs/instance-constructors.md#primary-constructors) declare parameters directly in the type declaration. The compiler synthesizes a field to store a primary constructor parameter when you use it in members or field initializers.

### Constructor chaining

- **CS8861**: *Unexpected argument list.*
- **CS8862**: *A constructor declared in a type with parameter list must have 'this' constructor initializer.*
- **CS9122**: *Unexpected parameter list.*

When a type has a primary constructor, all other explicitly declared constructors must chain to it by using `: this(...)`.

To fix these errors, try the following suggestions:

- Add a `: this(...)` initializer that passes appropriate arguments to the primary constructor, because all explicitly declared constructors must chain to the primary constructor (**CS8862**).
- Remove a parameter list from the base type reference when the base type doesn't have a primary constructor, because the syntax `class Derived : Base(args)` is only valid when `Base` has a primary constructor (**CS8861**).
- Remove a primary constructor parameter list from an `interface` declaration, because interfaces can't have primary constructors (**CS9122**).

### Parameter usage in base constructor calls

- **CS9105**: *Cannot use primary constructor parameter in this context.*
- **CS9106**: *Identifier is ambiguous between type and parameter in this context.*

You can only use primary constructor parameters in the base constructor call if you pass them as part of the primary constructor declaration.

To fix these errors, try the following suggestions:

- Move the parameter usage to the type declaration's base clause instead of using it in an explicitly declared constructor's `: base()` call, because primary constructor parameters can only appear in the base clause of the type declaration (**CS9105**).
- Rename either the type or the parameter when a type and a primary constructor parameter share the same name, because the reference becomes ambiguous (**CS9106**).

### Ref-like type parameters

- **CS9108**: *Cannot use parameter that has ref-like type inside an anonymous method, lambda expression, query expression, or local function.*
- **CS9109**: *Cannot use `ref`, `out`, or `in` primary constructor parameter inside an instance member.*
- **CS9110**: *Cannot use primary constructor parameter that has ref-like type inside an instance member.*
- **CS9136**: *Cannot use primary constructor parameter of type inside an instance member.*

To address these errors:

- Primary constructor parameters of `ref struct` type have restrictions on where you can use them. Move the parameter access out of lambda expressions, query expressions, or local functions (**CS9108**). In types that aren't `ref struct`, access `ref struct` parameters only in field initializers or the constructor body, not in instance members (**CS9110**, **CS9136**).
- For `ref struct` types, you can't use primary constructor parameters with `in`, `ref`, or `out` modifiers in instance methods or property accessors. Copy the parameter value to a field in the constructor and use that field in instance members instead (**CS9109**).

### Struct type restrictions

- **CS9111**: *Anonymous methods, lambda expressions, query expressions, and local functions inside an instance member of a struct cannot access primary constructor parameter.*
- **CS9112**: *Anonymous methods, lambda expressions, query expressions, and local functions inside a struct cannot access primary constructor parameter also used inside an instance member.*
- **CS9120**: *Cannot return primary constructor parameter by reference.*
- **CS9121**: *Struct primary constructor parameter of type causes a cycle in the struct layout.*

To address these errors:

- In struct types, you can't capture primary constructor parameters in lambda expressions, query expressions, or local functions inside instance members. Copy the parameter to a local variable or field before using it in these contexts (**CS9111**, **CS9112**).
- You can't return primary constructor parameters by reference in struct types. Store the value in a field and return that field by reference if needed (**CS9120**).
- Ensure that a primary constructor parameter's type doesn't create a cycle in the struct layout. A struct can't contain a field of its own type either directly or indirectly (**CS9121**).

### Readonly struct restrictions

- **CS9114**: *A primary constructor parameter of a readonly type cannot be assigned to (except in init-only setter of the type or a variable initializer).*
- **CS9115**: *A primary constructor parameter of a readonly type cannot be returned by writable reference.*
- **CS9116**: *A primary constructor parameter of a readonly type cannot be used as a `ref` or `out` value (except in init-only setter of the type or a variable initializer).*
- **CS9117**: *Members of primary constructor parameter of a readonly type cannot be modified (except in init-only setter of the type or a variable initializer).*
- **CS9118**: *Members of primary constructor parameter of a readonly type cannot be returned by writable reference.*
- **CS9119**: *Members of primary constructor parameter of a readonly type cannot be used as a `ref` or `out` value (except in init-only setter of the type or a variable initializer).*

To address these errors:

- In `readonly struct` types, you can't modify primary constructor parameters and their members outside of init-only setters or variable initializers. Move assignments to field initializers or init-only property setters (**CS9114**, **CS9117**).
- You can't return primary constructor parameters and their members by writable reference in `readonly struct` types. Return by `readonly ref` or by value instead (**CS9115**, **CS9118**).
- You can't pass primary constructor parameters and their members as `ref` or `out` arguments in `readonly struct` types. Pass them by value or as `in` arguments instead (**CS9116**, **CS9119**).

### Warnings for captured and shadowed parameters

- **CS9107**: *Parameter is captured into the state of the enclosing type and its value is also passed to the base constructor. The value might be captured by the base class as well.*
- **CS9113**: *Parameter is unread.*
- **CS9124**: *Parameter is captured into the state of the enclosing type and its value is also used to initialize a field, property, or event.*
- **CS9179**: *Primary constructor parameter is shadowed by a member from base.*

The following warnings indicate potential problems with how you store or access primary constructor parameters:

- You might store a parameter twice if you both pass it to the base constructor and access it in the derived type. You might have one copy in the base class and another in the derived class. Consider whether you need both copies, or restructure your code to avoid the duplication (**CS9107**).
- You don't need a primary constructor parameter if you never read it. Remove unused parameters from the primary constructor declaration (**CS9113**).
- You might store a parameter twice if you both capture it in the enclosing type and use it to initialize a field, property, or event. Consider using the captured parameter directly instead of initializing a separate member (**CS9124**).
- A base type member shadows a primary constructor parameter when both have the same name. Rename the parameter to avoid confusion (**CS9179**).
