---
title: Python Language Reference（統合版）
---

<span id="index--reference-index"></span>

# The Python Language Reference {#index--the-python-language-reference}

This reference manual describes the syntax and “core semantics” of the language. It is terse, but attempts to be exact and complete. The semantics of non-essential built-in object types and of the built-in functions and modules are described in [The Python Standard Library](https://docs.python.org/3/library/index.html#library-index). For an informal introduction to the language, see [The Python Tutorial](https://docs.python.org/3/tutorial/index.html#tutorial-index). For C or C++ programmers, two additional manuals exist: [Extending and Embedding the Python Interpreter](https://docs.python.org/3/extending/index.html#extending-index) describes the high-level picture of how to write a Python extension module, and the [Python/C API reference manual](https://docs.python.org/3/c-api/index.html#c-api-index) describes the interfaces available to C/C++ programmers in detail.

- [1. Introduction](#introduction--introduction)
  - [1.1. Alternate Implementations](#introduction--alternate-implementations)
  - [1.2. Notation](#introduction--notation)
- [2. Lexical analysis](#lexical_analysis--lexical-analysis)
  - [2.1. Line structure](#lexical_analysis--line-structure)
  - [2.2. Other tokens](#lexical_analysis--other-tokens)
  - [2.3. Names (identifiers and keywords)](#lexical_analysis--names-identifiers-and-keywords)
  - [2.4. Literals](#lexical_analysis--literals)
  - [2.5. String and Bytes literals](#lexical_analysis--string-and-bytes-literals)
  - [2.6. Numeric literals](#lexical_analysis--numeric-literals)
  - [2.7. Operators and delimiters](#lexical_analysis--operators-and-delimiters)
- [3. Data model](#datamodel--data-model)
  - [3.1. Objects, values and types](#datamodel--objects-values-and-types)
  - [3.2. The standard type hierarchy](#datamodel--the-standard-type-hierarchy)
  - [3.3. Special method names](#datamodel--special-method-names)
  - [3.4. Coroutines](#datamodel--coroutines)
- [4. Execution model](#executionmodel--execution-model)
  - [4.1. Structure of a program](#executionmodel--structure-of-a-program)
  - [4.2. Naming and binding](#executionmodel--naming-and-binding)
  - [4.3. Exceptions](#executionmodel--exceptions)
  - [4.4. Runtime Components](#executionmodel--runtime-components)
- [5. The import system](#import--the-import-system)
  - [5.1. `importlib`](#import--importlib)
  - [5.2. Packages](#import--packages)
  - [5.3. Searching](#import--searching)
  - [5.4. Loading](#import--loading)
  - [5.5. The Path Based Finder](#import--the-path-based-finder)
  - [5.6. Replacing the standard import system](#import--replacing-the-standard-import-system)
  - [5.7. Package Relative Imports](#import--package-relative-imports)
  - [5.8. Special considerations for \_\_main\_\_](#import--special-considerations-for-main)
  - [5.9. References](#import--references)
- [6. Expressions](#expressions--expressions)
  - [6.1. Arithmetic conversions](#expressions--arithmetic-conversions)
  - [6.2. Atoms](#expressions--atoms)
  - [6.3. Primaries](#expressions--primaries)
  - [6.4. Await expression](#expressions--await-expression)
  - [6.5. The power operator](#expressions--the-power-operator)
  - [6.6. Unary arithmetic and bitwise operations](#expressions--unary-arithmetic-and-bitwise-operations)
  - [6.7. Binary arithmetic operations](#expressions--binary-arithmetic-operations)
  - [6.8. Shifting operations](#expressions--shifting-operations)
  - [6.9. Binary bitwise operations](#expressions--binary-bitwise-operations)
  - [6.10. Comparisons](#expressions--comparisons)
  - [6.11. Boolean operations](#expressions--boolean-operations)
  - [6.12. Assignment expressions](#expressions--assignment-expressions)
  - [6.13. Conditional expressions](#expressions--conditional-expressions)
  - [6.14. Lambdas](#expressions--lambda)
  - [6.15. Expression lists](#expressions--expression-lists)
  - [6.16. Evaluation order](#expressions--evaluation-order)
  - [6.17. Operator precedence](#expressions--operator-precedence)
- [7. Simple statements](#simple_stmts--simple-statements)
  - [7.1. Expression statements](#simple_stmts--expression-statements)
  - [7.2. Assignment statements](#simple_stmts--assignment-statements)
  - [7.3. The `assert` statement](#simple_stmts--the-assert-statement)
  - [7.4. The `pass` statement](#simple_stmts--the-pass-statement)
  - [7.5. The `del` statement](#simple_stmts--the-del-statement)
  - [7.6. The `return` statement](#simple_stmts--the-return-statement)
  - [7.7. The `yield` statement](#simple_stmts--the-yield-statement)
  - [7.8. The `raise` statement](#simple_stmts--the-raise-statement)
  - [7.9. The `break` statement](#simple_stmts--the-break-statement)
  - [7.10. The `continue` statement](#simple_stmts--the-continue-statement)
  - [7.11. The `import` statement](#simple_stmts--the-import-statement)
  - [7.12. The `global` statement](#simple_stmts--the-global-statement)
  - [7.13. The `nonlocal` statement](#simple_stmts--the-nonlocal-statement)
  - [7.14. The `type` statement](#simple_stmts--the-type-statement)
- [8. Compound statements](#compound_stmts--compound-statements)
  - [8.1. The `if` statement](#compound_stmts--the-if-statement)
  - [8.2. The `while` statement](#compound_stmts--the-while-statement)
  - [8.3. The `for` statement](#compound_stmts--the-for-statement)
  - [8.4. The `try` statement](#compound_stmts--the-try-statement)
  - [8.5. The `with` statement](#compound_stmts--the-with-statement)
  - [8.6. The `match` statement](#compound_stmts--the-match-statement)
  - [8.7. Function definitions](#compound_stmts--function-definitions)
  - [8.8. Class definitions](#compound_stmts--class-definitions)
  - [8.9. Coroutines](#compound_stmts--coroutines)
  - [8.10. Type parameter lists](#compound_stmts--type-parameter-lists)
  - [8.11. Annotations](#compound_stmts--annotations)
- [9. Top-level components](#toplevel_components--top-level-components)
  - [9.1. Complete Python programs](#toplevel_components--complete-python-programs)
  - [9.2. File input](#toplevel_components--file-input)
  - [9.3. Interactive input](#toplevel_components--interactive-input)
  - [9.4. Expression input](#toplevel_components--expression-input)
- [10. Full Grammar specification](#grammar--full-grammar-specification)

<span id="introduction--id1"></span>

# 1. Introduction {#introduction--introduction}

This reference manual describes the Python programming language. It is not intended as a tutorial.

While I am trying to be as precise as possible, I chose to use English rather than formal specifications for everything except syntax and lexical analysis. This should make the document more understandable to the average reader, but will leave room for ambiguities. Consequently, if you were coming from Mars and tried to re-implement Python from this document alone, you might have to guess things and in fact you would probably end up implementing quite a different language. On the other hand, if you are using Python and wonder what the precise rules about a particular area of the language are, you should definitely be able to find them here. If you would like to see a more formal definition of the language, maybe you could volunteer your time — or invent a cloning machine :-).

It is dangerous to add too many implementation details to a language reference document — the implementation may change, and other implementations of the same language may work differently. On the other hand, CPython is the one Python implementation in widespread use (although alternate implementations continue to gain support), and its particular quirks are sometimes worth being mentioned, especially where the implementation imposes additional limitations. Therefore, you’ll find short “implementation notes” sprinkled throughout the text.

Every Python implementation comes with a number of built-in and standard modules. These are documented in [The Python Standard Library](https://docs.python.org/3/library/index.html#library-index). A few built-in modules are mentioned when they interact in a significant way with the language definition.

<span id="introduction--implementations"></span>

## 1.1. Alternate Implementations {#introduction--alternate-implementations}

Though there is one Python implementation which is by far the most popular, there are some alternate implementations which are of particular interest to different audiences.

Known implementations include:

CPython  
This is the original and most-maintained implementation of Python, written in C. New language features generally appear here first.

Jython  
Python implemented in Java. This implementation can be used as a scripting language for Java applications, or can be used to create applications using the Java class libraries. It is also often used to create tests for Java libraries. More information can be found at [the Jython website](https://www.jython.org/).

Python for .NET  
This implementation actually uses the CPython implementation, but is a managed .NET application and makes .NET libraries available. It was created by Brian Lloyd. For more information, see the [Python for .NET home page](https://pythonnet.github.io/).

IronPython  
An alternate Python for .NET. Unlike Python.NET, this is a complete Python implementation that generates IL, and compiles Python code directly to .NET assemblies. It was created by Jim Hugunin, the original creator of Jython. For more information, see [the IronPython website](https://ironpython.net/).

PyPy  
An implementation of Python written completely in Python. It supports several advanced features not found in other implementations like stackless support and a Just in Time compiler. One of the goals of the project is to encourage experimentation with the language itself by making it easier to modify the interpreter (since it is written in Python). Additional information is available on [the PyPy project’s home page](https://pypy.org/).

Each of these implementations varies in some way from the language as documented in this manual, or introduces specific information beyond what’s covered in the standard Python documentation. Please refer to the implementation-specific documentation to determine what else you need to know about the specific implementation you’re using.

<span id="introduction--id2"></span>

## 1.2. Notation {#introduction--notation}

The descriptions of lexical analysis and syntax use a grammar notation that is a mixture of [EBNF](https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form) and [PEG](https://en.wikipedia.org/wiki/Parsing_expression_grammar). For example:

    name:   letter (letter | digit | "_")*
    letter: "a"..."z" | "A"..."Z"
    digit:  "0"..."9"

In this example, the first line says that a `name` is a `letter` followed by a sequence of zero or more `letter`s, `digit`s, and underscores. A `letter` in turn is any of the single characters `'a'` through `'z'` and `A` through `Z`; a `digit` is a single character from `0` to `9`.

Each rule begins with a name (which identifies the rule that’s being defined) followed by a colon, `:`. The definition to the right of the colon uses the following syntax elements:

- `name`: A name refers to another rule. Where possible, it is a link to the rule’s definition.

  - `TOKEN`: An uppercase name refers to a [token](https://docs.python.org/3/glossary.html#term-token). For the purposes of grammar definitions, tokens are the same as rules.

- `"text"`, `'text'`: Text in single or double quotes must match literally (without the quotes). The type of quote is chosen according to the meaning of `text`:

  - `'if'`: A name in single quotes denotes a [keyword](#lexical_analysis--keywords).

  - `"case"`: A name in double quotes denotes a [soft-keyword](#lexical_analysis--soft-keywords).

  - `'@'`: A non-letter symbol in single quotes denotes an [`OP`](https://docs.python.org/3/library/token.html#token.OP) token, that is, a [delimiter](#lexical_analysis--delimiters) or [operator](#lexical_analysis--operators).

- `e1 e2`: Items separated only by whitespace denote a sequence. Here, `e1` must be followed by `e2`.

- `e1 | e2`: A vertical bar is used to separate alternatives. It denotes PEG’s “ordered choice”: if `e1` matches, `e2` is not considered. In traditional PEG grammars, this is written as a slash, `/`, rather than a vertical bar. See <span id="introduction--index-1"></span>[**PEP 617**](https://peps.python.org/pep-0617/) for more background and details.

- `e*`: A star means zero or more repetitions of the preceding item.

- `e+`: Likewise, a plus means one or more repetitions.

- `[e]`: A phrase enclosed in square brackets means zero or one occurrences. In other words, the enclosed phrase is optional.

- `e?`: A question mark has exactly the same meaning as square brackets: the preceding item is optional.

- `(e)`: Parentheses are used for grouping.

The following notation is only used in [lexical definitions](#introduction--notation-lexical-vs-syntactic).

- `"a"..."z"`: Two literal characters separated by three dots mean a choice of any single character in the given (inclusive) range of ASCII characters.

- `<...>`: A phrase between angular brackets gives an informal description of the matched symbol (for example, `<any ASCII character except "\">`), or an abbreviation that is defined in nearby text (for example, `<Lu>`).

Some definitions also use *lookaheads*, which indicate that an element must (or must not) match at a given position, but without consuming any input:

- `&e`: a positive lookahead (that is, `e` is required to match)

- `!e`: a negative lookahead (that is, `e` is required *not* to match)

The unary operators (`*`, `+`, `?`) bind as tightly as possible; the vertical bar (`|`) binds most loosely.

White space is only meaningful to separate tokens.

Rules are normally contained on a single line, but rules that are too long may be wrapped:

    literal: stringliteral | bytesliteral
             | integer | floatnumber | imagnumber

Alternatively, rules may be formatted with the first line ending at the colon, and each alternative beginning with a vertical bar on a new line. For example:

    literal:
       | stringliteral
       | bytesliteral
       | integer
       | floatnumber
       | imagnumber

This does *not* mean that there is an empty first alternative.

<span id="introduction--notation-lexical-vs-syntactic"></span> <span id="introduction--index-2"></span>

### 1.2.1. Lexical and Syntactic definitions {#introduction--lexical-and-syntactic-definitions}

There is some difference between *lexical* and *syntactic* analysis: the [lexical analyzer](https://docs.python.org/3/glossary.html#term-lexical-analyzer) operates on the individual characters of the input source, while the *parser* (syntactic analyzer) operates on the stream of [tokens](https://docs.python.org/3/glossary.html#term-token) generated by the lexical analysis. However, in some cases the exact boundary between the two phases is a CPython implementation detail.

The practical difference between the two is that in *lexical* definitions, all whitespace is significant. The lexical analyzer [discards](#lexical_analysis--whitespace) all whitespace that is not converted to tokens like [`token.INDENT`](https://docs.python.org/3/library/token.html#token.INDENT) or [`NEWLINE`](https://docs.python.org/3/library/token.html#token.NEWLINE). *Syntactic* definitions then use these tokens, rather than source characters.

This documentation uses the same BNF grammar for both styles of definitions. All uses of BNF in the next chapter ([Lexical analysis](#lexical_analysis--lexical)) are lexical definitions; uses in subsequent chapters are syntactic definitions.

<span id="lexical_analysis--lexical"></span>

# 2. Lexical analysis {#lexical_analysis--lexical-analysis}

A Python program is read by a *parser*. Input to the parser is a stream of [tokens](https://docs.python.org/3/glossary.html#term-token), generated by the *lexical analyzer* (also known as the *tokenizer*). This chapter describes how the lexical analyzer produces these tokens.

The lexical analyzer determines the program text’s [encoding](#lexical_analysis--encodings) (UTF-8 by default), and decodes the text into [source characters](#lexical_analysis--lexical-source-character). If the text cannot be decoded, a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) is raised.

Next, the lexical analyzer uses the source characters to generate a stream of tokens. The type of a generated token generally depends on the next source character to be processed. Similarly, other special behavior of the analyzer depends on the first source character that hasn’t yet been processed. The following table gives a quick summary of these source characters, with links to sections that contain more information.

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr class="header">
<th><p>Character</p></th>
<th><p>Next token (or other relevant documentation)</p></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><ul>
<li><p>space</p></li>
<li><p>tab</p></li>
<li><p>formfeed</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--whitespace">Whitespace</a></p></li>
</ul></td>
</tr>
<tr class="even">
<td><ul>
<li><p>CR, LF</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--line-structure">New line</a></p></li>
<li><p><a href="#lexical_analysis--indentation">Indentation</a></p></li>
</ul></td>
</tr>
<tr class="odd">
<td><ul>
<li><p>backslash (<code>\</code>)</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--explicit-joining">Explicit line joining</a></p></li>
<li><p>(Also significant in <a href="#lexical_analysis--escape-sequences">string escape sequences</a>)</p></li>
</ul></td>
</tr>
<tr class="even">
<td><ul>
<li><p>hash (<code>#</code>)</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--comments">Comment</a></p></li>
</ul></td>
</tr>
<tr class="odd">
<td><ul>
<li><p>quote (<code>'</code>, <code>"</code>)</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--strings">String literal</a></p></li>
</ul></td>
</tr>
<tr class="even">
<td><ul>
<li><p>ASCII letter (<code>a</code>-<code>z</code>, <code>A</code>-<code>Z</code>)</p></li>
<li><p>non-ASCII character</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--identifiers">Name</a></p></li>
<li><p>Prefixed <a href="#lexical_analysis--strings">string or bytes literal</a></p></li>
</ul></td>
</tr>
<tr class="odd">
<td><ul>
<li><p>underscore (<code>_</code>)</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--identifiers">Name</a></p></li>
<li><p>(Can also be part of <a href="#lexical_analysis--numbers">numeric literals</a>)</p></li>
</ul></td>
</tr>
<tr class="even">
<td><ul>
<li><p>number (<code>0</code>-<code>9</code>)</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--numbers">Numeric literal</a></p></li>
</ul></td>
</tr>
<tr class="odd">
<td><ul>
<li><p>dot (<code>.</code>)</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--numbers">Numeric literal</a></p></li>
<li><p><a href="#lexical_analysis--operators">Operator</a></p></li>
</ul></td>
</tr>
<tr class="even">
<td><ul>
<li><p>question mark (<code>?</code>)</p></li>
<li><p>dollar (<code>$</code>)</p></li>
<li><p>backquote (<code>​`​</code>)</p></li>
<li><p>control character</p></li>
</ul></td>
<td><ul>
<li><p>Error (outside string literals and comments)</p></li>
</ul></td>
</tr>
<tr class="odd">
<td><ul>
<li><p>other printing character</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--operators">Operator or delimiter</a></p></li>
</ul></td>
</tr>
<tr class="even">
<td><ul>
<li><p>end of file</p></li>
</ul></td>
<td><ul>
<li><p><a href="#lexical_analysis--endmarker-token">End marker</a></p></li>
</ul></td>
</tr>
</tbody>
</table>

<span id="lexical_analysis--id1"></span>

## 2.1. Line structure {#lexical_analysis--line-structure}

A Python program is divided into a number of *logical lines*.

<span id="lexical_analysis--id2"></span>

### 2.1.1. Logical lines {#lexical_analysis--logical-lines}

The end of a logical line is represented by the token [`NEWLINE`](https://docs.python.org/3/library/token.html#token.NEWLINE). Statements cannot cross logical line boundaries except where `NEWLINE` is allowed by the syntax (e.g., between statements in compound statements). A logical line is constructed from one or more *physical lines* by following the [explicit](#lexical_analysis--explicit-joining) or [implicit](#lexical_analysis--implicit-joining) *line joining* rules.

<span id="lexical_analysis--id3"></span>

### 2.1.2. Physical lines {#lexical_analysis--physical-lines}

A physical line is a sequence of characters terminated by one the following end-of-line sequences:

- the Unix form using ASCII LF (linefeed),

- the Windows form using the ASCII sequence CR LF (return followed by linefeed),

- the ‘[Classic Mac OS](https://en.wikipedia.org/wiki/Classic_Mac_OS)’ form using the ASCII CR (return) character.

Regardless of platform, each of these sequences is replaced by a single ASCII LF (linefeed) character. (This is done even inside [string literals](#lexical_analysis--strings).) Each line can use any of the sequences; they do not need to be consistent within a file.

The end of input also serves as an implicit terminator for the final physical line.

Formally:

    newline: <ASCII LF> | <ASCII CR> <ASCII LF> | <ASCII CR>

<span id="lexical_analysis--id5"></span>

### 2.1.3. Comments {#lexical_analysis--comments}

A comment starts with a hash character (`#`) that is not part of a string literal, and ends at the end of the physical line. A comment signifies the end of the logical line unless the implicit line joining rules are invoked. Comments are ignored by the syntax.

<span id="lexical_analysis--encodings"></span>

### 2.1.4. Encoding declarations {#lexical_analysis--encoding-declarations}

If a comment in the first or second line of the Python script matches the regular expression `coding[=:]\s*([-\w.]+)`, this comment is processed as an encoding declaration; the first group of this expression names the encoding of the source code file. The encoding declaration must appear on a line of its own. If it is the second line, the first line must also be a comment-only line. The recommended forms of an encoding expression are

    # -*- coding: <encoding-name> -*-

which is recognized also by GNU Emacs, and

    # vim:fileencoding=<encoding-name>

which is recognized by Bram Moolenaar’s VIM.

If no encoding declaration is found, the default encoding is UTF-8. If the implicit or explicit encoding of a file is UTF-8, an initial UTF-8 byte-order mark (`b'\xef\xbb\xbf'`) is ignored rather than being a syntax error.

If an encoding is declared, the encoding name must be recognized by Python (see [Standard Encodings](https://docs.python.org/3/library/codecs.html#standard-encodings)). The encoding is used for all lexical analysis, including string literals, comments and identifiers.

All lexical analysis, including string literals, comments and identifiers, works on Unicode text decoded using the source encoding. Any Unicode code point, except the NUL control character, can appear in Python source.

    source_character:  <any Unicode code point, except NUL>

<span id="lexical_analysis--explicit-joining"></span>

### 2.1.5. Explicit line joining {#lexical_analysis--explicit-line-joining}

Two or more physical lines may be joined into logical lines using backslash characters (`\`), as follows: when a physical line ends in a backslash that is not part of a string literal or comment, it is joined with the following forming a single logical line, deleting the backslash and the following end-of-line character. For example:

    if 1900 < year < 2100 and 1 <= month <= 12 \
       and 1 <= day <= 31 and 0 <= hour < 24 \
       and 0 <= minute < 60 and 0 <= second < 60:   # Looks like a valid date
            return 1

A line ending in a backslash cannot carry a comment. A backslash does not continue a comment. A backslash does not continue a token except for string literals (i.e., tokens other than string literals cannot be split across physical lines using a backslash). A backslash is illegal elsewhere on a line outside a string literal.

<span id="lexical_analysis--implicit-joining"></span>

### 2.1.6. Implicit line joining {#lexical_analysis--implicit-line-joining}

Expressions in parentheses, square brackets or curly braces can be split over more than one physical line without using backslashes. For example:

    month_names = ['Januari', 'Februari', 'Maart',      # These are the
                   'April',   'Mei',      'Juni',       # Dutch names
                   'Juli',    'Augustus', 'September',  # for the months
                   'Oktober', 'November', 'December']   # of the year

Implicitly continued lines can carry comments. The indentation of the continuation lines is not important. Blank continuation lines are allowed. There is no NEWLINE token between implicit continuation lines. Implicitly continued lines can also occur within triple-quoted strings (see below); in that case they cannot carry comments.

<span id="lexical_analysis--id6"></span>

### 2.1.7. Blank lines {#lexical_analysis--blank-lines}

A logical line that contains only spaces, tabs, formfeeds and possibly a comment, is ignored (i.e., no [`NEWLINE`](https://docs.python.org/3/library/token.html#token.NEWLINE) token is generated). During interactive input of statements, handling of a blank line may differ depending on the implementation of the read-eval-print loop. In the standard interactive interpreter, an entirely blank logical line (that is, one containing not even whitespace or a comment) terminates a multi-line statement.

<span id="lexical_analysis--id7"></span>

### 2.1.8. Indentation {#lexical_analysis--indentation}

Leading whitespace (spaces and tabs) at the beginning of a logical line is used to compute the indentation level of the line, which in turn is used to determine the grouping of statements.

Tabs are replaced (from left to right) by one to eight spaces such that the total number of characters up to and including the replacement is a multiple of eight (this is intended to be the same rule as used by Unix). The total number of spaces preceding the first non-blank character then determines the line’s indentation. Indentation cannot be split over multiple physical lines using backslashes; the whitespace up to the first backslash determines the indentation.

Indentation is rejected as inconsistent if a source file mixes tabs and spaces in a way that makes the meaning dependent on the worth of a tab in spaces; a [`TabError`](https://docs.python.org/3/library/exceptions.html#TabError) is raised in that case.

**Cross-platform compatibility note:** because of the nature of text editors on non-UNIX platforms, it is unwise to use a mixture of spaces and tabs for the indentation in a single source file. It should also be noted that different platforms may explicitly limit the maximum indentation level.

A formfeed character may be present at the start of the line; it will be ignored for the indentation calculations above. Formfeed characters occurring elsewhere in the leading whitespace have an undefined effect (for instance, they may reset the space count to zero).

The indentation levels of consecutive lines are used to generate [`INDENT`](https://docs.python.org/3/library/token.html#token.INDENT) and [`DEDENT`](https://docs.python.org/3/library/token.html#token.DEDENT) tokens, using a stack, as follows.

Before the first line of the file is read, a single zero is pushed on the stack; this will never be popped off again. The numbers pushed on the stack will always be strictly increasing from bottom to top. At the beginning of each logical line, the line’s indentation level is compared to the top of the stack. If it is equal, nothing happens. If it is larger, it is pushed on the stack, and one `INDENT` token is generated. If it is smaller, it *must* be one of the numbers occurring on the stack; all numbers on the stack that are larger are popped off, and for each number popped off a `DEDENT` token is generated. At the end of the file, a `DEDENT` token is generated for each number remaining on the stack that is larger than zero.

Here is an example of a correctly (though confusingly) indented piece of Python code:

    def perm(l):
            # Compute the list of all permutations of l
        if len(l) <= 1:
                      return [l]
        r = []
        for i in range(len(l)):
                 s = l[:i] + l[i+1:]
                 p = perm(s)
                 for x in p:
                  r.append(l[i:i+1] + x)
        return r

The following example shows various indentation errors:

     def perm(l):                       # error: first line indented
    for i in range(len(l)):             # error: not indented
        s = l[:i] + l[i+1:]
            p = perm(l[:i] + l[i+1:])   # error: unexpected indent
            for x in p:
                    r.append(l[i:i+1] + x)
                return r                # error: inconsistent dedent

(Actually, the first three errors are detected by the parser; only the last error is found by the lexical analyzer — the indentation of `return r` does not match a level popped off the stack.)

<span id="lexical_analysis--whitespace"></span>

### 2.1.9. Whitespace between tokens {#lexical_analysis--whitespace-between-tokens}

Except at the beginning of a logical line or in string literals, the whitespace characters space, tab and formfeed can be used interchangeably to separate tokens:

    whitespace:  ' ' | tab | formfeed

Whitespace is needed between two tokens only if their concatenation could otherwise be interpreted as a different token. For example, `ab` is one token, but `a b` is two tokens. However, `+a` and `+ a` both produce two tokens, `+` and `a`, as `+a` is not a valid token.

<span id="lexical_analysis--endmarker-token"></span>

### 2.1.10. End marker {#lexical_analysis--end-marker}

At the end of non-interactive input, the lexical analyzer generates an [`ENDMARKER`](https://docs.python.org/3/library/token.html#token.ENDMARKER) token.

<span id="lexical_analysis--id8"></span>

## 2.2. Other tokens {#lexical_analysis--other-tokens}

Besides [`NEWLINE`](https://docs.python.org/3/library/token.html#token.NEWLINE), [`INDENT`](https://docs.python.org/3/library/token.html#token.INDENT) and [`DEDENT`](https://docs.python.org/3/library/token.html#token.DEDENT), the following categories of tokens exist: *identifiers* and *keywords* ([`NAME`](https://docs.python.org/3/library/token.html#token.NAME)), *literals* (such as [`NUMBER`](https://docs.python.org/3/library/token.html#token.NUMBER) and [`STRING`](https://docs.python.org/3/library/token.html#token.STRING)), and other symbols (*operators* and *delimiters*, [`OP`](https://docs.python.org/3/library/token.html#token.OP)). Whitespace characters (other than logical line terminators, discussed earlier) are not tokens, but serve to delimit tokens. Where ambiguity exists, a token comprises the longest possible string that forms a legal token, when read from left to right.

<span id="lexical_analysis--identifiers"></span>

## 2.3. Names (identifiers and keywords) {#lexical_analysis--names-identifiers-and-keywords}

[`NAME`](https://docs.python.org/3/library/token.html#token.NAME) tokens represent *identifiers*, *keywords*, and *soft keywords*.

Names are composed of the following characters:

- uppercase and lowercase letters (`A-Z` and `a-z`),

- the underscore (`_`),

- digits (`0` through `9`), which cannot appear as the first character, and

- non-ASCII characters. Valid names may only contain “letter-like” and “digit-like” characters; see [Non-ASCII characters in names](#lexical_analysis--lexical-names-nonascii) for details.

Names must contain at least one character, but have no upper length limit. Case is significant.

Formally, names are described by the following lexical definitions:

    NAME:          name_start name_continue*
    name_start:    "a"..."z" | "A"..."Z" | "_" | <non-ASCII character>
    name_continue: name_start | "0"..."9"
    identifier:    <NAME, except keywords>

Note that not all names matched by this grammar are valid; see [Non-ASCII characters in names](#lexical_analysis--lexical-names-nonascii) for details.

<span id="lexical_analysis--id9"></span>

### 2.3.1. Keywords {#lexical_analysis--keywords}

The following names are used as reserved words, or *keywords* of the language, and cannot be used as ordinary identifiers. They must be spelled exactly as written here:

    False      await      else       import     pass
    None       break      except     in         raise
    True       class      finally    is         return
    and        continue   for        lambda     try
    as         def        from       nonlocal   while
    assert     del        global     not        with
    async      elif       if         or         yield

<span id="lexical_analysis--id10"></span>

### 2.3.2. Soft Keywords {#lexical_analysis--soft-keywords}

Added in version 3.10.

Some names are only reserved under specific contexts. These are known as *soft keywords*:

- `match`, `case`, and `_`, when used in the [`match`](#compound_stmts--match) statement.

- `type`, when used in the [`type`](#simple_stmts--type) statement.

These syntactically act as keywords in their specific contexts, but this distinction is done at the parser level, not when tokenizing.

As soft keywords, their use in the grammar is possible while still preserving compatibility with existing code that uses these names as identifier names.

Changed in version 3.12: `type` is now a soft keyword.

<span id="lexical_analysis--id-classes"></span> <span id="lexical_analysis--index-12"></span>

### 2.3.3. Reserved classes of identifiers {#lexical_analysis--reserved-classes-of-identifiers}

Certain classes of identifiers (besides keywords) have special meanings. These classes are identified by the patterns of leading and trailing underscore characters:

`_*`  
Not imported by `from module import *`.

`_`  
In a `case` pattern within a [`match`](#compound_stmts--match) statement, `_` is a [soft keyword](#lexical_analysis--soft-keywords) that denotes a [wildcard](#compound_stmts--wildcard-patterns).

Separately, the interactive interpreter makes the result of the last evaluation available in the variable `_`. (It is stored in the [`builtins`](https://docs.python.org/3/library/builtins.html#module-builtins) module, alongside built-in functions like `print`.)

Elsewhere, `_` is a regular identifier. It is often used to name “special” items, but it is not special to Python itself.

Note

The name `_` is often used in conjunction with internationalization; refer to the documentation for the [`gettext`](https://docs.python.org/3/library/gettext.html#module-gettext) module for more information on this convention.

It is also commonly used for unused variables.

`__*__`  
System-defined names, informally known as “dunder” names. These names are defined by the interpreter and its implementation (including the standard library). Current system names are discussed in the [Special method names](#datamodel--specialnames) section and elsewhere. More will likely be defined in future versions of Python. *Any* use of `__*__` names, in any context, that does not follow explicitly documented use, is subject to breakage without warning.

`__*`  
Class-private names. Names in this category, when used within the context of a class definition, are re-written to use a mangled form to help avoid name clashes between “private” attributes of base and derived classes. See section [Identifiers (Names)](#expressions--atom-identifiers).

<span id="lexical_analysis--lexical-names-nonascii"></span>

### 2.3.4. Non-ASCII characters in names {#lexical_analysis--non-ascii-characters-in-names}

Names that contain non-ASCII characters need additional normalization and validation beyond the rules and grammar explained [above](#lexical_analysis--identifiers). For example, `ř_1`, `蛇`, or `साँप` are valid names, but `r〰2`, `€`, or `🐍` are not.

This section explains the exact rules.

All names are converted into the [normalization form](https://www.unicode.org/reports/tr15/#Norm_Forms) NFKC while parsing. This means that, for example, some typographic variants of characters are converted to their “basic” form. For example, `ﬁⁿₐˡᵢᶻₐᵗᵢᵒₙ` normalizes to `finalization`, so Python treats them as the same name:

    >>> ﬁⁿₐˡᵢᶻₐᵗᵢᵒₙ = 3
    >>> finalization
    3

Note

Normalization is done at the lexical level only. Run-time functions that take names as *strings* generally do not normalize their arguments. For example, the variable defined above is accessible at run time in the [`globals()`](https://docs.python.org/3/library/functions.html#globals) dictionary as `globals()["finalization"]` but not `globals()["ﬁⁿₐˡᵢᶻₐᵗᵢᵒₙ"]`.

Similarly to how ASCII-only names must contain only letters, digits and the underscore, and cannot start with a digit, a valid name must start with a character in the “letter-like” set `xid_start`, and the remaining characters must be in the “letter- and digit-like” set `xid_continue`.

These sets are based on the *XID_Start* and *XID_Continue* sets as defined by the Unicode standard annex [UAX-31](https://www.unicode.org/reports/tr31/). Python’s `xid_start` additionally includes the underscore (`_`). Note that Python does not necessarily conform to [UAX-31](https://www.unicode.org/reports/tr31/).

A non-normative listing of characters in the *XID_Start* and *XID_Continue* sets as defined by Unicode is available in the [DerivedCoreProperties.txt](https://www.unicode.org/Public/16.0.0/ucd/DerivedCoreProperties.txt) file in the Unicode Character Database. For reference, the construction rules for the `xid_*` sets are given below.

The set `id_start` is defined as the union of:

- Unicode category `<Lu>` - uppercase letters (includes `A` to `Z`)

- Unicode category `<Ll>` - lowercase letters (includes `a` to `z`)

- Unicode category `<Lt>` - titlecase letters

- Unicode category `<Lm>` - modifier letters

- Unicode category `<Lo>` - other letters

- Unicode category `<Nl>` - letter numbers

- {`"_"`} - the underscore

- `<Other_ID_Start>` - an explicit set of characters in [PropList.txt](https://www.unicode.org/Public/16.0.0/ucd/PropList.txt) to support backwards compatibility

The set `xid_start` then closes this set under NFKC normalization, by removing all characters whose normalization is not of the form `id_start id_continue*`.

The set `id_continue` is defined as the union of:

- `id_start` (see above)

- Unicode category `<Nd>` - decimal numbers (includes `0` to `9`)

- Unicode category `<Pc>` - connector punctuations

- Unicode category `<Mn>` - nonspacing marks

- Unicode category `<Mc>` - spacing combining marks

- `<Other_ID_Continue>` - another explicit set of characters in [PropList.txt](https://www.unicode.org/Public/16.0.0/ucd/PropList.txt) to support backwards compatibility

Again, `xid_continue` closes this set under NFKC normalization.

Unicode categories use the version of the Unicode Character Database as included in the [`unicodedata`](https://docs.python.org/3/library/unicodedata.html#module-unicodedata) module.

See also

- <span id="lexical_analysis--index-13"></span>[**PEP 3131**](https://peps.python.org/pep-3131/) – Supporting Non-ASCII Identifiers

- <span id="lexical_analysis--index-14"></span>[**PEP 672**](https://peps.python.org/pep-0672/) – Unicode-related Security Considerations for Python

<span id="lexical_analysis--id11"></span>

## 2.4. Literals {#lexical_analysis--literals}

Literals are notations for constant values of some built-in types.

In terms of lexical analysis, Python has [string, bytes](#lexical_analysis--strings) and [numeric](#lexical_analysis--numbers) literals.

Other “literals” are lexically denoted using [keywords](#lexical_analysis--keywords) (`None`, `True`, `False`) and the special [ellipsis token](#lexical_analysis--lexical-ellipsis) (`...`).

<span id="lexical_analysis--strings"></span> <span id="lexical_analysis--index-16"></span>

## 2.5. String and Bytes literals {#lexical_analysis--string-and-bytes-literals}

String literals are text enclosed in single quotes (`'`) or double quotes (`"`). For example:

    "spam"
    'eggs'

The quote used to start the literal also terminates it, so a string literal can only contain the other quote (except with escape sequences, see below). For example:

    'Say "Hello", please.'
    "Don't do that!"

Except for this limitation, the choice of quote character (`'` or `"`) does not affect how the literal is parsed.

Inside a string literal, the backslash (`\`) character introduces an *escape sequence*, which has special meaning depending on the character after the backslash. For example, `\"` denotes the double quote character, and does *not* end the string:

    >>> print("Say \"Hello\" to everyone!")
    Say "Hello" to everyone!

See [escape sequences](#lexical_analysis--escape-sequences) below for a full list of such sequences, and more details.

<span id="lexical_analysis--index-17"></span>

### 2.5.1. Triple-quoted strings {#lexical_analysis--triple-quoted-strings}

Strings can also be enclosed in matching groups of three single or double quotes. These are generally referred to as *triple-quoted strings*:

    """This is a triple-quoted string."""

In triple-quoted literals, unescaped quotes are allowed (and are retained), except that three unescaped quotes in a row terminate the literal, if they are of the same kind (`'` or `"`) used at the start:

    """This string has "quotes" inside."""

Unescaped newlines are also allowed and retained:

    '''This triple-quoted string
    continues on the next line.'''

<span id="lexical_analysis--index-18"></span>

### 2.5.2. String prefixes {#lexical_analysis--string-prefixes}

String literals can have an optional *prefix* that influences how the content of the literal is parsed, for example:

    b"data"
    f'{result=}'

The allowed prefixes are:

- `b`: [Bytes literal](#lexical_analysis--bytes-literal)

- `r`: [Raw string](#lexical_analysis--raw-strings)

- `f`: [Formatted string literal](#lexical_analysis--f-strings) (“f-string”)

- `t`: [Template string literal](#lexical_analysis--t-strings) (“t-string”)

- `u`: No effect (allowed for backwards compatibility)

See the linked sections for details on each type.

Prefixes are case-insensitive (for example, ‘`B`’ works the same as ‘`b`’). The ‘`r`’ prefix can be combined with ‘`f`’, ‘`t`’ or ‘`b`’, so ‘`fr`’, ‘`rf`’, ‘`tr`’, ‘`rt`’, ‘`br`’, and ‘`rb`’ are also valid prefixes.

Added in version 3.3: The `'rb'` prefix of raw bytes literals has been added as a synonym of `'br'`.

Support for the unicode legacy literal (`u'value'`) was reintroduced to simplify the maintenance of dual Python 2.x and 3.x codebases. See <span id="lexical_analysis--index-19"></span>[**PEP 414**](https://peps.python.org/pep-0414/) for more information.

### 2.5.3. Formal grammar {#lexical_analysis--formal-grammar}

String literals, except [“f-strings”](#lexical_analysis--f-strings) and [“t-strings”](#lexical_analysis--t-strings), are described by the following lexical definitions.

These definitions use [negative lookaheads](#introduction--lexical-lookaheads) (`!`) to indicate that an ending quote ends the literal.

    STRING:          [stringprefix] (stringcontent)
    stringprefix:    <("r" | "u" | "b" | "br" | "rb"), case-insensitive>
    stringcontent:
       | "'''" ( !"'''" longstringitem)* "'''"
       | '"""' ( !'"""' longstringitem)* '"""'
       | "'" ( !"'" stringitem)* "'"
       | '"' ( !'"' stringitem)* '"'
    stringitem:      stringchar | stringescapeseq
    stringchar:      <any source_character, except backslash and newline>
    longstringitem:  stringitem | newline
    stringescapeseq: "\" <any source_character>

Note that as in all lexical definitions, whitespace is significant. In particular, the prefix (if any) must be immediately followed by the starting quote.

<span id="lexical_analysis--index-20"></span> <span id="lexical_analysis--id12"></span>

### 2.5.4. Escape sequences {#lexical_analysis--escape-sequences}

Unless an ‘`r`’ or ‘`R`’ prefix is present, escape sequences in string and bytes literals are interpreted according to rules similar to those used by Standard C. The recognized escape sequences are:

| Escape Sequence  | Meaning                                                                    |
|------------------|----------------------------------------------------------------------------|
| `\`\<newline\>   | [Ignored end of line](#lexical_analysis--string-escape-ignore)             |
| `\\`             | [Backslash](#lexical_analysis--string-escape-escaped-char)                 |
| `\'`             | [Single quote](#lexical_analysis--string-escape-escaped-char)              |
| `\"`             | [Double quote](#lexical_analysis--string-escape-escaped-char)              |
| `\a`             | ASCII Bell (BEL)                                                           |
| `\b`             | ASCII Backspace (BS)                                                       |
| `\f`             | ASCII Formfeed (FF)                                                        |
| `\n`             | ASCII Linefeed (LF)                                                        |
| `\r`             | ASCII Carriage Return (CR)                                                 |
| `\t`             | ASCII Horizontal Tab (TAB)                                                 |
| `\v`             | ASCII Vertical Tab (VT)                                                    |
| `\`*`ooo`*       | [Octal character](#lexical_analysis--string-escape-oct)                    |
| `\x`*`hh`*       | [Hexadecimal character](#lexical_analysis--string-escape-hex)              |
| `\N{`*`name`*`}` | [Named Unicode character](#lexical_analysis--string-escape-named)          |
| `\u`*`xxxx`*     | [Hexadecimal Unicode character](#lexical_analysis--string-escape-long-hex) |
| `\U`*`xxxxxxxx`* | [Hexadecimal Unicode character](#lexical_analysis--string-escape-long-hex) |

<span id="lexical_analysis--string-escape-ignore"></span>

#### 2.5.4.1. Ignored end of line {#lexical_analysis--ignored-end-of-line}

A backslash can be added at the end of a line to ignore the newline:

    >>> 'This string will not include \
    ... backslashes or newline characters.'
    'This string will not include backslashes or newline characters.'

The same result can be achieved using [triple-quoted strings](#lexical_analysis--strings), or parentheses and [string literal concatenation](#expressions--string-concatenation).

<span id="lexical_analysis--string-escape-escaped-char"></span>

#### 2.5.4.2. Escaped characters {#lexical_analysis--escaped-characters}

To include a backslash in a non-[raw](#lexical_analysis--raw-strings) Python string literal, it must be doubled. The `\\` escape sequence denotes a single backslash character:

    >>> print('C:\\Program Files')
    C:\Program Files

Similarly, the `\'` and `\"` sequences denote the single and double quote character, respectively:

    >>> print('\' and \"')
    ' and "

<span id="lexical_analysis--string-escape-oct"></span>

#### 2.5.4.3. Octal character {#lexical_analysis--octal-character}

The sequence `\`*`ooo`* denotes a *character* with the octal (base 8) value *ooo*:

    >>> '\120'
    'P'

Up to three octal digits (0 through 7) are accepted.

In a bytes literal, *character* means a *byte* with the given value. In a string literal, it means a Unicode character with the given value.

Changed in version 3.11: Octal escapes with value larger than `0o377` (255) produce a [`DeprecationWarning`](https://docs.python.org/3/library/exceptions.html#DeprecationWarning).

Changed in version 3.12: Octal escapes with value larger than `0o377` (255) produce a [`SyntaxWarning`](https://docs.python.org/3/library/exceptions.html#SyntaxWarning). In a future Python version they will raise a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError).

<span id="lexical_analysis--string-escape-hex"></span>

#### 2.5.4.4. Hexadecimal character {#lexical_analysis--hexadecimal-character}

The sequence `\x`*`hh`* denotes a *character* with the hex (base 16) value *hh*:

    >>> '\x50'
    'P'

Unlike in Standard C, exactly two hex digits are required.

In a bytes literal, *character* means a *byte* with the given value. In a string literal, it means a Unicode character with the given value.

<span id="lexical_analysis--string-escape-named"></span>

#### 2.5.4.5. Named Unicode character {#lexical_analysis--named-unicode-character}

The sequence `\N{`*`name`*`}` denotes a Unicode character with the given *name*:

    >>> '\N{LATIN CAPITAL LETTER P}'
    'P'
    >>> '\N{SNAKE}'
    '🐍'

This sequence cannot appear in [bytes literals](#lexical_analysis--bytes-literal).

Changed in version 3.3: Support for [name aliases](https://www.unicode.org/Public/16.0.0/ucd/NameAliases.txt) has been added.

<span id="lexical_analysis--string-escape-long-hex"></span>

#### 2.5.4.6. Hexadecimal Unicode characters {#lexical_analysis--hexadecimal-unicode-characters}

These sequences `\u`*`xxxx`* and `\U`*`xxxxxxxx`* denote the Unicode character with the given hex (base 16) value. Exactly four digits are required for `\u`; exactly eight digits are required for `\U`. The latter can encode any Unicode character.

    >>> '\u1234'
    'ሴ'
    >>> '\U0001f40d'
    '🐍'

These sequences cannot appear in [bytes literals](#lexical_analysis--bytes-literal).

<span id="lexical_analysis--index-21"></span>

#### 2.5.4.7. Unrecognized escape sequences {#lexical_analysis--unrecognized-escape-sequences}

Unlike in Standard C, all unrecognized escape sequences are left in the string unchanged, that is, *the backslash is left in the result*:

    >>> print('\q')
    \q
    >>> list('\q')
    ['\\', 'q']

Note that for bytes literals, the escape sequences only recognized in string literals (`\N...`, `\u...`, `\U...`) fall into the category of unrecognized escapes.

Changed in version 3.6: Unrecognized escape sequences produce a [`DeprecationWarning`](https://docs.python.org/3/library/exceptions.html#DeprecationWarning).

Changed in version 3.12: Unrecognized escape sequences produce a [`SyntaxWarning`](https://docs.python.org/3/library/exceptions.html#SyntaxWarning). In a future Python version they will raise a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError).

<span id="lexical_analysis--bytes-literal"></span> <span id="lexical_analysis--index-22"></span>

### 2.5.5. Bytes literals {#lexical_analysis--bytes-literals}

*Bytes literals* are always prefixed with ‘`b`’ or ‘`B`’; they produce an instance of the [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes) type instead of the [`str`](https://docs.python.org/3/library/stdtypes.html#str) type. They may only contain ASCII characters; bytes with a numeric value of 128 or greater must be expressed with escape sequences (typically [Hexadecimal character](#lexical_analysis--string-escape-hex) or [Octal character](#lexical_analysis--string-escape-oct)):

    >>> b'\x89PNG\r\n\x1a\n'
    b'\x89PNG\r\n\x1a\n'
    >>> list(b'\x89PNG\r\n\x1a\n')
    [137, 80, 78, 71, 13, 10, 26, 10]

Similarly, a zero byte must be expressed using an escape sequence (typically `\0` or `\x00`).

<span id="lexical_analysis--raw-strings"></span> <span id="lexical_analysis--index-23"></span>

### 2.5.6. Raw string literals {#lexical_analysis--raw-string-literals}

Both string and bytes literals may optionally be prefixed with a letter ‘`r`’ or ‘`R`’; such constructs are called *raw string literals* and *raw bytes literals* respectively and treat backslashes as literal characters. As a result, in raw string literals, [escape sequences](#lexical_analysis--escape-sequences) are not treated specially:

    >>> r'\d{4}-\d{2}-\d{2}'
    '\\d{4}-\\d{2}-\\d{2}'

Even in a raw literal, quotes can be escaped with a backslash, but the backslash remains in the result; for example, `r"\""` is a valid string literal consisting of two characters: a backslash and a double quote; `r"\"` is not a valid string literal (even a raw string cannot end in an odd number of backslashes). Specifically, *a raw literal cannot end in a single backslash* (since the backslash would escape the following quote character). Note also that a single backslash followed by a newline is interpreted as those two characters as part of the literal, *not* as a line continuation.

<span id="lexical_analysis--f-strings"></span> <span id="lexical_analysis--index-24"></span> <span id="lexical_analysis--id13"></span>

### 2.5.7. f-strings {#lexical_analysis--formatted-string-literals}

Added in version 3.6.

Changed in version 3.7: The [`await`](#expressions--await) and [`async for`](#compound_stmts--async-for) can be used in expressions within f-strings.

Changed in version 3.8: Added the debug specifier (`=`)

Changed in version 3.12: Many restrictions on expressions within f-strings have been removed. Notably, nested strings, comments, and backslashes are now permitted.

A *formatted string literal* or *f-string* is a string literal that is prefixed with ‘`f`’ or ‘`F`’. Unlike other string literals, f-strings do not have a constant value. They may contain *replacement fields* delimited by curly braces `{}`. Replacement fields contain expressions which are evaluated at run time. For example:

    >>> who = 'nobody'
    >>> nationality = 'Spanish'
    >>> f'{who.title()} expects the {nationality} Inquisition!'
    'Nobody expects the Spanish Inquisition!'

Any doubled curly braces (`{{` or `}}`) outside replacement fields are replaced with the corresponding single curly brace:

    >>> print(f'{{...}}')
    {...}

Other characters outside replacement fields are treated like in ordinary string literals. This means that escape sequences are decoded (except when a literal is also marked as a raw string), and newlines are possible in triple-quoted f-strings:

    >>> name = 'Galahad'
    >>> favorite_color = 'blue'
    >>> print(f'{name}:\t{favorite_color}')
    Galahad:       blue
    >>> print(rf"C:\Users\{name}")
    C:\Users\Galahad
    >>> print(f'''Three shall be the number of the counting
    ... and the number of the counting shall be three.''')
    Three shall be the number of the counting
    and the number of the counting shall be three.

Expressions in formatted string literals are treated like regular Python expressions. Each expression is evaluated in the context where the formatted string literal appears, in order from left to right. An empty expression is not allowed, and both [`lambda`](#expressions--lambda) and assignment expressions `:=` must be surrounded by explicit parentheses:

    >>> f'{(half := 1/2)}, {half * 42}'
    '0.5, 21.0'

Reusing the outer f-string quoting type inside a replacement field is permitted:

    >>> a = dict(x=2)
    >>> f"abc {a["x"]} def"
    'abc 2 def'

Backslashes are also allowed in replacement fields and are evaluated the same way as in any other context:

    >>> a = ["a", "b", "c"]
    >>> print(f"List a contains:\n{"\n".join(a)}")
    List a contains:
    a
    b
    c

It is possible to nest f-strings:

    >>> name = 'world'
    >>> f'Repeated:{f' hello {name}' * 3}'
    'Repeated: hello world hello world hello world'

Portable Python programs should not use more than 5 levels of nesting.

**CPython implementation detail:** CPython does not limit nesting of f-strings.

Replacement expressions can contain newlines in both single-quoted and triple-quoted f-strings and they can contain comments. Everything that comes after a `#` inside a replacement field is a comment (even closing braces and quotes). This means that replacement fields with comments must be closed in a different line:

    >>> a = 2
    >>> f"abc{a  # This comment  }"  continues until the end of the line
    ...       + 3}"
    'abc5'

After the expression, replacement fields may optionally contain:

- a *debug specifier* – an equal sign (`=`), optionally surrounded by whitespace on one or both sides;

- a *conversion specifier* – `!s`, `!r` or `!a`; and/or

- a *format specifier* prefixed with a colon (`:`).

See the [Standard Library section on f-strings](https://docs.python.org/3/library/stdtypes.html#stdtypes-fstrings) for details on how these fields are evaluated.

As that section explains, *format specifiers* are passed as the second argument to the [`format()`](https://docs.python.org/3/library/functions.html#format) function to format a replacement field value. For example, they can be used to specify a field width and padding characters using the [Format Specification Mini-Language](https://docs.python.org/3/library/string.html#formatspec):

    >>> number = 14.3
    >>> f'{number:20.7f}'
    '          14.3000000'

Top-level format specifiers may include nested replacement fields:

    >>> field_size = 20
    >>> precision = 7
    >>> f'{number:{field_size}.{precision}f}'
    '          14.3000000'

These nested fields may include their own conversion fields and [format specifiers](https://docs.python.org/3/library/string.html#formatspec):

    >>> number = 3
    >>> f'{number:{field_size}}'
    '                   3'
    >>> f'{number:{field_size:05}}'
    '00000000000000000003'

However, these nested fields may not include more deeply nested replacement fields.

Formatted string literals cannot be used as [docstrings](https://docs.python.org/3/glossary.html#term-docstring), even if they do not include expressions:

    >>> def foo():
    ...     f"Not a docstring"
    ...
    >>> print(foo.__doc__)
    None

See also

- <span id="lexical_analysis--index-25"></span>[**PEP 498**](https://peps.python.org/pep-0498/) – Literal String Interpolation

- <span id="lexical_analysis--index-26"></span>[**PEP 701**](https://peps.python.org/pep-0701/) – Syntactic formalization of f-strings

- [`str.format()`](https://docs.python.org/3/library/stdtypes.html#str.format), which uses a related format string mechanism.

<span id="lexical_analysis--t-strings"></span> <span id="lexical_analysis--id14"></span>

### 2.5.8. t-strings {#lexical_analysis--template-string-literals}

Added in version 3.14.

A *template string literal* or *t-string* is a string literal that is prefixed with ‘`t`’ or ‘`T`’. These strings follow the same syntax rules as [formatted string literals](#lexical_analysis--f-strings). For differences in evaluation rules, see the [Standard Library section on t-strings](https://docs.python.org/3/library/stdtypes.html#stdtypes-tstrings)

### 2.5.9. Formal grammar for f-strings {#lexical_analysis--formal-grammar-for-f-strings}

F-strings are handled partly by the [lexical analyzer](https://docs.python.org/3/glossary.html#term-lexical-analyzer), which produces the tokens [`FSTRING_START`](https://docs.python.org/3/library/token.html#token.FSTRING_START), [`FSTRING_MIDDLE`](https://docs.python.org/3/library/token.html#token.FSTRING_MIDDLE) and [`FSTRING_END`](https://docs.python.org/3/library/token.html#token.FSTRING_END), and partly by the parser, which handles expressions in the replacement field. The exact way the work is split is a CPython implementation detail.

Correspondingly, the f-string grammar is a mix of [lexical and syntactic definitions](#introduction--notation-lexical-vs-syntactic).

Whitespace is significant in these situations:

- There may be no whitespace in [`FSTRING_START`](https://docs.python.org/3/library/token.html#token.FSTRING_START) (between the prefix and quote).

- Whitespace in [`FSTRING_MIDDLE`](https://docs.python.org/3/library/token.html#token.FSTRING_MIDDLE) is part of the literal string contents.

- In `fstring_replacement_field`, if `f_debug_specifier` is present, all whitespace after the opening brace until the `f_debug_specifier`, as well as whitespace immediately following `f_debug_specifier`, is retained as part of the expression.

  **CPython implementation detail:** The expression is not handled in the tokenization phase; it is retrieved from the source code using locations of the `{` token and the token after `=`.

The `FSTRING_MIDDLE` definition uses [negative lookaheads](#introduction--lexical-lookaheads) (`!`) to indicate special characters (backslash, newline, `{`, `}`) and sequences (`f_quote`).

    fstring:    FSTRING_START fstring_middle* FSTRING_END

    FSTRING_START:      fstringprefix ("'" | '"' | "'''" | '"""')
    FSTRING_END:        f_quote
    fstringprefix:      <("f" | "fr" | "rf"), case-insensitive>
    f_debug_specifier:  '='
    f_quote:            <the quote character(s) used in FSTRING_START>

    fstring_middle:
       | fstring_replacement_field
       | FSTRING_MIDDLE
    FSTRING_MIDDLE:
       | (!"\" !newline !'{' !'}' !f_quote) source_character
       | stringescapeseq
       | "{{"
       | "}}"
       | <newline, in triple-quoted f-strings only>
    fstring_replacement_field:
       | '{' f_expression [f_debug_specifier] [fstring_conversion]
             [fstring_full_format_spec] '}'
    fstring_conversion:
       | "!" ("s" | "r" | "a")
    fstring_full_format_spec:
       | ':' fstring_format_spec*
    fstring_format_spec:
       | FSTRING_MIDDLE
       | fstring_replacement_field
    f_expression:
       | ','.(conditional_expression | "*" or_expr)+ [","]
       | yield_expression

Note

In the above grammar snippet, the `f_quote` and `FSTRING_MIDDLE` rules are context-sensitive – they depend on the contents of `FSTRING_START` of the nearest enclosing `fstring`.

Constructing a more traditional formal grammar from this template is left as an exercise for the reader.

The grammar for t-strings is identical to the one for f-strings, with *t* instead of *f* at the beginning of rule and token names and in the prefix.

    tstring:    TSTRING_START tstring_middle* TSTRING_END

    <rest of the t-string grammar is omitted; see above>

<span id="lexical_analysis--numbers"></span>

## 2.6. Numeric literals {#lexical_analysis--numeric-literals}

[`NUMBER`](https://docs.python.org/3/library/token.html#token.NUMBER) tokens represent numeric literals, of which there are three types: integers, floating-point numbers, and imaginary numbers.

    NUMBER: integer | floatnumber | imagnumber

The numeric value of a numeric literal is the same as if it were passed as a string to the [`int`](https://docs.python.org/3/library/functions.html#int), [`float`](https://docs.python.org/3/library/functions.html#float) or [`complex`](https://docs.python.org/3/library/functions.html#complex) class constructor, respectively. Note that not all valid inputs for those constructors are also valid literals.

Numeric literals do not include a sign; a phrase like `-1` is actually an expression composed of the unary operator ‘`-`’ and the literal `1`.

<span id="lexical_analysis--integers"></span> <span id="lexical_analysis--index-28"></span>

### 2.6.1. Integer literals {#lexical_analysis--integer-literals}

Integer literals denote whole numbers. For example:

    7
    3
    2147483647

There is no limit for the length of integer literals apart from what can be stored in available memory:

    7922816251426433759354395033679228162514264337593543950336

Underscores can be used to group digits for enhanced readability, and are ignored for determining the numeric value of the literal. For example, the following literals are equivalent:

    100_000_000_000
    100000000000
    1_00_00_00_00_000

Underscores can only occur between digits. For example, `_123`, `321_`, and `123__321` are *not* valid literals.

Integers can be specified in binary (base 2), octal (base 8), or hexadecimal (base 16) using the prefixes `0b`, `0o` and `0x`, respectively. Hexadecimal digits 10 through 15 are represented by letters `A`-`F`, case-insensitive. For example:

    0b100110111
    0b_1110_0101
    0o177
    0o377
    0xdeadbeef
    0xDead_Beef

An underscore can follow the base specifier. For example, `0x_1f` is a valid literal, but `0_x1f` and `0x__1f` are not.

Leading zeros in a non-zero decimal number are not allowed. For example, `0123` is not a valid literal. This is for disambiguation with C-style octal literals, which Python used before version 3.0.

Formally, integer literals are described by the following lexical definitions:

    integer:      decinteger | bininteger | octinteger | hexinteger | zerointeger
    decinteger:   nonzerodigit (["_"] digit)*
    bininteger:   "0" ("b" | "B") (["_"] bindigit)+
    octinteger:   "0" ("o" | "O") (["_"] octdigit)+
    hexinteger:   "0" ("x" | "X") (["_"] hexdigit)+
    zerointeger:  "0"+ (["_"] "0")*
    nonzerodigit: "1"..."9"
    digit:        "0"..."9"
    bindigit:     "0" | "1"
    octdigit:     "0"..."7"
    hexdigit:     digit | "a"..."f" | "A"..."F"

Changed in version 3.6: Underscores are now allowed for grouping purposes in literals.

<span id="lexical_analysis--floating"></span> <span id="lexical_analysis--index-29"></span>

### 2.6.2. Floating-point literals {#lexical_analysis--floating-point-literals}

Floating-point (float) literals, such as `3.14` or `1.5`, denote [approximations of real numbers](#datamodel--datamodel-float).

They consist of *integer* and *fraction* parts, each composed of decimal digits. The parts are separated by a decimal point, `.`:

    2.71828
    4.0

Unlike in integer literals, leading zeros are allowed. For example, `077.010` is legal, and denotes the same number as `77.01`.

As in integer literals, single underscores may occur between digits to help readability:

    96_485.332_123
    3.14_15_93

Either of these parts, but not both, can be empty. For example:

    10.  # (equivalent to 10.0)
    .001  # (equivalent to 0.001)

Optionally, the integer and fraction may be followed by an *exponent*: the letter `e` or `E`, followed by an optional sign, `+` or `-`, and a number in the same format as the integer and fraction parts. The `e` or `E` represents “times ten raised to the power of”:

    1.0e3  # (represents 1.0×10³, or 1000.0)
    1.166e-5  # (represents 1.166×10⁻⁵, or 0.00001166)
    6.02214076e+23  # (represents 6.02214076×10²³, or 602214076000000000000000.)

In floats with only integer and exponent parts, the decimal point may be omitted:

    1e3  # (equivalent to 1.e3 and 1.0e3)
    0e0  # (equivalent to 0.)

Formally, floating-point literals are described by the following lexical definitions:

    floatnumber:
       | digitpart "." [digitpart] [exponent]
       | "." digitpart [exponent]
       | digitpart exponent
    digitpart: digit (["_"] digit)*
    exponent:  ("e" | "E") ["+" | "-"] digitpart

Changed in version 3.6: Underscores are now allowed for grouping purposes in literals.

<span id="lexical_analysis--imaginary"></span> <span id="lexical_analysis--index-30"></span>

### 2.6.3. Imaginary literals {#lexical_analysis--imaginary-literals}

Python has [complex number](https://docs.python.org/3/library/stdtypes.html#typesnumeric) objects, but no complex literals. Instead, *imaginary literals* denote complex numbers with a zero real part.

For example, in math, the complex number 3+4.2*i* is written as the real number 3 added to the imaginary number 4.2*i*. Python uses a similar syntax, except the imaginary unit is written as `j` rather than *i*:

    3+4.2j

This is an expression composed of the [integer literal](#lexical_analysis--integers) `3`, the [operator](#lexical_analysis--operators) ‘`+`’, and the [imaginary literal](#lexical_analysis--imaginary) `4.2j`. Since these are three separate tokens, whitespace is allowed between them:

    3 + 4.2j

No whitespace is allowed *within* each token. In particular, the `j` suffix, may not be separated from the number before it.

The number before the `j` has the same syntax as a floating-point literal. Thus, the following are valid imaginary literals:

    4.2j
    3.14j
    10.j
    .001j
    1e100j
    3.14e-10j
    3.14_15_93j

Unlike in a floating-point literal the decimal point can be omitted if the imaginary number only has an integer part. The number is still evaluated as a floating-point number, not an integer:

    10j
    0j
    1000000000000000000000000j   # equivalent to 1e+24j

The `j` suffix is case-insensitive. That means you can use `J` instead:

    3.14J   # equivalent to 3.14j

Formally, imaginary literals are described by the following lexical definition:

    imagnumber: (floatnumber | digitpart) ("j" | "J")

<span id="lexical_analysis--lexical-ellipsis"></span> <span id="lexical_analysis--operators"></span> <span id="lexical_analysis--delimiters"></span>

## 2.7. Operators and delimiters {#lexical_analysis--operators-and-delimiters}

The following grammar defines *operator* and *delimiter* tokens, that is, the generic [`OP`](https://docs.python.org/3/library/token.html#token.OP) token type. A [list of these tokens and their names](https://docs.python.org/3/library/token.html#token-operators-delimiters) is also available in the `token` module documentation.

    OP:
       | assignment_operator
       | bitwise_operator
       | comparison_operator
       | enclosing_delimiter
       | other_delimiter
       | arithmetic_operator
       | "..."
       | other_op

    assignment_operator:   "+=" | "-=" | "*=" | "**=" | "/="  | "//=" | "%=" |
                           "&=" | "|=" | "^=" | "<<=" | ">>=" | "@="  | ":="
    bitwise_operator:      "&"  | "|"  | "^"  | "~"   | "<<"  | ">>"
    comparison_operator:   "<=" | ">=" | "<"  | ">"   | "=="  | "!="
    enclosing_delimiter:   "("  | ")"  | "["  | "]"   | "{"   | "}"
    other_delimiter:       ","  | ":"  | "!"  | ";"   | "="   | "->"
    arithmetic_operator:   "+"  | "-"  | "**" | "*"   | "//"  | "/"   | "%"
    other_op:              "."  | "@"

Note

Generally, *operators* are used to combine [expressions](#expressions--expressions), while *delimiters* serve other purposes. However, there is no clear, formal distinction between the two categories.

Some tokens can serve as either operators or delimiters, depending on usage. For example, `*` is both the multiplication operator and a delimiter used for sequence unpacking, and `@` is both the matrix multiplication and a delimiter that introduces decorators.

For some tokens, the distinction is unclear. For example, some people consider `.`, `(`, and `)` to be delimiters, while others see the [`getattr()`](https://docs.python.org/3/library/functions.html#getattr) operator and the function call operator(s).

Some of Python’s operators, like `and`, `or`, and `not in`, use [keyword](#lexical_analysis--keywords) tokens rather than “symbols” (operator tokens).

A sequence of three consecutive periods (`...`) has a special meaning as an [`Ellipsis`](https://docs.python.org/3/library/constants.html#Ellipsis) literal.

<span id="datamodel--datamodel"></span>

# 3. Data model {#datamodel--data-model}

<span id="datamodel--objects"></span>

## 3.1. Objects, values and types {#datamodel--objects-values-and-types}

*Objects* are Python’s abstraction for data. All data in a Python program is represented by objects or by relations between objects. Even code is represented by objects.

Every object has an identity, a type and a value. An object’s *identity* never changes once it has been created; you may think of it as the object’s address in memory. The [`is`](#expressions--is) operator compares the identity of two objects; the [`id()`](https://docs.python.org/3/library/functions.html#id) function returns an integer representing its identity.

**CPython implementation detail:** For CPython, `id(x)` is the memory address where `x` is stored.

An object’s type determines the operations that the object supports (e.g., “does it have a length?”) and also defines the possible values for objects of that type. The [`type()`](https://docs.python.org/3/library/functions.html#type) function returns an object’s type (which is an object itself). Like its identity, an object’s *type* is also unchangeable. [\[1\]](#datamodel--id20){#datamodel--id1}

The *value* of some objects can change. Objects whose value can change are said to be *mutable*; objects whose value is unchangeable once they are created are called *immutable*. (The value of an immutable container object that contains a reference to a mutable object can change when the latter’s value is changed; however the container is still considered immutable, because the collection of objects it contains cannot be changed. So, immutability is not strictly the same as having an unchangeable value, it is more subtle.) An object’s mutability is determined by its type; for instance, numbers, strings and tuples are immutable, while dictionaries and lists are mutable.

Objects are never explicitly destroyed; however, when they become unreachable they may be garbage-collected. An implementation is allowed to postpone garbage collection or omit it altogether — it is a matter of implementation quality how garbage collection is implemented, as long as no objects are collected that are still reachable.

**CPython implementation detail:** CPython currently uses a reference-counting scheme with (optional) delayed detection of cyclically linked garbage, which collects most objects as soon as they become unreachable, but is not guaranteed to collect garbage containing circular references. See the documentation of the [`gc`](https://docs.python.org/3/library/gc.html#module-gc) module for information on controlling the collection of cyclic garbage. Other implementations act differently and CPython may change. Do not depend on immediate finalization of objects when they become unreachable (so you should always close files explicitly).

Note that the use of the implementation’s tracing or debugging facilities may keep objects alive that would normally be collectable. Also note that catching an exception with a [`try`](#compound_stmts--try)…[`except`](#compound_stmts--except) statement may keep objects alive.

Some objects contain references to “external” resources such as open files or windows. It is understood that these resources are freed when the object is garbage-collected, but since garbage collection is not guaranteed to happen, such objects also provide an explicit way to release the external resource, usually a `close()` method. Programs are strongly recommended to explicitly close such objects. The [`try`](#compound_stmts--try)…[`finally`](#compound_stmts--finally) statement and the [`with`](#compound_stmts--with) statement provide convenient ways to do this.

Some objects contain references to other objects; these are called *containers*. Examples of containers are tuples, lists and dictionaries. The references are part of a container’s value. In most cases, when we talk about the value of a container, we imply the values, not the identities of the contained objects; however, when we talk about the mutability of a container, only the identities of the immediately contained objects are implied. So, if an immutable container (like a tuple) contains a reference to a mutable object, its value changes if that mutable object is changed.

Types affect almost all aspects of object behavior. Even the importance of object identity is affected in some sense: for immutable types, operations that compute new values may actually return a reference to any existing object with the same type and value, while for mutable objects this is not allowed. For example, after `a = 1; b = 1`, *a* and *b* may or may not refer to the same object with the value one, depending on the implementation. This is because [`int`](https://docs.python.org/3/library/functions.html#int) is an immutable type, so the reference to `1` can be reused. This behaviour depends on the implementation used, so should not be relied upon, but is something to be aware of when making use of object identity tests. However, after `c = []; d = []`, *c* and *d* are guaranteed to refer to two different, unique, newly created empty lists. (Note that `e = f = []` assigns the *same* object to both *e* and *f*.)

<span id="datamodel--types"></span>

## 3.2. The standard type hierarchy {#datamodel--the-standard-type-hierarchy}

Below is a list of the types that are built into Python. Extension modules (written in C, Java, or other languages, depending on the implementation) can define additional types. Future versions of Python may add types to the type hierarchy (e.g., rational numbers, efficiently stored arrays of integers, etc.), although such additions will often be provided via the standard library instead.

Some of the type descriptions below contain a paragraph listing ‘special attributes.’ These are attributes that provide access to the implementation and are not intended for general use. Their definition may change in the future.

### 3.2.1. None {#datamodel--none}

This type has a single value. There is a single object with this value. This object is accessed through the built-in name `None`. It is used to signify the absence of a value in many situations, e.g., it is returned from functions that don’t explicitly return anything. Its truth value is false.

### 3.2.2. NotImplemented {#datamodel--notimplemented}

This type has a single value. There is a single object with this value. This object is accessed through the built-in name [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented). Numeric methods and rich comparison methods should return this value if they do not implement the operation for the operands provided. (The interpreter will then try the reflected operation, or some other fallback, depending on the operator.) It should not be evaluated in a boolean context.

See [Implementing the arithmetic operations](https://docs.python.org/3/library/numbers.html#implementing-the-arithmetic-operations) for more details.

Changed in version 3.9: Evaluating [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented) in a boolean context was deprecated.

Changed in version 3.14: Evaluating [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented) in a boolean context now raises a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError). It previously evaluated to [`True`](https://docs.python.org/3/library/constants.html#True) and emitted a [`DeprecationWarning`](https://docs.python.org/3/library/exceptions.html#DeprecationWarning) since Python 3.9.

### 3.2.3. Ellipsis {#datamodel--ellipsis}

This type has a single value. There is a single object with this value. This object is accessed through the literal `...` or the built-in name `Ellipsis`. Its truth value is true.

### 3.2.4. [`numbers.Number`](https://docs.python.org/3/library/numbers.html#numbers.Number) {#datamodel--numbers-number}

These are created by numeric literals and returned as results by arithmetic operators and arithmetic built-in functions. Numeric objects are immutable; once created their value never changes. Python numbers are of course strongly related to mathematical numbers, but subject to the limitations of numerical representation in computers.

The string representations of the numeric classes, computed by [`__repr__()`](#datamodel--object.__repr__) and [`__str__()`](#datamodel--object.__str__), have the following properties:

- They are valid numeric literals which, when passed to their class constructor, produce an object having the value of the original numeric.

- The representation is in base 10, when possible.

- Leading zeros, possibly excepting a single zero before a decimal point, are not shown.

- Trailing zeros, possibly excepting a single zero after a decimal point, are not shown.

- A sign is shown only when the number is negative.

Python distinguishes between integers, floating-point numbers, and complex numbers:

#### 3.2.4.1. [`numbers.Integral`](https://docs.python.org/3/library/numbers.html#numbers.Integral) {#datamodel--numbers-integral}

These represent elements from the mathematical set of integers (positive and negative).

Note

The rules for integer representation are intended to give the most meaningful interpretation of shift and mask operations involving negative integers.

There are two types of integers:

Integers ([`int`](https://docs.python.org/3/library/functions.html#int))  
These represent numbers in an unlimited range, subject to available (virtual) memory only. For the purpose of shift and mask operations, a binary representation is assumed, and negative numbers are represented in a variant of 2’s complement which gives the illusion of an infinite string of sign bits extending to the left.

Booleans ([`bool`](https://docs.python.org/3/library/functions.html#bool))  
These represent the truth values False and True. The two objects representing the values `False` and `True` are the only Boolean objects. The Boolean type is a subtype of the integer type, and Boolean values behave like the values 0 and 1, respectively, in almost all contexts, the exception being that when converted to a string, the strings `"False"` or `"True"` are returned, respectively.

<span id="datamodel--datamodel-float"></span>

#### 3.2.4.2. [`numbers.Real`](https://docs.python.org/3/library/numbers.html#numbers.Real) ([`float`](https://docs.python.org/3/library/functions.html#float)) {#datamodel--numbers-real-float}

These represent machine-level double precision floating-point numbers. You are at the mercy of the underlying machine architecture (and C or Java implementation) for the accepted range and handling of overflow. Python does not support single-precision floating-point numbers; the savings in processor and memory usage that are usually the reason for using these are dwarfed by the overhead of using objects in Python, so there is no reason to complicate the language with two kinds of floating-point numbers.

#### 3.2.4.3. [`numbers.Complex`](https://docs.python.org/3/library/numbers.html#numbers.Complex) ([`complex`](https://docs.python.org/3/library/functions.html#complex)) {#datamodel--numbers-complex-complex}

These represent complex numbers as a pair of machine-level double precision floating-point numbers. The same caveats apply as for floating-point numbers. The real and imaginary parts of a complex number `z` can be retrieved through the read-only attributes `z.real` and `z.imag`.

<span id="datamodel--datamodel-sequences"></span>

### 3.2.5. Sequences {#datamodel--sequences}

These represent finite ordered sets indexed by non-negative numbers. The built-in function [`len()`](https://docs.python.org/3/library/functions.html#len) returns the number of items of a sequence. When the length of a sequence is *n*, the index set contains the numbers 0, 1, …, *n*-1. Item *i* of sequence *a* is selected by `a[i]`. Some sequences, including built-in sequences, interpret negative subscripts by adding the sequence length. For example, `a[-2]` equals `a[n-2]`, the second to last item of sequence a with length `n`.

The resulting value must be a nonnegative integer less than the number of items in the sequence. If it is not, an [`IndexError`](https://docs.python.org/3/library/exceptions.html#IndexError) is raised.

Sequences also support slicing: `a[start:stop]` selects all items with index *k* such that *start* `<=` *k* `<` *stop*. When used as an expression, a slice is a sequence of the same type. The comment above about negative subscripts also applies to negative slice positions. Note that no error is raised if a slice position is less than zero or larger than the length of the sequence.

If *start* is missing or [`None`](https://docs.python.org/3/library/constants.html#None), slicing behaves as if *start* was zero. If *stop* is missing or `None`, slicing behaves as if *stop* was equal to the length of the sequence.

Some sequences also support “extended slicing” with a third “step” parameter: `a[i:j:k]` selects all items of *a* with index *x* where `x = i + n*k`, *n* `>=` `0` and *i* `<=` *x* `<` *j*.

Sequences are distinguished according to their mutability:

#### 3.2.5.1. Immutable sequences {#datamodel--immutable-sequences}

An object of an immutable sequence type cannot change once it is created. (If the object contains references to other objects, these other objects may be mutable and may be changed; however, the collection of objects directly referenced by an immutable object cannot change.)

The following types are immutable sequences:

Strings  
A string ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) is a sequence of values that represent *characters*, or more formally, *Unicode code points*. All the code points in the range `0` to `0x10FFFF` can be represented in a string.

Python doesn’t have a dedicated *character* type. Instead, every code point in the string is represented as a string object with length `1`.

The built-in function [`ord()`](https://docs.python.org/3/library/functions.html#ord) converts a code point from its string form to an integer in the range `0` to `0x10FFFF`; [`chr()`](https://docs.python.org/3/library/functions.html#chr) converts an integer in the range `0` to `0x10FFFF` to the corresponding length `1` string object. [`str.encode()`](https://docs.python.org/3/library/stdtypes.html#str.encode) can be used to convert a [`str`](https://docs.python.org/3/library/stdtypes.html#str) to [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes) using the given text encoding, and [`bytes.decode()`](https://docs.python.org/3/library/stdtypes.html#bytes.decode) can be used to achieve the opposite.

Tuples  
The items of a [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple) are arbitrary Python objects. Tuples of two or more items are formed by comma-separated lists of expressions. A tuple of one item (a ‘singleton’) can be formed by affixing a comma to an expression (an expression by itself does not create a tuple, since parentheses must be usable for grouping of expressions). An empty tuple can be formed by an empty pair of parentheses.

Bytes  
A [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes) object is an immutable array. The items are 8-bit bytes, represented by integers in the range 0 \<= x \< 256. Bytes literals (like `b'abc'`) and the built-in [`bytes()`](https://docs.python.org/3/library/stdtypes.html#bytes) constructor can be used to create bytes objects. Also, bytes objects can be decoded to strings via the [`decode()`](https://docs.python.org/3/library/stdtypes.html#bytes.decode) method.

#### 3.2.5.2. Mutable sequences {#datamodel--mutable-sequences}

Mutable sequences can be changed after they are created. The subscription and slicing notations can be used as the target of assignment and [`del`](#simple_stmts--del) (delete) statements.

Note

<span id="datamodel--index-23"></span>The [`collections`](https://docs.python.org/3/library/collections.html#module-collections) and [`array`](https://docs.python.org/3/library/array.html#module-array) module provide additional examples of mutable sequence types.

There are currently two intrinsic mutable sequence types:

Lists  
The items of a list are arbitrary Python objects. Lists are formed by placing a comma-separated list of expressions in square brackets. (Note that there are no special cases needed to form lists of length 0 or 1.)

Byte Arrays  
A bytearray object is a mutable array. They are created by the built-in [`bytearray()`](https://docs.python.org/3/library/stdtypes.html#bytearray) constructor. Aside from being mutable (and hence unhashable), byte arrays otherwise provide the same interface and functionality as immutable [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes) objects.

### 3.2.6. Set types {#datamodel--set-types}

These represent unordered, finite sets of unique, immutable objects. As such, they cannot be indexed by any subscript. However, they can be iterated over, and the built-in function [`len()`](https://docs.python.org/3/library/functions.html#len) returns the number of items in a set. Common uses for sets are fast membership testing, removing duplicates from a sequence, and computing mathematical operations such as intersection, union, difference, and symmetric difference.

For set elements, the same immutability rules apply as for dictionary keys. Note that numeric types obey the normal rules for numeric comparison: if two numbers compare equal (e.g., `1` and `1.0`), only one of them can be contained in a set.

There are currently two intrinsic set types:

Sets  
These represent a mutable set. They are created by the built-in [`set()`](https://docs.python.org/3/library/stdtypes.html#set) constructor and can be modified afterwards by several methods, such as [`add()`](https://docs.python.org/3/library/stdtypes.html#set.add).

Frozen sets  
These represent an immutable set. They are created by the built-in [`frozenset()`](https://docs.python.org/3/library/stdtypes.html#frozenset) constructor. As a frozenset is immutable and [hashable](https://docs.python.org/3/glossary.html#term-hashable), it can be used again as an element of another set, or as a dictionary key.

<span id="datamodel--datamodel-mappings"></span>

### 3.2.7. Mappings {#datamodel--mappings}

These represent finite sets of objects indexed by arbitrary index sets. The subscript notation `a[k]` selects the item indexed by `k` from the mapping `a`; this can be used in expressions and as the target of assignments or [`del`](#simple_stmts--del) statements. The built-in function [`len()`](https://docs.python.org/3/library/functions.html#len) returns the number of items in a mapping.

There is currently a single intrinsic mapping type:

#### 3.2.7.1. Dictionaries {#datamodel--dictionaries}

These represent finite sets of objects indexed by nearly arbitrary values. The only types of values not acceptable as keys are values containing lists or dictionaries or other mutable types that are compared by value rather than by object identity, the reason being that the efficient implementation of dictionaries requires a key’s hash value to remain constant. Numeric types used for keys obey the normal rules for numeric comparison: if two numbers compare equal (e.g., `1` and `1.0`) then they can be used interchangeably to index the same dictionary entry.

Dictionaries preserve insertion order, meaning that keys will be produced in the same order they were added sequentially over the dictionary. Replacing an existing key does not change the order, however removing a key and re-inserting it will add it to the end instead of keeping its old place.

Dictionaries are mutable; they can be created by the `{}` notation (see section [Dictionary displays](#expressions--dict)).

The extension modules [`dbm.ndbm`](https://docs.python.org/3/library/dbm.html#module-dbm.ndbm) and [`dbm.gnu`](https://docs.python.org/3/library/dbm.html#module-dbm.gnu) provide additional examples of mapping types, as does the [`collections`](https://docs.python.org/3/library/collections.html#module-collections) module.

Changed in version 3.7: Dictionaries did not preserve insertion order in versions of Python before 3.6. In CPython 3.6, insertion order was preserved, but it was considered an implementation detail at that time rather than a language guarantee.

### 3.2.8. Callable types {#datamodel--callable-types}

These are the types to which the function call operation (see section [Calls](#expressions--calls)) can be applied:

<span id="datamodel--user-defined-funcs"></span>

#### 3.2.8.1. User-defined functions {#datamodel--user-defined-functions}

A user-defined function object is created by a function definition (see section [Function definitions](#compound_stmts--function)). It should be called with an argument list containing the same number of items as the function’s formal parameter list.

##### 3.2.8.1.1. Special read-only attributes {#datamodel--special-read-only-attributes}

<table id="datamodel--index-35">
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr class="header">
<th><p>Attribute</p></th>
<th><p>Meaning</p></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><dl>
<dt>function.__builtins__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A reference to the <a href="https://docs.python.org/3/library/stdtypes.html#dict"><code>dictionary</code></a> that holds the function’s builtins namespace.</p>
<p>Added in version 3.10.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>function.__globals__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A reference to the <a href="https://docs.python.org/3/library/stdtypes.html#dict"><code>dictionary</code></a> that holds the function’s <a href="#executionmodel--naming">global variables</a> – the global namespace of the module in which the function was defined.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>function.__closure__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p><code>None</code> or a <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> of cells that contain bindings for the names specified in the <a href="#datamodel--codeobject.co_freevars"><code>co_freevars</code></a> attribute of the function’s <a href="#datamodel--function.__code__"><code>code object</code></a>.</p>
<p>A cell object has the attribute <code>cell_contents</code>. This can be used to get the value of the cell, as well as set the value.</p></td>
</tr>
</tbody>
</table>

##### 3.2.8.1.2. Special writable attributes {#datamodel--special-writable-attributes}

Most of these attributes check the type of the assigned value:

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr class="header">
<th><p>Attribute</p></th>
<th><p>Meaning</p></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><dl>
<dt>function.__doc__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The function’s documentation string, or <code>None</code> if unavailable.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>function.__name__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The function’s name. See also: <a href="https://docs.python.org/3/library/stdtypes.html#definition.__name__"><code>__name__ attributes</code></a>.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>function.__qualname__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The function’s <a href="https://docs.python.org/3/glossary.html#term-qualified-name">qualified name</a>. See also: <a href="https://docs.python.org/3/library/stdtypes.html#definition.__qualname__"><code>__qualname__ attributes</code></a>.</p>
<p>Added in version 3.3.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>function.__module__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The name of the module the function was defined in, or <code>None</code> if unavailable.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>function.__defaults__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing default <a href="https://docs.python.org/3/glossary.html#term-parameter">parameter</a> values for those parameters that have defaults, or <code>None</code> if no parameters have a default value.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>function.__code__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The <a href="#datamodel--code-objects">code object</a> representing the compiled function body.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>function.__dict__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The namespace supporting arbitrary function attributes. See also: <a href="#datamodel--object.__dict__"><code>__dict__ attributes</code></a>.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>function.__annotations__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#dict"><code>dictionary</code></a> containing annotations of <a href="https://docs.python.org/3/glossary.html#term-parameter">parameters</a>. The keys of the dictionary are the parameter names, and <code>'return'</code> for the return annotation, if provided. See also: <a href="#datamodel--object.__annotations__"><code>object.__annotations__</code></a>.</p>
<p>Changed in version 3.14: Annotations are now <a href="#executionmodel--lazy-evaluation">lazily evaluated</a>. See <span id="datamodel--index-37"></span><a href="https://peps.python.org/pep-0649/"><strong>PEP 649</strong></a>.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>function.__annotate__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The <a href="https://docs.python.org/3/glossary.html#term-annotate-function">annotate function</a> for this function, or <code>None</code> if the function has no annotations. See <a href="#datamodel--object.__annotate__"><code>object.__annotate__</code></a>.</p>
<p>Added in version 3.14.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>function.__kwdefaults__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#dict"><code>dictionary</code></a> containing defaults for keyword-only <a href="https://docs.python.org/3/glossary.html#term-parameter">parameters</a>.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>function.__type_params__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the <a href="#compound_stmts--type-params">type parameters</a> of a <a href="#compound_stmts--generic-functions">generic function</a>.</p>
<p>Added in version 3.12.</p></td>
</tr>
</tbody>
</table>

Function objects also support getting and setting arbitrary attributes, which can be used, for example, to attach metadata to functions. Regular attribute dot-notation is used to get and set such attributes.

**CPython implementation detail:** CPython’s current implementation only supports function attributes on user-defined functions. Function attributes on [built-in functions](#datamodel--builtin-functions) may be supported in the future.

Additional information about a function’s definition can be retrieved from its [code object](#datamodel--code-objects) (accessible via the [`__code__`](#datamodel--function.__code__) attribute).

<span id="datamodel--id2"></span>

#### 3.2.8.2. Instance methods {#datamodel--instance-methods}

An instance method object combines a class, a class instance and any callable object (normally a user-defined function).

Special read-only attributes:

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr class="odd">
<td><dl>
<dt>method.__self__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Refers to the class instance object to which the method is <a href="#datamodel--method-binding">bound</a></p></td>
</tr>
<tr class="even">
<td><dl>
<dt>method.__func__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Refers to the original <a href="#datamodel--user-defined-funcs">function object</a></p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>method.__doc__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The method’s documentation (same as <a href="#datamodel--function.__doc__"><code>method.__func__.__doc__</code></a>). A <a href="https://docs.python.org/3/library/stdtypes.html#str"><code>string</code></a> if the original function had a docstring, else <code>None</code>.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>method.__name__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The name of the method (same as <a href="#datamodel--function.__name__"><code>method.__func__.__name__</code></a>)</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>method.__module__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The name of the module the method was defined in, or <code>None</code> if unavailable.</p></td>
</tr>
</tbody>
</table>

Methods also support accessing (but not setting) the arbitrary function attributes on the underlying [function object](#datamodel--user-defined-funcs).

User-defined method objects may be created when getting an attribute of a class (perhaps via an instance of that class), if that attribute is a user-defined [function object](#datamodel--user-defined-funcs) or a [`classmethod`](https://docs.python.org/3/library/functions.html#classmethod) object.

When an instance method object is created by retrieving a user-defined [function object](#datamodel--user-defined-funcs) from a class via one of its instances, its [`__self__`](#datamodel--method.__self__) attribute is the instance, and the method object is said to be *bound*. The new method’s [`__func__`](#datamodel--method.__func__) attribute is the original function object.

When an instance method object is created by retrieving a [`classmethod`](https://docs.python.org/3/library/functions.html#classmethod) object from a class or instance, its [`__self__`](#datamodel--method.__self__) attribute is the class itself, and its [`__func__`](#datamodel--method.__func__) attribute is the function object underlying the class method.

When an instance method object is called, the underlying function ([`__func__`](#datamodel--method.__func__)) is called, inserting the class instance ([`__self__`](#datamodel--method.__self__)) in front of the argument list. For instance, when `C` is a class which contains a definition for a function `f()`, and `x` is an instance of `C`, calling `x.f(1)` is equivalent to calling `C.f(x, 1)`.

When an instance method object is derived from a [`classmethod`](https://docs.python.org/3/library/functions.html#classmethod) object, the “class instance” stored in [`__self__`](#datamodel--method.__self__) will actually be the class itself, so that calling either `x.f(1)` or `C.f(1)` is equivalent to calling `f(C,1)` where `f` is the underlying function.

It is important to note that user-defined functions which are attributes of a class instance are not converted to bound methods; this *only* happens when the function is an attribute of the class.

#### 3.2.8.3. Generator functions {#datamodel--generator-functions}

A function or method which contains a [`yield`](#simple_stmts--yield) expression (see section [Yield expressions](#expressions--yieldexpr)) is called a *generator function*. Such a function, when called, always returns an [iterator](https://docs.python.org/3/glossary.html#term-iterator) object which can be used to execute the body of the function: calling the iterator’s [`iterator.__next__()`](https://docs.python.org/3/library/stdtypes.html#iterator.__next__) method will cause the function to execute until it provides a value using the `yield` expression. When the function executes a [`return`](#simple_stmts--return) statement or falls off the end, a [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) exception is raised and the iterator will have reached the end of the set of values to be returned.

#### 3.2.8.4. Coroutine functions {#datamodel--coroutine-functions}

A function or method which is defined using [`async def`](#compound_stmts--async-def) is called a *coroutine function*. Such a function, when called, returns a [coroutine](https://docs.python.org/3/glossary.html#term-coroutine) object. It may contain [`await`](#expressions--await) expressions, as well as [`async with`](#compound_stmts--async-with) and [`async for`](#compound_stmts--async-for) statements. See also the [Coroutine Objects](#datamodel--coroutine-objects) section.

#### 3.2.8.5. Asynchronous generator functions {#datamodel--asynchronous-generator-functions}

A function or method which is defined using [`async def`](#compound_stmts--async-def) and which contains a [`yield`](#simple_stmts--yield) expression is called a *asynchronous generator function*. Such a function, when called, returns an [asynchronous iterator](https://docs.python.org/3/glossary.html#term-asynchronous-iterator) object which can be used in an [`async for`](#compound_stmts--async-for) statement to execute the body of the function.

Calling the asynchronous iterator’s [`aiterator.__anext__`](#datamodel--object.__anext__) method will return an [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) which when awaited will execute until it provides a value using the [`yield`](#simple_stmts--yield) expression. When the function executes an empty [`return`](#simple_stmts--return) statement or falls off the end, a [`StopAsyncIteration`](https://docs.python.org/3/library/exceptions.html#StopAsyncIteration) exception is raised and the asynchronous iterator will have reached the end of the set of values to be yielded.

<span id="datamodel--builtin-functions"></span>

#### 3.2.8.6. Built-in functions {#datamodel--built-in-functions}

A built-in function object is a wrapper around a C function. Examples of built-in functions are [`len()`](https://docs.python.org/3/library/functions.html#len) and [`math.sin()`](https://docs.python.org/3/library/math.html#math.sin) ([`math`](https://docs.python.org/3/library/math.html#module-math) is a standard built-in module). The number and type of the arguments are determined by the C function. Special read-only attributes:

- `__doc__` is the function’s documentation string, or `None` if unavailable. See [`function.__doc__`](#datamodel--function.__doc__).

- `__name__` is the function’s name. See [`function.__name__`](#datamodel--function.__name__).

- `__self__` is set to `None` (but see the next item).

- `__module__` is the name of the module the function was defined in or `None` if unavailable. See [`function.__module__`](#datamodel--function.__module__).

<span id="datamodel--builtin-methods"></span>

#### 3.2.8.7. Built-in methods {#datamodel--built-in-methods}

This is really a different disguise of a built-in function, this time containing an object passed to the C function as an implicit extra argument. An example of a built-in method is `alist.append()`, assuming *alist* is a list object. In this case, the special read-only attribute `__self__` is set to the object denoted by *alist*. (The attribute has the same semantics as it does with [`other instance methods`](#datamodel--method.__self__).)

<span id="datamodel--id3"></span>

#### 3.2.8.8. Classes {#datamodel--classes}

Classes are callable. These objects normally act as factories for new instances of themselves, but variations are possible for class types that override [`__new__()`](#datamodel--object.__new__). The arguments of the call are passed to `__new__()` and, in the typical case, to [`__init__()`](#datamodel--object.__init__) to initialize the new instance.

#### 3.2.8.9. Class Instances {#datamodel--class-instances}

Instances of arbitrary classes can be made callable by defining a [`__call__()`](#datamodel--object.__call__) method in their class.

<span id="datamodel--module-objects"></span>

### 3.2.9. Modules {#datamodel--modules}

Modules are a basic organizational unit of Python code, and are created by the [import system](#import--importsystem) as invoked either by the [`import`](#simple_stmts--import) statement, or by calling functions such as [`importlib.import_module()`](https://docs.python.org/3/library/importlib.html#importlib.import_module) and built-in [`__import__()`](https://docs.python.org/3/library/functions.html#import__). A module object has a namespace implemented by a [`dictionary`](https://docs.python.org/3/library/stdtypes.html#dict) object (this is the dictionary referenced by the [`__globals__`](#datamodel--function.__globals__) attribute of functions defined in the module). Attribute references are translated to lookups in this dictionary, e.g., `m.x` is equivalent to `m.__dict__["x"]`. A module object does not contain the code object used to initialize the module (since it isn’t needed once the initialization is done).

Attribute assignment updates the module’s namespace dictionary, e.g., `m.x = 1` is equivalent to `m.__dict__["x"] = 1`.

<span id="datamodel--import-mod-attrs"></span> <span id="datamodel--index-46"></span>

#### 3.2.9.1. Import-related attributes on module objects {#datamodel--import-related-attributes-on-module-objects}

Module objects have the following attributes that relate to the [import system](#import--importsystem). When a module is created using the machinery associated with the import system, these attributes are filled in based on the module’s [spec](https://docs.python.org/3/glossary.html#term-module-spec), before the [loader](https://docs.python.org/3/glossary.html#term-loader) executes and loads the module.

To create a module dynamically rather than using the import system, it’s recommended to use [`importlib.util.module_from_spec()`](https://docs.python.org/3/library/importlib.html#importlib.util.module_from_spec), which will set the various import-controlled attributes to appropriate values. It’s also possible to use the [`types.ModuleType`](https://docs.python.org/3/library/types.html#types.ModuleType) constructor to create modules directly, but this technique is more error-prone, as most attributes must be manually set on the module object after it has been created when using this approach.

Caution

With the exception of [`__name__`](#datamodel--module.__name__), it is **strongly** recommended that you rely on [`__spec__`](#datamodel--module.__spec__) and its attributes instead of any of the other individual attributes listed in this subsection. Note that updating an attribute on `__spec__` will not update the corresponding attribute on the module itself:

    >>> import typing
    >>> typing.__name__, typing.__spec__.name
    ('typing', 'typing')
    >>> typing.__spec__.name = 'spelling'
    >>> typing.__name__, typing.__spec__.name
    ('typing', 'spelling')
    >>> typing.__name__ = 'keyboard_smashing'
    >>> typing.__name__, typing.__spec__.name
    ('keyboard_smashing', 'spelling')

module.\_\_name\_\_  
The name used to uniquely identify the module in the import system. For a directly executed module, this will be set to `"__main__"`.

This attribute must be set to the fully qualified name of the module. It is expected to match the value of [`module.__spec__.name`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.name).

<!-- -->

module.\_\_spec\_\_  
A record of the module’s import-system-related state.

Set to the [`module spec`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec) that was used when importing the module. See [Module specs](#import--module-specs) for more details.

Added in version 3.4.

<!-- -->

module.\_\_package\_\_  
The [package](https://docs.python.org/3/glossary.html#term-package) a module belongs to.

If the module is top-level (that is, not a part of any specific package) then the attribute should be set to `''` (the empty string). Otherwise, it should be set to the name of the module’s package (which can be equal to [`module.__name__`](#datamodel--module.__name__) if the module itself is a package). See <span id="datamodel--index-47"></span>[**PEP 366**](https://peps.python.org/pep-0366/) for further details.

This attribute is used instead of [`__name__`](#datamodel--module.__name__) to calculate explicit relative imports for main modules. It defaults to `None` for modules created dynamically using the [`types.ModuleType`](https://docs.python.org/3/library/types.html#types.ModuleType) constructor; use [`importlib.util.module_from_spec()`](https://docs.python.org/3/library/importlib.html#importlib.util.module_from_spec) instead to ensure the attribute is set to a [`str`](https://docs.python.org/3/library/stdtypes.html#str).

It is **strongly** recommended that you use [`module.__spec__.parent`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.parent) instead of `module.__package__`. [`__package__`](#datamodel--module.__package__) is now only used as a fallback if `__spec__.parent` is not set, and this fallback path is deprecated.

Changed in version 3.4: This attribute now defaults to `None` for modules created dynamically using the [`types.ModuleType`](https://docs.python.org/3/library/types.html#types.ModuleType) constructor. Previously the attribute was optional.

Changed in version 3.6: The value of `__package__` is expected to be the same as [`__spec__.parent`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.parent). [`__package__`](#datamodel--module.__package__) is now only used as a fallback during import resolution if `__spec__.parent` is not defined.

Changed in version 3.10: [`ImportWarning`](https://docs.python.org/3/library/exceptions.html#ImportWarning) is raised if an import resolution falls back to `__package__` instead of [`__spec__.parent`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.parent).

Changed in version 3.12: Raise [`DeprecationWarning`](https://docs.python.org/3/library/exceptions.html#DeprecationWarning) instead of [`ImportWarning`](https://docs.python.org/3/library/exceptions.html#ImportWarning) when falling back to `__package__` during import resolution.

Deprecated since version 3.13, will be removed in version 3.15: `__package__` will cease to be set or taken into consideration by the import system or standard library.

<!-- -->

module.\_\_loader\_\_  
The [loader](https://docs.python.org/3/glossary.html#term-loader) object that the import machinery used to load the module.

This attribute is mostly useful for introspection, but can be used for additional loader-specific functionality, for example getting data associated with a loader.

`__loader__` defaults to `None` for modules created dynamically using the [`types.ModuleType`](https://docs.python.org/3/library/types.html#types.ModuleType) constructor; use [`importlib.util.module_from_spec()`](https://docs.python.org/3/library/importlib.html#importlib.util.module_from_spec) instead to ensure the attribute is set to a [loader](https://docs.python.org/3/glossary.html#term-loader) object.

It is **strongly** recommended that you use [`module.__spec__.loader`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.loader) instead of `module.__loader__`.

Changed in version 3.4: This attribute now defaults to `None` for modules created dynamically using the [`types.ModuleType`](https://docs.python.org/3/library/types.html#types.ModuleType) constructor. Previously the attribute was optional.

Deprecated since version 3.12, will be removed in version 3.16: Setting `__loader__` on a module while failing to set `__spec__.loader` is deprecated. In Python 3.16, `__loader__` will cease to be set or taken into consideration by the import system or the standard library.

<!-- -->

module.\_\_path\_\_  
A (possibly empty) [sequence](https://docs.python.org/3/glossary.html#term-sequence) of strings enumerating the locations where the package’s submodules will be found. Non-package modules should not have a `__path__` attribute. See [\_\_path\_\_ attributes on modules](#import--package-path-rules) for more details.

It is **strongly** recommended that you use [`module.__spec__.submodule_search_locations`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.submodule_search_locations) instead of `module.__path__`.

<!-- -->

module.\_\_file\_\_  

<!-- -->

module.\_\_cached\_\_  
`__file__` and `__cached__` are both optional attributes that may or may not be set. Both attributes should be a [`str`](https://docs.python.org/3/library/stdtypes.html#str) when they are available.

`__file__` indicates the pathname of the file from which the module was loaded (if loaded from a file), or the pathname of the shared library file for extension modules loaded dynamically from a shared library. It might be missing for certain types of modules, such as C modules that are statically linked into the interpreter, and the [import system](#import--importsystem) may opt to leave it unset if it has no semantic meaning (for example, a module loaded from a database).

If `__file__` is set then the `__cached__` attribute might also be set, which is the path to any compiled version of the code (for example, a byte-compiled file). The file does not need to exist to set this attribute; the path can simply point to where the compiled file *would* exist (see <span id="datamodel--index-48"></span>[**PEP 3147**](https://peps.python.org/pep-3147/)).

Note that `__cached__` may be set even if `__file__` is not set. However, that scenario is quite atypical. Ultimately, the [loader](https://docs.python.org/3/glossary.html#term-loader) is what makes use of the module spec provided by the [finder](https://docs.python.org/3/glossary.html#term-finder) (from which `__file__` and `__cached__` are derived). So if a loader can load from a cached module but otherwise does not load from a file, that atypical scenario may be appropriate.

It is **strongly** recommended that you use [`module.__spec__.cached`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.cached) instead of `module.__cached__`.

Deprecated since version 3.13, will be removed in version 3.15: Setting `__cached__` on a module while failing to set `__spec__.cached` is deprecated. In Python 3.15, `__cached__` will cease to be set or taken into consideration by the import system or standard library.

#### 3.2.9.2. Other writable attributes on module objects {#datamodel--other-writable-attributes-on-module-objects}

As well as the import-related attributes listed above, module objects also have the following writable attributes:

module.\_\_doc\_\_  
The module’s documentation string, or `None` if unavailable. See also: [`__doc__ attributes`](https://docs.python.org/3/library/stdtypes.html#definition.__doc__).

<!-- -->

module.\_\_annotations\_\_  
A dictionary containing [variable annotations](https://docs.python.org/3/glossary.html#term-variable-annotation) collected during module body execution. For best practices on working with `__annotations__`, see [`annotationlib`](https://docs.python.org/3/library/annotationlib.html#module-annotationlib).

Changed in version 3.14: Annotations are now [lazily evaluated](#executionmodel--lazy-evaluation). See <span id="datamodel--index-49"></span>[**PEP 649**](https://peps.python.org/pep-0649/).

<!-- -->

module.\_\_annotate\_\_  
The [annotate function](https://docs.python.org/3/glossary.html#term-annotate-function) for this module, or `None` if the module has no annotations. See also: [`__annotate__`](#datamodel--object.__annotate__) attributes.

Added in version 3.14.

#### 3.2.9.3. Module dictionaries {#datamodel--module-dictionaries}

Module objects also have the following special read-only attribute:

module.\_\_dict\_\_  
The module’s namespace as a dictionary object. Uniquely among the attributes listed here, `__dict__` cannot be accessed as a global variable from within a module; it can only be accessed as an attribute on module objects.

**CPython implementation detail:** Because of the way CPython clears module dictionaries, the module dictionary will be cleared when the module falls out of scope even if the dictionary still has live references. To avoid this, copy the dictionary or keep the module around while using its dictionary directly.

<span id="datamodel--class-attrs-and-methods"></span>

### 3.2.10. Custom classes {#datamodel--custom-classes}

Custom class types are typically created by class definitions (see section [Class definitions](#compound_stmts--class)). A class has a namespace implemented by a dictionary object. Class attribute references are translated to lookups in this dictionary, e.g., `C.x` is translated to `C.__dict__["x"]` (although there are a number of hooks which allow for other means of locating attributes). When the attribute name is not found there, the attribute search continues in the base classes. This search of the base classes uses the C3 method resolution order which behaves correctly even in the presence of ‘diamond’ inheritance structures where there are multiple inheritance paths leading back to a common ancestor. Additional details on the C3 MRO used by Python can be found at [The Python 2.3 Method Resolution Order](https://docs.python.org/3/howto/mro.html#python-2-3-mro).

When a class attribute reference (for class `C`, say) would yield a class method object, it is transformed into an instance method object whose [`__self__`](#datamodel--method.__self__) attribute is `C`. When it would yield a [`staticmethod`](https://docs.python.org/3/library/functions.html#staticmethod) object, it is transformed into the object wrapped by the static method object. See section [Implementing Descriptors](#datamodel--descriptors) for another way in which attributes retrieved from a class may differ from those actually contained in its [`__dict__`](#datamodel--object.__dict__).

Class attribute assignments update the class’s dictionary, never the dictionary of a base class.

A class object can be called (see above) to yield a class instance (see below).

#### 3.2.10.1. Special attributes {#datamodel--special-attributes}

<table id="datamodel--index-54">
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr class="header">
<th><p>Attribute</p></th>
<th><p>Meaning</p></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><dl>
<dt>type.__name__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The class’s name. See also: <a href="https://docs.python.org/3/library/stdtypes.html#definition.__name__"><code>__name__ attributes</code></a>.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>type.__qualname__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The class’s <a href="https://docs.python.org/3/glossary.html#term-qualified-name">qualified name</a>. See also: <a href="https://docs.python.org/3/library/stdtypes.html#definition.__qualname__"><code>__qualname__ attributes</code></a>.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>type.__module__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The name of the module in which the class was defined.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>type.__dict__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/types.html#types.MappingProxyType"><code>mapping proxy</code></a> providing a read-only view of the class’s namespace. See also: <a href="#datamodel--object.__dict__"><code>__dict__ attributes</code></a>.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>type.__bases__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the class’s bases. In most cases, for a class defined as <code>class X(A, B, C)</code>, <code>X.__bases__</code> will be exactly equal to <code>(A, B, C)</code>.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>type.__base__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p><strong>CPython implementation detail:</strong> The single base class in the inheritance chain that is responsible for the memory layout of instances. This attribute corresponds to <a href="https://docs.python.org/3/c-api/typeobj.html#c.PyTypeObject.tp_base"><code>tp_base</code></a> at the C level.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>type.__doc__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The class’s documentation string, or <code>None</code> if undefined. Not inherited by subclasses.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>type.__annotations__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A dictionary containing <a href="https://docs.python.org/3/glossary.html#term-variable-annotation">variable annotations</a> collected during class body execution. See also: <a href="#datamodel--object.__annotations__"><code>__annotations__ attributes</code></a>.</p>
<p>For best practices on working with <a href="#datamodel--object.__annotations__"><code>__annotations__</code></a>, please see <a href="https://docs.python.org/3/library/annotationlib.html#module-annotationlib"><code>annotationlib</code></a>. Use <a href="https://docs.python.org/3/library/annotationlib.html#annotationlib.get_annotations"><code>annotationlib.get_annotations()</code></a> instead of accessing this attribute directly.</p>
<p>Warning</p>
<p>Accessing the <code>__annotations__</code> attribute directly on a class object may return annotations for the wrong class, specifically in certain cases where the class, its base class, or a metaclass is defined under <code>from __future__ import annotations</code>. See <span id="datamodel--index-55"></span><a href="https://peps.python.org/pep-0749/#pep749-metaclasses"><strong>749</strong></a> for details.</p>
<p>This attribute does not exist on certain builtin classes. On user-defined classes without <code>__annotations__</code>, it is an empty dictionary.</p>
<p>Changed in version 3.14: Annotations are now <a href="#executionmodel--lazy-evaluation">lazily evaluated</a>. See <span id="datamodel--index-56"></span><a href="https://peps.python.org/pep-0649/"><strong>PEP 649</strong></a>.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>type.__annotate__()</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The <a href="https://docs.python.org/3/glossary.html#term-annotate-function">annotate function</a> for this class, or <code>None</code> if the class has no annotations. See also: <a href="#datamodel--object.__annotate__"><code>__annotate__ attributes</code></a>.</p>
<p>Added in version 3.14.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>type.__type_params__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the <a href="#compound_stmts--type-params">type parameters</a> of a <a href="#compound_stmts--generic-classes">generic class</a>.</p>
<p>Added in version 3.12.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>type.__static_attributes__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing names of attributes of this class which are assigned through <code>self.X</code> from any function in its body.</p>
<p>Added in version 3.13.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>type.__firstlineno__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The line number of the first line of the class definition, including decorators. Setting the <a href="#datamodel--type.__module__"><code>__module__</code></a> attribute removes the <code>__firstlineno__</code> item from the type’s dictionary.</p>
<p>Added in version 3.13.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>type.__mro__</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> of classes that are considered when looking for base classes during method resolution.</p></td>
</tr>
</tbody>
</table>

#### 3.2.10.2. Special methods {#datamodel--special-methods}

In addition to the special attributes described above, all Python classes also have the following two methods available:

type.mro()  
This method can be overridden by a metaclass to customize the method resolution order for its instances. It is called at class instantiation, and its result is stored in [`__mro__`](#datamodel--type.__mro__).

<!-- -->

type.\_\_subclasses\_\_()  
Each class keeps a list of weak references to its immediate subclasses. This method returns a list of all those references still alive. The list is in definition order. Example:

    >>> class A: pass
    >>> class B(A): pass
    >>> A.__subclasses__()
    [<class 'B'>]

### 3.2.11. Class instances {#datamodel--id4}

A class instance is created by calling a class object (see above). A class instance has a namespace implemented as a dictionary which is the first place in which attribute references are searched. When an attribute is not found there, and the instance’s class has an attribute by that name, the search continues with the class attributes. If a class attribute is found that is a user-defined function object, it is transformed into an instance method object whose [`__self__`](#datamodel--method.__self__) attribute is the instance. Static method and class method objects are also transformed; see above under “Classes”. See section [Implementing Descriptors](#datamodel--descriptors) for another way in which attributes of a class retrieved via its instances may differ from the objects actually stored in the class’s [`__dict__`](#datamodel--object.__dict__). If no class attribute is found, and the object’s class has a [`__getattr__()`](#datamodel--object.__getattr__) method, that is called to satisfy the lookup.

Attribute assignments and deletions update the instance’s dictionary, never a class’s dictionary. If the class has a [`__setattr__()`](#datamodel--object.__setattr__) or [`__delattr__()`](#datamodel--object.__delattr__) method, this is called instead of updating the instance dictionary directly.

Class instances can pretend to be numbers, sequences, or mappings if they have methods with certain special names. See section [Special method names](#datamodel--specialnames).

#### 3.2.11.1. Special attributes {#datamodel--id5}

object.\_\_class\_\_  
The class to which a class instance belongs.

<!-- -->

object.\_\_dict\_\_  
A dictionary or other mapping object used to store an object’s (writable) attributes. Not all instances have a `__dict__` attribute; see the section on [\_\_slots\_\_](#datamodel--slots) for more details.

### 3.2.12. I/O objects (also known as file objects) {#datamodel--i-o-objects-also-known-as-file-objects}

A [file object](https://docs.python.org/3/glossary.html#term-file-object) represents an open file. Various shortcuts are available to create file objects: the [`open()`](https://docs.python.org/3/library/functions.html#open) built-in function, and also [`os.popen()`](https://docs.python.org/3/library/os.html#os.popen), [`os.fdopen()`](https://docs.python.org/3/library/os.html#os.fdopen), and the [`makefile()`](https://docs.python.org/3/library/socket.html#socket.socket.makefile) method of socket objects (and perhaps by other functions or methods provided by extension modules).

File objects implement common methods, listed below, to simplify usage in generic code. They are expected to be [With Statement Context Managers](#datamodel--context-managers).

The objects `sys.stdin`, `sys.stdout` and `sys.stderr` are initialized to file objects corresponding to the interpreter’s standard input, output and error streams; they are all open in text mode and therefore follow the interface defined by the [`io.TextIOBase`](https://docs.python.org/3/library/io.html#io.TextIOBase) abstract class.

file.read(*size=-1*, */*)  
Retrieve up to *size* data from the file. As a convenience if *size* is unspecified or -1 retrieve all data available.

<!-- -->

file.write(*data*, */*)  
Store *data* to the file.

<!-- -->

file.close()  
Flush any buffers and close the underlying file.

### 3.2.13. Internal types {#datamodel--internal-types}

A few types used internally by the interpreter are exposed to the user. Their definitions may change with future versions of the interpreter, but they are mentioned here for completeness.

<span id="datamodel--id6"></span>

#### 3.2.13.1. Code objects {#datamodel--code-objects}

Code objects represent *byte-compiled* executable Python code, or [bytecode](https://docs.python.org/3/glossary.html#term-bytecode). The difference between a code object and a function object is that the function object contains an explicit reference to the function’s globals (the module in which it was defined), while a code object contains no context; also the default argument values are stored in the function object, not in the code object (because they represent values calculated at run-time). Unlike function objects, code objects are immutable and contain no references (directly or indirectly) to mutable objects.

<span id="datamodel--id7"></span>

##### 3.2.13.1.1. Special read-only attributes {#datamodel--index-64}

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr class="odd">
<td><dl>
<dt>codeobject.co_name</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The function name</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_qualname</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The fully qualified function name</p>
<p>Added in version 3.11.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_argcount</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The total number of positional <a href="https://docs.python.org/3/glossary.html#term-parameter">parameters</a> (including positional-only parameters and parameters with default values) that the function has</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_posonlyargcount</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The number of positional-only <a href="https://docs.python.org/3/glossary.html#term-parameter">parameters</a> (including arguments with default values) that the function has</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_kwonlyargcount</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The number of keyword-only <a href="https://docs.python.org/3/glossary.html#term-parameter">parameters</a> (including arguments with default values) that the function has</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_nlocals</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The number of <a href="#executionmodel--naming">local variables</a> used by the function (including parameters)</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_varnames</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the names of the local variables in the function (starting with the parameter names)</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_cellvars</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the names of <a href="#executionmodel--naming">local variables</a> that are referenced from at least one <a href="https://docs.python.org/3/glossary.html#term-nested-scope">nested scope</a> inside the function</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_freevars</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the names of <a href="https://docs.python.org/3/glossary.html#term-closure-variable">free (closure) variables</a> that a <a href="https://docs.python.org/3/glossary.html#term-nested-scope">nested scope</a> references in an outer scope. See also <a href="#datamodel--function.__closure__"><code>function.__closure__</code></a>.</p>
<p>Note: references to global and builtin names are <em>not</em> included.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_code</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A string representing the sequence of <a href="https://docs.python.org/3/glossary.html#term-bytecode">bytecode</a> instructions in the function</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_consts</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the literals used by the <a href="https://docs.python.org/3/glossary.html#term-bytecode">bytecode</a> in the function</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_names</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A <a href="https://docs.python.org/3/library/stdtypes.html#tuple"><code>tuple</code></a> containing the names used by the <a href="https://docs.python.org/3/glossary.html#term-bytecode">bytecode</a> in the function</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_filename</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The name of the file from which the code was compiled</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_firstlineno</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The line number of the first line of the function</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_lnotab</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>A string encoding the mapping from <a href="https://docs.python.org/3/glossary.html#term-bytecode">bytecode</a> offsets to line numbers. For details, see the source code of the interpreter.</p>
<p>Deprecated since version 3.12: This attribute of code objects is deprecated, and may be removed in Python 3.15.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>codeobject.co_stacksize</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The required stack size of the code object</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>codeobject.co_flags</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>An <a href="https://docs.python.org/3/library/functions.html#int"><code>integer</code></a> encoding a number of flags for the interpreter.</p></td>
</tr>
</tbody>
</table>

The following flag bits are defined for [`co_flags`](#datamodel--codeobject.co_flags): bit `0x04` is set if the function uses the `*arguments` syntax to accept an arbitrary number of positional arguments; bit `0x08` is set if the function uses the `**keywords` syntax to accept arbitrary keyword arguments; bit `0x20` is set if the function is a generator. See [Code Objects Bit Flags](https://docs.python.org/3/library/inspect.html#inspect-module-co-flags) for details on the semantics of each flags that might be present.

Future feature declarations (for example, `from __future__ import division`) also use bits in [`co_flags`](#datamodel--codeobject.co_flags) to indicate whether a code object was compiled with a particular feature enabled. See [`compiler_flag`](https://docs.python.org/3/library/__future__.html#future__._Feature.compiler_flag).

Other bits in [`co_flags`](#datamodel--codeobject.co_flags) are reserved for internal use.

If a code object represents a function and has a docstring, the [`CO_HAS_DOCSTRING`](https://docs.python.org/3/library/inspect.html#inspect.CO_HAS_DOCSTRING) bit is set in [`co_flags`](#datamodel--codeobject.co_flags) and the first item in [`co_consts`](#datamodel--codeobject.co_consts) is the docstring of the function.

##### 3.2.13.1.2. Methods on code objects {#datamodel--methods-on-code-objects}

codeobject.co_positions()  
Returns an iterable over the source code positions of each [bytecode](https://docs.python.org/3/glossary.html#term-bytecode) instruction in the code object.

The iterator returns [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)s containing the `(start_line, end_line, start_column, end_column)`. The *i-th* tuple corresponds to the position of the source code that compiled to the *i-th* code unit. Column information is 0-indexed utf-8 byte offsets on the given source line.

This positional information can be missing. A non-exhaustive lists of cases where this may happen:

- Running the interpreter with [`-X`](https://docs.python.org/3/using/cmdline.html#cmdoption-X) `no_debug_ranges`.

- Loading a pyc file compiled while using [`-X`](https://docs.python.org/3/using/cmdline.html#cmdoption-X) `no_debug_ranges`.

- Position tuples corresponding to artificial instructions.

- Line and column numbers that can’t be represented due to implementation specific limitations.

When this occurs, some or all of the tuple elements can be [`None`](https://docs.python.org/3/library/constants.html#None).

Added in version 3.11.

Note

This feature requires storing column positions in code objects which may result in a small increase of disk usage of compiled Python files or interpreter memory usage. To avoid storing the extra information and/or deactivate printing the extra traceback information, the [`-X`](https://docs.python.org/3/using/cmdline.html#cmdoption-X) `no_debug_ranges` command line flag or the <span id="datamodel--index-67"></span>[`PYTHONNODEBUGRANGES`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONNODEBUGRANGES) environment variable can be used.

<!-- -->

codeobject.co_lines()  
Returns an iterator that yields information about successive ranges of [bytecode](https://docs.python.org/3/glossary.html#term-bytecode)s. Each item yielded is a `(start, end, lineno)` [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple):

- `start` (an [`int`](https://docs.python.org/3/library/functions.html#int)) represents the offset (inclusive) of the start of the [bytecode](https://docs.python.org/3/glossary.html#term-bytecode) range

- `end` (an [`int`](https://docs.python.org/3/library/functions.html#int)) represents the offset (exclusive) of the end of the [bytecode](https://docs.python.org/3/glossary.html#term-bytecode) range

- `lineno` is an [`int`](https://docs.python.org/3/library/functions.html#int) representing the line number of the [bytecode](https://docs.python.org/3/glossary.html#term-bytecode) range, or `None` if the bytecodes in the given range have no line number

The items yielded will have the following properties:

- The first range yielded will have a `start` of 0.

- The `(start, end)` ranges will be non-decreasing and consecutive. That is, for any pair of [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)s, the `start` of the second will be equal to the `end` of the first.

- No range will be backwards: `end >= start` for all triples.

- The last [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple) yielded will have `end` equal to the size of the [bytecode](https://docs.python.org/3/glossary.html#term-bytecode).

Zero-width ranges, where `start == end`, are allowed. Zero-width ranges are used for lines that are present in the source code, but have been eliminated by the [bytecode](https://docs.python.org/3/glossary.html#term-bytecode) compiler.

Added in version 3.10.

See also

<span id="datamodel--index-68"></span>[**PEP 626**](https://peps.python.org/pep-0626/) - Precise line numbers for debugging and other tools.  
The PEP that introduced the `co_lines()` method.

<!-- -->

codeobject.replace(*\*\*kwargs*)  
Return a copy of the code object with new values for the specified fields.

Code objects are also supported by the generic function [`copy.replace()`](https://docs.python.org/3/library/copy.html#copy.replace).

Added in version 3.8.

<span id="datamodel--id8"></span>

#### 3.2.13.2. Frame objects {#datamodel--frame-objects}

Frame objects represent execution frames. They may occur in [traceback objects](#datamodel--traceback-objects), and are also passed to registered trace functions.

<span id="datamodel--id9"></span>

##### 3.2.13.2.1. Special read-only attributes {#datamodel--index-70}

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr class="odd">
<td><dl>
<dt>frame.f_back</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Points to the previous stack frame (towards the caller), or <code>None</code> if this is the bottom stack frame</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>frame.f_code</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The <a href="#datamodel--code-objects">code object</a> being executed in this frame. Accessing this attribute raises an <a href="https://docs.python.org/3/library/sys.html#auditing">auditing event</a> <code>object.__getattr__</code> with arguments <code>obj</code> and <code>"f_code"</code>.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>frame.f_locals</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The mapping used by the frame to look up <a href="#executionmodel--naming">local variables</a>. If the frame refers to an <a href="https://docs.python.org/3/glossary.html#term-optimized-scope">optimized scope</a>, this may return a write-through proxy object.</p>
<p>Changed in version 3.13: Return a proxy for optimized scopes.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>frame.f_globals</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The dictionary used by the frame to look up <a href="#executionmodel--naming">global variables</a></p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>frame.f_builtins</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The dictionary used by the frame to look up <a href="#executionmodel--naming">built-in (intrinsic) names</a></p></td>
</tr>
<tr class="even">
<td><dl>
<dt>frame.f_lasti</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The “precise instruction” of the frame object (this is an index into the <a href="https://docs.python.org/3/glossary.html#term-bytecode">bytecode</a> string of the <a href="#datamodel--code-objects">code object</a>)</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>frame.f_generator</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The <a href="https://docs.python.org/3/glossary.html#term-generator">generator</a> or <a href="https://docs.python.org/3/glossary.html#term-coroutine">coroutine</a> object that owns this frame, or <code>None</code> if the frame is a normal function.</p>
<p>Added in version 3.14.</p></td>
</tr>
</tbody>
</table>

<span id="datamodel--id10"></span>

##### 3.2.13.2.2. Special writable attributes {#datamodel--index-71}

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr class="odd">
<td><dl>
<dt>frame.f_trace</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>If not <code>None</code>, this is a function called for various events during code execution (this is used by debuggers). Normally an event is triggered for each new source line (see <a href="#datamodel--frame.f_trace_lines"><code>f_trace_lines</code></a>).</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>frame.f_trace_lines</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Set this attribute to <a href="https://docs.python.org/3/library/constants.html#False"><code>False</code></a> to disable triggering a tracing event for each source line.</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>frame.f_trace_opcodes</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Set this attribute to <a href="https://docs.python.org/3/library/constants.html#True"><code>True</code></a> to allow per-opcode events to be requested. Note that this may lead to undefined interpreter behaviour if exceptions raised by the trace function escape to the function being traced.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>frame.f_lineno</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>The current line number of the frame – writing to this from within a trace function jumps to the given line (only for the bottom-most frame). A debugger can implement a Jump command (aka Set Next Statement) by writing to this attribute.</p></td>
</tr>
</tbody>
</table>

##### 3.2.13.2.3. Frame object methods {#datamodel--frame-object-methods}

Frame objects support one method:

frame.clear()  
This method clears all references to [local variables](#executionmodel--naming) held by the frame. Also, if the frame belonged to a [generator](https://docs.python.org/3/glossary.html#term-generator), the generator is finalized. This helps break reference cycles involving frame objects (for example when catching an [exception](https://docs.python.org/3/library/exceptions.html#bltin-exceptions) and storing its [traceback](#datamodel--traceback-objects) for later use).

[`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) is raised if the frame is currently executing or suspended.

Added in version 3.4.

Changed in version 3.13: Attempting to clear a suspended frame raises [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) (as has always been the case for executing frames).

<span id="datamodel--id11"></span>

#### 3.2.13.3. Traceback objects {#datamodel--traceback-objects}

Traceback objects represent the stack trace of an [exception](https://docs.python.org/3/tutorial/errors.html#tut-errors). A traceback object is implicitly created when an exception occurs, and may also be explicitly created by calling [`types.TracebackType`](https://docs.python.org/3/library/types.html#types.TracebackType).

Changed in version 3.7: Traceback objects can now be explicitly instantiated from Python code.

For implicitly created tracebacks, when the search for an exception handler unwinds the execution stack, at each unwound level a traceback object is inserted in front of the current traceback. When an exception handler is entered, the stack trace is made available to the program. (See section [The try statement](#compound_stmts--try).) It is accessible as the third item of the tuple returned by [`sys.exc_info()`](https://docs.python.org/3/library/sys.html#sys.exc_info), and as the [`__traceback__`](https://docs.python.org/3/library/exceptions.html#BaseException.__traceback__) attribute of the caught exception.

When the program contains no suitable handler, the stack trace is written (nicely formatted) to the standard error stream; if the interpreter is interactive, it is also made available to the user as [`sys.last_traceback`](https://docs.python.org/3/library/sys.html#sys.last_traceback).

For explicitly created tracebacks, it is up to the creator of the traceback to determine how the [`tb_next`](#datamodel--traceback.tb_next) attributes should be linked to form a full stack trace.

Special read-only attributes:

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr class="odd">
<td><dl>
<dt>traceback.tb_frame</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Points to the execution <a href="#datamodel--frame-objects">frame</a> of the current level.</p>
<p>Accessing this attribute raises an <a href="https://docs.python.org/3/library/sys.html#auditing">auditing event</a> <code>object.__getattr__</code> with arguments <code>obj</code> and <code>"tb_frame"</code>.</p></td>
</tr>
<tr class="even">
<td><dl>
<dt>traceback.tb_lineno</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Gives the line number where the exception occurred</p></td>
</tr>
<tr class="odd">
<td><dl>
<dt>traceback.tb_lasti</dt>
<dd>
&#10;</dd>
</dl></td>
<td><p>Indicates the “precise instruction”.</p></td>
</tr>
</tbody>
</table>

The line number and last instruction in the traceback may differ from the line number of its [frame object](#datamodel--frame-objects) if the exception occurred in a [`try`](#compound_stmts--try) statement with no matching except clause or with a [`finally`](#compound_stmts--finally) clause.

traceback.tb_next  
The special writable attribute `tb_next` is the next level in the stack trace (towards the frame where the exception occurred), or `None` if there is no next level.

Changed in version 3.7: This attribute is now writable

#### 3.2.13.4. Slice objects {#datamodel--slice-objects}

Slice objects are used to represent slices for [`__getitem__()`](#datamodel--object.__getitem__) methods. They are also created by the built-in [`slice()`](https://docs.python.org/3/library/functions.html#slice) function.

Special read-only attributes: [`start`](https://docs.python.org/3/library/functions.html#slice.start) is the lower bound; [`stop`](https://docs.python.org/3/library/functions.html#slice.stop) is the upper bound; [`step`](https://docs.python.org/3/library/functions.html#slice.step) is the step value; each is `None` if omitted. These attributes can have any type.

Slice objects support one method:

slice.indices(*self*, *length*)  
This method takes a single integer argument *length* and computes information about the slice that the slice object would describe if applied to a sequence of *length* items. It returns a tuple of three integers; respectively these are the *start* and *stop* indices and the *step* or stride length of the slice. Missing or out-of-bounds indices are handled in a manner consistent with regular slices.

#### 3.2.13.5. Static method objects {#datamodel--static-method-objects}

Static method objects provide a way of defeating the transformation of function objects to method objects described above. A static method object is a wrapper around any other object, usually a user-defined method object. When a static method object is retrieved from a class or a class instance, the object actually returned is the wrapped object, which is not subject to any further transformation. Static method objects are also callable. Static method objects are created by the built-in [`staticmethod()`](https://docs.python.org/3/library/functions.html#staticmethod) constructor.

#### 3.2.13.6. Class method objects {#datamodel--class-method-objects}

A class method object, like a static method object, is a wrapper around another object that alters the way in which that object is retrieved from classes and class instances. The behaviour of class method objects upon such retrieval is described above, under [“instance methods”](#datamodel--instance-methods). Class method objects are created by the built-in [`classmethod()`](https://docs.python.org/3/library/functions.html#classmethod) constructor.

<span id="datamodel--specialnames"></span>

## 3.3. Special method names {#datamodel--special-method-names}

A class can implement certain operations that are invoked by special syntax (such as arithmetic operations or subscripting and slicing) by defining methods with special names. This is Python’s approach to *operator overloading*, allowing classes to define their own behavior with respect to language operators. For instance, if a class defines a method named [`__getitem__()`](#datamodel--object.__getitem__), and `x` is an instance of this class, then `x[i]` is roughly equivalent to `type(x).__getitem__(x, i)`. Except where mentioned, attempts to execute an operation raise an exception when no appropriate method is defined (typically [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError) or [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError)).

Setting a special method to `None` indicates that the corresponding operation is not available. For example, if a class sets [`__iter__()`](#datamodel--object.__iter__) to `None`, the class is not iterable, so calling [`iter()`](https://docs.python.org/3/library/functions.html#iter) on its instances will raise a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) (without falling back to [`__getitem__()`](#datamodel--object.__getitem__)). [\[2\]](#datamodel--id21){#datamodel--id12}

When implementing a class that emulates any built-in type, it is important that the emulation only be implemented to the degree that it makes sense for the object being modelled. For example, some sequences may work well with retrieval of individual elements, but extracting a slice may not make sense. (One example of this is the [NodeList](https://docs.python.org/3/library/xml.dom.html#dom-nodelist-objects) interface in the W3C’s Document Object Model.)

<span id="datamodel--customization"></span>

### 3.3.1. Basic customization {#datamodel--basic-customization}

object.\_\_new\_\_(*cls*\[, *...*\])  
Called to create a new instance of class *cls*. `__new__()` is a static method (special-cased so you need not declare it as such) that takes the class of which an instance was requested as its first argument. The remaining arguments are those passed to the object constructor expression (the call to the class). The return value of `__new__()` should be the new object instance (usually an instance of *cls*).

Typical implementations create a new instance of the class by invoking the superclass’s `__new__()` method using `super().__new__(cls[, ...])` with appropriate arguments and then modifying the newly created instance as necessary before returning it.

If `__new__()` is invoked during object construction and it returns an instance of *cls*, then the new instance’s [`__init__()`](#datamodel--object.__init__) method will be invoked like `__init__(self[, ...])`, where *self* is the new instance and the remaining arguments are the same as were passed to the object constructor.

If `__new__()` does not return an instance of *cls*, then the new instance’s [`__init__()`](#datamodel--object.__init__) method will not be invoked.

`__new__()` is intended mainly to allow subclasses of immutable types (like int, str, or tuple) to customize instance creation. It is also commonly overridden in custom metaclasses in order to customize class creation.

<!-- -->

object.\_\_init\_\_(*self*\[, *...*\])  
Called after the instance has been created (by [`__new__()`](#datamodel--object.__new__)), but before it is returned to the caller. The arguments are those passed to the class constructor expression. If a base class has an `__init__()` method, the derived class’s `__init__()` method, if any, must explicitly call it to ensure proper initialization of the base class part of the instance; for example: `super().__init__([args...])`.

Because [`__new__()`](#datamodel--object.__new__) and `__init__()` work together in constructing objects (`__new__()` to create it, and `__init__()` to customize it), no non-`None` value may be returned by `__init__()`; doing so will cause a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) to be raised at runtime.

<!-- -->

object.\_\_del\_\_(*self*)  
Called when the instance is about to be destroyed. This is also called a finalizer or (improperly) a destructor. If a base class has a `__del__()` method, the derived class’s `__del__()` method, if any, must explicitly call it to ensure proper deletion of the base class part of the instance.

It is possible (though not recommended!) for the `__del__()` method to postpone destruction of the instance by creating a new reference to it. This is called object *resurrection*. It is implementation-dependent whether `__del__()` is called a second time when a resurrected object is about to be destroyed; the current [CPython](https://docs.python.org/3/glossary.html#term-CPython) implementation only calls it once.

It is not guaranteed that `__del__()` methods are called for objects that still exist when the interpreter exits. [`weakref.finalize`](https://docs.python.org/3/library/weakref.html#weakref.finalize) provides a straightforward way to register a cleanup function to be called when an object is garbage collected.

Note

`del x` doesn’t directly call `x.__del__()` — the former decrements the reference count for `x` by one, and the latter is only called when `x`’s reference count reaches zero.

**CPython implementation detail:** It is possible for a reference cycle to prevent the reference count of an object from going to zero. In this case, the cycle will be later detected and deleted by the [cyclic garbage collector](https://docs.python.org/3/glossary.html#term-garbage-collection). A common cause of reference cycles is when an exception has been caught in a local variable. The frame’s locals then reference the exception, which references its own traceback, which references the locals of all frames caught in the traceback.

See also

Documentation for the [`gc`](https://docs.python.org/3/library/gc.html#module-gc) module.

Warning

Due to the precarious circumstances under which `__del__()` methods are invoked, exceptions that occur during their execution are ignored, and a warning is printed to `sys.stderr` instead. In particular:

- `__del__()` can be invoked when arbitrary code is being executed, including from any arbitrary thread. If `__del__()` needs to take a lock or invoke any other blocking resource, it may deadlock as the resource may already be taken by the code that gets interrupted to execute `__del__()`.

- `__del__()` can be executed during interpreter shutdown. As a consequence, the global variables it needs to access (including other modules) may already have been deleted or set to `None`. Python guarantees that globals whose name begins with a single underscore are deleted from their module before other globals are deleted; if no other references to such globals exist, this may help in assuring that imported modules are still available at the time when the `__del__()` method is called.

<span id="datamodel--index-81"></span>

<!-- -->

object.\_\_repr\_\_(*self*)  
Called by the [`repr()`](https://docs.python.org/3/library/functions.html#repr) built-in function to compute the “official” string representation of an object. If at all possible, this should look like a valid Python expression that could be used to recreate an object with the same value (given an appropriate environment). If this is not possible, a string of the form `<...some useful description...>` should be returned. The return value must be a string object. If a class defines `__repr__()` but not [`__str__()`](#datamodel--object.__str__), then `__repr__()` is also used when an “informal” string representation of instances of that class is required.

This is typically used for debugging, so it is important that the representation is information-rich and unambiguous. A default implementation is provided by the [`object`](https://docs.python.org/3/library/functions.html#object) class itself.

<span id="datamodel--index-82"></span>

<!-- -->

object.\_\_str\_\_(*self*)  
Called by [`str(object)`](https://docs.python.org/3/library/stdtypes.html#str), the default [`__format__()`](#datamodel--object.__format__) implementation, and the built-in function [`print()`](https://docs.python.org/3/library/functions.html#print), to compute the “informal” or nicely printable string representation of an object. The return value must be a [str](https://docs.python.org/3/library/stdtypes.html#textseq) object.

This method differs from [`object.__repr__()`](#datamodel--object.__repr__) in that there is no expectation that `__str__()` return a valid Python expression: a more convenient or concise representation can be used.

The default implementation defined by the built-in type [`object`](https://docs.python.org/3/library/functions.html#object) calls [`object.__repr__()`](#datamodel--object.__repr__).

<!-- -->

object.\_\_bytes\_\_(*self*)  
Called by [bytes](https://docs.python.org/3/library/functions.html#func-bytes) to compute a byte-string representation of an object. This should return a [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes) object. The [`object`](https://docs.python.org/3/library/functions.html#object) class itself does not provide this method.

<span id="datamodel--index-84"></span>

<!-- -->

object.\_\_format\_\_(*self*, *format_spec*)  
Called by the [`format()`](https://docs.python.org/3/library/functions.html#format) built-in function, and by extension, evaluation of [formatted string literals](#lexical_analysis--f-strings) and the [`str.format()`](https://docs.python.org/3/library/stdtypes.html#str.format) method, to produce a “formatted” string representation of an object. The *format_spec* argument is a string that contains a description of the formatting options desired. The interpretation of the *format_spec* argument is up to the type implementing `__format__()`, however most classes will either delegate formatting to one of the built-in types, or use a similar formatting option syntax.

See [Format specification mini-language](https://docs.python.org/3/library/string.html#formatspec) for a description of the standard formatting syntax.

The return value must be a string object.

The default implementation by the [`object`](https://docs.python.org/3/library/functions.html#object) class should be given an empty *format_spec* string. It delegates to [`__str__()`](#datamodel--object.__str__).

Changed in version 3.4: The \_\_format\_\_ method of `object` itself raises a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) if passed any non-empty string.

Changed in version 3.7: `object.__format__(x, '')` is now equivalent to `str(x)` rather than `format(str(x), '')`.

<!-- -->

object.\_\_lt\_\_(*self*, *other*)  
object.\_\_le\_\_(*self*, *other*)  
object.\_\_eq\_\_(*self*, *other*)  
object.\_\_ne\_\_(*self*, *other*)  
object.\_\_gt\_\_(*self*, *other*)  
object.\_\_ge\_\_(*self*, *other*)  
These are the so-called “rich comparison” methods. The correspondence between operator symbols and method names is as follows: `x<y` calls `x.__lt__(y)`, `x<=y` calls `x.__le__(y)`, `x==y` calls `x.__eq__(y)`, `x!=y` calls `x.__ne__(y)`, `x>y` calls `x.__gt__(y)`, and `x>=y` calls `x.__ge__(y)`.

A rich comparison method may return the singleton [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented) if it does not implement the operation for a given pair of arguments. By convention, `False` and `True` are returned for a successful comparison. However, these methods can return any value, so if the comparison operator is used in a Boolean context (e.g., in the condition of an `if` statement), Python will call [`bool()`](https://docs.python.org/3/library/functions.html#bool) on the value to determine if the result is true or false.

By default, `object` implements `__eq__()` by using `is`, returning [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented) in the case of a false comparison: `True if x is y else NotImplemented`. For `__ne__()`, by default it delegates to `__eq__()` and inverts the result unless it is `NotImplemented`. There are no other implied relationships among the comparison operators or default implementations; for example, the truth of `(x<y or x==y)` does not imply `x<=y`. To automatically generate ordering operations from a single root operation, see [`@functools.total_ordering`](https://docs.python.org/3/library/functools.html#functools.total_ordering).

By default, the [`object`](https://docs.python.org/3/library/functions.html#object) class provides implementations consistent with [Value comparisons](#expressions--expressions-value-comparisons): equality compares according to object identity, and order comparisons raise [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError). Each default method may generate these results directly, but may also return [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented).

See the paragraph on [`__hash__()`](#datamodel--object.__hash__) for some important notes on creating [hashable](https://docs.python.org/3/glossary.html#term-hashable) objects which support custom comparison operations and are usable as dictionary keys.

There are no swapped-argument versions of these methods (to be used when the left argument does not support the operation but the right argument does); rather, `__lt__()` and `__gt__()` are each other’s reflection, `__le__()` and `__ge__()` are each other’s reflection, and `__eq__()` and `__ne__()` are their own reflection. If the operands are of different types, and the right operand’s type is a direct or indirect subclass of the left operand’s type, the reflected method of the right operand has priority, otherwise the left operand’s method has priority. Virtual subclassing is not considered.

When no appropriate method returns any value other than [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented), the `==` and `!=` operators will fall back to `is` and `is not`, respectively.

<!-- -->

object.\_\_hash\_\_(*self*)  
Called by built-in function [`hash()`](https://docs.python.org/3/library/functions.html#hash) and for operations on members of hashed collections including [`set`](https://docs.python.org/3/library/stdtypes.html#set), [`frozenset`](https://docs.python.org/3/library/stdtypes.html#frozenset), and [`dict`](https://docs.python.org/3/library/stdtypes.html#dict). The `__hash__()` method should return an integer. The only required property is that objects which compare equal have the same hash value; it is advised to mix together the hash values of the components of the object that also play a part in comparison of objects by packing them into a tuple and hashing the tuple. Example:

    def __hash__(self):
        return hash((self.name, self.nick, self.color))

Note

[`hash()`](https://docs.python.org/3/library/functions.html#hash) truncates the value returned from an object’s custom `__hash__()` method to the size of a [`Py_ssize_t`](https://docs.python.org/3/c-api/intro.html#c.Py_ssize_t). This is typically 8 bytes on 64-bit builds and 4 bytes on 32-bit builds. If an object’s `__hash__()` must interoperate on builds of different bit sizes, be sure to check the width on all supported builds. An easy way to do this is with `python -c "import sys; print(sys.hash_info.width)"`.

If a class does not define an [`__eq__()`](#datamodel--object.__eq__) method it should not define a `__hash__()` operation either; if it defines `__eq__()` but not `__hash__()`, its instances will not be usable as items in hashable collections. If a class defines mutable objects and implements an `__eq__()` method, it should not implement `__hash__()`, since the implementation of [hashable](https://docs.python.org/3/glossary.html#term-hashable) collections requires that a key’s hash value is immutable (if the object’s hash value changes, it will be in the wrong hash bucket).

User-defined classes have [`__eq__()`](#datamodel--object.__eq__) and `__hash__()` methods by default (inherited from the [`object`](https://docs.python.org/3/library/functions.html#object) class); with them, all objects compare unequal (except with themselves) and `x.__hash__()` returns an appropriate value such that `x == y` implies both that `x is y` and `hash(x) == hash(y)`.

A class that overrides [`__eq__()`](#datamodel--object.__eq__) and does not define `__hash__()` will have its `__hash__()` implicitly set to `None`. When the `__hash__()` method of a class is `None`, instances of the class will raise an appropriate [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) when a program attempts to retrieve their hash value, and will also be correctly identified as unhashable when checking `isinstance(obj, collections.abc.Hashable)`.

If a class that overrides [`__eq__()`](#datamodel--object.__eq__) needs to retain the implementation of `__hash__()` from a parent class, the interpreter must be told this explicitly by setting `__hash__ = <ParentClass>.__hash__`.

If a class that does not override [`__eq__()`](#datamodel--object.__eq__) wishes to suppress hash support, it should include `__hash__ = None` in the class definition. A class which defines its own `__hash__()` that explicitly raises a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) would be incorrectly identified as hashable by an `isinstance(obj, collections.abc.Hashable)` call.

Note

By default, the `__hash__()` values of str and bytes objects are “salted” with an unpredictable random value. Although they remain constant within an individual Python process, they are not predictable between repeated invocations of Python.

This is intended to provide protection against a denial-of-service caused by carefully chosen inputs that exploit the worst case performance of a dict insertion, *O*(*n*<sup>2</sup>) complexity. See <https://ocert.org/advisories/ocert-2011-003.html> for details.

Changing hash values affects the iteration order of sets. Python has never made guarantees about this ordering (and it typically varies between 32-bit and 64-bit builds).

See also <span id="datamodel--index-87"></span>[`PYTHONHASHSEED`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED).

Changed in version 3.3: Hash randomization is enabled by default.

<!-- -->

object.\_\_bool\_\_(*self*)  
Called to implement truth value testing and the built-in operation `bool()`; should return `False` or `True`. When this method is not defined, [`__len__()`](#datamodel--object.__len__) is called, if it is defined, and the object is considered true if its result is nonzero. If a class defines neither `__len__()` nor `__bool__()` (which is true of the [`object`](https://docs.python.org/3/library/functions.html#object) class itself), all its instances are considered true.

<span id="datamodel--attribute-access"></span>

### 3.3.2. Customizing attribute access {#datamodel--customizing-attribute-access}

The following methods can be defined to customize the meaning of attribute access (use of, assignment to, or deletion of `x.name`) for class instances.

object.\_\_getattr\_\_(*self*, *name*)  
Called when the default attribute access fails with an [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError) (either [`__getattribute__()`](#datamodel--object.__getattribute__) raises an `AttributeError` because *name* is not an instance attribute or an attribute in the class tree for `self`; or [`__get__()`](#datamodel--object.__get__) of a *name* property raises `AttributeError`). This method should either return the (computed) attribute value or raise an `AttributeError` exception. The [`object`](https://docs.python.org/3/library/functions.html#object) class itself does not provide this method.

Note that if the attribute is found through the normal mechanism, `__getattr__()` is not called. (This is an intentional asymmetry between `__getattr__()` and [`__setattr__()`](#datamodel--object.__setattr__).) This is done both for efficiency reasons and because otherwise `__getattr__()` would have no way to access other attributes of the instance. Note that at least for instance variables, you can take total control by not inserting any values in the instance attribute dictionary (but instead inserting them in another object). See the [`__getattribute__()`](#datamodel--object.__getattribute__) method below for a way to actually get total control over attribute access.

<!-- -->

object.\_\_getattribute\_\_(*self*, *name*)  
Called unconditionally to implement attribute accesses for instances of the class. If the class also defines [`__getattr__()`](#datamodel--object.__getattr__), the latter will not be called unless `__getattribute__()` either calls it explicitly or raises an [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError). This method should return the (computed) attribute value or raise an `AttributeError` exception. In order to avoid infinite recursion in this method, its implementation should always call the base class method with the same name to access any attributes it needs, for example, `object.__getattribute__(self, name)`.

Note

This method may still be bypassed when looking up special methods as the result of implicit invocation via language syntax or [built-in functions](#datamodel--builtin-functions). See [Special method lookup](#datamodel--special-lookup).

For certain sensitive attribute accesses, raises an [auditing event](https://docs.python.org/3/library/sys.html#auditing) `object.__getattr__` with arguments `obj` and `name`.

<!-- -->

object.\_\_setattr\_\_(*self*, *name*, *value*)  
Called when an attribute assignment is attempted. This is called instead of the normal mechanism (i.e. store the value in the instance dictionary). *name* is the attribute name, *value* is the value to be assigned to it.

If `__setattr__()` wants to assign to an instance attribute, it should call the base class method with the same name, for example, `object.__setattr__(self, name, value)`.

For certain sensitive attribute assignments, raises an [auditing event](https://docs.python.org/3/library/sys.html#auditing) `object.__setattr__` with arguments `obj`, `name`, `value`.

<!-- -->

object.\_\_delattr\_\_(*self*, *name*)  
Like [`__setattr__()`](#datamodel--object.__setattr__) but for attribute deletion instead of assignment. This should only be implemented if `del obj.name` is meaningful for the object.

For certain sensitive attribute deletions, raises an [auditing event](https://docs.python.org/3/library/sys.html#auditing) `object.__delattr__` with arguments `obj` and `name`.

<!-- -->

object.\_\_dir\_\_(*self*)  
Called when [`dir()`](https://docs.python.org/3/library/functions.html#dir) is called on the object. An iterable must be returned. `dir()` converts the returned iterable to a list and sorts it.

#### 3.3.2.1. Customizing module attribute access {#datamodel--customizing-module-attribute-access}

module.\_\_getattr\_\_()  
module.\_\_dir\_\_()  

Special names `__getattr__` and `__dir__` can be also used to customize access to module attributes. The `__getattr__` function at the module level should accept one argument which is the name of an attribute and return the computed value or raise an [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError). If an attribute is not found on a module object through the normal lookup, i.e. [`object.__getattribute__()`](#datamodel--object.__getattribute__), then `__getattr__` is searched in the module `__dict__` before raising an `AttributeError`. If found, it is called with the attribute name and the result is returned.

The `__dir__` function should accept no arguments, and return an iterable of strings that represents the names accessible on module. If present, this function overrides the standard [`dir()`](https://docs.python.org/3/library/functions.html#dir) search on a module.

module.\_\_class\_\_  

For a more fine grained customization of the module behavior (setting attributes, properties, etc.), one can set the `__class__` attribute of a module object to a subclass of [`types.ModuleType`](https://docs.python.org/3/library/types.html#types.ModuleType). For example:

    import sys
    from types import ModuleType

    class VerboseModule(ModuleType):
        def __repr__(self):
            return f'Verbose {self.__name__}'

        def __setattr__(self, attr, value):
            print(f'Setting {attr}...')
            super().__setattr__(attr, value)

    sys.modules[__name__].__class__ = VerboseModule

Note

Defining module `__getattr__` and setting module `__class__` only affect lookups made using the attribute access syntax – directly accessing the module globals (whether by code within the module, or via a reference to the module’s globals dictionary) is unaffected.

Changed in version 3.5: `__class__` module attribute is now writable.

Added in version 3.7: `__getattr__` and `__dir__` module attributes.

See also

<span id="datamodel--index-90"></span>[**PEP 562**](https://peps.python.org/pep-0562/) - Module \_\_getattr\_\_ and \_\_dir\_\_  
Describes the `__getattr__` and `__dir__` functions on modules.

<span id="datamodel--descriptors"></span>

#### 3.3.2.2. Implementing Descriptors {#datamodel--implementing-descriptors}

The following methods only apply when an instance of the class containing the method (a so-called *descriptor* class) appears in an *owner* class (the descriptor must be in either the owner’s class dictionary or in the class dictionary for one of its parents). In the examples below, “the attribute” refers to the attribute whose name is the key of the property in the owner class’ [`__dict__`](#datamodel--object.__dict__). The [`object`](https://docs.python.org/3/library/functions.html#object) class itself does not implement any of these protocols.

object.\_\_get\_\_(*self*, *instance*, *owner=None*)  
Called to get the attribute of the owner class (class attribute access) or of an instance of that class (instance attribute access). The optional *owner* argument is the owner class, while *instance* is the instance that the attribute was accessed through, or `None` when the attribute is accessed through the *owner*.

This method should return the computed attribute value or raise an [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError) exception.

<span id="datamodel--index-91"></span>[**PEP 252**](https://peps.python.org/pep-0252/) specifies that `__get__()` is callable with one or two arguments. Python’s own built-in descriptors support this specification; however, it is likely that some third-party tools have descriptors that require both arguments. Python’s own [`__getattribute__()`](#datamodel--object.__getattribute__) implementation always passes in both arguments whether they are required or not.

<!-- -->

object.\_\_set\_\_(*self*, *instance*, *value*)  
Called to set the attribute on an instance *instance* of the owner class to a new value, *value*.

Note, adding `__set__()` or [`__delete__()`](#datamodel--object.__delete__) changes the kind of descriptor to a “data descriptor”. See [Invoking Descriptors](#datamodel--descriptor-invocation) for more details.

<!-- -->

object.\_\_delete\_\_(*self*, *instance*)  
Called to delete the attribute on an instance *instance* of the owner class.

Instances of descriptors may also have the `__objclass__` attribute present:

object.\_\_objclass\_\_  
The attribute `__objclass__` is interpreted by the [`inspect`](https://docs.python.org/3/library/inspect.html#module-inspect) module as specifying the class where this object was defined (setting this appropriately can assist in runtime introspection of dynamic class attributes). For callables, it may indicate that an instance of the given type (or a subclass) is expected or required as the first positional argument (for example, CPython sets this attribute for unbound methods that are implemented in C).

<span id="datamodel--descriptor-invocation"></span>

#### 3.3.2.3. Invoking Descriptors {#datamodel--invoking-descriptors}

In general, a descriptor is an object attribute with “binding behavior”, one whose attribute access has been overridden by methods in the descriptor protocol: [`__get__()`](#datamodel--object.__get__), [`__set__()`](#datamodel--object.__set__), and [`__delete__()`](#datamodel--object.__delete__). If any of those methods are defined for an object, it is said to be a descriptor.

The default behavior for attribute access is to get, set, or delete the attribute from an object’s dictionary. For instance, `a.x` has a lookup chain starting with `a.__dict__['x']`, then `type(a).__dict__['x']`, and continuing through the base classes of `type(a)` excluding metaclasses.

However, if the looked-up value is an object defining one of the descriptor methods, then Python may override the default behavior and invoke the descriptor method instead. Where this occurs in the precedence chain depends on which descriptor methods were defined and how they were called.

The starting point for descriptor invocation is a binding, `a.x`. How the arguments are assembled depends on `a`:

Direct Call  
The simplest and least common call is when user code directly invokes a descriptor method: `x.__get__(a)`.

Instance Binding  
If binding to an object instance, `a.x` is transformed into the call: `type(a).__dict__['x'].__get__(a, type(a))`.

Class Binding  
If binding to a class, `A.x` is transformed into the call: `A.__dict__['x'].__get__(None, A)`.

Super Binding  
A dotted lookup such as `super(A, a).x` searches `a.__class__.__mro__` for a base class `B` following `A` and then returns `B.__dict__['x'].__get__(a, A)`. If not a descriptor, `x` is returned unchanged.

For instance bindings, the precedence of descriptor invocation depends on which descriptor methods are defined. A descriptor can define any combination of [`__get__()`](#datamodel--object.__get__), [`__set__()`](#datamodel--object.__set__) and [`__delete__()`](#datamodel--object.__delete__). If it does not define `__get__()`, then accessing the attribute will return the descriptor object itself unless there is a value in the object’s instance dictionary. If the descriptor defines `__set__()` and/or `__delete__()`, it is a data descriptor; if it defines neither, it is a non-data descriptor. Normally, data descriptors define both `__get__()` and `__set__()`, while non-data descriptors have just the `__get__()` method. Data descriptors with `__get__()` and `__set__()` (and/or `__delete__()`) defined always override a redefinition in an instance dictionary. In contrast, non-data descriptors can be overridden by instances.

Python methods (including those decorated with [`@staticmethod`](https://docs.python.org/3/library/functions.html#staticmethod) and [`@classmethod`](https://docs.python.org/3/library/functions.html#classmethod)) are implemented as non-data descriptors. Accordingly, instances can redefine and override methods. This allows individual instances to acquire behaviors that differ from other instances of the same class.

The [`@property`](https://docs.python.org/3/library/functions.html#property) decorator is implemented as a data descriptor. Accordingly, instances cannot override the behavior of a property.

<span id="datamodel--id13"></span>

#### 3.3.2.4. \_\_slots\_\_ {#datamodel--slots}

*\_\_slots\_\_* allow us to explicitly declare data members (like properties) and deny the creation of [`__dict__`](#datamodel--object.__dict__) and *\_\_weakref\_\_* (unless explicitly declared in *\_\_slots\_\_* or available in a parent.)

The space saved over using [`__dict__`](#datamodel--object.__dict__) can be significant. Attribute lookup speed can be significantly improved as well.

object.\_\_slots\_\_  
This class variable can be assigned a string, iterable, or sequence of strings with variable names used by instances. *\_\_slots\_\_* reserves space for the declared variables and prevents the automatic creation of [`__dict__`](#datamodel--object.__dict__) and *\_\_weakref\_\_* for each instance.

Notes on using *\_\_slots\_\_*:

- When inheriting from a class without *\_\_slots\_\_*, the [`__dict__`](#datamodel--object.__dict__) and *\_\_weakref\_\_* attribute of the instances will always be accessible.

- Without a [`__dict__`](#datamodel--object.__dict__) variable, instances cannot be assigned new variables not listed in the *\_\_slots\_\_* definition. Attempts to assign to an unlisted variable name raises [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError). If dynamic assignment of new variables is desired, then add `'__dict__'` to the sequence of strings in the *\_\_slots\_\_* declaration.

- Without a *\_\_weakref\_\_* variable for each instance, classes defining *\_\_slots\_\_* do not support [`weak references`](https://docs.python.org/3/library/weakref.html#module-weakref) to its instances. If weak reference support is needed, then add `'__weakref__'` to the sequence of strings in the *\_\_slots\_\_* declaration.

- *\_\_slots\_\_* are implemented at the class level by creating [descriptors](#datamodel--descriptors) for each variable name. As a result, class attributes cannot be used to set default values for instance variables defined by *\_\_slots\_\_*; otherwise, the class attribute would overwrite the descriptor assignment.

- The action of a *\_\_slots\_\_* declaration is not limited to the class where it is defined. *\_\_slots\_\_* declared in parents are available in child classes. However, instances of a child subclass will get a [`__dict__`](#datamodel--object.__dict__) and *\_\_weakref\_\_* unless the subclass also defines *\_\_slots\_\_* (which should only contain names of any *additional* slots).

- If a class defines a slot also defined in a base class, the instance variable defined by the base class slot is inaccessible (except by retrieving its descriptor directly from the base class). This renders the meaning of the program undefined. In the future, a check may be added to prevent this.

- [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) will be raised if nonempty *\_\_slots\_\_* are defined for a class derived from a [`"variable-length" built-in type`](https://docs.python.org/3/c-api/typeobj.html#c.PyTypeObject.tp_itemsize) such as [`int`](https://docs.python.org/3/library/functions.html#int), [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes), and [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple).

- Any non-string [iterable](https://docs.python.org/3/glossary.html#term-iterable) may be assigned to *\_\_slots\_\_*.

- If a [`dictionary`](https://docs.python.org/3/library/stdtypes.html#dict) is used to assign *\_\_slots\_\_*, the dictionary keys will be used as the slot names. The values of the dictionary can be used to provide per-attribute docstrings that will be recognised by [`inspect.getdoc()`](https://docs.python.org/3/library/inspect.html#inspect.getdoc) and displayed in the output of [`help()`](https://docs.python.org/3/library/functions.html#help).

- [`__class__`](#datamodel--object.__class__) assignment works only if both classes have the same *\_\_slots\_\_*.

- [Multiple inheritance](https://docs.python.org/3/tutorial/classes.html#tut-multiple) with multiple slotted parent classes can be used, but only one parent is allowed to have attributes created by slots (the other bases must have empty slot layouts) - violations raise [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError).

- If an [iterator](https://docs.python.org/3/glossary.html#term-iterator) is used for *\_\_slots\_\_* then a [descriptor](https://docs.python.org/3/glossary.html#term-descriptor) is created for each of the iterator’s values. However, the *\_\_slots\_\_* attribute will be an empty iterator.

<span id="datamodel--class-customization"></span>

### 3.3.3. Customizing class creation {#datamodel--customizing-class-creation}

Whenever a class inherits from another class, [`__init_subclass__()`](#datamodel--object.__init_subclass__) is called on the parent class. This way, it is possible to write classes which change the behavior of subclasses. This is closely related to class decorators, but where class decorators only affect the specific class they’re applied to, `__init_subclass__` solely applies to future subclasses of the class defining the method.

*classmethod* object.\_\_init_subclass\_\_(*cls*)  
This method is called whenever the containing class is subclassed. *cls* is then the new subclass. If defined as a normal instance method, this method is implicitly converted to a class method.

Keyword arguments which are given to a new class are passed to the parent class’s `__init_subclass__`. For compatibility with other classes using `__init_subclass__`, one should take out the needed keyword arguments and pass the others over to the base class, as in:

    class Philosopher:
        def __init_subclass__(cls, /, default_name, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.default_name = default_name

    class AustralianPhilosopher(Philosopher, default_name="Bruce"):
        pass

The default implementation `object.__init_subclass__` does nothing, but raises an error if it is called with any arguments.

Note

The metaclass hint `metaclass` is consumed by the rest of the type machinery, and is never passed to `__init_subclass__` implementations. The actual metaclass (rather than the explicit hint) can be accessed as `type(cls)`.

Added in version 3.6.

When a class is created, `type.__new__()` scans the class variables and makes callbacks to those with a [`__set_name__()`](#datamodel--object.__set_name__) hook.

object.\_\_set_name\_\_(*self*, *owner*, *name*)  
Automatically called at the time the owning class *owner* is created. The object has been assigned to *name* in that class:

    class A:
        x = C()  # Automatically calls: x.__set_name__(A, 'x')

If the class variable is assigned after the class is created, `__set_name__()` will not be called automatically. If needed, `__set_name__()` can be called directly:

    class A:
       pass

    c = C()
    A.x = c                  # The hook is not called
    c.__set_name__(A, 'x')   # Manually invoke the hook

See [Creating the class object](#datamodel--class-object-creation) for more details.

Added in version 3.6.

<span id="datamodel--id14"></span>

#### 3.3.3.1. Metaclasses {#datamodel--metaclasses}

By default, classes are constructed using [`type()`](https://docs.python.org/3/library/functions.html#type). The class body is executed in a new namespace and the class name is bound locally to the result of `type(name, bases, namespace)`.

The class creation process can be customized by passing the `metaclass` keyword argument in the class definition line, or by inheriting from an existing class that included such an argument. In the following example, both `MyClass` and `MySubclass` are instances of `Meta`:

    class Meta(type):
        pass

    class MyClass(metaclass=Meta):
        pass

    class MySubclass(MyClass):
        pass

Any other keyword arguments that are specified in the class definition are passed through to all metaclass operations described below.

When a class definition is executed, the following steps occur:

- MRO entries are resolved;

- the appropriate metaclass is determined;

- the class namespace is prepared;

- the class body is executed;

- the class object is created.

#### 3.3.3.2. Resolving MRO entries {#datamodel--resolving-mro-entries}

object.\_\_mro_entries\_\_(*self*, *bases*)  
If a base that appears in a class definition is not an instance of [`type`](https://docs.python.org/3/library/functions.html#type), then an `__mro_entries__()` method is searched on the base. If an `__mro_entries__()` method is found, the base is substituted with the result of a call to `__mro_entries__()` when creating the class. The method is called with the original bases tuple passed to the *bases* parameter, and must return a tuple of classes that will be used instead of the base. The returned tuple may be empty: in these cases, the original base is ignored.

See also

[`types.resolve_bases()`](https://docs.python.org/3/library/types.html#types.resolve_bases)  
Dynamically resolve bases that are not instances of [`type`](https://docs.python.org/3/library/functions.html#type).

[`types.get_original_bases()`](https://docs.python.org/3/library/types.html#types.get_original_bases)  
Retrieve a class’s “original bases” prior to modifications by [`__mro_entries__()`](#datamodel--object.__mro_entries__).

<span id="datamodel--index-93"></span>[**PEP 560**](https://peps.python.org/pep-0560/)  
Core support for typing module and generic types.

#### 3.3.3.3. Determining the appropriate metaclass {#datamodel--determining-the-appropriate-metaclass}

The appropriate metaclass for a class definition is determined as follows:

- if no bases and no explicit metaclass are given, then [`type()`](https://docs.python.org/3/library/functions.html#type) is used;

- if an explicit metaclass is given and it is *not* an instance of [`type()`](https://docs.python.org/3/library/functions.html#type), then it is used directly as the metaclass;

- if an instance of [`type()`](https://docs.python.org/3/library/functions.html#type) is given as the explicit metaclass, or bases are defined, then the most derived metaclass is used.

The most derived metaclass is selected from the explicitly specified metaclass (if any) and the metaclasses (i.e. `type(cls)`) of all specified base classes. The most derived metaclass is one which is a subtype of *all* of these candidate metaclasses. If none of the candidate metaclasses meets that criterion, then the class definition will fail with `TypeError`.

<span id="datamodel--prepare"></span>

#### 3.3.3.4. Preparing the class namespace {#datamodel--preparing-the-class-namespace}

Once the appropriate metaclass has been identified, then the class namespace is prepared. If the metaclass has a `__prepare__` attribute, it is called as `namespace = metaclass.__prepare__(name, bases, **kwds)` (where the additional keyword arguments, if any, come from the class definition). The `__prepare__` method should be implemented as a [`classmethod`](https://docs.python.org/3/library/functions.html#classmethod). The namespace returned by `__prepare__` is passed in to `__new__`, but when the final class object is created the namespace is copied into a new `dict`.

If the metaclass has no `__prepare__` attribute, then the class namespace is initialised as an empty ordered mapping.

See also

<span id="datamodel--index-96"></span>[**PEP 3115**](https://peps.python.org/pep-3115/) - Metaclasses in Python 3000  
Introduced the `__prepare__` namespace hook

#### 3.3.3.5. Executing the class body {#datamodel--executing-the-class-body}

The class body is executed (approximately) as `exec(body, globals(), namespace)`. The key difference from a normal call to [`exec()`](https://docs.python.org/3/library/functions.html#exec) is that lexical scoping allows the class body (including any methods) to reference names from the current and outer scopes when the class definition occurs inside a function.

However, even when the class definition occurs inside the function, methods defined inside the class still cannot see names defined at the class scope. Class variables must be accessed through the first parameter of instance or class methods, or through the implicit lexically scoped `__class__` reference described in the next section.

<span id="datamodel--class-object-creation"></span>

#### 3.3.3.6. Creating the class object {#datamodel--creating-the-class-object}

Once the class namespace has been populated by executing the class body, the class object is created by calling `metaclass(name, bases, namespace, **kwds)` (the additional keywords passed here are the same as those passed to `__prepare__`).

This class object is the one that will be referenced by the zero-argument form of [`super()`](https://docs.python.org/3/library/functions.html#super). `__class__` is an implicit closure reference created by the compiler if any methods in a class body refer to either `__class__` or `super`. This allows the zero argument form of `super()` to correctly identify the class being defined based on lexical scoping, while the class or instance that was used to make the current call is identified based on the first argument passed to the method.

**CPython implementation detail:** In CPython 3.6 and later, the `__class__` cell is passed to the metaclass as a `__classcell__` entry in the class namespace. If present, this must be propagated up to the `type.__new__` call in order for the class to be initialised correctly. Failing to do so will result in a [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) in Python 3.8.

When using the default metaclass [`type`](https://docs.python.org/3/library/functions.html#type), or any metaclass that ultimately calls `type.__new__`, the following additional customization steps are invoked after creating the class object:

1.  The `type.__new__` method collects all of the attributes in the class namespace that define a [`__set_name__()`](#datamodel--object.__set_name__) method;

2.  Those `__set_name__` methods are called with the class being defined and the assigned name of that particular attribute;

3.  The [`__init_subclass__()`](#datamodel--object.__init_subclass__) hook is called on the immediate parent of the new class in its method resolution order.

After the class object is created, it is passed to the class decorators included in the class definition (if any) and the resulting object is bound in the local namespace as the defined class.

When a new class is created by `type.__new__`, the object provided as the namespace parameter is copied to a new ordered mapping and the original object is discarded. The new copy is wrapped in a read-only proxy, which becomes the [`__dict__`](#datamodel--type.__dict__) attribute of the class object.

See also

<span id="datamodel--index-99"></span>[**PEP 3135**](https://peps.python.org/pep-3135/) - New super  
Describes the implicit `__class__` closure reference

#### 3.3.3.7. Uses for metaclasses {#datamodel--uses-for-metaclasses}

The potential uses for metaclasses are boundless. Some ideas that have been explored include enum, logging, interface checking, automatic delegation, automatic property creation, proxies, frameworks, and automatic resource locking/synchronization.

### 3.3.4. Customizing instance and subclass checks {#datamodel--customizing-instance-and-subclass-checks}

The following methods are used to override the default behavior of the [`isinstance()`](https://docs.python.org/3/library/functions.html#isinstance) and [`issubclass()`](https://docs.python.org/3/library/functions.html#issubclass) built-in functions.

In particular, the metaclass [`abc.ABCMeta`](https://docs.python.org/3/library/abc.html#abc.ABCMeta) implements these methods in order to allow the addition of Abstract Base Classes (ABCs) as “virtual base classes” to any class or type (including built-in types), including other ABCs.

type.\_\_instancecheck\_\_(*self*, *instance*)  
Return true if *instance* should be considered a (direct or indirect) instance of *class*. If defined, called to implement `isinstance(instance, class)`.

<!-- -->

type.\_\_subclasscheck\_\_(*self*, *subclass*)  
Return true if *subclass* should be considered a (direct or indirect) subclass of *class*. If defined, called to implement `issubclass(subclass, class)`.

Note that these methods are looked up on the type (metaclass) of a class. They cannot be defined as class methods in the actual class. This is consistent with the lookup of special methods that are called on instances, only in this case the instance is itself a class.

See also

<span id="datamodel--index-100"></span>[**PEP 3119**](https://peps.python.org/pep-3119/) - Introducing Abstract Base Classes  
Includes the specification for customizing [`isinstance()`](https://docs.python.org/3/library/functions.html#isinstance) and [`issubclass()`](https://docs.python.org/3/library/functions.html#issubclass) behavior through [`__instancecheck__()`](#datamodel--type.__instancecheck__) and [`__subclasscheck__()`](#datamodel--type.__subclasscheck__), with motivation for this functionality in the context of adding Abstract Base Classes (see the [`abc`](https://docs.python.org/3/library/abc.html#module-abc) module) to the language.

### 3.3.5. Emulating generic types {#datamodel--emulating-generic-types}

When using [type annotations](https://docs.python.org/3/glossary.html#term-annotation), it is often useful to *parameterize* a [generic type](https://docs.python.org/3/glossary.html#term-generic-type) using Python’s square-brackets notation. For example, the annotation `list[int]` might be used to signify a [`list`](https://docs.python.org/3/library/stdtypes.html#list) in which all the elements are of type [`int`](https://docs.python.org/3/library/functions.html#int).

See also

<span id="datamodel--index-101"></span>[**PEP 484**](https://peps.python.org/pep-0484/) - Type Hints  
Introducing Python’s framework for type annotations

[Generic Alias Types](https://docs.python.org/3/library/stdtypes.html#types-genericalias)  
Documentation for objects representing parameterized generic classes

[Generics](https://docs.python.org/3/library/typing.html#generics), [user-defined generics](https://docs.python.org/3/library/typing.html#user-defined-generics) and [`typing.Generic`](https://docs.python.org/3/library/typing.html#typing.Generic)  
Documentation on how to implement generic classes that can be parameterized at runtime and understood by static type-checkers.

A class can *generally* only be parameterized if it defines the special class method `__class_getitem__()`.

*classmethod* object.\_\_class_getitem\_\_(*cls*, *key*)  
Return an object representing the specialization of a generic class by type arguments found in *key*.

When defined on a class, `__class_getitem__()` is automatically a class method. As such, there is no need for it to be decorated with [`@classmethod`](https://docs.python.org/3/library/functions.html#classmethod) when it is defined.

#### 3.3.5.1. The purpose of *\_\_class_getitem\_\_* {#datamodel--the-purpose-of-class-getitem}

The purpose of [`__class_getitem__()`](#datamodel--object.__class_getitem__) is to allow runtime parameterization of standard-library generic classes in order to more easily apply [type hints](https://docs.python.org/3/glossary.html#term-type-hint) to these classes.

To implement custom generic classes that can be parameterized at runtime and understood by static type-checkers, users should either inherit from a standard library class that already implements [`__class_getitem__()`](#datamodel--object.__class_getitem__), or inherit from [`typing.Generic`](https://docs.python.org/3/library/typing.html#typing.Generic), which has its own implementation of `__class_getitem__()`.

Custom implementations of [`__class_getitem__()`](#datamodel--object.__class_getitem__) on classes defined outside of the standard library may not be understood by third-party type-checkers such as mypy. Using `__class_getitem__()` on any class for purposes other than type hinting is discouraged.

<span id="datamodel--classgetitem-versus-getitem"></span>

#### 3.3.5.2. *\_\_class_getitem\_\_* versus *\_\_getitem\_\_* {#datamodel--class-getitem-versus-getitem}

Usually, the [subscription](#expressions--subscriptions) of an object using square brackets will call the [`__getitem__()`](#datamodel--object.__getitem__) instance method defined on the object’s class. However, if the object being subscribed is itself a class, the class method [`__class_getitem__()`](#datamodel--object.__class_getitem__) may be called instead. `__class_getitem__()` should return a [GenericAlias](https://docs.python.org/3/library/stdtypes.html#types-genericalias) object if it is properly defined.

Presented with the [expression](https://docs.python.org/3/glossary.html#term-expression) `obj[x]`, the Python interpreter follows something like the following process to decide whether [`__getitem__()`](#datamodel--object.__getitem__) or [`__class_getitem__()`](#datamodel--object.__class_getitem__) should be called:

    from inspect import isclass

    def subscribe(obj, x):
        """Return the result of the expression 'obj[x]'"""

        class_of_obj = type(obj)

        # If the class of obj defines __getitem__,
        # call class_of_obj.__getitem__(obj, x)
        if hasattr(class_of_obj, '__getitem__'):
            return class_of_obj.__getitem__(obj, x)

        # Else, if obj is a class and defines __class_getitem__,
        # call obj.__class_getitem__(x)
        elif isclass(obj) and hasattr(obj, '__class_getitem__'):
            return obj.__class_getitem__(x)

        # Else, raise an exception
        else:
            raise TypeError(
                f"'{class_of_obj.__name__}' object is not subscriptable"
            )

In Python, all classes are themselves instances of other classes. The class of a class is known as that class’s [metaclass](https://docs.python.org/3/glossary.html#term-metaclass), and most classes have the [`type`](https://docs.python.org/3/library/functions.html#type) class as their metaclass. `type` does not define [`__getitem__()`](#datamodel--object.__getitem__), meaning that expressions such as `list[int]`, `dict[str, float]` and `tuple[str, bytes]` all result in [`__class_getitem__()`](#datamodel--object.__class_getitem__) being called:

    >>> # list has class "type" as its metaclass, like most classes:
    >>> type(list)
    <class 'type'>
    >>> type(dict) == type(list) == type(tuple) == type(str) == type(bytes)
    True
    >>> # "list[int]" calls "list.__class_getitem__(int)"
    >>> list[int]
    list[int]
    >>> # list.__class_getitem__ returns a GenericAlias object:
    >>> type(list[int])
    <class 'types.GenericAlias'>

However, if a class has a custom metaclass that defines [`__getitem__()`](#datamodel--object.__getitem__), subscribing the class may result in different behaviour. An example of this can be found in the [`enum`](https://docs.python.org/3/library/enum.html#module-enum) module:

    >>> from enum import Enum
    >>> class Menu(Enum):
    ...     """A breakfast menu"""
    ...     SPAM = 'spam'
    ...     BACON = 'bacon'
    ...
    >>> # Enum classes have a custom metaclass:
    >>> type(Menu)
    <class 'enum.EnumMeta'>
    >>> # EnumMeta defines __getitem__,
    >>> # so __class_getitem__ is not called,
    >>> # and the result is not a GenericAlias object:
    >>> Menu['SPAM']
    <Menu.SPAM: 'spam'>
    >>> type(Menu['SPAM'])
    <enum 'Menu'>

See also

<span id="datamodel--index-102"></span>[**PEP 560**](https://peps.python.org/pep-0560/) - Core Support for typing module and generic types  
Introducing [`__class_getitem__()`](#datamodel--object.__class_getitem__), and outlining when a [subscription](#expressions--subscriptions) results in `__class_getitem__()` being called instead of [`__getitem__()`](#datamodel--object.__getitem__)

<span id="datamodel--id15"></span>

### 3.3.6. Emulating callable objects {#datamodel--emulating-callable-objects}

object.\_\_call\_\_(*self*\[, *args...*\])  
Called when the instance is “called” as a function; if this method is defined, `x(arg1, arg2, ...)` roughly translates to `type(x).__call__(x, arg1, ...)`. The [`object`](https://docs.python.org/3/library/functions.html#object) class itself does not provide this method.

<span id="datamodel--sequence-types"></span>

### 3.3.7. Emulating container types {#datamodel--emulating-container-types}

The following methods can be defined to implement container objects. None of them are provided by the [`object`](https://docs.python.org/3/library/functions.html#object) class itself. Containers usually are [sequences](https://docs.python.org/3/glossary.html#term-sequence) (such as [`lists`](https://docs.python.org/3/library/stdtypes.html#list) or [`tuples`](https://docs.python.org/3/library/stdtypes.html#tuple)) or [mappings](https://docs.python.org/3/glossary.html#term-mapping) (like [dictionaries](https://docs.python.org/3/glossary.html#term-dictionary)), but can represent other containers as well. The first set of methods is used either to emulate a sequence or to emulate a mapping; the difference is that for a sequence, the allowable keys should be the integers *k* for which `0 <= k < N` where *N* is the length of the sequence, or [`slice`](https://docs.python.org/3/library/functions.html#slice) objects, which define a range of items. It is also recommended that mappings provide the methods `keys()`, `values()`, `items()`, `get()`, `clear()`, `setdefault()`, `pop()`, `popitem()`, `copy()`, and `update()` behaving similar to those for Python’s standard [`dictionary`](https://docs.python.org/3/library/stdtypes.html#dict) objects. The [`collections.abc`](https://docs.python.org/3/library/collections.abc.html#module-collections.abc) module provides a [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping) [abstract base class](https://docs.python.org/3/glossary.html#term-abstract-base-class) to help create those methods from a base set of [`__getitem__()`](#datamodel--object.__getitem__), [`__setitem__()`](#datamodel--object.__setitem__), [`__delitem__()`](#datamodel--object.__delitem__), and `keys()`.

Mutable sequences should provide methods [`append()`](https://docs.python.org/3/library/stdtypes.html#sequence.append), [`clear()`](https://docs.python.org/3/library/stdtypes.html#sequence.clear), [`count()`](https://docs.python.org/3/library/stdtypes.html#sequence.count), [`extend()`](https://docs.python.org/3/library/stdtypes.html#sequence.extend), [`index()`](https://docs.python.org/3/library/stdtypes.html#sequence.index), [`insert()`](https://docs.python.org/3/library/stdtypes.html#sequence.insert), [`pop()`](https://docs.python.org/3/library/stdtypes.html#sequence.pop), [`remove()`](https://docs.python.org/3/library/stdtypes.html#sequence.remove), and [`reverse()`](https://docs.python.org/3/library/stdtypes.html#sequence.reverse), like Python standard [`list`](https://docs.python.org/3/library/stdtypes.html#list) objects. Finally, sequence types should implement addition (meaning concatenation) and multiplication (meaning repetition) by defining the methods [`__add__()`](#datamodel--object.__add__), [`__radd__()`](#datamodel--object.__radd__), [`__iadd__()`](#datamodel--object.__iadd__), [`__mul__()`](#datamodel--object.__mul__), [`__rmul__()`](#datamodel--object.__rmul__) and [`__imul__()`](#datamodel--object.__imul__) described below; they should not define other numerical operators.

It is recommended that both mappings and sequences implement the [`__contains__()`](#datamodel--object.__contains__) method to allow efficient use of the `in` operator; for mappings, `in` should search the mapping’s keys; for sequences, it should search through the values. It is further recommended that both mappings and sequences implement the [`__iter__()`](#datamodel--object.__iter__) method to allow efficient iteration through the container; for mappings, `__iter__()` should iterate through the object’s keys; for sequences, it should iterate through the values.

object.\_\_len\_\_(*self*)  
Called to implement the built-in function [`len()`](https://docs.python.org/3/library/functions.html#len). Should return the length of the object, an integer `>=` 0. Also, an object that doesn’t define a [`__bool__()`](#datamodel--object.__bool__) method and whose `__len__()` method returns zero is considered to be false in a Boolean context.

**CPython implementation detail:** In CPython, the length is required to be at most [`sys.maxsize`](https://docs.python.org/3/library/sys.html#sys.maxsize). If the length is larger than `sys.maxsize` some features (such as [`len()`](https://docs.python.org/3/library/functions.html#len)) may raise [`OverflowError`](https://docs.python.org/3/library/exceptions.html#OverflowError). To prevent raising `OverflowError` by truth value testing, an object must define a [`__bool__()`](#datamodel--object.__bool__) method.

<!-- -->

object.\_\_length_hint\_\_(*self*)  
Called to implement [`operator.length_hint()`](https://docs.python.org/3/library/operator.html#operator.length_hint). Should return an estimated length for the object (which may be greater or less than the actual length). The length must be an integer `>=` 0. The return value may also be [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented), which is treated the same as if the `__length_hint__` method didn’t exist at all. This method is purely an optimization and is never required for correctness.

Added in version 3.4.

<!-- -->

object.\_\_getitem\_\_(*self*, *subscript*)  
Called to implement *subscription*, that is, `self[subscript]`. See [Subscriptions and slicings](#expressions--subscriptions) for details on the syntax.

There are two types of built-in objects that support subscription via `__getitem__()`:

- **sequences**, where *subscript* (also called [index](https://docs.python.org/3/glossary.html#term-index)) should be an integer or a [`slice`](https://docs.python.org/3/library/functions.html#slice) object. See the [sequence documentation](#datamodel--datamodel-sequences) for the expected behavior, including handling `slice` objects and negative indices.

- **mappings**, where *subscript* is also called the [key](https://docs.python.org/3/glossary.html#term-key). See [mapping documentation](#datamodel--datamodel-mappings) for the expected behavior.

If *subscript* is of an inappropriate type, `__getitem__()` should raise [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError). If *subscript* has an inappropriate value, `__getitem__()` should raise an [`LookupError`](https://docs.python.org/3/library/exceptions.html#LookupError) or one of its subclasses ([`IndexError`](https://docs.python.org/3/library/exceptions.html#IndexError) for sequences; [`KeyError`](https://docs.python.org/3/library/exceptions.html#KeyError) for mappings).

Note

Slicing is handled by `__getitem__()`, [`__setitem__()`](#datamodel--object.__setitem__), and [`__delitem__()`](#datamodel--object.__delitem__). A call like

    a[1:2] = b

is translated to

    a[slice(1, 2, None)] = b

and so forth. Missing slice items are always filled in with `None`.

Note

The sequence iteration protocol (used, for example, in [`for`](#compound_stmts--for) loops), expects that an [`IndexError`](https://docs.python.org/3/library/exceptions.html#IndexError) will be raised for illegal indexes to allow proper detection of the end of a sequence.

Note

When [subscripting](#expressions--subscriptions) a *class*, the special class method [`__class_getitem__()`](#datamodel--object.__class_getitem__) may be called instead of `__getitem__()`. See [\_\_class_getitem\_\_ versus \_\_getitem\_\_](#datamodel--classgetitem-versus-getitem) for more details.

<!-- -->

object.\_\_setitem\_\_(*self*, *key*, *value*)  
Called to implement assignment to `self[key]`. Same note as for [`__getitem__()`](#datamodel--object.__getitem__). This should only be implemented for mappings if the objects support changes to the values for keys, or if new keys can be added, or for sequences if elements can be replaced. The same exceptions should be raised for improper *key* values as for the `__getitem__()` method.

<!-- -->

object.\_\_delitem\_\_(*self*, *key*)  
Called to implement deletion of `self[key]`. Same note as for [`__getitem__()`](#datamodel--object.__getitem__). This should only be implemented for mappings if the objects support removal of keys, or for sequences if elements can be removed from the sequence. The same exceptions should be raised for improper *key* values as for the `__getitem__()` method.

<!-- -->

object.\_\_missing\_\_(*self*, *key*)  
Called by [`dict`](https://docs.python.org/3/library/stdtypes.html#dict).[`__getitem__()`](#datamodel--object.__getitem__) to implement `self[key]` for dict subclasses when key is not in the dictionary.

<!-- -->

object.\_\_iter\_\_(*self*)  
This method is called when an [iterator](https://docs.python.org/3/glossary.html#term-iterator) is required for a container. This method should return a new iterator object that can iterate over all the objects in the container. For mappings, it should iterate over the keys of the container.

<!-- -->

object.\_\_reversed\_\_(*self*)  
Called (if present) by the [`reversed()`](https://docs.python.org/3/library/functions.html#reversed) built-in to implement reverse iteration. It should return a new iterator object that iterates over all the objects in the container in reverse order.

If the `__reversed__()` method is not provided, the [`reversed()`](https://docs.python.org/3/library/functions.html#reversed) built-in will fall back to using the sequence protocol ([`__len__()`](#datamodel--object.__len__) and [`__getitem__()`](#datamodel--object.__getitem__)). Objects that support the sequence protocol should only provide `__reversed__()` if they can provide an implementation that is more efficient than the one provided by `reversed()`.

The membership test operators ([`in`](#expressions--in) and [`not in`](#expressions--not-in)) are normally implemented as an iteration through a container. However, container objects can supply the following special method with a more efficient implementation, which also does not require the object be iterable.

object.\_\_contains\_\_(*self*, *item*)  
Called to implement membership test operators. Should return true if *item* is in *self*, false otherwise. For mapping objects, this should consider the keys of the mapping rather than the values or the key-item pairs.

For objects that don’t define `__contains__()`, the membership test first tries iteration via [`__iter__()`](#datamodel--object.__iter__), then the old sequence iteration protocol via [`__getitem__()`](#datamodel--object.__getitem__), see [this section in the language reference](#expressions--membership-test-details).

<span id="datamodel--numeric-types"></span>

### 3.3.8. Emulating numeric types {#datamodel--emulating-numeric-types}

The following methods can be defined to emulate numeric objects. Methods corresponding to operations that are not supported by the particular kind of number implemented (e.g., bitwise operations for non-integral numbers) should be left undefined.

object.\_\_add\_\_(*self*, *other*)  
object.\_\_sub\_\_(*self*, *other*)  
object.\_\_mul\_\_(*self*, *other*)  
object.\_\_matmul\_\_(*self*, *other*)  
object.\_\_truediv\_\_(*self*, *other*)  
object.\_\_floordiv\_\_(*self*, *other*)  
object.\_\_mod\_\_(*self*, *other*)  
object.\_\_divmod\_\_(*self*, *other*)  
object.\_\_pow\_\_(*self*, *other*\[, *modulo*\])  
object.\_\_lshift\_\_(*self*, *other*)  
object.\_\_rshift\_\_(*self*, *other*)  
object.\_\_and\_\_(*self*, *other*)  
object.\_\_xor\_\_(*self*, *other*)  
object.\_\_or\_\_(*self*, *other*)  
These methods are called to implement the binary arithmetic operations (`+`, `-`, `*`, `@`, `/`, `//`, `%`, [`divmod()`](https://docs.python.org/3/library/functions.html#divmod), [`pow()`](https://docs.python.org/3/library/functions.html#pow), `**`, `<<`, `>>`, `&`, `^`, `|`). For instance, to evaluate the expression `x + y`, where *x* is an instance of a class that has an `__add__()` method, `type(x).__add__(x, y)` is called. The `__divmod__()` method should be the equivalent to using `__floordiv__()` and `__mod__()`; it should not be related to `__truediv__()`. Note that `__pow__()` should be defined to accept an optional third argument if the three-argument version of the built-in `pow()` function is to be supported.

If one of those methods does not support the operation with the supplied arguments, it should return [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented).

<!-- -->

object.\_\_radd\_\_(*self*, *other*)  
object.\_\_rsub\_\_(*self*, *other*)  
object.\_\_rmul\_\_(*self*, *other*)  
object.\_\_rmatmul\_\_(*self*, *other*)  
object.\_\_rtruediv\_\_(*self*, *other*)  
object.\_\_rfloordiv\_\_(*self*, *other*)  
object.\_\_rmod\_\_(*self*, *other*)  
object.\_\_rdivmod\_\_(*self*, *other*)  
object.\_\_rpow\_\_(*self*, *other*\[, *modulo*\])  
object.\_\_rlshift\_\_(*self*, *other*)  
object.\_\_rrshift\_\_(*self*, *other*)  
object.\_\_rand\_\_(*self*, *other*)  
object.\_\_rxor\_\_(*self*, *other*)  
object.\_\_ror\_\_(*self*, *other*)  
These methods are called to implement the binary arithmetic operations (`+`, `-`, `*`, `@`, `/`, `//`, `%`, [`divmod()`](https://docs.python.org/3/library/functions.html#divmod), [`pow()`](https://docs.python.org/3/library/functions.html#pow), `**`, `<<`, `>>`, `&`, `^`, `|`) with reflected (swapped) operands. These functions are only called if the operands are of different types, when the left operand does not support the corresponding operation [\[3\]](#datamodel--id22){#datamodel--id16}, or the right operand’s class is derived from the left operand’s class. [\[4\]](#datamodel--id23){#datamodel--id17} For instance, to evaluate the expression `x - y`, where *y* is an instance of a class that has an `__rsub__()` method, `type(y).__rsub__(y, x)` is called if `type(x).__sub__(x, y)` returns [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented) or `type(y)` is a subclass of `type(x)`. [\[5\]](#datamodel--id24){#datamodel--id18}

Note that `__rpow__()` should be defined to accept an optional third argument if the three-argument version of the built-in [`pow()`](https://docs.python.org/3/library/functions.html#pow) function is to be supported.

Changed in version 3.14: Three-argument [`pow()`](https://docs.python.org/3/library/functions.html#pow) now try calling `__rpow__()` if necessary. Previously it was only called in two-argument `pow()` and the binary power operator.

Note

If the right operand’s type is a subclass of the left operand’s type and that subclass provides a different implementation of the reflected method for the operation, this method will be called before the left operand’s non-reflected method. This behavior allows subclasses to override their ancestors’ operations.

<!-- -->

object.\_\_iadd\_\_(*self*, *other*)  
object.\_\_isub\_\_(*self*, *other*)  
object.\_\_imul\_\_(*self*, *other*)  
object.\_\_imatmul\_\_(*self*, *other*)  
object.\_\_itruediv\_\_(*self*, *other*)  
object.\_\_ifloordiv\_\_(*self*, *other*)  
object.\_\_imod\_\_(*self*, *other*)  
object.\_\_ipow\_\_(*self*, *other*\[, *modulo*\])  
object.\_\_ilshift\_\_(*self*, *other*)  
object.\_\_irshift\_\_(*self*, *other*)  
object.\_\_iand\_\_(*self*, *other*)  
object.\_\_ixor\_\_(*self*, *other*)  
object.\_\_ior\_\_(*self*, *other*)  
These methods are called to implement the augmented arithmetic assignments (`+=`, `-=`, `*=`, `@=`, `/=`, `//=`, `%=`, `**=`, `<<=`, `>>=`, `&=`, `^=`, `|=`). These methods should attempt to do the operation in-place (modifying *self*) and return the result (which could be, but does not have to be, *self*). If a specific method is not defined, or if that method returns [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented), the augmented assignment falls back to the normal methods. For instance, if *x* is an instance of a class with an `__iadd__()` method, `x += y` is equivalent to `x = x.__iadd__(y)` . If `__iadd__()` does not exist, or if `x.__iadd__(y)` returns `NotImplemented`, `x.__add__(y)` and `y.__radd__(x)` are considered, as with the evaluation of `x + y`. In certain situations, augmented assignment can result in unexpected errors (see [Why does a_tuple\[i\] += \[‘item’\] raise an exception when the addition works?](https://docs.python.org/3/faq/programming.html#faq-augmented-assignment-tuple-error)), but this behavior is in fact part of the data model.

<!-- -->

object.\_\_neg\_\_(*self*)  
object.\_\_pos\_\_(*self*)  
object.\_\_abs\_\_(*self*)  
object.\_\_invert\_\_(*self*)  
Called to implement the unary arithmetic operations (`-`, `+`, [`abs()`](https://docs.python.org/3/library/functions.html#abs) and `~`).

<!-- -->

object.\_\_complex\_\_(*self*)  
object.\_\_int\_\_(*self*)  
object.\_\_float\_\_(*self*)  
Called to implement the built-in functions [`complex()`](https://docs.python.org/3/library/functions.html#complex), [`int()`](https://docs.python.org/3/library/functions.html#int) and [`float()`](https://docs.python.org/3/library/functions.html#float). Should return a value of the appropriate type.

<!-- -->

object.\_\_index\_\_(*self*)  
Called to implement [`operator.index()`](https://docs.python.org/3/library/operator.html#operator.index), and whenever Python needs to losslessly convert the numeric object to an integer object (such as in slicing, or in the built-in [`bin()`](https://docs.python.org/3/library/functions.html#bin), [`hex()`](https://docs.python.org/3/library/functions.html#hex) and [`oct()`](https://docs.python.org/3/library/functions.html#oct) functions). Presence of this method indicates that the numeric object is an integer type. Must return an integer.

If [`__int__()`](#datamodel--object.__int__), [`__float__()`](#datamodel--object.__float__) and [`__complex__()`](#datamodel--object.__complex__) are not defined then corresponding built-in functions [`int()`](https://docs.python.org/3/library/functions.html#int), [`float()`](https://docs.python.org/3/library/functions.html#float) and [`complex()`](https://docs.python.org/3/library/functions.html#complex) fall back to `__index__()`.

<!-- -->

object.\_\_round\_\_(*self*\[, *ndigits*\])  
object.\_\_trunc\_\_(*self*)  
object.\_\_floor\_\_(*self*)  
object.\_\_ceil\_\_(*self*)  
Called to implement the built-in function [`round()`](https://docs.python.org/3/library/functions.html#round) and [`math`](https://docs.python.org/3/library/math.html#module-math) functions [`trunc()`](https://docs.python.org/3/library/math.html#math.trunc), [`floor()`](https://docs.python.org/3/library/math.html#math.floor) and [`ceil()`](https://docs.python.org/3/library/math.html#math.ceil). Unless *ndigits* is passed to `__round__()` all these methods should return the value of the object truncated to an [`Integral`](https://docs.python.org/3/library/numbers.html#numbers.Integral) (typically an [`int`](https://docs.python.org/3/library/functions.html#int)).

Changed in version 3.14: [`int()`](https://docs.python.org/3/library/functions.html#int) no longer delegates to the `__trunc__()` method.

<span id="datamodel--context-managers"></span>

### 3.3.9. With Statement Context Managers {#datamodel--with-statement-context-managers}

A *context manager* is an object that defines the runtime context to be established when executing a [`with`](#compound_stmts--with) statement. The context manager handles the entry into, and the exit from, the desired runtime context for the execution of the block of code. Context managers are normally invoked using the `with` statement (described in section [The with statement](#compound_stmts--with)), but can also be used by directly invoking their methods.

Typical uses of context managers include saving and restoring various kinds of global state, locking and unlocking resources, closing opened files, etc.

For more information on context managers, see [Context Manager Types](https://docs.python.org/3/library/stdtypes.html#typecontextmanager). The [`object`](https://docs.python.org/3/library/functions.html#object) class itself does not provide the context manager methods.

object.\_\_enter\_\_(*self*)  
Enter the runtime context related to this object. The [`with`](#compound_stmts--with) statement will bind this method’s return value to the target(s) specified in the `as` clause of the statement, if any.

<!-- -->

object.\_\_exit\_\_(*self*, *exc_type*, *exc_value*, *traceback*)  
Exit the runtime context related to this object. The parameters describe the exception that caused the context to be exited. If the context was exited without an exception, all three arguments will be [`None`](https://docs.python.org/3/library/constants.html#None).

If an exception is supplied, and the method wishes to suppress the exception (i.e., prevent it from being propagated), it should return a true value. Otherwise, the exception will be processed normally upon exit from this method.

Note that `__exit__()` methods should not reraise the passed-in exception; this is the caller’s responsibility.

See also

<span id="datamodel--index-112"></span>[**PEP 343**](https://peps.python.org/pep-0343/) - The “with” statement  
The specification, background, and examples for the Python [`with`](#compound_stmts--with) statement.

<span id="datamodel--class-pattern-matching"></span>

### 3.3.10. Customizing positional arguments in class pattern matching {#datamodel--customizing-positional-arguments-in-class-pattern-matching}

When using a class name in a pattern, positional arguments in the pattern are not allowed by default, i.e. `case MyClass(x, y)` is typically invalid without special support in `MyClass`. To be able to use that kind of pattern, the class needs to define a *\_\_match_args\_\_* attribute.

object.\_\_match_args\_\_  
This class variable can be assigned a tuple of strings. When this class is used in a class pattern with positional arguments, each positional argument will be converted into a keyword argument, using the corresponding value in *\_\_match_args\_\_* as the keyword. The absence of this attribute is equivalent to setting it to `()`.

For example, if `MyClass.__match_args__` is `("left", "center", "right")` that means that `case MyClass(x, y)` is equivalent to `case MyClass(left=x, center=y)`. Note that the number of arguments in the pattern must be smaller than or equal to the number of elements in *\_\_match_args\_\_*; if it is larger, the pattern match attempt will raise a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError).

Added in version 3.10.

See also

<span id="datamodel--index-113"></span>[**PEP 634**](https://peps.python.org/pep-0634/) - Structural Pattern Matching  
The specification for the Python `match` statement.

<span id="datamodel--python-buffer-protocol"></span>

### 3.3.11. Emulating buffer types {#datamodel--emulating-buffer-types}

The [buffer protocol](https://docs.python.org/3/c-api/buffer.html#bufferobjects) provides a way for Python objects to expose efficient access to a low-level memory array. This protocol is implemented by builtin types such as [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes) and [`memoryview`](https://docs.python.org/3/library/stdtypes.html#memoryview), and third-party libraries may define additional buffer types.

While buffer types are usually implemented in C, it is also possible to implement the protocol in Python.

object.\_\_buffer\_\_(*self*, *flags*)  
Called when a buffer is requested from *self* (for example, by the [`memoryview`](https://docs.python.org/3/library/stdtypes.html#memoryview) constructor). The *flags* argument is an integer representing the kind of buffer requested, affecting for example whether the returned buffer is read-only or writable. [`inspect.BufferFlags`](https://docs.python.org/3/library/inspect.html#inspect.BufferFlags) provides a convenient way to interpret the flags. The method must return a `memoryview` object.

**Thread safety:** In [free-threaded](https://docs.python.org/3/glossary.html#term-free-threading) Python, implementations must manage any internal export counter using atomic operations. The method must be safe to call concurrently from multiple threads, and the returned buffer’s underlying data must remain valid until the corresponding [`__release_buffer__()`](#datamodel--object.__release_buffer__) call completes. See [Thread safety for memoryview objects](https://docs.python.org/3/library/threadsafety.html#thread-safety-memoryview) for details.

<!-- -->

object.\_\_release_buffer\_\_(*self*, *buffer*)  
Called when a buffer is no longer needed. The *buffer* argument is a [`memoryview`](https://docs.python.org/3/library/stdtypes.html#memoryview) object that was previously returned by [`__buffer__()`](#datamodel--object.__buffer__). The method must release any resources associated with the buffer. This method should return `None`.

**Thread safety:** In [free-threaded](https://docs.python.org/3/glossary.html#term-free-threading) Python, any export counter decrement must use atomic operations. Resource cleanup must be thread-safe, as the final release may race with concurrent releases from other threads.

Buffer objects that do not need to perform any cleanup are not required to implement this method.

Added in version 3.12.

See also

<span id="datamodel--index-114"></span>[**PEP 688**](https://peps.python.org/pep-0688/) - Making the buffer protocol accessible in Python  
Introduces the Python `__buffer__` and `__release_buffer__` methods.

[`collections.abc.Buffer`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Buffer)  
ABC for buffer types.

### 3.3.12. Annotations {#datamodel--annotations}

Functions, classes, and modules may contain [annotations](https://docs.python.org/3/glossary.html#term-annotation), which are a way to associate information (usually [type hints](https://docs.python.org/3/glossary.html#term-type-hint)) with a symbol.

object.\_\_annotations\_\_  
This attribute contains the annotations for an object. It is [lazily evaluated](#executionmodel--lazy-evaluation), so accessing the attribute may execute arbitrary code and raise exceptions. If evaluation is successful, the attribute is set to a dictionary mapping from variable names to annotations.

Changed in version 3.14: Annotations are now lazily evaluated.

<!-- -->

object.\_\_annotate\_\_(*format*)  
An [annotate function](https://docs.python.org/3/glossary.html#term-annotate-function). Returns a new dictionary object mapping attribute/parameter names to their annotation values.

Takes a format parameter specifying the format in which annotations values should be provided. It must be a member of the [`annotationlib.Format`](https://docs.python.org/3/library/annotationlib.html#annotationlib.Format) enum, or an integer with a value corresponding to a member of the enum.

If an annotate function doesn’t support the requested format, it must raise [`NotImplementedError`](https://docs.python.org/3/library/exceptions.html#NotImplementedError). Annotate functions must always support [`VALUE`](https://docs.python.org/3/library/annotationlib.html#annotationlib.Format.VALUE) format; they must not raise [`NotImplementedError()`](https://docs.python.org/3/library/exceptions.html#NotImplementedError) when called with this format.

When called with [`VALUE`](https://docs.python.org/3/library/annotationlib.html#annotationlib.Format.VALUE) format, an annotate function may raise [`NameError`](https://docs.python.org/3/library/exceptions.html#NameError); it must not raise `NameError` when called requesting any other format.

If an object does not have any annotations, [`__annotate__`](#datamodel--object.__annotate__) should preferably be set to `None` (it can’t be deleted), rather than set to a function that returns an empty dict.

Added in version 3.14.

See also

<span id="datamodel--index-115"></span>[**PEP 649**](https://peps.python.org/pep-0649/) — Deferred evaluation of annotation using descriptors  
Introduces lazy evaluation of annotations and the `__annotate__` function.

<span id="datamodel--special-lookup"></span>

### 3.3.13. Special method lookup {#datamodel--special-method-lookup}

For custom classes, implicit invocations of special methods are only guaranteed to work correctly if defined on an object’s type, not in the object’s instance dictionary. That behaviour is the reason why the following code raises an exception:

    >>> class C:
    ...     pass
    ...
    >>> c = C()
    >>> c.__len__ = lambda: 5
    >>> len(c)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: object of type 'C' has no len()

The rationale behind this behaviour lies with a number of special methods such as [`__hash__()`](#datamodel--object.__hash__) and [`__repr__()`](#datamodel--object.__repr__) that are implemented by all objects, including type objects. If the implicit lookup of these methods used the conventional lookup process, they would fail when invoked on the type object itself:

    >>> 1 .__hash__() == hash(1)
    True
    >>> int.__hash__() == hash(int)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: descriptor '__hash__' of 'int' object needs an argument

Incorrectly attempting to invoke an unbound method of a class in this way is sometimes referred to as ‘metaclass confusion’, and is avoided by bypassing the instance when looking up special methods:

    >>> type(1).__hash__(1) == hash(1)
    True
    >>> type(int).__hash__(int) == hash(int)
    True

In addition to bypassing any instance attributes in the interest of correctness, implicit special method lookup generally also bypasses the [`__getattribute__()`](#datamodel--object.__getattribute__) method even of the object’s metaclass:

    >>> class Meta(type):
    ...     def __getattribute__(*args):
    ...         print("Metaclass getattribute invoked")
    ...         return type.__getattribute__(*args)
    ...
    >>> class C(object, metaclass=Meta):
    ...     def __len__(self):
    ...         return 10
    ...     def __getattribute__(*args):
    ...         print("Class getattribute invoked")
    ...         return object.__getattribute__(*args)
    ...
    >>> c = C()
    >>> c.__len__()                 # Explicit lookup via instance
    Class getattribute invoked
    10
    >>> type(c).__len__(c)          # Explicit lookup via type
    Metaclass getattribute invoked
    10
    >>> len(c)                      # Implicit lookup
    10

Bypassing the [`__getattribute__()`](#datamodel--object.__getattribute__) machinery in this fashion provides significant scope for speed optimisations within the interpreter, at the cost of some flexibility in the handling of special methods (the special method *must* be set on the class object itself in order to be consistently invoked by the interpreter).

<span id="datamodel--index-116"></span>

## 3.4. Coroutines {#datamodel--coroutines}

### 3.4.1. Awaitable Objects {#datamodel--awaitable-objects}

An [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) object generally implements an [`__await__()`](#datamodel--object.__await__) method. [Coroutine objects](https://docs.python.org/3/glossary.html#term-coroutine) returned from [`async def`](#compound_stmts--async-def) functions are awaitable.

Note

The [generator iterator](https://docs.python.org/3/glossary.html#term-generator-iterator) objects returned from generators decorated with [`types.coroutine()`](https://docs.python.org/3/library/types.html#types.coroutine) are also awaitable, but they do not implement [`__await__()`](#datamodel--object.__await__).

object.\_\_await\_\_(*self*)  
Must return an [iterator](https://docs.python.org/3/glossary.html#term-iterator). Should be used to implement [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) objects. For instance, [`asyncio.Future`](https://docs.python.org/3/library/asyncio-future.html#asyncio.Future) implements this method to be compatible with the [`await`](#expressions--await) expression. The [`object`](https://docs.python.org/3/library/functions.html#object) class itself is not awaitable and does not provide this method.

Note

The language doesn’t place any restriction on the type or value of the objects yielded by the iterator returned by `__await__`, as this is specific to the implementation of the asynchronous execution framework (e.g. [`asyncio`](https://docs.python.org/3/library/asyncio.html#module-asyncio)) that will be managing the [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) object.

Added in version 3.5.

See also

<span id="datamodel--index-117"></span>[**PEP 492**](https://peps.python.org/pep-0492/) for additional information about awaitable objects.

<span id="datamodel--id19"></span>

### 3.4.2. Coroutine Objects {#datamodel--coroutine-objects}

[Coroutine objects](https://docs.python.org/3/glossary.html#term-coroutine) are [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) objects. A coroutine’s execution can be controlled by calling [`__await__()`](#datamodel--object.__await__) and iterating over the result. When the coroutine has finished executing and returns, the iterator raises [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration), and the exception’s [`value`](https://docs.python.org/3/library/exceptions.html#StopIteration.value) attribute holds the return value. If the coroutine raises an exception, it is propagated by the iterator. Coroutines should not directly raise unhandled `StopIteration` exceptions.

Coroutines also have the methods listed below, which are analogous to those of generators (see [Generator-iterator methods](#expressions--generator-methods)). However, unlike generators, coroutines do not directly support iteration.

Coroutines are [generic](https://docs.python.org/3/library/typing.html#generics) over the types of their yield, send, and return values, respectively.

Changed in version 3.5.2: It is a [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) to await on a coroutine more than once.

coroutine.send(*value*)  
Starts or resumes execution of the coroutine. If *value* is `None`, this is equivalent to advancing the iterator returned by [`__await__()`](#datamodel--object.__await__). If *value* is not `None`, this method delegates to the [`send()`](#expressions--generator.send) method of the iterator that caused the coroutine to suspend. The result (return value, [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration), or other exception) is the same as when iterating over the `__await__()` return value, described above.

<!-- -->

coroutine.throw(*value*)  
coroutine.throw(*type*\[, *value*\[, *traceback*\]\])  
Raises the specified exception in the coroutine. This method delegates to the [`throw()`](#expressions--generator.throw) method of the iterator that caused the coroutine to suspend, if it has such a method. Otherwise, the exception is raised at the suspension point. The result (return value, [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration), or other exception) is the same as when iterating over the [`__await__()`](#datamodel--object.__await__) return value, described above. If the exception is not caught in the coroutine, it propagates back to the caller.

Changed in version 3.12: The second signature (type\[, value\[, traceback\]\]) is deprecated and may be removed in a future version of Python.

<!-- -->

coroutine.close()  
Causes the coroutine to clean itself up and exit. If the coroutine is suspended, this method first delegates to the [`close()`](#expressions--generator.close) method of the iterator that caused the coroutine to suspend, if it has such a method. Then it raises [`GeneratorExit`](https://docs.python.org/3/library/exceptions.html#GeneratorExit) at the suspension point, causing the coroutine to immediately clean itself up. Finally, the coroutine is marked as having finished executing, even if it was never started.

Coroutine objects are automatically closed using the above process when they are about to be destroyed.

<span id="datamodel--async-iterators"></span>

### 3.4.3. Asynchronous Iterators {#datamodel--asynchronous-iterators}

An *asynchronous iterator* can call asynchronous code in its `__anext__` method.

Asynchronous iterators can be used in an [`async for`](#compound_stmts--async-for) statement.

The [`object`](https://docs.python.org/3/library/functions.html#object) class itself does not provide these methods.

object.\_\_aiter\_\_(*self*)  
Must return an *asynchronous iterator* object.

<!-- -->

object.\_\_anext\_\_(*self*)  
Must return an *awaitable* resulting in a next value of the iterator. Should raise a [`StopAsyncIteration`](https://docs.python.org/3/library/exceptions.html#StopAsyncIteration) error when the iteration is over.

An example of an asynchronous iterable object:

    class Reader:
        async def readline(self):
            ...

        def __aiter__(self):
            return self

        async def __anext__(self):
            val = await self.readline()
            if val == b'':
                raise StopAsyncIteration
            return val

Added in version 3.5.

Changed in version 3.7: Prior to Python 3.7, [`__aiter__()`](#datamodel--object.__aiter__) could return an *awaitable* that would resolve to an [asynchronous iterator](https://docs.python.org/3/glossary.html#term-asynchronous-iterator).

Starting with Python 3.7, [`__aiter__()`](#datamodel--object.__aiter__) must return an asynchronous iterator object. Returning anything else will result in a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) error.

<span id="datamodel--async-context-managers"></span>

### 3.4.4. Asynchronous Context Managers {#datamodel--asynchronous-context-managers}

An *asynchronous context manager* is a *context manager* that is able to suspend execution in its `__aenter__` and `__aexit__` methods.

Asynchronous context managers can be used in an [`async with`](#compound_stmts--async-with) statement.

The [`object`](https://docs.python.org/3/library/functions.html#object) class itself does not provide these methods.

object.\_\_aenter\_\_(*self*)  
Semantically similar to [`__enter__()`](#datamodel--object.__enter__), the only difference being that it must return an *awaitable*.

<!-- -->

object.\_\_aexit\_\_(*self*, *exc_type*, *exc_value*, *traceback*)  
Semantically similar to [`__exit__()`](#datamodel--object.__exit__), the only difference being that it must return an *awaitable*.

An example of an asynchronous context manager class:

    class AsyncContextManager:
        async def __aenter__(self):
            await log('entering context')

        async def __aexit__(self, exc_type, exc, tb):
            await log('exiting context')

Added in version 3.5.

Footnotes

\[[1](#datamodel--id1)\]

It *is* possible in some cases to change an object’s type, under certain controlled conditions. It generally isn’t a good idea though, since it can lead to some very strange behaviour if it is handled incorrectly.

\[[2](#datamodel--id12)\]

The [`__hash__()`](#datamodel--object.__hash__), [`__iter__()`](#datamodel--object.__iter__), [`__reversed__()`](#datamodel--object.__reversed__), [`__contains__()`](#datamodel--object.__contains__), [`__class_getitem__()`](#datamodel--object.__class_getitem__) and [`__fspath__()`](https://docs.python.org/3/library/os.html#os.PathLike.__fspath__) methods have special handling for this. Others will still raise a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError), but may do so by relying on the behavior that `None` is not callable.

\[[3](#datamodel--id16)\]

“Does not support” here means that the class has no such method, or the method returns [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented). Do not set the method to `None` if you want to force fallback to the right operand’s reflected method—that will instead have the opposite effect of explicitly *blocking* such fallback.

\[[4](#datamodel--id17)\]

For operands of the same type, it is assumed that if the non-reflected method (such as [`__add__()`](#datamodel--object.__add__)) fails then the operation is not supported, which is why the reflected method is not called.

\[[5](#datamodel--id18)\]

If the right operand’s type is a subclass of the left operand’s type, the reflected method having precedence allows subclasses to override their ancestors’ operations.

<span id="executionmodel--execmodel"></span>

# 4. Execution model {#executionmodel--execution-model}

<span id="executionmodel--prog-structure"></span> <span id="executionmodel--index-0"></span>

## 4.1. Structure of a program {#executionmodel--structure-of-a-program}

A Python program is constructed from code blocks. A *block* is a piece of Python program text that is executed as a unit. The following are blocks: a module, a function body, and a class definition. Each command typed interactively is a block. A script file (a file given as standard input to the interpreter or specified as a command line argument to the interpreter) is a code block. A script command (a command specified on the interpreter command line with the [`-c`](https://docs.python.org/3/using/cmdline.html#cmdoption-c) option) is a code block. A module run as a top level script (as module `__main__`) from the command line using a [`-m`](https://docs.python.org/3/using/cmdline.html#cmdoption-m) argument is also a code block. The string argument passed to the built-in functions [`eval()`](https://docs.python.org/3/library/functions.html#eval) and [`exec()`](https://docs.python.org/3/library/functions.html#exec) is a code block.

A code block is executed in an *execution frame*. A frame contains some administrative information (used for debugging) and determines where and how execution continues after the code block’s execution has completed.

<span id="executionmodel--naming"></span>

## 4.2. Naming and binding {#executionmodel--naming-and-binding}

<span id="executionmodel--bind-names"></span> <span id="executionmodel--index-3"></span>

### 4.2.1. Binding of names {#executionmodel--binding-of-names}

*Names* refer to objects. Names are introduced by name binding operations.

The following constructs bind names:

- formal parameters to functions,

- class definitions,

- function definitions,

- assignment expressions,

- [targets](#simple_stmts--assignment) that are identifiers if occurring in an assignment:

  - [`for`](#compound_stmts--for) loop header,

  - after `as` in a [`with`](#compound_stmts--with) statement, [`except`](#compound_stmts--except) clause, [`except*`](#compound_stmts--except-star) clause, or in the as-pattern in structural pattern matching,

  - in a capture pattern in structural pattern matching

- [`import`](#simple_stmts--import) statements.

- [`type`](#simple_stmts--type) statements.

- [type parameter lists](#compound_stmts--type-params).

The `import` statement of the form `from ... import *` binds all names defined in the imported module, except those beginning with an underscore. This form may only be used at the module level.

A target occurring in a [`del`](#simple_stmts--del) statement is also considered bound for this purpose (though the actual semantics are to unbind the name).

Each assignment or import statement occurs within a block defined by a class or function definition or at the module level (the top-level code block).

If a name is bound in a block, it is a local variable of that block, unless declared as [`nonlocal`](#simple_stmts--nonlocal) or [`global`](#simple_stmts--global). If a name is bound at the module level, it is a global variable. (The variables of the module code block are local and global.) If a variable is used in a code block but not defined there, it is a [free variable](https://docs.python.org/3/glossary.html#term-free-variable).

Each occurrence of a name in the program text refers to the *binding* of that name established by the following name resolution rules.

<span id="executionmodel--resolve-names"></span>

### 4.2.2. Resolution of names {#executionmodel--resolution-of-names}

A *scope* defines the visibility of a name within a block. If a local variable is defined in a block, its scope includes that block. If the definition occurs in a function block, the scope extends to any blocks contained within the defining one, unless a contained block introduces a different binding for the name.

When a name is used in a code block, it is resolved using the nearest enclosing scope. The set of all such scopes visible to a code block is called the block’s *environment*.

When a name is not found at all, a [`NameError`](https://docs.python.org/3/library/exceptions.html#NameError) exception is raised. If the current scope is a function scope, and the name refers to a local variable that has not yet been bound to a value at the point where the name is used, an [`UnboundLocalError`](https://docs.python.org/3/library/exceptions.html#UnboundLocalError) exception is raised. `UnboundLocalError` is a subclass of `NameError`.

If a name binding operation occurs anywhere within a code block, all uses of the name within the block are treated as references to the current block. This can lead to errors when a name is used within a block before it is bound. This rule is subtle. Python lacks declarations and allows name binding operations to occur anywhere within a code block. The local variables of a code block can be determined by scanning the entire text of the block for name binding operations. See [the FAQ entry on UnboundLocalError](https://docs.python.org/3/faq/programming.html#faq-unboundlocalerror) for examples.

If the [`global`](#simple_stmts--global) statement occurs within a block, all uses of the names specified in the statement refer to the bindings of those names in the top-level namespace. Names are resolved in the top-level namespace by searching the global namespace, i.e. the namespace of the module containing the code block, and the builtins namespace, the namespace of the module [`builtins`](https://docs.python.org/3/library/builtins.html#module-builtins). The global namespace is searched first. If the names are not found there, the builtins namespace is searched next. If the names are also not found in the builtins namespace, new variables are created in the global namespace. The global statement must precede all uses of the listed names.

The [`global`](#simple_stmts--global) statement has the same scope as a name binding operation in the same block. If the nearest enclosing scope for a free variable contains a global statement, the free variable is treated as a global.

The [`nonlocal`](#simple_stmts--nonlocal) statement causes corresponding names to refer to previously bound variables in the nearest enclosing function scope. [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) is raised at compile time if the given name does not exist in any enclosing function scope. [Type parameters](#compound_stmts--type-params) cannot be rebound with the `nonlocal` statement.

The namespace for a module is automatically created the first time a module is imported. The main module for a script is always called [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__).

Class definition blocks and arguments to [`exec()`](https://docs.python.org/3/library/functions.html#exec) and [`eval()`](https://docs.python.org/3/library/functions.html#eval) are special in the context of name resolution. A class definition is an executable statement that may use and define names. These references follow the normal rules for name resolution with an exception that unbound local variables are looked up in the global namespace. The namespace of the class definition becomes the attribute dictionary of the class. The scope of names defined in a class block is limited to the class block; it does not extend to the code blocks of methods. This includes comprehensions and generator expressions, but it does not include [annotation scopes](#executionmodel--annotation-scopes), which have access to their enclosing class scopes. This means that the following will fail:

    class A:
        a = 42
        b = list(a + i for i in range(10))

However, the following will succeed:

    class A:
        type Alias = Nested
        class Nested: pass

    print(A.Alias.__value__)  # <type 'A.Nested'>

<span id="executionmodel--id1"></span>

### 4.2.3. Annotation scopes {#executionmodel--annotation-scopes}

[Annotations](https://docs.python.org/3/glossary.html#term-annotation), [type parameter lists](#compound_stmts--type-params) and [`type`](#simple_stmts--type) statements introduce *annotation scopes*, which behave mostly like function scopes, but with some exceptions discussed below.

Annotation scopes are used in the following contexts:

- [Function annotations](https://docs.python.org/3/glossary.html#term-function-annotation).

- [Variable annotations](https://docs.python.org/3/glossary.html#term-variable-annotation).

- Type parameter lists for [generic type aliases](#compound_stmts--generic-type-aliases).

- Type parameter lists for [generic functions](#compound_stmts--generic-functions). A generic function’s annotations are executed within the annotation scope, but its defaults and decorators are not.

- Type parameter lists for [generic classes](#compound_stmts--generic-classes). A generic class’s base classes and keyword arguments are executed within the annotation scope, but its decorators are not.

- The bounds, constraints, and default values for type parameters ([lazily evaluated](#executionmodel--lazy-evaluation)).

- The value of type aliases ([lazily evaluated](#executionmodel--lazy-evaluation)).

Annotation scopes differ from function scopes in the following ways:

- Annotation scopes have access to their enclosing class namespace. If an annotation scope is immediately within a class scope, or within another annotation scope that is immediately within a class scope, the code in the annotation scope can use names defined in the class scope as if it were executed directly within the class body. This contrasts with regular functions defined within classes, which cannot access names defined in the class scope.

- Expressions in annotation scopes cannot contain [`yield`](#simple_stmts--yield), `yield from`, [`await`](#expressions--await), or [`:=`](#expressions--grammar-token-python-grammar-assignment_expression) expressions. (These expressions are allowed in other scopes contained within the annotation scope.)

- Names defined in annotation scopes cannot be rebound with [`nonlocal`](#simple_stmts--nonlocal) statements in inner scopes. This includes only type parameters, as no other syntactic elements that can appear within annotation scopes can introduce new names.

- While annotation scopes have an internal name, that name is not reflected in the [qualified name](https://docs.python.org/3/glossary.html#term-qualified-name) of objects defined within the scope. Instead, the [`__qualname__`](https://docs.python.org/3/library/stdtypes.html#definition.__qualname__) of such objects is as if the object were defined in the enclosing scope.

Added in version 3.12: Annotation scopes were introduced in Python 3.12 as part of <span id="executionmodel--index-11"></span>[**PEP 695**](https://peps.python.org/pep-0695/).

Changed in version 3.13: Annotation scopes are also used for type parameter defaults, as introduced by <span id="executionmodel--index-12"></span>[**PEP 696**](https://peps.python.org/pep-0696/).

Changed in version 3.14: Annotation scopes are now also used for annotations, as specified in <span id="executionmodel--index-13"></span>[**PEP 649**](https://peps.python.org/pep-0649/) and <span id="executionmodel--index-14"></span>[**PEP 749**](https://peps.python.org/pep-0749/).

<span id="executionmodel--id2"></span>

### 4.2.4. Lazy evaluation {#executionmodel--lazy-evaluation}

Most annotation scopes are *lazily evaluated*. This includes annotations, the values of type aliases created through the [`type`](#simple_stmts--type) statement, and the bounds, constraints, and default values of type variables created through the [type parameter syntax](#compound_stmts--type-params). This means that they are not evaluated when the type alias or type variable is created, or when the object carrying annotations is created. Instead, they are only evaluated when necessary, for example when the `__value__` attribute on a type alias is accessed.

Example:

    >>> type Alias = 1/0
    >>> Alias.__value__
    Traceback (most recent call last):
      ...
    ZeroDivisionError: division by zero
    >>> def func[T: 1/0](): pass
    >>> T = func.__type_params__[0]
    >>> T.__bound__
    Traceback (most recent call last):
      ...
    ZeroDivisionError: division by zero

Here the exception is raised only when the `__value__` attribute of the type alias or the `__bound__` attribute of the type variable is accessed.

This behavior is primarily useful for references to types that have not yet been defined when the type alias or type variable is created. For example, lazy evaluation enables creation of mutually recursive type aliases:

    from typing import Literal

    type SimpleExpr = int | Parenthesized
    type Parenthesized = tuple[Literal["("], Expr, Literal[")"]]
    type Expr = SimpleExpr | tuple[SimpleExpr, Literal["+", "-"], Expr]

Lazily evaluated values are evaluated in [annotation scope](#executionmodel--annotation-scopes), which means that names that appear inside the lazily evaluated value are looked up as if they were used in the immediately enclosing scope.

Added in version 3.12.

<span id="executionmodel--restrict-exec"></span>

### 4.2.5. Builtins and restricted execution {#executionmodel--builtins-and-restricted-execution}

**CPython implementation detail:** Users should not touch `__builtins__`; it is strictly an implementation detail. Users wanting to override values in the builtins namespace should [`import`](#simple_stmts--import) the [`builtins`](https://docs.python.org/3/library/builtins.html#module-builtins) module and modify its attributes appropriately.

The builtins namespace associated with the execution of a code block is actually found by looking up the name `__builtins__` in its global namespace; this should be a dictionary or a module (in the latter case the module’s dictionary is used). By default, when in the [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__) module, `__builtins__` is the built-in module [`builtins`](https://docs.python.org/3/library/builtins.html#module-builtins); when in any other module, `__builtins__` is an alias for the dictionary of the `builtins` module itself.

<span id="executionmodel--dynamic-features"></span>

### 4.2.6. Interaction with dynamic features {#executionmodel--interaction-with-dynamic-features}

Name resolution of free variables occurs at runtime, not at compile time. This means that the following code will print 42:

    i = 10
    def f():
        print(i)
    i = 42
    f()

The [`eval()`](https://docs.python.org/3/library/functions.html#eval) and [`exec()`](https://docs.python.org/3/library/functions.html#exec) functions do not have access to the full environment for resolving names. Names may be resolved in the local and global namespaces of the caller. Free variables are not resolved in the nearest enclosing namespace, but in the global namespace. [\[1\]](#executionmodel--id5){#executionmodel--id3} The `exec()` and `eval()` functions have optional arguments to override the global and local namespace. If only one namespace is specified, it is used for both.

<span id="executionmodel--id4"></span>

## 4.3. Exceptions {#executionmodel--exceptions}

<span id="executionmodel--index-16"></span>Exceptions are a means of breaking out of the normal flow of control of a code block in order to handle errors or other exceptional conditions. An exception is *raised* at the point where the error is detected; it may be *handled* by the surrounding code block or by any code block that directly or indirectly invoked the code block where the error occurred.

The Python interpreter raises an exception when it detects a run-time error (such as division by zero). A Python program can also explicitly raise an exception with the [`raise`](#simple_stmts--raise) statement. Exception handlers are specified with the [`try`](#compound_stmts--try) … [`except`](#compound_stmts--except) statement. The [`finally`](#compound_stmts--finally) clause of such a statement can be used to specify cleanup code which does not handle the exception, but is executed whether an exception occurred or not in the preceding code.

Python uses the “termination” model of error handling: an exception handler can find out what happened and continue execution at an outer level, but it cannot repair the cause of the error and retry the failing operation (except by re-entering the offending piece of code from the top).

When an exception is not handled at all, the interpreter terminates execution of the program, or returns to its interactive main loop. In either case, it prints a stack traceback, except when the exception is [`SystemExit`](https://docs.python.org/3/library/exceptions.html#SystemExit).

Exceptions are identified by class instances. The [`except`](#compound_stmts--except) clause is selected depending on the class of the instance: it must reference the class of the instance or a [non-virtual base class](https://docs.python.org/3/glossary.html#term-abstract-base-class) thereof. The instance can be received by the handler and can carry additional information about the exceptional condition.

Note

Exception messages are not part of the Python API. Their contents may change from one version of Python to the next without warning and should not be relied on by code which will run under multiple versions of the interpreter.

See also the description of the [`try`](#compound_stmts--try) statement in section [The try statement](#compound_stmts--try) and [`raise`](#simple_stmts--raise) statement in section [The raise statement](#simple_stmts--raise).

<span id="executionmodel--execcomponents"></span>

## 4.4. Runtime Components {#executionmodel--runtime-components}

### 4.4.1. General Computing Model {#executionmodel--general-computing-model}

Python’s execution model does not operate in a vacuum. It runs on a host machine and through that host’s runtime environment, including its operating system (OS), if there is one. When a program runs, the conceptual layers of how it runs on the host look something like this:

> **host machine** **process** (global resources) **thread** (runs machine code)

Each process represents a program running on the host. Think of each process itself as the data part of its program. Think of the process’ threads as the execution part of the program. This distinction will be important to understand the conceptual Python runtime.

The process, as the data part, is the execution context in which the program runs. It mostly consists of the set of resources assigned to the program by the host, including memory, signals, file handles, sockets, and environment variables.

Processes are isolated and independent from one another. (The same is true for hosts.) The host manages the process’ access to its assigned resources, in addition to coordinating between processes.

Each thread represents the actual execution of the program’s machine code, running relative to the resources assigned to the program’s process. It’s strictly up to the host how and when that execution takes place.

From the point of view of Python, a program always starts with exactly one thread. However, the program may grow to run in multiple simultaneous threads. Not all hosts support multiple threads per process, but most do. Unlike processes, threads in a process are not isolated and independent from one another. Specifically, all threads in a process share all of the process’ resources.

The fundamental point of threads is that each one does *run* independently, at the same time as the others. That may be only conceptually at the same time (“concurrently”) or physically (“in parallel”). Either way, the threads effectively run at a non-synchronized rate.

Note

That non-synchronized rate means none of the process’ memory is guaranteed to stay consistent for the code running in any given thread. Thus multi-threaded programs must take care to coordinate access to intentionally shared resources. Likewise, they must take care to be absolutely diligent about not accessing any *other* resources in multiple threads; otherwise two threads running at the same time might accidentally interfere with each other’s use of some shared data. All this is true for both Python programs and the Python runtime.

The cost of this broad, unstructured requirement is the tradeoff for the kind of raw concurrency that threads provide. The alternative to the required discipline generally means dealing with non-deterministic bugs and data corruption.

### 4.4.2. Python Runtime Model {#executionmodel--python-runtime-model}

The same conceptual layers apply to each Python program, with some extra data layers specific to Python:

> **host machine** **process** (global resources) Python global runtime (*state*) Python interpreter (*state*) **thread** (runs Python bytecode and “C-API”) Python thread *state*

At the conceptual level: when a Python program starts, it looks exactly like that diagram, with one of each. The runtime may grow to include multiple interpreters, and each interpreter may grow to include multiple thread states.

Note

A Python implementation won’t necessarily implement the runtime layers distinctly or even concretely. The only exception is places where distinct layers are directly specified or exposed to users, like through the [`threading`](https://docs.python.org/3/library/threading.html#module-threading) module.

Note

The initial interpreter is typically called the “main” interpreter. Some Python implementations, like CPython, assign special roles to the main interpreter.

Likewise, the host thread where the runtime was initialized is known as the “main” thread. It may be different from the process’ initial thread, though they are often the same. In some cases “main thread” may be even more specific and refer to the initial thread state. A Python runtime might assign specific responsibilities to the main thread, such as handling signals.

As a whole, the Python runtime consists of the global runtime state, interpreters, and thread states. The runtime ensures all that state stays consistent over its lifetime, particularly when used with multiple host threads.

The global runtime, at the conceptual level, is just a set of interpreters. While those interpreters are otherwise isolated and independent from one another, they may share some data or other resources. The runtime is responsible for managing these global resources safely. The actual nature and management of these resources is implementation-specific. Ultimately, the external utility of the global runtime is limited to managing interpreters.

In contrast, an “interpreter” is conceptually what we would normally think of as the (full-featured) “Python runtime”. When machine code executing in a host thread interacts with the Python runtime, it calls into Python in the context of a specific interpreter.

Note

The term “interpreter” here is not the same as the “bytecode interpreter”, which is what regularly runs in threads, executing compiled Python code.

In an ideal world, “Python runtime” would refer to what we currently call “interpreter”. However, it’s been called “interpreter” at least since introduced in 1997 ([CPython:a027efa5b](https://github.com/python/cpython/commit/a027efa5b)).

Each interpreter completely encapsulates all of the non-process-global, non-thread-specific state needed for the Python runtime to work. Notably, the interpreter’s state persists between uses. It includes fundamental data like [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules). The runtime ensures multiple threads using the same interpreter will safely share it between them.

A Python implementation may support using multiple interpreters at the same time in the same process. They are independent and isolated from one another. For example, each interpreter has its own [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules).

For thread-specific runtime state, each interpreter has a set of thread states, which it manages, in the same way the global runtime contains a set of interpreters. It can have thread states for as many host threads as it needs. It may even have multiple thread states for the same host thread, though that isn’t as common.

Each thread state, conceptually, has all the thread-specific runtime data an interpreter needs to operate in one host thread. The thread state includes the current raised exception and the thread’s Python call stack. It may include other thread-specific resources.

Note

The term “Python thread” can sometimes refer to a thread state, but normally it means a thread created using the [`threading`](https://docs.python.org/3/library/threading.html#module-threading) module.

Each thread state, over its lifetime, is always tied to exactly one interpreter and exactly one host thread. It will only ever be used in that thread and with that interpreter.

Multiple thread states may be tied to the same host thread, whether for different interpreters or even the same interpreter. However, for any given host thread, only one of the thread states tied to it can be used by the thread at a time.

Thread states are isolated and independent from one another and don’t share any data, except for possibly sharing an interpreter and objects or other resources belonging to that interpreter.

Once a program is running, new Python threads can be created using the [`threading`](https://docs.python.org/3/library/threading.html#module-threading) module (on platforms and Python implementations that support threads). Additional processes can be created using the [`os`](https://docs.python.org/3/library/os.html#module-os), [`subprocess`](https://docs.python.org/3/library/subprocess.html#module-subprocess), and [`multiprocessing`](https://docs.python.org/3/library/multiprocessing.html#module-multiprocessing) modules. Interpreters can be created and used with the [`interpreters`](https://docs.python.org/3/library/concurrent.interpreters.html#module-concurrent.interpreters) module. Coroutines (async) can be run using [`asyncio`](https://docs.python.org/3/library/asyncio.html#module-asyncio) in each interpreter, typically only in a single thread (often the main thread).

Footnotes

\[[1](#executionmodel--id3)\]

This limitation occurs because the code that is executed by these operations is not available at the time the module is compiled.

<span id="import--importsystem"></span>

# 5. The import system {#import--the-import-system}

Python code in one [module](https://docs.python.org/3/glossary.html#term-module) gains access to the code in another module by the process of [importing](https://docs.python.org/3/glossary.html#term-importing) it. The [`import`](#simple_stmts--import) statement is the most common way of invoking the import machinery, but it is not the only way. Functions such as [`importlib.import_module()`](https://docs.python.org/3/library/importlib.html#importlib.import_module) and built-in [`__import__()`](https://docs.python.org/3/library/functions.html#import__) can also be used to invoke the import machinery.

The [`import`](#simple_stmts--import) statement combines two operations; it searches for the named module, then it binds the results of that search to a name in the local scope. The search operation of the `import` statement is defined as a call to the [`__import__()`](https://docs.python.org/3/library/functions.html#import__) function, with the appropriate arguments. The return value of `__import__()` is used to perform the name binding operation of the `import` statement. See the `import` statement for the exact details of that name binding operation.

A direct call to [`__import__()`](https://docs.python.org/3/library/functions.html#import__) performs only the module search and, if found, the module creation operation. While certain side-effects may occur, such as the importing of parent packages, and the updating of various caches (including [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules)), only the [`import`](#simple_stmts--import) statement performs a name binding operation.

When an [`import`](#simple_stmts--import) statement is executed, the standard builtin [`__import__()`](https://docs.python.org/3/library/functions.html#import__) function is called. Other mechanisms for invoking the import system (such as [`importlib.import_module()`](https://docs.python.org/3/library/importlib.html#importlib.import_module)) may choose to bypass `__import__()` and use their own solutions to implement import semantics.

When a module is first imported, Python searches for the module and if found, it creates a module object [\[1\]](#import--fnmo){#import--id1}, initializing it. If the named module cannot be found, a [`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError) is raised. Python implements various strategies to search for the named module when the import machinery is invoked. These strategies can be modified and extended by using various hooks described in the sections below.

Changed in version 3.3: The import system has been updated to fully implement the second phase of <span id="import--index-1"></span>[**PEP 302**](https://peps.python.org/pep-0302/). There is no longer any implicit import machinery - the full import system is exposed through [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path). In addition, native namespace package support has been implemented (see <span id="import--index-2"></span>[**PEP 420**](https://peps.python.org/pep-0420/)).

## 5.1. [`importlib`](https://docs.python.org/3/library/importlib.html#module-importlib) {#import--importlib}

The [`importlib`](https://docs.python.org/3/library/importlib.html#module-importlib) module provides a rich API for interacting with the import system. For example [`importlib.import_module()`](https://docs.python.org/3/library/importlib.html#importlib.import_module) provides a recommended, simpler API than built-in [`__import__()`](https://docs.python.org/3/library/functions.html#import__) for invoking the import machinery. Refer to the `importlib` library documentation for additional detail.

## 5.2. Packages {#import--packages}

Python has only one type of module object, and all modules are of this type, regardless of whether the module is implemented in Python, C, or something else. To help organize modules and provide a naming hierarchy, Python has a concept of [packages](https://docs.python.org/3/glossary.html#term-package).

You can think of packages as the directories on a file system and modules as files within directories, but don’t take this analogy too literally since packages and modules need not originate from the file system. For the purposes of this documentation, we’ll use this convenient analogy of directories and files. Like file system directories, packages are organized hierarchically, and packages may themselves contain subpackages, as well as regular modules.

It’s important to keep in mind that all packages are modules, but not all modules are packages. Or put another way, packages are just a special kind of module. Specifically, any module that contains a `__path__` attribute is considered a package.

All modules have a name. Subpackage names are separated from their parent package name by a dot, akin to Python’s standard attribute access syntax. Thus you might have a package called [`email`](https://docs.python.org/3/library/email.html#module-email), which in turn has a subpackage called [`email.mime`](https://docs.python.org/3/library/email.mime.html#module-email.mime) and a module within that subpackage called [`email.mime.text`](https://docs.python.org/3/library/email.mime.html#module-email.mime.text).

### 5.2.1. Regular packages {#import--regular-packages}

Python defines two types of packages, [regular packages](https://docs.python.org/3/glossary.html#term-regular-package) and [namespace packages](https://docs.python.org/3/glossary.html#term-namespace-package). Regular packages are traditional packages as they existed in Python 3.2 and earlier. A regular package is typically implemented as a directory containing an `__init__.py` file. When a regular package is imported, this `__init__.py` file is implicitly executed, and the objects it defines are bound to names in the package’s namespace. The `__init__.py` file can contain the same Python code that any other module can contain, and Python will add some additional attributes to the module when it is imported.

For example, the following file system layout defines a top level `parent` package with three subpackages:

    parent/
        __init__.py
        one/
            __init__.py
        two/
            __init__.py
        three/
            __init__.py

Importing `parent.one` will implicitly execute `parent/__init__.py` and `parent/one/__init__.py`. Subsequent imports of `parent.two` or `parent.three` will execute `parent/two/__init__.py` and `parent/three/__init__.py` respectively.

A subdirectory inside a regular package that does not contain an `__init__.py` file is treated as an implicit [namespace package](#import--reference-namespace-package) (a “namespace subpackage”) rooted in that parent. See <span id="import--index-5"></span>[**PEP 420**](https://peps.python.org/pep-0420/) for the underlying specification.

<span id="import--reference-namespace-package"></span>

### 5.2.2. Namespace packages {#import--namespace-packages}

A namespace package is a composite of various [portions](https://docs.python.org/3/glossary.html#term-portion), where each portion contributes a subpackage to the parent package. Portions may reside in different locations on the file system. Portions may also be found in zip files, on the network, or anywhere else that Python searches during import. Namespace packages may or may not correspond directly to objects on the file system; they may be virtual modules that have no concrete representation.

Namespace packages do not use an ordinary list for their `__path__` attribute. They instead use a custom iterable type which will automatically perform a new search for package portions on the next import attempt within that package if the path of their parent package (or [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) for a top level package) changes.

With namespace packages, there is no `parent/__init__.py` file. In fact, there may be multiple `parent` directories found during import search, where each one is provided by a different portion. Thus `parent/one` may not be physically located next to `parent/two`. In this case, Python will create a namespace package for the top-level `parent` package whenever it or one of its subpackages is imported.

Namespace packages may also be nested inside a regular package. When the import system searches a regular package’s `__path__` and encounters a subdirectory that does not contain an `__init__.py` file, that subdirectory becomes a [portion](https://docs.python.org/3/glossary.html#term-portion) contributing to a namespace subpackage of the enclosing regular package.

See also <span id="import--index-7"></span>[**PEP 420**](https://peps.python.org/pep-0420/) for the namespace package specification.

## 5.3. Searching {#import--searching}

To begin the search, Python needs the [fully qualified](https://docs.python.org/3/glossary.html#term-qualified-name) name of the module (or package, but for the purposes of this discussion, the difference is immaterial) being imported. This name may come from various arguments to the [`import`](#simple_stmts--import) statement, or from the parameters to the [`importlib.import_module()`](https://docs.python.org/3/library/importlib.html#importlib.import_module) or [`__import__()`](https://docs.python.org/3/library/functions.html#import__) functions.

This name will be used in various phases of the import search, and it may be the dotted path to a submodule, e.g. `foo.bar.baz`. In this case, Python first tries to import `foo`, then `foo.bar`, and finally `foo.bar.baz`. If any of the intermediate imports fail, a [`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError) is raised.

### 5.3.1. The module cache {#import--the-module-cache}

The first place checked during import search is [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules). This mapping serves as a cache of all modules that have been previously imported, including the intermediate paths. So if `foo.bar.baz` was previously imported, `sys.modules` will contain entries for `foo`, `foo.bar`, and `foo.bar.baz`. Each key will have as its value the corresponding module object.

During import, the module name is looked up in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules) and if present, the associated value is the module satisfying the import, and the process completes. However, if the value is `None`, then a [`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError) is raised. If the module name is missing, Python will continue searching for the module.

[`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules) is writable. Deleting a key may not destroy the associated module (as other modules may hold references to it), but it will invalidate the cache entry for the named module, causing Python to search anew for the named module upon its next import. The key can also be assigned to `None`, forcing the next import of the module to result in a [`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError).

Beware though, as if you keep a reference to the module object, invalidate its cache entry in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules), and then re-import the named module, the two module objects will *not* be the same. By contrast, [`importlib.reload()`](https://docs.python.org/3/library/importlib.html#importlib.reload) will reuse the *same* module object, and simply reinitialise the module contents by rerunning the module’s code.

<span id="import--id2"></span>

### 5.3.2. Finders and loaders {#import--finders-and-loaders}

If the named module is not found in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules), then Python’s import protocol is invoked to find and load the module. This protocol consists of two conceptual objects, [finders](https://docs.python.org/3/glossary.html#term-finder) and [loaders](https://docs.python.org/3/glossary.html#term-loader). A finder’s job is to determine whether it can find the named module using whatever strategy it knows about. Objects that implement both of these interfaces are referred to as [importers](https://docs.python.org/3/glossary.html#term-importer) - they return themselves when they find that they can load the requested module.

Python includes a number of default finders and importers. The first one knows how to locate built-in modules, and the second knows how to locate frozen modules. A third default finder searches an [import path](https://docs.python.org/3/glossary.html#term-import-path) for modules. The import path is a list of locations that may name file system paths or zip files. It can also be extended to search for any locatable resource, such as those identified by URLs.

The import machinery is extensible, so new finders can be added to extend the range and scope of module searching.

Finders do not actually load modules. If they can find the named module, they return a *module spec*, an encapsulation of the module’s import-related information, which the import machinery then uses when loading the module.

The following sections describe the protocol for finders and loaders in more detail, including how you can create and register new ones to extend the import machinery.

Changed in version 3.4: In previous versions of Python, finders returned [loaders](https://docs.python.org/3/glossary.html#term-loader) directly, whereas now they return module specs which *contain* loaders. Loaders are still used during import but have fewer responsibilities.

### 5.3.3. Import hooks {#import--import-hooks}

The import machinery is designed to be extensible; the primary mechanism for this are the *import hooks*. There are two types of import hooks: *meta hooks* and *import path hooks*.

Meta hooks are called at the start of import processing, before any other import processing has occurred, other than [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules) cache look up. This allows meta hooks to override [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) processing, frozen modules, or even built-in modules. Meta hooks are registered by adding new finder objects to [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path), as described below.

Import path hooks are called as part of [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) (or `package.__path__`) processing, at the point where their associated path item is encountered. Import path hooks are registered by adding new callables to [`sys.path_hooks`](https://docs.python.org/3/library/sys.html#sys.path_hooks) as described below.

### 5.3.4. The meta path {#import--the-meta-path}

When the named module is not found in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules), Python next searches [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path), which contains a list of meta path finder objects. These finders are queried in order to see if they know how to handle the named module. Meta path finders must implement a method called [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec) which takes three arguments: a name, an import path, and (optionally) a target module. The meta path finder can use any strategy it wants to determine whether it can handle the named module or not.

If the meta path finder knows how to handle the named module, it returns a spec object. If it cannot handle the named module, it returns `None`. If [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path) processing reaches the end of its list without returning a spec, then a [`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError) is raised. Any other exceptions raised are simply propagated up, aborting the import process.

The [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec) method of meta path finders is called with two or three arguments. The first is the fully qualified name of the module being imported, for example `foo.bar.baz`. The second argument is the path entries to use for the module search. For top-level modules, the second argument is `None`, but for submodules or subpackages, the second argument is the value of the parent package’s `__path__` attribute. If the appropriate `__path__` attribute cannot be accessed, a [`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError) is raised. The third argument is an existing module object that will be the target of loading later. The import system passes in a target module only during reload.

The meta path may be traversed multiple times for a single import request. For example, assuming none of the modules involved has already been cached, importing `foo.bar.baz` will first perform a top level import, calling `mpf.find_spec("foo", None, None)` on each meta path finder (`mpf`). After `foo` has been imported, `foo.bar` will be imported by traversing the meta path a second time, calling `mpf.find_spec("foo.bar", foo.__path__, None)`. Once `foo.bar` has been imported, the final traversal will call `mpf.find_spec("foo.bar.baz", foo.bar.__path__, None)`.

Some meta path finders only support top level imports. These importers will always return `None` when anything other than `None` is passed as the second argument.

Python’s default [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path) has three meta path finders, one that knows how to import built-in modules, one that knows how to import frozen modules, and one that knows how to import modules from an [import path](https://docs.python.org/3/glossary.html#term-import-path) (i.e. the [path based finder](https://docs.python.org/3/glossary.html#term-path-based-finder)).

Changed in version 3.4: The [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec) method of meta path finders replaced `find_module()`, which is now deprecated. While it will continue to work without change, the import machinery will try it only if the finder does not implement `find_spec()`.

Changed in version 3.10: Use of `find_module()` by the import system now raises [`ImportWarning`](https://docs.python.org/3/library/exceptions.html#ImportWarning).

Changed in version 3.12: `find_module()` has been removed. Use [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec) instead.

## 5.4. Loading {#import--loading}

If and when a module spec is found, the import machinery will use it (and the loader it contains) when loading the module. Here is an approximation of what happens during the loading portion of import:

    module = None
    if spec.loader is not None and hasattr(spec.loader, 'create_module'):
        # It is assumed 'exec_module' will also be defined on the loader.
        module = spec.loader.create_module(spec)
    if module is None:
        module = ModuleType(spec.name)
    # The import-related module attributes get set here:
    _init_module_attrs(spec, module)

    if spec.loader is None:
        # unsupported
        raise ImportError
    if spec.origin is None and spec.submodule_search_locations is not None:
        # namespace package
        sys.modules[spec.name] = module
    elif not hasattr(spec.loader, 'exec_module'):
        module = spec.loader.load_module(spec.name)
    else:
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            try:
                del sys.modules[spec.name]
            except KeyError:
                pass
            raise
    return sys.modules[spec.name]

Note the following details:

- If there is an existing module object with the given name in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules), import will have already returned it.

- The module will exist in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules) before the loader executes the module code. This is crucial because the module code may (directly or indirectly) import itself; adding it to `sys.modules` beforehand prevents unbounded recursion in the worst case and multiple loading in the best.

- If loading fails, the failing module – and only the failing module – gets removed from [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules). Any module already in the `sys.modules` cache, and any module that was successfully loaded as a side-effect, must remain in the cache. This contrasts with reloading where even the failing module is left in `sys.modules`.

- After the module is created but before execution, the import machinery sets the import-related module attributes (“\_init_module_attrs” in the pseudo-code example above), as summarized in a [later section](#datamodel--import-mod-attrs).

- Module execution is the key moment of loading in which the module’s namespace gets populated. Execution is entirely delegated to the loader, which gets to decide what gets populated and how.

- The module created during loading and passed to exec_module() may not be the one returned at the end of import [\[2\]](#import--fnlo){#import--id3}.

Changed in version 3.4: The import system has taken over the boilerplate responsibilities of loaders. These were previously performed by the [`importlib.abc.Loader.load_module()`](https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.load_module) method.

### 5.4.1. Loaders {#import--loaders}

Module loaders provide the critical function of loading: module execution. The import machinery calls the [`importlib.abc.Loader.exec_module()`](https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.exec_module) method with a single argument, the module object to execute. Any value returned from `exec_module()` is ignored.

Loaders must satisfy the following requirements:

- If the module is a Python module (as opposed to a built-in module or a dynamically loaded extension), the loader should execute the module’s code in the module’s global name space (`module.__dict__`).

- If the loader cannot execute the module, it should raise an [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError), although any other exception raised during [`exec_module()`](https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.exec_module) will be propagated.

In many cases, the finder and loader can be the same object; in such cases the [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec) method would just return a spec with the loader set to `self`.

Module loaders may opt in to creating the module object during loading by implementing a [`create_module()`](https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.create_module) method. It takes one argument, the module spec, and returns the new module object to use during loading. `create_module()` does not need to set any attributes on the module object. If the method returns `None`, the import machinery will create the new module itself.

Added in version 3.4: The [`create_module()`](https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.create_module) method of loaders.

Changed in version 3.4: The [`load_module()`](https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.load_module) method was replaced by [`exec_module()`](https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.exec_module) and the import machinery assumed all the boilerplate responsibilities of loading.

For compatibility with existing loaders, the import machinery will use the `load_module()` method of loaders if it exists and the loader does not also implement `exec_module()`. However, `load_module()` has been deprecated and loaders should implement `exec_module()` instead.

The `load_module()` method must implement all the boilerplate loading functionality described above in addition to executing the module. All the same constraints apply, with some additional clarification:

- If there is an existing module object with the given name in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules), the loader must use that existing module. (Otherwise, [`importlib.reload()`](https://docs.python.org/3/library/importlib.html#importlib.reload) will not work correctly.) If the named module does not exist in `sys.modules`, the loader must create a new module object and add it to `sys.modules`.

- The module *must* exist in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules) before the loader executes the module code, to prevent unbounded recursion or multiple loading.

- If loading fails, the loader must remove any modules it has inserted into [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules), but it must remove **only** the failing module(s), and only if the loader itself has loaded the module(s) explicitly.

Changed in version 3.5: A [`DeprecationWarning`](https://docs.python.org/3/library/exceptions.html#DeprecationWarning) is raised when `exec_module()` is defined but `create_module()` is not.

Changed in version 3.6: An [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError) is raised when `exec_module()` is defined but `create_module()` is not.

Changed in version 3.10: Use of `load_module()` will raise [`ImportWarning`](https://docs.python.org/3/library/exceptions.html#ImportWarning).

### 5.4.2. Submodules {#import--submodules}

When a submodule is loaded using any mechanism (e.g. `importlib` APIs, the `import` or `import-from` statements, or built-in `__import__()`) a binding is placed in the parent module’s namespace to the submodule object. For example, if package `spam` has a submodule `foo`, after importing `spam.foo`, `spam` will have an attribute `foo` which is bound to the submodule. Let’s say you have the following directory structure:

    spam/
        __init__.py
        foo.py

and `spam/__init__.py` has the following line in it:

    from .foo import Foo

then executing the following puts name bindings for `foo` and `Foo` in the `spam` module:

    >>> import spam
    >>> spam.foo
    <module 'spam.foo' from '/tmp/imports/spam/foo.py'>
    >>> spam.Foo
    <class 'spam.foo.Foo'>

Given Python’s familiar name binding rules this might seem surprising, but it’s actually a fundamental feature of the import system. The invariant holding is that if you have `sys.modules['spam']` and `sys.modules['spam.foo']` (as you would after the above import), the latter must appear as the `foo` attribute of the former.

<span id="import--id4"></span>

### 5.4.3. Module specs {#import--module-specs}

The import machinery uses a variety of information about each module during import, especially before loading. Most of the information is common to all modules. The purpose of a module’s spec is to encapsulate this import-related information on a per-module basis.

Using a spec during import allows state to be transferred between import system components, e.g. between the finder that creates the module spec and the loader that executes it. Most importantly, it allows the import machinery to perform the boilerplate operations of loading, whereas without a module spec the loader had that responsibility.

The module’s spec is exposed as [`module.__spec__`](#datamodel--module.__spec__). Setting `__spec__` appropriately applies equally to [modules initialized during interpreter startup](#toplevel_components--programs). The one exception is `__main__`, where `__spec__` is [set to None in some cases](#import--main-spec).

See [`ModuleSpec`](https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec) for details on the contents of the module spec.

Added in version 3.4.

<span id="import--package-path-rules"></span>

### 5.4.4. \_\_path\_\_ attributes on modules {#import--path-attributes-on-modules}

The [`__path__`](#datamodel--module.__path__) attribute should be a (possibly empty) [sequence](https://docs.python.org/3/glossary.html#term-sequence) of strings enumerating the locations where the package’s submodules will be found. By definition, if a module has a `__path__` attribute, it is a [package](https://docs.python.org/3/glossary.html#term-package).

A package’s [`__path__`](#datamodel--module.__path__) attribute is used during imports of its subpackages. Within the import machinery, it functions much the same as [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path), i.e. providing a list of locations to search for modules during import. However, `__path__` is typically much more constrained than `sys.path`.

The same rules used for [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) also apply to a package’s `__path__`. [`sys.path_hooks`](https://docs.python.org/3/library/sys.html#sys.path_hooks) (described below) are consulted when traversing a package’s `__path__`.

A package’s `__init__.py` file may set or alter the package’s [`__path__`](#datamodel--module.__path__) attribute, and this was typically the way namespace packages were implemented prior to <span id="import--index-12"></span>[**PEP 420**](https://peps.python.org/pep-0420/). With the adoption of <span id="import--index-13"></span>[**PEP 420**](https://peps.python.org/pep-0420/), namespace packages no longer need to supply `__init__.py` files containing only `__path__` manipulation code; the import machinery automatically sets `__path__` correctly for the namespace package.

### 5.4.5. Module reprs {#import--module-reprs}

By default, all modules have a usable repr, however depending on the attributes set above, and in the module’s spec, you can more explicitly control the repr of module objects.

If the module has a spec (`__spec__`), the import machinery will try to generate a repr from it. If that fails or there is no spec, the import system will craft a default repr using whatever information is available on the module. It will try to use the `module.__name__`, `module.__file__`, and `module.__loader__` as input into the repr, with defaults for whatever information is missing.

Here are the exact rules used:

- If the module has a `__spec__` attribute, the information in the spec is used to generate the repr. The “name”, “loader”, “origin”, and “has_location” attributes are consulted.

- If the module has a `__file__` attribute, this is used as part of the module’s repr.

- If the module has no `__file__` but does have a `__loader__` that is not `None`, then the loader’s repr is used as part of the module’s repr.

- Otherwise, just use the module’s `__name__` in the repr.

Changed in version 3.12: Use of `module_repr()`, having been deprecated since Python 3.4, was removed in Python 3.12 and is no longer called during the resolution of a module’s repr.

<span id="import--pyc-invalidation"></span>

### 5.4.6. Cached bytecode invalidation {#import--cached-bytecode-invalidation}

Before Python loads cached bytecode from a `.pyc` file, it checks whether the cache is up-to-date with the source `.py` file. By default, Python does this by storing the source’s last-modified timestamp and size in the cache file when writing it. At runtime, the import system then validates the cache file by checking the stored metadata in the cache file against the source’s metadata.

Python also supports “hash-based” cache files, which store a hash of the source file’s contents rather than its metadata. There are two variants of hash-based `.pyc` files: checked and unchecked. For checked hash-based `.pyc` files, Python validates the cache file by hashing the source file and comparing the resulting hash with the hash in the cache file. If a checked hash-based cache file is found to be invalid, Python regenerates it and writes a new checked hash-based cache file. For unchecked hash-based `.pyc` files, Python simply assumes the cache file is valid if it exists. Hash-based `.pyc` files validation behavior may be overridden with the [`--check-hash-based-pycs`](https://docs.python.org/3/using/cmdline.html#cmdoption-check-hash-based-pycs) flag.

Changed in version 3.7: Added hash-based `.pyc` files. Previously, Python only supported timestamp-based invalidation of bytecode caches.

## 5.5. The Path Based Finder {#import--the-path-based-finder}

As mentioned previously, Python comes with several default meta path finders. One of these, called the [path based finder](https://docs.python.org/3/glossary.html#term-path-based-finder) ([`PathFinder`](https://docs.python.org/3/library/importlib.html#importlib.machinery.PathFinder)), searches an [import path](https://docs.python.org/3/glossary.html#term-import-path), which contains a list of [path entries](https://docs.python.org/3/glossary.html#term-path-entry). Each path entry names a location to search for modules.

The path based finder itself doesn’t know how to import anything. Instead, it traverses the individual path entries, associating each of them with a path entry finder that knows how to handle that particular kind of path.

The default set of path entry finders implement all the semantics for finding modules on the file system, handling special file types such as Python source code (`.py` files), Python byte code (`.pyc` files) and shared libraries (e.g. `.so` files). When supported by the [`zipimport`](https://docs.python.org/3/library/zipimport.html#module-zipimport) module in the standard library, the default path entry finders also handle loading all of these file types (other than shared libraries) from zipfiles.

Path entries need not be limited to file system locations. They can refer to URLs, database queries, or any other location that can be specified as a string.

The path based finder provides additional hooks and protocols so that you can extend and customize the types of searchable path entries. For example, if you wanted to support path entries as network URLs, you could write a hook that implements HTTP semantics to find modules on the web. This hook (a callable) would return a [path entry finder](https://docs.python.org/3/glossary.html#term-path-entry-finder) supporting the protocol described below, which was then used to get a loader for the module from the web.

A word of warning: this section and the previous both use the term *finder*, distinguishing between them by using the terms [meta path finder](https://docs.python.org/3/glossary.html#term-meta-path-finder) and [path entry finder](https://docs.python.org/3/glossary.html#term-path-entry-finder). These two types of finders are very similar, support similar protocols, and function in similar ways during the import process, but it’s important to keep in mind that they are subtly different. In particular, meta path finders operate at the beginning of the import process, as keyed off the [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path) traversal.

By contrast, path entry finders are in a sense an implementation detail of the path based finder, and in fact, if the path based finder were to be removed from [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path), none of the path entry finder semantics would be invoked.

### 5.5.1. Path entry finders {#import--path-entry-finders}

The [path based finder](https://docs.python.org/3/glossary.html#term-path-based-finder) is responsible for finding and loading Python modules and packages whose location is specified with a string [path entry](https://docs.python.org/3/glossary.html#term-path-entry). Most path entries name locations in the file system, but they need not be limited to this.

As a meta path finder, the [path based finder](https://docs.python.org/3/glossary.html#term-path-based-finder) implements the [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec) protocol previously described, however it exposes additional hooks that can be used to customize how modules are found and loaded from the [import path](https://docs.python.org/3/glossary.html#term-import-path).

Three variables are used by the [path based finder](https://docs.python.org/3/glossary.html#term-path-based-finder), [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path), [`sys.path_hooks`](https://docs.python.org/3/library/sys.html#sys.path_hooks) and [`sys.path_importer_cache`](https://docs.python.org/3/library/sys.html#sys.path_importer_cache). The `__path__` attributes on package objects are also used. These provide additional ways that the import machinery can be customized.

[`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) contains a list of strings providing search locations for modules and packages. It is initialized from the <span id="import--index-16"></span>[`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH) environment variable and various other installation- and implementation-specific defaults. Entries in `sys.path` can name directories on the file system, zip files, and potentially other “locations” (see the [`site`](https://docs.python.org/3/library/site.html#module-site) module) that should be searched for modules, such as URLs, or database queries. Only strings should be present on `sys.path`; all other data types are ignored.

The [path based finder](https://docs.python.org/3/glossary.html#term-path-based-finder) is a [meta path finder](https://docs.python.org/3/glossary.html#term-meta-path-finder), so the import machinery begins the [import path](https://docs.python.org/3/glossary.html#term-import-path) search by calling the path based finder’s [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.machinery.PathFinder.find_spec) method as described previously. When the `path` argument to `find_spec()` is given, it will be a list of string paths to traverse - typically a package’s `__path__` attribute for an import within that package. If the `path` argument is `None`, this indicates a top level import and [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) is used.

The path based finder iterates over every entry in the search path, and for each of these, looks for an appropriate [path entry finder](https://docs.python.org/3/glossary.html#term-path-entry-finder) ([`PathEntryFinder`](https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder)) for the path entry. Because this can be an expensive operation (e.g. there may be `stat()` call overheads for this search), the path based finder maintains a cache mapping path entries to path entry finders. This cache is maintained in [`sys.path_importer_cache`](https://docs.python.org/3/library/sys.html#sys.path_importer_cache) (despite the name, this cache actually stores finder objects rather than being limited to [importer](https://docs.python.org/3/glossary.html#term-importer) objects). In this way, the expensive search for a particular [path entry](https://docs.python.org/3/glossary.html#term-path-entry) location’s path entry finder need only be done once. User code is free to remove cache entries from `sys.path_importer_cache` forcing the path based finder to perform the path entry search again.

If the path entry is not present in the cache, the path based finder iterates over every callable in [`sys.path_hooks`](https://docs.python.org/3/library/sys.html#sys.path_hooks). Each of the [path entry hooks](https://docs.python.org/3/glossary.html#term-path-entry-hook) in this list is called with a single argument, the path entry to be searched. This callable may either return a [path entry finder](https://docs.python.org/3/glossary.html#term-path-entry-finder) that can handle the path entry, or it may raise [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError). An `ImportError` is used by the path based finder to signal that the hook cannot find a path entry finder for that [path entry](https://docs.python.org/3/glossary.html#term-path-entry). The exception is ignored and [import path](https://docs.python.org/3/glossary.html#term-import-path) iteration continues. The hook should expect either a string or bytes object; the encoding of bytes objects is up to the hook (e.g. it may be a file system encoding, UTF-8, or something else), and if the hook cannot decode the argument, it should raise `ImportError`.

If [`sys.path_hooks`](https://docs.python.org/3/library/sys.html#sys.path_hooks) iteration ends with no [path entry finder](https://docs.python.org/3/glossary.html#term-path-entry-finder) being returned, then the path based finder’s [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.machinery.PathFinder.find_spec) method will store `None` in [`sys.path_importer_cache`](https://docs.python.org/3/library/sys.html#sys.path_importer_cache) (to indicate that there is no finder for this path entry) and return `None`, indicating that this [meta path finder](https://docs.python.org/3/glossary.html#term-meta-path-finder) could not find the module.

If a [path entry finder](https://docs.python.org/3/glossary.html#term-path-entry-finder) *is* returned by one of the [path entry hook](https://docs.python.org/3/glossary.html#term-path-entry-hook) callables on [`sys.path_hooks`](https://docs.python.org/3/library/sys.html#sys.path_hooks), then the following protocol is used to ask the finder for a module spec, which is then used when loading the module.

The current working directory – denoted by an empty string – is handled slightly differently from other entries on [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path). First, if the current working directory cannot be determined or is found not to exist, no value is stored in [`sys.path_importer_cache`](https://docs.python.org/3/library/sys.html#sys.path_importer_cache). Second, the value for the current working directory is looked up fresh for each module lookup. Third, the path used for `sys.path_importer_cache` and returned by [`importlib.machinery.PathFinder.find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.machinery.PathFinder.find_spec) will be the actual current working directory and not the empty string.

### 5.5.2. Path entry finder protocol {#import--path-entry-finder-protocol}

In order to support imports of modules and initialized packages and also to contribute portions to namespace packages, path entry finders must implement the [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder.find_spec) method.

[`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder.find_spec) takes two arguments: the fully qualified name of the module being imported, and the (optional) target module. `find_spec()` returns a fully populated spec for the module. This spec will always have “loader” set (with one exception).

To indicate to the import machinery that the spec represents a namespace [portion](https://docs.python.org/3/glossary.html#term-portion), the path entry finder sets `submodule_search_locations` to a list containing the portion.

Changed in version 3.4: [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder.find_spec) replaced `find_loader()` and `find_module()`, both of which are now deprecated, but will be used if `find_spec()` is not defined.

Older path entry finders may implement one of these two deprecated methods instead of `find_spec()`. The methods are still respected for the sake of backward compatibility. However, if `find_spec()` is implemented on the path entry finder, the legacy methods are ignored.

`find_loader()` takes one argument, the fully qualified name of the module being imported. `find_loader()` returns a 2-tuple where the first item is the loader and the second item is a namespace [portion](https://docs.python.org/3/glossary.html#term-portion).

For backwards compatibility with other implementations of the import protocol, many path entry finders also support the same, traditional `find_module()` method that meta path finders support. However path entry finder `find_module()` methods are never called with a `path` argument (they are expected to record the appropriate path information from the initial call to the path hook).

The `find_module()` method on path entry finders is deprecated, as it does not allow the path entry finder to contribute portions to namespace packages. If both `find_loader()` and `find_module()` exist on a path entry finder, the import system will always call `find_loader()` in preference to `find_module()`.

Changed in version 3.10: Calls to `find_module()` and `find_loader()` by the import system will raise [`ImportWarning`](https://docs.python.org/3/library/exceptions.html#ImportWarning).

Changed in version 3.12: `find_module()` and `find_loader()` have been removed.

## 5.6. Replacing the standard import system {#import--replacing-the-standard-import-system}

The most reliable mechanism for replacing the entire import system is to delete the default contents of [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path), replacing them entirely with a custom meta path hook.

If it is acceptable to only alter the behaviour of import statements without affecting other APIs that access the import system, then replacing the builtin [`__import__()`](https://docs.python.org/3/library/functions.html#import__) function may be sufficient.

To selectively prevent the import of some modules from a hook early on the meta path (rather than disabling the standard import system entirely), it is sufficient to raise [`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError) directly from [`find_spec()`](https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec) instead of returning `None`. The latter indicates that the meta path search should continue, while raising an exception terminates it immediately.

<span id="import--relativeimports"></span>

## 5.7. Package Relative Imports {#import--package-relative-imports}

Relative imports use leading dots. A single leading dot indicates a relative import, starting with the current package. Two or more leading dots indicate a relative import to the parent(s) of the current package, one level per dot after the first. For example, given the following package layout:

    package/
        __init__.py
        subpackage1/
            __init__.py
            moduleX.py
            moduleY.py
        subpackage2/
            __init__.py
            moduleZ.py
        moduleA.py

In either `subpackage1/moduleX.py` or `subpackage1/__init__.py`, the following are valid relative imports:

    from .moduleY import spam
    from .moduleY import spam as ham
    from . import moduleY
    from ..subpackage1 import moduleY
    from ..subpackage2.moduleZ import eggs
    from ..moduleA import foo

Absolute imports may use either the `import <>` or `from <> import <>` syntax, but relative imports may only use the second form; the reason for this is that:

    import XXX.YYY.ZZZ

should expose `XXX.YYY.ZZZ` as a usable expression, but .moduleY is not a valid expression.

<span id="import--import-dunder-main"></span>

## 5.8. Special considerations for \_\_main\_\_ {#import--special-considerations-for-main}

The [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__) module is a special case relative to Python’s import system. As noted [elsewhere](#toplevel_components--programs), the `__main__` module is directly initialized at interpreter startup, much like [`sys`](https://docs.python.org/3/library/sys.html#module-sys) and [`builtins`](https://docs.python.org/3/library/builtins.html#module-builtins). However, unlike those two, it doesn’t strictly qualify as a built-in module. This is because the manner in which `__main__` is initialized depends on the flags and other options with which the interpreter is invoked.

<span id="import--id5"></span>

### 5.8.1. \_\_main\_\_.\_\_spec\_\_ {#import--main-spec}

Depending on how [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__) is initialized, `__main__.__spec__` gets set appropriately or to `None`.

When Python is started with the [`-m`](https://docs.python.org/3/using/cmdline.html#cmdoption-m) option, `__spec__` is set to the module spec of the corresponding module or package. `__spec__` is also populated when the `__main__` module is loaded as part of executing a directory, zipfile or other [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) entry.

In [the remaining cases](https://docs.python.org/3/using/cmdline.html#using-on-interface-options) `__main__.__spec__` is set to `None`, as the code used to populate the [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__) does not correspond directly with an importable module:

- interactive prompt

- [`-c`](https://docs.python.org/3/using/cmdline.html#cmdoption-c) option

- running from stdin

- running directly from a source or bytecode file

Note that `__main__.__spec__` is always `None` in the last case, *even if* the file could technically be imported directly as a module instead. Use the [`-m`](https://docs.python.org/3/using/cmdline.html#cmdoption-m) switch if valid module metadata is desired in [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__).

Note also that even when `__main__` corresponds with an importable module and `__main__.__spec__` is set accordingly, they’re still considered *distinct* modules. This is due to the fact that blocks guarded by `if __name__ == "__main__":` checks only execute when the module is used to populate the `__main__` namespace, and not during normal import.

## 5.9. References {#import--references}

The import machinery has evolved considerably since Python’s early days. The original [specification for packages](https://www.python.org/doc/essays/packages/) is still available to read, although some details have changed since the writing of that document.

The original specification for [`sys.meta_path`](https://docs.python.org/3/library/sys.html#sys.meta_path) was <span id="import--index-17"></span>[**PEP 302**](https://peps.python.org/pep-0302/), with subsequent extension in <span id="import--index-18"></span>[**PEP 420**](https://peps.python.org/pep-0420/).

<span id="import--index-19"></span>[**PEP 420**](https://peps.python.org/pep-0420/) introduced [namespace packages](https://docs.python.org/3/glossary.html#term-namespace-package) for Python 3.3. <span id="import--index-20"></span>[**PEP 420**](https://peps.python.org/pep-0420/) also introduced the `find_loader()` protocol as an alternative to `find_module()`.

<span id="import--index-21"></span>[**PEP 366**](https://peps.python.org/pep-0366/) describes the addition of the `__package__` attribute for explicit relative imports in main modules.

<span id="import--index-22"></span>[**PEP 328**](https://peps.python.org/pep-0328/) introduced absolute and explicit relative imports and initially proposed `__name__` for semantics <span id="import--index-23"></span>[**PEP 366**](https://peps.python.org/pep-0366/) would eventually specify for `__package__`.

<span id="import--index-24"></span>[**PEP 338**](https://peps.python.org/pep-0338/) defines executing modules as scripts.

<span id="import--index-25"></span>[**PEP 451**](https://peps.python.org/pep-0451/) adds the encapsulation of per-module import state in spec objects. It also off-loads most of the boilerplate responsibilities of loaders back onto the import machinery. These changes allow the deprecation of several APIs in the import system and also addition of new methods to finders and loaders.

Footnotes

\[[1](#import--id1)\]

See [`types.ModuleType`](https://docs.python.org/3/library/types.html#types.ModuleType).

\[[2](#import--id3)\]

The importlib implementation avoids using the return value directly. Instead, it gets the module object by looking the module name up in [`sys.modules`](https://docs.python.org/3/library/sys.html#sys.modules). The indirect effect of this is that an imported module may replace itself in `sys.modules`. This is implementation-specific behavior that is not guaranteed to work in other Python implementations.

<span id="expressions--id1"></span>

# 6. Expressions {#expressions--expressions}

This chapter explains the meaning of the elements of expressions in Python.

**Syntax Notes:** In this and the following chapters, [grammar notation](#introduction--notation) will be used to describe syntax, not lexical analysis.

When (one alternative of) a syntax rule has the form:

    name: othername

and no semantics are given, the semantics of this form of `name` are the same as for `othername`.

<span id="expressions--conversions"></span>

## 6.1. Arithmetic conversions {#expressions--arithmetic-conversions}

When a description of an arithmetic operator below uses the phrase “the numeric arguments are converted to a common real type”, this means that the operator implementation for built-in numeric types works as described in the [Numeric Types](https://docs.python.org/3/library/stdtypes.html#stdtypes-mixed-arithmetic) section of the standard library documentation.

Some additional rules apply for certain operators and non-numeric operands (for example, a string as a left argument to the `%` operator). Extensions must define their own conversion behavior.

<span id="expressions--id2"></span>

## 6.2. Atoms {#expressions--atoms}

Atoms are the most basic elements of expressions. The simplest atoms are [names](#lexical_analysis--identifiers) or literals. Forms enclosed in parentheses, brackets or braces are also categorized syntactically as atoms.

Formally, the syntax for atoms is:

    atom:
       | 'True'
       | 'False'
       | 'None'
       | '...'
       | identifier
       | literal
       | enclosure
    enclosure:
       | parenth_form
       | list_display
       | dict_display
       | set_display
       | generator_expression
       | yield_atom

<span id="expressions--atom-singletons"></span>

### 6.2.1. Built-in constants {#expressions--built-in-constants}

The keywords `True`, `False`, and `None` name [built-in constants](https://docs.python.org/3/library/constants.html#built-in-consts). The token `...` names the [`Ellipsis`](https://docs.python.org/3/library/constants.html#Ellipsis) constant.

Evaluation of these atoms yields the corresponding value.

Note

Several more built-in constants are available as global variables, but only the ones mentioned here are [keywords](#lexical_analysis--keywords). In particular, these names cannot be reassigned or used as attributes:

    >>> False = 123
      File "<input>", line 1
       False = 123
       ^^^^^
    SyntaxError: cannot assign to False

<span id="expressions--identifiers-names"></span>

### 6.2.2. Identifiers (Names) {#expressions--atom-identifiers}

An identifier occurring as an atom is a name. See section [Names (identifiers and keywords)](#lexical_analysis--identifiers) for lexical definition and section [Naming and binding](#executionmodel--naming) for documentation of naming and binding.

When the name is bound to an object, evaluation of the atom yields that object. When a name is not bound, an attempt to evaluate it raises a [`NameError`](https://docs.python.org/3/library/exceptions.html#NameError) exception.

<span id="expressions--private-name-mangling"></span> <span id="expressions--id3"></span>

#### 6.2.2.1. Private name mangling {#expressions--index-5}

When an identifier that textually occurs in a class definition begins with two or more underscore characters and does not end in two or more underscores, it is considered a *private name* of that class.

See also

The [class specifications](#compound_stmts--class).

More precisely, private names are transformed to a longer form before code is generated for them. If the transformed name is longer than 255 characters, implementation-defined truncation may happen.

The transformation is independent of the syntactical context in which the identifier is used but only the following private identifiers are mangled:

- Any name used as the name of a variable that is assigned or read or any name of an attribute being accessed.

  The [`__name__`](https://docs.python.org/3/library/stdtypes.html#definition.__name__) attribute of nested functions, classes, and type aliases is however not mangled.

- The name of imported modules, e.g., `__spam` in `import __spam`. If the module is part of a package (i.e., its name contains a dot), the name is *not* mangled, e.g., the `__foo` in `import __foo.bar` is not mangled.

- The name of an imported member, e.g., `__f` in `from spam import __f`.

The transformation rule is defined as follows:

- The class name, with leading underscores removed and a single leading underscore inserted, is inserted in front of the identifier, e.g., the identifier `__spam` occurring in a class named `Foo`, `_Foo` or `__Foo` is transformed to `_Foo__spam`.

- If the class name consists only of underscores, the transformation is the identity, e.g., the identifier `__spam` occurring in a class named `_` or `__` is left as is.

<span id="expressions--atom-literals"></span>

### 6.2.3. Literals {#expressions--literals}

A *literal* is a textual representation of a value. Python supports numeric, string and bytes literals. [Format strings](#lexical_analysis--f-strings) and [template strings](#lexical_analysis--t-strings) are treated as string literals.

Numeric literals consist of a single [`NUMBER`](#lexical_analysis--grammar-token-python-grammar-NUMBER) token, which names an integer, floating-point number, or an imaginary number. See the [Numeric literals](#lexical_analysis--numbers) section in Lexical analysis documentation for details.

String and bytes literals may consist of several tokens. See section [String literal concatenation](#expressions--string-concatenation) for details.

Note that negative and complex numbers, like `-3` or `3+4.2j`, are syntactically not literals, but [unary](#expressions--unary) or [binary](#expressions--binary) arithmetic operations involving the `-` or `+` operator.

Evaluation of a literal yields an object of the given type ([`int`](https://docs.python.org/3/library/functions.html#int), [`float`](https://docs.python.org/3/library/functions.html#float), [`complex`](https://docs.python.org/3/library/functions.html#complex), [`str`](https://docs.python.org/3/library/stdtypes.html#str), [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes), or [`Template`](https://docs.python.org/3/library/string.templatelib.html#string.templatelib.Template)) with the given value. The value may be approximated in the case of floating-point and imaginary literals.

The formal grammar for literals is:

    literal: strings | NUMBER

<span id="expressions--index-7"></span>

#### 6.2.3.1. Literals and object identity {#expressions--literals-and-object-identity}

All literals correspond to immutable data types, and hence the object’s identity is less important than its value. Multiple evaluations of literals with the same value (either the same occurrence in the program text or a different occurrence) may obtain the same object or a different object with the same value.

CPython implementation detail

For example, in CPython, *small* integers with the same value evaluate to the same object:

    >>> x = 7
    >>> y = 7
    >>> x is y
    True

However, large integers evaluate to different objects:

    >>> x = 123456789
    >>> y = 123456789
    >>> x is y
    False

This behavior may change in future versions of CPython. In particular, the boundary between “small” and “large” integers has already changed in the past.

CPython will emit a [`SyntaxWarning`](https://docs.python.org/3/library/exceptions.html#SyntaxWarning) when you compare literals using `is`:

    >>> x = 7
    >>> x is 7
    <input>:1: SyntaxWarning: "is" with 'int' literal. Did you mean "=="?
    True

See [When can I rely on identity tests with the is operator?](https://docs.python.org/3/faq/programming.html#faq-identity-with-is) for more information.

[Template strings](#lexical_analysis--t-strings) are immutable but may reference mutable objects as [`Interpolation`](https://docs.python.org/3/library/string.templatelib.html#string.templatelib.Interpolation) values. For the purposes of this section, two t-strings have the “same value” if both their structure and the *identity* of the values match.

**CPython implementation detail:** Currently, each evaluation of a template string results in a different object.

<span id="expressions--string-concatenation"></span>

#### 6.2.3.2. String literal concatenation {#expressions--string-literal-concatenation}

Multiple adjacent string or bytes literals, possibly using different quoting conventions, are allowed, and their meaning is the same as their concatenation:

    >>> "hello" 'world'
    "helloworld"

This feature is defined at the syntactical level, so it only works with literals. To concatenate string expressions at run time, the ‘+’ operator may be used:

    >>> greeting = "Hello"
    >>> space = " "
    >>> name = "Blaise"
    >>> print(greeting + space + name)   # not: print(greeting space name)
    Hello Blaise

Literal concatenation can freely mix raw strings, triple-quoted strings, and formatted string literals. For example:

    >>> "Hello" r', ' f"{name}!"
    "Hello, Blaise!"

This feature can be used to reduce the number of backslashes needed, to split long strings conveniently across long lines, or even to add comments to parts of strings. For example:

    re.compile("[A-Za-z_]"       # letter or underscore
               "[A-Za-z0-9_]*"   # letter, digit or underscore
              )

However, bytes literals may only be combined with other byte literals; not with string literals of any kind. Also, template string literals may only be combined with other template string literals:

    >>> t"Hello" t"{name}!"
    Template(strings=('Hello', '!'), interpolations=(...))

Formally:

    strings: (STRING | fstring)+ | tstring+

<span id="expressions--parenthesized"></span>

### 6.2.4. Parenthesized forms {#expressions--parenthesized-forms}

A parenthesized form is an optional expression list enclosed in parentheses:

    parenth_form: "(" [starred_expression] ")"

A parenthesized expression list yields whatever that expression list yields: if the list contains at least one comma, it yields a tuple; otherwise, it yields the single expression that makes up the expression list.

An empty pair of parentheses yields an empty tuple object. Since tuples are immutable, the same rules as for literals apply (i.e., two occurrences of the empty tuple may or may not yield the same object).

Note that tuples are not formed by the parentheses, but rather by use of the comma. The exception is the empty tuple, for which parentheses *are* required — allowing unparenthesized “nothing” in expressions would cause ambiguities and allow common typos to pass uncaught.

<span id="expressions--comprehensions"></span>

### 6.2.5. Displays for lists, sets and dictionaries {#expressions--displays-for-lists-sets-and-dictionaries}

For constructing a list, a set or a dictionary Python provides special syntax called “displays”, each of them in two flavors:

- either the container contents are listed explicitly, or

- they are computed via a set of looping and filtering instructions, called a *comprehension*.

Common syntax elements for comprehensions are:

    comprehension: assignment_expression comp_for
    comp_for:      ["async"] "for" target_list "in" or_test [comp_iter]
    comp_iter:     comp_for | comp_if
    comp_if:       "if" or_test [comp_iter]

The comprehension consists of a single expression followed by at least one `for` clause and zero or more `for` or `if` clauses. In this case, the elements of the new container are those that would be produced by considering each of the `for` or `if` clauses a block, nesting from left to right, and evaluating the expression to produce an element each time the innermost block is reached.

However, aside from the iterable expression in the leftmost `for` clause, the comprehension is executed in a separate implicitly nested scope. This ensures that names assigned to in the target list don’t “leak” into the enclosing scope.

The iterable expression in the leftmost `for` clause is evaluated directly in the enclosing scope and then passed as an argument to the implicitly nested scope. Subsequent `for` clauses and any filter condition in the leftmost `for` clause cannot be evaluated in the enclosing scope as they may depend on the values obtained from the leftmost iterable. For example: `[x*y for x in range(10) for y in range(x, x+10)]`.

To ensure the comprehension always results in a container of the appropriate type, `yield` and `yield from` expressions are prohibited in the implicitly nested scope.

Since Python 3.6, in an [`async def`](#compound_stmts--async-def) function, an `async for` clause may be used to iterate over a [asynchronous iterator](https://docs.python.org/3/glossary.html#term-asynchronous-iterator). A comprehension in an `async def` function may consist of either a `for` or `async for` clause following the leading expression, may contain additional `for` or `async for` clauses, and may also use [`await`](#expressions--await) expressions.

If a comprehension contains `async for` clauses, or if it contains `await` expressions or other asynchronous comprehensions anywhere except the iterable expression in the leftmost `for` clause, it is called an *asynchronous comprehension*. An asynchronous comprehension may suspend the execution of the coroutine function in which it appears. See also <span id="expressions--index-14"></span>[**PEP 530**](https://peps.python.org/pep-0530/).

Added in version 3.6: Asynchronous comprehensions were introduced.

Changed in version 3.8: `yield` and `yield from` prohibited in the implicitly nested scope.

Changed in version 3.11: Asynchronous comprehensions are now allowed inside comprehensions in asynchronous functions. Outer comprehensions implicitly become asynchronous.

<span id="expressions--lists"></span>

### 6.2.6. List displays {#expressions--list-displays}

A list display is a possibly empty series of expressions enclosed in square brackets:

    list_display: "[" [flexible_expression_list | comprehension] "]"

A list display yields a new list object, the contents being specified by either a list of expressions or a comprehension. When a comma-separated list of expressions is supplied, its elements are evaluated from left to right and placed into the list object in that order. When a comprehension is supplied, the list is constructed from the elements resulting from the comprehension.

<span id="expressions--set"></span>

### 6.2.7. Set displays {#expressions--set-displays}

A set display is denoted by curly braces and distinguishable from dictionary displays by the lack of colons separating keys and values:

    set_display: "{" (flexible_expression_list | comprehension) "}"

A set display yields a new mutable set object, the contents being specified by either a sequence of expressions or a comprehension. When a comma-separated list of expressions is supplied, its elements are evaluated from left to right and added to the set object. When a comprehension is supplied, the set is constructed from the elements resulting from the comprehension.

An empty set cannot be constructed with `{}`; this literal constructs an empty dictionary.

<span id="expressions--dict"></span>

### 6.2.8. Dictionary displays {#expressions--dictionary-displays}

A dictionary display is a possibly empty series of dict items (key/value pairs) enclosed in curly braces:

    dict_display:       "{" [dict_item_list | dict_comprehension] "}"
    dict_item_list:     dict_item ("," dict_item)* [","]
    dict_item:          expression ":" expression | "**" or_expr
    dict_comprehension: expression ":" expression comp_for

A dictionary display yields a new dictionary object.

If a comma-separated sequence of dict items is given, they are evaluated from left to right to define the entries of the dictionary: each key object is used as a key into the dictionary to store the corresponding value. This means that you can specify the same key multiple times in the dict item list, and the final dictionary’s value for that key will be the last one given.

A double asterisk `**` denotes *dictionary unpacking*. Its operand must be a [mapping](https://docs.python.org/3/glossary.html#term-mapping). Each mapping item is added to the new dictionary. Later values replace values already set by earlier dict items and earlier dictionary unpackings.

Added in version 3.5: Unpacking into dictionary displays, originally proposed by <span id="expressions--index-19"></span>[**PEP 448**](https://peps.python.org/pep-0448/).

A dict comprehension, in contrast to list and set comprehensions, needs two expressions separated with a colon followed by the usual “for” and “if” clauses. When the comprehension is run, the resulting key and value elements are inserted in the new dictionary in the order they are produced.

Restrictions on the types of the key values are listed earlier in section [The standard type hierarchy](#datamodel--types). (To summarize, the key type should be [hashable](https://docs.python.org/3/glossary.html#term-hashable), which excludes all mutable objects.) Clashes between duplicate keys are not detected; the last value (textually rightmost in the display) stored for a given key value prevails.

Changed in version 3.8: Prior to Python 3.8, in dict comprehensions, the evaluation order of key and value was not well-defined. In CPython, the value was evaluated before the key. Starting with 3.8, the key is evaluated before the value, as proposed by <span id="expressions--index-21"></span>[**PEP 572**](https://peps.python.org/pep-0572/).

<span id="expressions--genexpr"></span>

### 6.2.9. Generator expressions {#expressions--generator-expressions}

The syntax for *generator expressions* is the same as for list [comprehensions](#expressions--comprehensions), except that they are enclosed in parentheses instead of brackets. For example:

    >>> iterator = (x ** 2 for x in range(10))
    >>> iterator
    <generator object <genexpr> at ...>

At runtime, a generator expression evaluates to a [generator iterator](https://docs.python.org/3/glossary.html#term-generator-iterator) which yields the same values as the corresponding list comprehension:

    >>> list(iterator)
    [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

Thus, the example above is roughly equivalent to defining and calling the following generator function:

    def make_generator_of_squares(iterator):
        for x in iterator:
            yield x ** 2

    make_generator_of_squares(iter(range(10)))

The enclosing parentheses can be omitted in calls when the generator expression is the only positional argument and there are no keyword arguments. See the [Calls section](#expressions--calls) for details. For example:

    # The parentheses after `sum` are part of the call syntax:
    >>> sum(x ** 2 for x in range(10))
    285

    # The generator needs its own parentheses if it's not the only argument:
    >>> sum((x ** 2 for x in range(10)), start=1000)
    1285

The iterable expression in the leftmost `for` clause is evaluated immediately, so that an error raised by this expression will be emitted at the point where the generator expression is defined, rather than at the point where the first value is retrieved:

    >>> (x ** 2 for x in nonexistent_iterable)
    Traceback (most recent call last):
      ...
    NameError: name 'nonexistent_iterable' is not defined

After the expression is evaluated, an iterator is created from the result, as if [`iter()`](https://docs.python.org/3/library/functions.html#iter) was called on it. Any error raised when creating the iterator is also emitted immediately:

    >>> (x ** 2 for x in None)
    Traceback (most recent call last):
      ...
    TypeError: 'NoneType' object is not iterable

All other expressions are evaluated lazily, in the same fashion as normal generators (that is, when the iterator is asked to yield a value):

    >>> iterator = (nonexistent_value for x in range(10))
    >>> iterator
    <generator object <genexpr> at ...>
    >>> list(iterator)
    Traceback (most recent call last):
      ...
    NameError: name 'nonexistent_value' is not defined

    >>> iterator = (x * y for x in range(10) for y in nonexistent_iterable)
    >>> iterator
    <generator object <genexpr> at ...>
    >>> list(iterator)
    Traceback (most recent call last):
      ...
    NameError: name 'nonexistent_iterable' is not defined

To avoid interfering with the expected operation of the generator expression itself, `yield` and `yield from` expressions are prohibited inside the implicitly nested scope.

If a generator expression contains either `async for` clauses or [`await`](#expressions--await) expressions it is called an *asynchronous generator expression*. An asynchronous generator expression returns a new asynchronous generator object, which is an asynchronous iterator (see [Asynchronous Iterators](#datamodel--async-iterators)).

The formal grammar for generator expressions is:

    generator_expression: "(" expression comp_for ")"

Added in version 3.6: Asynchronous generator expressions were introduced.

Changed in version 3.7: Prior to Python 3.7, asynchronous generator expressions could only appear in [`async def`](#compound_stmts--async-def) coroutines. Starting with 3.7, any function can use asynchronous generator expressions.

Changed in version 3.8: `yield` and `yield from` prohibited in the implicitly nested scope.

<span id="expressions--yieldexpr"></span>

### 6.2.10. Yield expressions {#expressions--yield-expressions}

``` {#expressions--index-23}
yield_atom:       "(" yield_expression ")"
yield_from:       "yield" "from" expression
yield_expression: "yield" yield_list | yield_from
```

The yield expression is used when defining a [generator](https://docs.python.org/3/glossary.html#term-generator) function or an [asynchronous generator](https://docs.python.org/3/glossary.html#term-asynchronous-generator) function and thus can only be used in the body of a function definition. Using a yield expression in a function’s body causes that function to be a generator function, and using it in an [`async def`](#compound_stmts--async-def) function’s body causes that coroutine function to be an asynchronous generator function. For example:

    def gen():  # defines a generator function
        yield 123

    async def agen(): # defines an asynchronous generator function
        yield 123

Due to their side effects on the containing scope, `yield` expressions are not permitted as part of the implicitly defined scopes used to implement comprehensions and generator expressions.

Changed in version 3.8: Yield expressions prohibited in the implicitly nested scopes used to implement comprehensions and generator expressions.

Generator functions are described below, while asynchronous generator functions are described separately in section [Asynchronous generator functions](#expressions--asynchronous-generator-functions).

When a generator function is called, it returns an iterator known as a generator. That generator then controls the execution of the generator function. The execution starts when one of the generator’s methods is called. At that time, the execution proceeds to the first yield expression, where it is suspended again, returning the value of [`yield_list`](#expressions--grammar-token-python-grammar-yield_list) to the generator’s caller, or `None` if `yield_list` is omitted. By suspended, we mean that all local state is retained, including the current bindings of local variables, the instruction pointer, the internal evaluation stack, and the state of any exception handling. When the execution is resumed by calling one of the generator’s methods, the function can proceed exactly as if the yield expression were just another external call. The value of the yield expression after resuming depends on the method which resumed the execution. If [`__next__()`](#expressions--generator.__next__) is used (typically via either a [`for`](#compound_stmts--for) or the [`next()`](https://docs.python.org/3/library/functions.html#next) builtin) then the result is [`None`](https://docs.python.org/3/library/constants.html#None). Otherwise, if [`send()`](#expressions--generator.send) is used, then the result will be the value passed in to that method.

All of this makes generator functions quite similar to coroutines; they yield multiple times, they have more than one entry point and their execution can be suspended. The only difference is that a generator function cannot control where the execution should continue after it yields; the control is always transferred to the generator’s caller.

Yield expressions are allowed anywhere in a [`try`](#compound_stmts--try) construct. If the generator is not resumed before it is finalized (by reaching a zero reference count or by being garbage collected), the generator-iterator’s [`close()`](#expressions--generator.close) method will be called, allowing any pending [`finally`](#compound_stmts--finally) clauses to execute.

When `yield from <expr>` is used, the supplied expression must be an iterable. The values produced by iterating that iterable are passed directly to the caller of the current generator’s methods. Any values passed in with [`send()`](#expressions--generator.send) and any exceptions passed in with [`throw()`](#expressions--generator.throw) are passed to the underlying iterator if it has the appropriate methods. If this is not the case, then `send()` will raise [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError) or [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError), while `throw()` will just raise the passed in exception immediately.

When the underlying iterator is complete, the [`value`](https://docs.python.org/3/library/exceptions.html#StopIteration.value) attribute of the raised [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) instance becomes the value of the yield expression. It can be either set explicitly when raising `StopIteration`, or automatically when the subiterator is a generator (by returning a value from the subgenerator).

Changed in version 3.3: Added `yield from <expr>` to delegate control flow to a subiterator.

The parentheses may be omitted when the yield expression is the sole expression on the right hand side of an assignment statement.

See also

<span id="expressions--index-26"></span>[**PEP 255**](https://peps.python.org/pep-0255/) - Simple Generators  
The proposal for adding generators and the [`yield`](#simple_stmts--yield) statement to Python.

<span id="expressions--index-27"></span>[**PEP 342**](https://peps.python.org/pep-0342/) - Coroutines via Enhanced Generators  
The proposal to enhance the API and syntax of generators, making them usable as simple coroutines.

<span id="expressions--index-28"></span>[**PEP 380**](https://peps.python.org/pep-0380/) - Syntax for Delegating to a Subgenerator  
The proposal to introduce the [`yield_from`](#expressions--grammar-token-python-grammar-yield_from) syntax, making delegation to subgenerators easy.

<span id="expressions--index-29"></span>[**PEP 525**](https://peps.python.org/pep-0525/) - Asynchronous Generators  
The proposal that expanded on <span id="expressions--index-30"></span>[**PEP 492**](https://peps.python.org/pep-0492/) by adding generator capabilities to coroutine functions.

<span id="expressions--generator-methods"></span> <span id="expressions--index-31"></span>

#### 6.2.10.1. Generator-iterator methods {#expressions--generator-iterator-methods}

This subsection describes the methods of a generator iterator. They can be used to control the execution of a generator function.

Note that calling any of the generator methods below when the generator is already executing raises a [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError) exception.

generator.\_\_next\_\_()  
Starts the execution of a generator function or resumes it at the last executed yield expression. When a generator function is resumed with a `__next__()` method, the current yield expression always evaluates to [`None`](https://docs.python.org/3/library/constants.html#None). The execution then continues to the next yield expression, where the generator is suspended again, and the value of the [`yield_list`](#expressions--grammar-token-python-grammar-yield_list) is returned to `__next__()`’s caller. If the generator exits without yielding another value, a [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) exception is raised.

This method is normally called implicitly, e.g. by a [`for`](#compound_stmts--for) loop, or by the built-in [`next()`](https://docs.python.org/3/library/functions.html#next) function.

<!-- -->

generator.send(*value*)  
Resumes the execution and “sends” a value into the generator function. The *value* argument becomes the result of the current yield expression. The `send()` method returns the next value yielded by the generator, or raises [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) if the generator exits without yielding another value. When `send()` is called to start the generator, it must be called with [`None`](https://docs.python.org/3/library/constants.html#None) as the argument, because there is no yield expression that could receive the value.

<!-- -->

generator.throw(*value*)  
generator.throw(*type*\[, *value*\[, *traceback*\]\])  
Raises an exception at the point where the generator was paused, and returns the next value yielded by the generator function. If the generator exits without yielding another value, a [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) exception is raised. If the generator function does not catch the passed-in exception, or raises a different exception, then that exception propagates to the caller.

In typical use, this is called with a single exception instance similar to the way the [`raise`](#simple_stmts--raise) keyword is used.

For backwards compatibility, however, the second signature is supported, following a convention from older versions of Python. The *type* argument should be an exception class, and *value* should be an exception instance. If the *value* is not provided, the *type* constructor is called to get an instance. If *traceback* is provided, it is set on the exception, otherwise any existing [`__traceback__`](https://docs.python.org/3/library/exceptions.html#BaseException.__traceback__) attribute stored in *value* may be cleared.

Changed in version 3.12: The second signature (type\[, value\[, traceback\]\]) is deprecated and may be removed in a future version of Python.

<!-- -->

generator.close()  
Raises a [`GeneratorExit`](https://docs.python.org/3/library/exceptions.html#GeneratorExit) exception at the point where the generator function was paused (equivalent to calling `throw(GeneratorExit)`). The exception is raised by the yield expression where the generator was paused. If the generator function catches the exception and returns a value, this value is returned from `close()`. If the generator function is already closed, or raises `GeneratorExit` (by not catching the exception), `close()` returns [`None`](https://docs.python.org/3/library/constants.html#None). If the generator yields a value, a [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) is raised. If the generator raises any other exception, it is propagated to the caller. If the generator has already exited due to an exception or normal exit, `close()` returns `None` and has no other effect.

Changed in version 3.13: If a generator returns a value upon being closed, the value is returned by `close()`.

<span id="expressions--index-34"></span>

#### 6.2.10.2. Examples {#expressions--examples}

Here is a simple example that demonstrates the behavior of generators and generator functions:

    >>> def echo(value=None):
    ...     print("Execution starts when 'next()' is called for the first time.")
    ...     try:
    ...         while True:
    ...             try:
    ...                 value = (yield value)
    ...             except Exception as e:
    ...                 value = e
    ...     finally:
    ...         print("Don't forget to clean up when 'close()' is called.")
    ...
    >>> generator = echo(1)
    >>> print(next(generator))
    Execution starts when 'next()' is called for the first time.
    1
    >>> print(next(generator))
    None
    >>> print(generator.send(2))
    2
    >>> generator.throw(TypeError, "spam")
    TypeError('spam',)
    >>> generator.close()
    Don't forget to clean up when 'close()' is called.

For examples using `yield from`, see [PEP 380: Syntax for Delegating to a Subgenerator](https://docs.python.org/3/whatsnew/3.3.html#pep-380) in “What’s New in Python.”

<span id="expressions--id4"></span>

#### 6.2.10.3. Asynchronous generator functions {#expressions--asynchronous-generator-functions}

The presence of a yield expression in a function or method defined using [`async def`](#compound_stmts--async-def) further defines the function as an [asynchronous generator](https://docs.python.org/3/glossary.html#term-asynchronous-generator) function.

When an asynchronous generator function is called, it returns an asynchronous iterator known as an asynchronous generator object. That object then controls the execution of the generator function. An asynchronous generator object is typically used in an [`async for`](#compound_stmts--async-for) statement in a coroutine function analogously to how a generator object would be used in a [`for`](#compound_stmts--for) statement.

Calling one of the asynchronous generator’s methods returns an [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) object, and the execution starts when this object is awaited on. At that time, the execution proceeds to the first yield expression, where it is suspended again, returning the value of [`yield_list`](#expressions--grammar-token-python-grammar-yield_list) to the awaiting coroutine. As with a generator, suspension means that all local state is retained, including the current bindings of local variables, the instruction pointer, the internal evaluation stack, and the state of any exception handling. When the execution is resumed by awaiting on the next object returned by the asynchronous generator’s methods, the function can proceed exactly as if the yield expression were just another external call. The value of the yield expression after resuming depends on the method which resumed the execution. If [`__anext__()`](#expressions--agen.__anext__) is used then the result is [`None`](https://docs.python.org/3/library/constants.html#None). Otherwise, if [`asend()`](#expressions--agen.asend) is used, then the result will be the value passed in to that method.

If an asynchronous generator happens to exit early by [`break`](#simple_stmts--break), the caller task being cancelled, or other exceptions, the generator’s async cleanup code will run and possibly raise exceptions or access context variables in an unexpected context–perhaps after the lifetime of tasks it depends, or during the event loop shutdown when the async-generator garbage collection hook is called. To prevent this, the caller must explicitly close the async generator by calling [`aclose()`](#expressions--agen.aclose) method to finalize the generator and ultimately detach it from the event loop.

In an asynchronous generator function, yield expressions are allowed anywhere in a [`try`](#compound_stmts--try) construct. However, if an asynchronous generator is not resumed before it is finalized (by reaching a zero reference count or by being garbage collected), then a yield expression within a `try` construct could result in a failure to execute pending [`finally`](#compound_stmts--finally) clauses. In this case, it is the responsibility of the event loop or scheduler running the asynchronous generator to call the asynchronous generator-iterator’s [`aclose()`](#expressions--agen.aclose) method and run the resulting coroutine object, thus allowing any pending `finally` clauses to execute.

To take care of finalization upon event loop termination, an event loop should define a *finalizer* function which takes an asynchronous generator-iterator and presumably calls [`aclose()`](#expressions--agen.aclose) and executes the coroutine. This *finalizer* may be registered by calling [`sys.set_asyncgen_hooks()`](https://docs.python.org/3/library/sys.html#sys.set_asyncgen_hooks). When first iterated over, an asynchronous generator-iterator will store the registered *finalizer* to be called upon finalization. For a reference example of a *finalizer* method see the implementation of `asyncio.Loop.shutdown_asyncgens` in [Lib/asyncio/base_events.py](https://github.com/python/cpython/tree/3.14/Lib/asyncio/base_events.py).

The expression `yield from <expr>` is a syntax error when used in an asynchronous generator function.

<span id="expressions--asynchronous-generator-methods"></span> <span id="expressions--index-35"></span>

#### 6.2.10.4. Asynchronous generator-iterator methods {#expressions--asynchronous-generator-iterator-methods}

This subsection describes the methods of an asynchronous generator iterator, which are used to control the execution of a generator function.

*async* agen.\_\_anext\_\_()  
Returns an awaitable which when run starts to execute the asynchronous generator or resumes it at the last executed yield expression. When an asynchronous generator function is resumed with an `__anext__()` method, the current yield expression always evaluates to [`None`](https://docs.python.org/3/library/constants.html#None) in the returned awaitable, which when run will continue to the next yield expression. The value of the [`yield_list`](#expressions--grammar-token-python-grammar-yield_list) of the yield expression is the value of the [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) exception raised by the completing coroutine. If the asynchronous generator exits without yielding another value, the awaitable instead raises a [`StopAsyncIteration`](https://docs.python.org/3/library/exceptions.html#StopAsyncIteration) exception, signalling that the asynchronous iteration has completed.

This method is normally called implicitly by a [`async for`](#compound_stmts--async-for) loop.

<!-- -->

*async* agen.asend(*value*)  
Returns an awaitable which when run resumes the execution of the asynchronous generator. As with the [`send()`](#expressions--generator.send) method for a generator, this “sends” a value into the asynchronous generator function, and the *value* argument becomes the result of the current yield expression. The awaitable returned by the `asend()` method will return the next value yielded by the generator as the value of the raised [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration), or raises [`StopAsyncIteration`](https://docs.python.org/3/library/exceptions.html#StopAsyncIteration) if the asynchronous generator exits without yielding another value. When `asend()` is called to start the asynchronous generator, it must be called with [`None`](https://docs.python.org/3/library/constants.html#None) as the argument, because there is no yield expression that could receive the value.

<!-- -->

*async* agen.athrow(*value*)  
*async* agen.athrow(*type*\[, *value*\[, *traceback*\]\])  
Returns an awaitable that raises an exception of type `type` at the point where the asynchronous generator was paused, and returns the next value yielded by the generator function as the value of the raised [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) exception. If the asynchronous generator exits without yielding another value, a [`StopAsyncIteration`](https://docs.python.org/3/library/exceptions.html#StopAsyncIteration) exception is raised by the awaitable. If the generator function does not catch the passed-in exception, or raises a different exception, then when the awaitable is run that exception propagates to the caller of the awaitable.

Changed in version 3.12: The second signature (type\[, value\[, traceback\]\]) is deprecated and may be removed in a future version of Python.

<!-- -->

*async* agen.aclose()  
Returns an awaitable that when run will throw a [`GeneratorExit`](https://docs.python.org/3/library/exceptions.html#GeneratorExit) into the asynchronous generator function at the point where it was paused. If the asynchronous generator function then exits gracefully, is already closed, or raises `GeneratorExit` (by not catching the exception), then the returned awaitable will raise a [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) exception. Any further awaitables returned by subsequent calls to the asynchronous generator will raise a [`StopAsyncIteration`](https://docs.python.org/3/library/exceptions.html#StopAsyncIteration) exception. If the asynchronous generator yields a value, a [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) is raised by the awaitable. If the asynchronous generator raises any other exception, it is propagated to the caller of the awaitable. If the asynchronous generator has already exited due to an exception or normal exit, then further calls to `aclose()` will return an awaitable that does nothing.

<span id="expressions--id5"></span>

## 6.3. Primaries {#expressions--primaries}

Primaries represent the most tightly bound operations of the language. Their syntax is:

    primary: atom | attributeref | subscription | call

<span id="expressions--id6"></span>

### 6.3.1. Attribute references {#expressions--attribute-references}

An attribute reference is a primary followed by a period and a name:

    attributeref: primary "." identifier

The primary must evaluate to an object of a type that supports attribute references, which most objects do. This object is then asked to produce the attribute whose name is the identifier. The type and value produced is determined by the object. Multiple evaluations of the same attribute reference may yield different objects.

This production can be customized by overriding the [`__getattribute__()`](#datamodel--object.__getattribute__) method or the [`__getattr__()`](#datamodel--object.__getattr__) method. The `__getattribute__()` method is called first and either returns a value or raises [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError) if the attribute is not available.

If an [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError) is raised and the object has a `__getattr__()` method, that method is called as a fallback.

<span id="expressions--subscriptions"></span>

### 6.3.2. Subscriptions and slicings {#expressions--subscriptions-and-slicings}

<span id="expressions--index-41"></span>The *subscription* syntax is usually used for selecting an element from a [container](#datamodel--sequence-types) – for example, to get a value from a [`dict`](https://docs.python.org/3/library/stdtypes.html#dict):

    >>> digits_by_name = {'one': 1, 'two': 2}
    >>> digits_by_name['two']  # Subscripting a dictionary using the key 'two'
    2

In the subscription syntax, the object being subscribed – a [primary](#expressions--primaries) – is followed by a *subscript* in square brackets. In the simplest case, the subscript is a single expression.

Depending on the type of the object being subscribed, the subscript is sometimes called a [key](https://docs.python.org/3/glossary.html#term-key) (for mappings), [index](https://docs.python.org/3/glossary.html#term-index) (for sequences), or *type argument* (for [generic types](https://docs.python.org/3/glossary.html#term-generic-type)). Syntactically, these are all equivalent:

    >>> colors = ['red', 'blue', 'green', 'black']
    >>> colors[3]  # Subscripting a list using the index 3
    'black'

    >>> list[str]  # Parameterizing the list type using the type argument str
    list[str]

At runtime, the interpreter will evaluate the primary and the subscript, and call the primary’s [`__getitem__()`](#datamodel--object.__getitem__) or [`__class_getitem__()`](#datamodel--object.__class_getitem__) [special method](https://docs.python.org/3/glossary.html#term-special-method) with the subscript as argument. For more details on which of these methods is called, see [\_\_class_getitem\_\_ versus \_\_getitem\_\_](#datamodel--classgetitem-versus-getitem).

To show how subscription works, we can define a custom object that implements [`__getitem__()`](#datamodel--object.__getitem__) and prints out the value of the subscript:

    >>> class SubscriptionDemo:
    ...     def __getitem__(self, key):
    ...         print(f'subscripted with: {key!r}')
    ...
    >>> demo = SubscriptionDemo()
    >>> demo[1]
    subscripted with: 1
    >>> demo['a' * 3]
    subscripted with: 'aaa'

See [`__getitem__()`](#datamodel--object.__getitem__) documentation for how built-in types handle subscription.

Subscriptions may also be used as targets in [assignment](#simple_stmts--assignment) or [deletion](#simple_stmts--del) statements. In these cases, the interpreter will call the subscripted object’s [`__setitem__()`](#datamodel--object.__setitem__) or [`__delitem__()`](#datamodel--object.__delitem__) [special method](https://docs.python.org/3/glossary.html#term-special-method), respectively, instead of [`__getitem__()`](#datamodel--object.__getitem__).

    >>> colors = ['red', 'blue', 'green', 'black']
    >>> colors[3] = 'white'  # Setting item at index
    >>> colors
    ['red', 'blue', 'green', 'white']
    >>> del colors[3]  # Deleting item at index 3
    >>> colors
    ['red', 'blue', 'green']

All advanced forms of *subscript* documented in the following sections are also usable for assignment and deletion.

<span id="expressions--index-44"></span> <span id="expressions--index-43"></span> <span id="expressions--id7"></span>

#### 6.3.2.1. Slicings {#expressions--slicings}

A more advanced form of subscription, *slicing*, is commonly used to extract a portion of a [sequence](#datamodel--datamodel-sequences). In this form, the subscript is a [slice](https://docs.python.org/3/glossary.html#term-slice): up to three expressions separated by colons. Any of the expressions may be omitted, but a slice must contain at least one colon:

    >>> number_names = ['zero', 'one', 'two', 'three', 'four', 'five']
    >>> number_names[1:3]
    ['one', 'two']
    >>> number_names[1:]
    ['one', 'two', 'three', 'four', 'five']
    >>> number_names[:3]
    ['zero', 'one', 'two']
    >>> number_names[:]
    ['zero', 'one', 'two', 'three', 'four', 'five']
    >>> number_names[::2]
    ['zero', 'two', 'four']
    >>> number_names[:-3]
    ['zero', 'one', 'two']
    >>> del number_names[4:]
    >>> number_names
    ['zero', 'one', 'two', 'three']

When a slice is evaluated, the interpreter constructs a [`slice`](https://docs.python.org/3/library/functions.html#slice) object whose [`start`](https://docs.python.org/3/library/functions.html#slice.start), [`stop`](https://docs.python.org/3/library/functions.html#slice.stop) and [`step`](https://docs.python.org/3/library/functions.html#slice.step) attributes, respectively, are the results of the expressions between the colons. Any missing expression evaluates to [`None`](https://docs.python.org/3/library/constants.html#None). This `slice` object is then passed to the [`__getitem__()`](#datamodel--object.__getitem__) or [`__class_getitem__()`](#datamodel--object.__class_getitem__) [special method](https://docs.python.org/3/glossary.html#term-special-method), as above.

    # continuing with the SubscriptionDemo instance defined above:
    >>> demo[2:3]
    subscripted with: slice(2, 3, None)
    >>> demo[::'spam']
    subscripted with: slice(None, None, 'spam')

#### 6.3.2.2. Comma-separated subscripts {#expressions--comma-separated-subscripts}

The subscript can also be given as two or more comma-separated expressions or slices:

    # continuing with the SubscriptionDemo instance defined above:
    >>> demo[1, 2, 3]
    subscripted with: (1, 2, 3)
    >>> demo[1:2, 3]
    subscripted with: (slice(1, 2, None), 3)

This form is commonly used with numerical libraries for slicing multi-dimensional data. In this case, the interpreter constructs a [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple) of the results of the expressions or slices, and passes this tuple to the [`__getitem__()`](#datamodel--object.__getitem__) or [`__class_getitem__()`](#datamodel--object.__class_getitem__) [special method](https://docs.python.org/3/glossary.html#term-special-method), as above.

The subscript may also be given as a single expression or slice followed by a comma, to specify a one-element tuple:

    >>> demo['spam',]
    subscripted with: ('spam',)

#### 6.3.2.3. “Starred” subscriptions {#expressions--starred-subscriptions}

Added in version 3.11: Expressions in *tuple_slices* may be starred. See <span id="expressions--index-45"></span>[**PEP 646**](https://peps.python.org/pep-0646/).

The subscript can also contain a starred expression. In this case, the interpreter unpacks the result into a tuple, and passes this tuple to [`__getitem__()`](#datamodel--object.__getitem__) or [`__class_getitem__()`](#datamodel--object.__class_getitem__):

    # continuing with the SubscriptionDemo instance defined above:
    >>> demo[*range(10)]
    subscripted with: (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)

Starred expressions may be combined with comma-separated expressions and slices:

    >>> demo['a', 'b', *range(3), 'c']
    subscripted with: ('a', 'b', 0, 1, 2, 'c')

#### 6.3.2.4. Formal subscription grammar {#expressions--formal-subscription-grammar}

    subscription:     primary '[' subscript ']'
    subscript:        single_subscript | tuple_subscript
    single_subscript: proper_slice | assignment_expression
    proper_slice:     [expression] ":" [expression] [ ":" [expression] ]
    tuple_subscript:  ','.(single_subscript | starred_expression)+ [',']

Recall that the `|` operator [denotes ordered choice](#introduction--notation). Specifically, in `subscript`, if both alternatives would match, the first (`single_subscript`) has priority.

<span id="expressions--index-46"></span> <span id="expressions--id8"></span>

### 6.3.3. Calls {#expressions--calls}

A call calls a callable object (e.g., a [function](https://docs.python.org/3/glossary.html#term-function)) with a possibly empty series of [arguments](https://docs.python.org/3/glossary.html#term-argument):

    call:                 primary "(" [argument_list [","] | comprehension] ")"
    argument_list:        positional_arguments ["," starred_and_keywords]
                            ["," keywords_arguments]
                          | starred_and_keywords ["," keywords_arguments]
                          | keywords_arguments
    positional_arguments: positional_item ("," positional_item)*
    positional_item:      assignment_expression | "*" expression
    starred_and_keywords: ("*" expression | keyword_item)
                          ("," "*" expression | "," keyword_item)*
    keywords_arguments:   (keyword_item | "**" expression)
                          ("," keyword_item | "," "**" expression)*
    keyword_item:         identifier "=" expression

An optional trailing comma may be present after the positional and keyword arguments but does not affect the semantics.

The primary must evaluate to a callable object (user-defined functions, built-in functions, methods of built-in objects, class objects, methods of class instances, and all objects having a [`__call__()`](#datamodel--object.__call__) method are callable). All argument expressions are evaluated before the call is attempted. Please refer to section [Function definitions](#compound_stmts--function) for the syntax of formal [parameter](https://docs.python.org/3/glossary.html#term-parameter) lists.

If keyword arguments are present, they are first converted to positional arguments, as follows. First, a list of unfilled slots is created for the formal parameters. If there are N positional arguments, they are placed in the first N slots. Next, for each keyword argument, the identifier is used to determine the corresponding slot (if the identifier is the same as the first formal parameter name, the first slot is used, and so on). If the slot is already filled, a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) exception is raised. Otherwise, the argument is placed in the slot, filling it (even if the expression is `None`, it fills the slot). When all arguments have been processed, the slots that are still unfilled are filled with the corresponding default value from the function definition. (Default values are calculated, once, when the function is defined; thus, a mutable object such as a list or dictionary used as default value will be shared by all calls that don’t specify an argument value for the corresponding slot; this should usually be avoided.) If there are any unfilled slots for which no default value is specified, a `TypeError` exception is raised. Otherwise, the list of filled slots is used as the argument list for the call.

**CPython implementation detail:** An implementation may provide built-in functions whose positional parameters do not have names, even if they are ‘named’ for the purpose of documentation, and which therefore cannot be supplied by keyword. In CPython, this is the case for functions implemented in C that use [`PyArg_ParseTuple()`](https://docs.python.org/3/c-api/arg.html#c.PyArg_ParseTuple) to parse their arguments.

If there are more positional arguments than there are formal parameter slots, a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) exception is raised, unless a formal parameter using the syntax `*identifier` is present; in this case, that formal parameter receives a tuple containing the excess positional arguments (or an empty tuple if there were no excess positional arguments).

If any keyword argument does not correspond to a formal parameter name, a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) exception is raised, unless a formal parameter using the syntax `**identifier` is present; in this case, that formal parameter receives a dictionary containing the excess keyword arguments (using the keywords as keys and the argument values as corresponding values), or a (new) empty dictionary if there were no excess keyword arguments.

If the syntax `*expression` appears in the function call, `expression` must evaluate to an [iterable](https://docs.python.org/3/glossary.html#term-iterable). Elements from these iterables are treated as if they were additional positional arguments. For the call `f(x1, x2, *y, x3, x4)`, if *y* evaluates to a sequence *y1*, …, *yM*, this is equivalent to a call with M+4 positional arguments *x1*, *x2*, *y1*, …, *yM*, *x3*, *x4*.

A consequence of this is that although the `*expression` syntax may appear *after* explicit keyword arguments, it is processed *before* the keyword arguments (and any `**expression` arguments – see below). So:

    >>> def f(a, b):
    ...     print(a, b)
    ...
    >>> f(b=1, *(2,))
    2 1
    >>> f(a=1, *(2,))
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: f() got multiple values for keyword argument 'a'
    >>> f(1, *(2,))
    1 2

It is unusual for both keyword arguments and the `*expression` syntax to be used in the same call, so in practice this confusion does not often arise.

If the syntax `**expression` appears in the function call, `expression` must evaluate to a [mapping](https://docs.python.org/3/glossary.html#term-mapping), the contents of which are treated as additional keyword arguments. If a parameter matching a key has already been given a value (by an explicit keyword argument, or from another unpacking), a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) exception is raised.

When `**expression` is used, each key in this mapping must be a string. Each value from the mapping is assigned to the first formal parameter eligible for keyword assignment whose name is equal to the key. A key need not be a Python identifier (e.g. `"max-temp °F"` is acceptable, although it will not match any formal parameter that could be declared). If there is no match to a formal parameter the key-value pair is collected by the `**` parameter, if there is one, or if there is not, a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) exception is raised.

Formal parameters using the syntax `*identifier` or `**identifier` cannot be used as positional argument slots or as keyword argument names.

Changed in version 3.5: Function calls accept any number of `*` and `**` unpackings, positional arguments may follow iterable unpackings (`*`), and keyword arguments may follow dictionary unpackings (`**`). Originally proposed by <span id="expressions--index-50"></span>[**PEP 448**](https://peps.python.org/pep-0448/).

A call always returns some value, possibly `None`, unless it raises an exception. How this value is computed depends on the type of the callable object.

If it is—

a user-defined function:  
The code block for the function is executed, passing it the argument list. The first thing the code block will do is bind the formal parameters to the arguments; this is described in section [Function definitions](#compound_stmts--function). When the code block executes a [`return`](#simple_stmts--return) statement, this specifies the return value of the function call. If execution reaches the end of the code block without executing a `return` statement, the return value is `None`.

a built-in function or method:  
The result is up to the interpreter; see [Built-in Functions](https://docs.python.org/3/library/functions.html#built-in-funcs) for the descriptions of built-in functions and methods.

a class object:  
A new instance of that class is returned.

a class instance method:  
The corresponding user-defined function is called, with an argument list that is one longer than the argument list of the call: the instance becomes the first argument.

a class instance:  
The class must define a [`__call__()`](#datamodel--object.__call__) method; the effect is then the same as if that method was called.

<span id="expressions--await"></span> <span id="expressions--index-56"></span>

## 6.4. Await expression {#expressions--await-expression}

Suspend the execution of [coroutine](https://docs.python.org/3/glossary.html#term-coroutine) on an [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) object. Can only be used inside a [coroutine function](https://docs.python.org/3/glossary.html#term-coroutine-function).

    await_expr: "await" primary

Added in version 3.5.

<span id="expressions--power"></span>

## 6.5. The power operator {#expressions--the-power-operator}

The power operator binds more tightly than unary operators on its left; it binds less tightly than unary operators on its right. The syntax is:

    power: (await_expr | primary) ["**" u_expr]

Thus, in an unparenthesized sequence of power and unary operators, the operators are evaluated from right to left (this does not constrain the evaluation order for the operands): `-1**2` results in `-1`.

The power operator has the same semantics as the built-in [`pow()`](https://docs.python.org/3/library/functions.html#pow) function, when called with two arguments: it yields its left argument raised to the power of its right argument. Numeric arguments are first [converted to a common type](https://docs.python.org/3/library/stdtypes.html#stdtypes-mixed-arithmetic), and the result is of that type.

For int operands, the result has the same type as the operands unless the second argument is negative; in that case, all arguments are converted to float and a float result is delivered. For example, `10**2` returns `100`, but `10**-2` returns `0.01`.

Raising `0.0` to a negative power results in a [`ZeroDivisionError`](https://docs.python.org/3/library/exceptions.html#ZeroDivisionError). Raising a negative number to a fractional power results in a [`complex`](https://docs.python.org/3/library/functions.html#complex) number. (In earlier versions it raised a [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError).)

This operation can be customized using the special [`__pow__()`](#datamodel--object.__pow__) and [`__rpow__()`](#datamodel--object.__rpow__) methods.

<span id="expressions--unary"></span>

## 6.6. Unary arithmetic and bitwise operations {#expressions--unary-arithmetic-and-bitwise-operations}

All unary arithmetic and bitwise operations have the same priority:

    u_expr: power | "-" u_expr | "+" u_expr | "~" u_expr

The unary `-` (minus) operator yields the negation of its numeric argument; the operation can be overridden with the [`__neg__()`](#datamodel--object.__neg__) special method.

The unary `+` (plus) operator yields its numeric argument unchanged; the operation can be overridden with the [`__pos__()`](#datamodel--object.__pos__) special method.

The unary `~` (invert) operator yields the bitwise inversion of its integer argument. The bitwise inversion of `x` is defined as `-(x+1)`. It only applies to integral numbers or to custom objects that override the [`__invert__()`](#datamodel--object.__invert__) special method.

In all three cases, if the argument does not have the proper type, a [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) exception is raised.

<span id="expressions--binary"></span>

## 6.7. Binary arithmetic operations {#expressions--binary-arithmetic-operations}

The binary arithmetic operations have the conventional priority levels. Note that some of these operations also apply to certain non-numeric types. Apart from the power operator, there are only two levels, one for multiplicative operators and one for additive operators:

    m_expr: u_expr | m_expr "*" u_expr | m_expr "@" m_expr |
            m_expr "//" u_expr | m_expr "/" u_expr |
            m_expr "%" u_expr
    a_expr: m_expr | a_expr "+" m_expr | a_expr "-" m_expr

The `*` (multiplication) operator yields the product of its arguments. The arguments must either both be numbers, or one argument must be an integer and the other must be a sequence. In the former case, the numbers are [converted to a common real type](https://docs.python.org/3/library/stdtypes.html#stdtypes-mixed-arithmetic) and then multiplied together. In the latter case, sequence repetition is performed; a negative repetition factor yields an empty sequence.

This operation can be customized using the special [`__mul__()`](#datamodel--object.__mul__) and [`__rmul__()`](#datamodel--object.__rmul__) methods.

Changed in version 3.14: If only one operand is a complex number, the other operand is converted to a floating-point number.

The `@` (at) operator is intended to be used for matrix multiplication. No builtin Python types implement this operator.

This operation can be customized using the special [`__matmul__()`](#datamodel--object.__matmul__) and [`__rmatmul__()`](#datamodel--object.__rmatmul__) methods.

Added in version 3.5.

The `/` (division) and `//` (floor division) operators yield the quotient of their arguments. The numeric arguments are first [converted to a common type](https://docs.python.org/3/library/stdtypes.html#stdtypes-mixed-arithmetic). Division of integers yields a float, while floor division of integers results in an integer; the result is that of mathematical division with the ‘floor’ function applied to the result. Division by zero raises the [`ZeroDivisionError`](https://docs.python.org/3/library/exceptions.html#ZeroDivisionError) exception.

The division operation can be customized using the special [`__truediv__()`](#datamodel--object.__truediv__) and [`__rtruediv__()`](#datamodel--object.__rtruediv__) methods. The floor division operation can be customized using the special [`__floordiv__()`](#datamodel--object.__floordiv__) and [`__rfloordiv__()`](#datamodel--object.__rfloordiv__) methods.

The `%` (modulo) operator yields the remainder from the division of the first argument by the second. The numeric arguments are first [converted to a common type](https://docs.python.org/3/library/stdtypes.html#stdtypes-mixed-arithmetic). A zero right argument raises the [`ZeroDivisionError`](https://docs.python.org/3/library/exceptions.html#ZeroDivisionError) exception. The arguments may be floating-point numbers, e.g., `3.14%0.7` equals `0.34` (since `3.14` equals `4*0.7 + 0.34`.) The modulo operator always yields a result with the same sign as its second operand (or zero); the absolute value of the result is strictly smaller than the absolute value of the second operand [\[1\]](#expressions--id18){#expressions--id9}.

The floor division and modulo operators are connected by the following identity: `x == (x//y)*y + (x%y)`. Floor division and modulo are also connected with the built-in function [`divmod()`](https://docs.python.org/3/library/functions.html#divmod): `divmod(x, y) == (x//y, x%y)`. [\[2\]](#expressions--id19){#expressions--id10}.

In addition to performing the modulo operation on numbers, the `%` operator is also overloaded by string objects to perform old-style string formatting (also known as interpolation). The syntax for string formatting is described in the Python Library Reference, section [printf-style String Formatting](https://docs.python.org/3/library/stdtypes.html#old-string-formatting).

The *modulo* operation can be customized using the special [`__mod__()`](#datamodel--object.__mod__) and [`__rmod__()`](#datamodel--object.__rmod__) methods.

The floor division operator, the modulo operator, and the [`divmod()`](https://docs.python.org/3/library/functions.html#divmod) function are not defined for complex numbers. Instead, convert to a floating-point number using the [`abs()`](https://docs.python.org/3/library/functions.html#abs) function if appropriate.

The `+` (addition) operator yields the sum of its arguments. The arguments must either both be numbers or both be sequences of the same type. In the former case, the numbers are [converted to a common real type](https://docs.python.org/3/library/stdtypes.html#stdtypes-mixed-arithmetic) and then added together. In the latter case, the sequences are concatenated.

This operation can be customized using the special [`__add__()`](#datamodel--object.__add__) and [`__radd__()`](#datamodel--object.__radd__) methods.

Changed in version 3.14: If only one operand is a complex number, the other operand is converted to a floating-point number.

The `-` (subtraction) operator yields the difference of its arguments. The numeric arguments are first [converted to a common real type](https://docs.python.org/3/library/stdtypes.html#stdtypes-mixed-arithmetic).

This operation can be customized using the special [`__sub__()`](#datamodel--object.__sub__) and [`__rsub__()`](#datamodel--object.__rsub__) methods.

Changed in version 3.14: If only one operand is a complex number, the other operand is converted to a floating-point number.

<span id="expressions--shifting"></span>

## 6.8. Shifting operations {#expressions--shifting-operations}

The shifting operations have lower priority than the arithmetic operations:

    shift_expr: a_expr | shift_expr ("<<" | ">>") a_expr

These operators accept integers as arguments. They shift the first argument to the left or right by the number of bits given by the second argument.

The left shift operation can be customized using the special [`__lshift__()`](#datamodel--object.__lshift__) and [`__rlshift__()`](#datamodel--object.__rlshift__) methods. The right shift operation can be customized using the special [`__rshift__()`](#datamodel--object.__rshift__) and [`__rrshift__()`](#datamodel--object.__rrshift__) methods.

A right shift by *n* bits is defined as floor division by `pow(2,n)`. A left shift by *n* bits is defined as multiplication with `pow(2,n)`.

<span id="expressions--bitwise"></span>

## 6.9. Binary bitwise operations {#expressions--binary-bitwise-operations}

Each of the three bitwise operations has a different priority level:

    and_expr: shift_expr | and_expr "&" shift_expr
    xor_expr: and_expr | xor_expr "^" and_expr
    or_expr:  xor_expr | or_expr "|" xor_expr

The `&` operator yields the bitwise AND of its arguments, which must be integers or one of them must be a custom object overriding [`__and__()`](#datamodel--object.__and__) or [`__rand__()`](#datamodel--object.__rand__) special methods.

The `^` operator yields the bitwise XOR (exclusive OR) of its arguments, which must be integers or one of them must be a custom object overriding [`__xor__()`](#datamodel--object.__xor__) or [`__rxor__()`](#datamodel--object.__rxor__) special methods.

The `|` operator yields the bitwise (inclusive) OR of its arguments, which must be integers or one of them must be a custom object overriding [`__or__()`](#datamodel--object.__or__) or [`__ror__()`](#datamodel--object.__ror__) special methods.

<span id="expressions--id11"></span>

## 6.10. Comparisons {#expressions--comparisons}

Unlike C, all comparison operations in Python have the same priority, which is lower than that of any arithmetic, shifting or bitwise operation. Also unlike C, expressions like `a < b < c` have the interpretation that is conventional in mathematics:

    comparison:    or_expr (comp_operator or_expr)*
    comp_operator: "<" | ">" | "==" | ">=" | "<=" | "!="
                   | "is" ["not"] | ["not"] "in"

Comparisons yield boolean values: `True` or `False`. Custom *rich comparison methods* may return non-boolean values. In this case Python will call [`bool()`](https://docs.python.org/3/library/functions.html#bool) on such value in boolean contexts.

Comparisons can be chained arbitrarily, e.g., `x < y <= z` is equivalent to `x < y and y <= z`, except that `y` is evaluated only once (but in both cases `z` is not evaluated at all when `x < y` is found to be false).

Formally, if *a*, *b*, *c*, …, *y*, *z* are expressions and *op1*, *op2*, …, *opN* are comparison operators, then `a op1 b op2 c ... y opN z` is equivalent to `a op1 b and b op2 c and ... y opN z`, except that each expression is evaluated at most once.

Note that `a op1 b op2 c` doesn’t imply any kind of comparison between *a* and *c*, so that, e.g., `x < y > z` is perfectly legal (though perhaps not pretty).

<span id="expressions--expressions-value-comparisons"></span>

### 6.10.1. Value comparisons {#expressions--value-comparisons}

The operators `<`, `>`, `==`, `>=`, `<=`, and `!=` compare the values of two objects. The objects do not need to have the same type.

Chapter [Objects, values and types](#datamodel--objects) states that objects have a value (in addition to type and identity). The value of an object is a rather abstract notion in Python: For example, there is no canonical access method for an object’s value. Also, there is no requirement that the value of an object should be constructed in a particular way, e.g. comprised of all its data attributes. Comparison operators implement a particular notion of what the value of an object is. One can think of them as defining the value of an object indirectly, by means of their comparison implementation.

Because all types are (direct or indirect) subtypes of [`object`](https://docs.python.org/3/library/functions.html#object), they inherit the default comparison behavior from `object`. Types can customize their comparison behavior by implementing *rich comparison methods* like [`__lt__()`](#datamodel--object.__lt__), described in [Basic customization](#datamodel--customization).

The default behavior for equality comparison (`==` and `!=`) is based on the identity of the objects. Hence, equality comparison of instances with the same identity results in equality, and equality comparison of instances with different identities results in inequality. A motivation for this default behavior is the desire that all objects should be reflexive (i.e. `x is y` implies `x == y`).

A default order comparison (`<`, `>`, `<=`, and `>=`) is not provided; an attempt raises [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError). A motivation for this default behavior is the lack of a similar invariant as for equality.

The behavior of the default equality comparison, that instances with different identities are always unequal, may be in contrast to what types will need that have a sensible definition of object value and value-based equality. Such types will need to customize their comparison behavior, and in fact, a number of built-in types have done that.

The following list describes the comparison behavior of the most important built-in types.

- Numbers of built-in numeric types ([Numeric Types — int, float, complex](https://docs.python.org/3/library/stdtypes.html#typesnumeric)) and of the standard library types [`fractions.Fraction`](https://docs.python.org/3/library/fractions.html#fractions.Fraction) and [`decimal.Decimal`](https://docs.python.org/3/library/decimal.html#decimal.Decimal) can be compared within and across their types, with the restriction that complex numbers do not support order comparison. Within the limits of the types involved, they compare mathematically (algorithmically) correct without loss of precision.

  The not-a-number values `float('NaN')` and `decimal.Decimal('NaN')` are special. Any ordered comparison of a number to a not-a-number value is false. A counter-intuitive implication is that not-a-number values are not equal to themselves. For example, if `x = float('NaN')`, `3 < x`, `x < 3` and `x == x` are all false, while `x != x` is true. This behavior is compliant with IEEE 754.

- `None` and [`NotImplemented`](https://docs.python.org/3/library/constants.html#NotImplemented) are singletons. <span id="expressions--index-78"></span>[**PEP 8**](https://peps.python.org/pep-0008/) advises that comparisons for singletons should always be done with `is` or `is not`, never the equality operators.

- Binary sequences (instances of [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes) or [`bytearray`](https://docs.python.org/3/library/stdtypes.html#bytearray)) can be compared within and across their types. They compare lexicographically using the numeric values of their elements.

- Strings (instances of [`str`](https://docs.python.org/3/library/stdtypes.html#str)) compare lexicographically using the numerical Unicode code points (the result of the built-in function [`ord()`](https://docs.python.org/3/library/functions.html#ord)) of their characters. [\[3\]](#expressions--id20){#expressions--id12}

  Strings and binary sequences cannot be directly compared.

- Sequences (instances of [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple), [`list`](https://docs.python.org/3/library/stdtypes.html#list), or [`range`](https://docs.python.org/3/library/stdtypes.html#range)) can be compared only within each of their types, with the restriction that ranges do not support order comparison. Equality comparison across these types results in inequality, and ordering comparison across these types raises [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError).

  Sequences compare lexicographically using comparison of corresponding elements. The built-in containers typically assume identical objects are equal to themselves. That lets them bypass equality tests for identical objects to improve performance and to maintain their internal invariants.

  Lexicographical comparison between built-in collections works as follows:

  - For two collections to compare equal, they must be of the same type, have the same length, and each pair of corresponding elements must compare equal (for example, `[1,2] == (1,2)` is false because the type is not the same).

  - Collections that support order comparison are ordered the same as their first unequal elements (for example, `[1,2,x] <= [1,2,y]` has the same value as `x <= y`). If a corresponding element does not exist, the shorter collection is ordered first (for example, `[1,2] < [1,2,3]` is true).

- Mappings (instances of [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)) compare equal if and only if they have equal `(key, value)` pairs. Equality comparison of the keys and values enforces reflexivity.

  Order comparisons (`<`, `>`, `<=`, and `>=`) raise [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError).

- Sets (instances of [`set`](https://docs.python.org/3/library/stdtypes.html#set) or [`frozenset`](https://docs.python.org/3/library/stdtypes.html#frozenset)) can be compared within and across their types.

  They define order comparison operators to mean subset and superset tests. Those relations do not define total orderings (for example, the two sets `{1,2}` and `{2,3}` are not equal, nor subsets of one another, nor supersets of one another). Accordingly, sets are not appropriate arguments for functions which depend on total ordering (for example, [`min()`](https://docs.python.org/3/library/functions.html#min), [`max()`](https://docs.python.org/3/library/functions.html#max), and [`sorted()`](https://docs.python.org/3/library/functions.html#sorted) produce undefined results given a list of sets as inputs).

  Comparison of sets enforces reflexivity of its elements.

- Most other built-in types have no comparison methods implemented, so they inherit the default comparison behavior.

User-defined classes that customize their comparison behavior should follow some consistency rules, if possible:

- Equality comparison should be reflexive. In other words, identical objects should compare equal:

  > `x is y` implies `x == y`

- Comparison should be symmetric. In other words, the following expressions should have the same result:

  > `x == y` and `y == x`
  >
  > `x != y` and `y != x`
  >
  > `x < y` and `y > x`
  >
  > `x <= y` and `y >= x`

- Comparison should be transitive. The following (non-exhaustive) examples illustrate that:

  > `x > y and y > z` implies `x > z`
  >
  > `x < y and y <= z` implies `x < z`

- Inverse comparison should result in the boolean negation. In other words, the following expressions should have the same result:

  > `x == y` and `not x != y`
  >
  > `x < y` and `not x >= y` (for total ordering)
  >
  > `x > y` and `not x <= y` (for total ordering)

  The last two expressions apply to totally ordered collections (e.g. to sequences, but not to sets or mappings). See also the [`@~functools.total_ordering`](https://docs.python.org/3/library/functools.html#functools.total_ordering) decorator.

- The [`hash()`](https://docs.python.org/3/library/functions.html#hash) result should be consistent with equality. Objects that are equal should either have the same hash value, or be marked as unhashable.

Python does not enforce these consistency rules. In fact, the not-a-number values are an example for not following these rules.

<span id="expressions--membership-test-details"></span> <span id="expressions--not-in"></span> <span id="expressions--in"></span>

### 6.10.2. Membership test operations {#expressions--membership-test-operations}

The operators [`in`](#expressions--in) and [`not in`](#expressions--not-in) test for membership. `x in s` evaluates to `True` if *x* is a member of *s*, and `False` otherwise. `x not in s` returns the negation of `x in s`. All built-in sequences and set types support this as well as dictionary, for which `in` tests whether the dictionary has a given key. For container types such as list, tuple, set, frozenset, dict, or collections.deque, the expression `x in y` is equivalent to `any(x is e or x == e for e in y)`.

For the string and bytes types, `x in y` is `True` if and only if *x* is a substring of *y*. An equivalent test is `y.find(x) != -1`. Empty strings are always considered to be a substring of any other string, so `"" in "abc"` will return `True`.

For user-defined classes which define the [`__contains__()`](#datamodel--object.__contains__) method, `x in y` returns `True` if `y.__contains__(x)` returns a true value, and `False` otherwise.

For user-defined classes which do not define [`__contains__()`](#datamodel--object.__contains__) but do define [`__iter__()`](#datamodel--object.__iter__), `x in y` is `True` if some value `z`, for which the expression `x is z or x == z` is true, is produced while iterating over `y`. If an exception is raised during the iteration, it is as if [`in`](#expressions--in) raised that exception.

Lastly, the old-style iteration protocol is tried: if a class defines [`__getitem__()`](#datamodel--object.__getitem__), `x in y` is `True` if and only if there is a non-negative integer index *i* such that `x is y[i] or x == y[i]`, and no lower integer index raises the [`IndexError`](https://docs.python.org/3/library/exceptions.html#IndexError) exception. (If any other exception is raised, it is as if [`in`](#expressions--in) raised that exception).

The operator [`not in`](#expressions--not-in) is defined to have the inverse truth value of [`in`](#expressions--in).

<span id="expressions--is"></span> <span id="expressions--index-80"></span> <span id="expressions--identity-comparisons"></span>

### 6.10.3. Identity comparisons {#expressions--is-not}

The operators [`is`](#expressions--is) and [`is not`](#expressions--is-not) test for an object’s identity: `x is y` is true if and only if *x* and *y* are the same object. An Object’s identity is determined using the [`id()`](https://docs.python.org/3/library/functions.html#id) function. `x is not y` yields the inverse truth value. [\[4\]](#expressions--id21){#expressions--id13}

<span id="expressions--not"></span> <span id="expressions--or"></span> <span id="expressions--and"></span> <span id="expressions--booleans"></span>

## 6.11. Boolean operations {#expressions--boolean-operations}

``` {#expressions--index-81}
or_test:  and_test | or_test "or" and_test
and_test: not_test | and_test "and" not_test
not_test: comparison | "not" not_test
```

In the context of Boolean operations, and also when expressions are used by control flow statements, the following values are interpreted as false: `False`, `None`, numeric zero of all types, and empty strings and containers (including strings, tuples, lists, dictionaries, sets and frozensets). All other values are interpreted as true. User-defined objects can customize their truth value by providing a [`__bool__()`](#datamodel--object.__bool__) method.

The operator [`not`](#expressions--not) yields `True` if its argument is false, `False` otherwise.

The expression `x and y` first evaluates *x*; if *x* is false, its value is returned; otherwise, *y* is evaluated and the resulting value is returned.

The expression `x or y` first evaluates *x*; if *x* is true, its value is returned; otherwise, *y* is evaluated and the resulting value is returned.

Note that neither [`and`](#expressions--and) nor [`or`](#expressions--or) restrict the value and type they return to `False` and `True`, but rather return the last evaluated argument. This is sometimes useful, e.g., if `s` is a string that should be replaced by a default value if it is empty, the expression `s or 'foo'` yields the desired value. Because [`not`](#expressions--not) has to create a new value, it returns a boolean value regardless of the type of its argument (for example, `not 'foo'` produces `False` rather than `''`.)

<span id="expressions--index-85"></span> <span id="expressions--id14"></span>

## 6.12. Assignment expressions {#expressions--assignment-expressions}

    assignment_expression: [identifier ":="] expression

An assignment expression (sometimes also called a “named expression” or “walrus”) assigns an [`expression`](#expressions--grammar-token-python-grammar-expression) to an [`identifier`](#lexical_analysis--grammar-token-python-grammar-identifier), while also returning the value of the `expression`.

One common use case is when handling matched regular expressions:

    if matching := pattern.search(data):
        do_something(matching)

Or, when processing a file stream in chunks:

    while chunk := file.read(9000):
        process(chunk)

Assignment expressions must be surrounded by parentheses when used as expression statements and when used as sub-expressions in slicing, conditional, lambda, keyword-argument, and comprehension-if expressions and in `assert`, `with`, and `assignment` statements. In all other places where they can be used, parentheses are not required, including in `if` and `while` statements.

Added in version 3.8: See <span id="expressions--index-86"></span>[**PEP 572**](https://peps.python.org/pep-0572/) for more details about assignment expressions.

<span id="expressions--if-expr"></span>

## 6.13. Conditional expressions {#expressions--conditional-expressions}

``` {#expressions--index-87}
conditional_expression: or_test ["if" or_test "else" expression]
expression:             conditional_expression | lambda_expr
```

A conditional expression (sometimes called a “ternary operator”) is an alternative to the if-else statement. As it is an expression, it returns a value and can appear as a sub-expression.

The expression `x if C else y` first evaluates the condition, *C* rather than *x*. If *C* is true, *x* is evaluated and its value is returned; otherwise, *y* is evaluated and its value is returned.

See <span id="expressions--index-88"></span>[**PEP 308**](https://peps.python.org/pep-0308/) for more details about conditional expressions.

<span id="expressions--lambdas"></span> <span id="expressions--id15"></span>

## 6.14. Lambdas {#expressions--lambda}

``` {#expressions--index-89}
lambda_expr: "lambda" [parameter_list] ":" expression
```

Lambda expressions (sometimes called lambda forms) are used to create anonymous functions. The expression `lambda parameters: expression` yields a function object. The unnamed object behaves like a function object defined with:

    def <lambda>(parameters):
        return expression

See section [Function definitions](#compound_stmts--function) for the syntax of parameter lists. Note that functions created with lambda expressions cannot contain statements or annotations.

<span id="expressions--exprlists"></span>

## 6.15. Expression lists {#expressions--expression-lists}

``` {#expressions--index-90}
starred_expression:       "*" or_expr | expression
flexible_expression:      assignment_expression | starred_expression
flexible_expression_list: flexible_expression ("," flexible_expression)* [","]
starred_expression_list:  starred_expression ("," starred_expression)* [","]
expression_list:          expression ("," expression)* [","]
yield_list:               expression_list | starred_expression "," [starred_expression_list]
```

Except when part of a list or set display, an expression list containing at least one comma yields a tuple. The length of the tuple is the number of expressions in the list. The expressions are evaluated from left to right.

An asterisk `*` denotes *iterable unpacking*. Its operand must be an [iterable](https://docs.python.org/3/glossary.html#term-iterable). The iterable is expanded into a sequence of items, which are included in the new tuple, list, or set, at the site of the unpacking.

Added in version 3.5: Iterable unpacking in expression lists, originally proposed by <span id="expressions--index-93"></span>[**PEP 448**](https://peps.python.org/pep-0448/).

Added in version 3.11: Any item in an expression list may be starred. See <span id="expressions--index-94"></span>[**PEP 646**](https://peps.python.org/pep-0646/).

A trailing comma is required only to create a one-item tuple, such as `1,`; it is optional in all other cases. A single expression without a trailing comma doesn’t create a tuple, but rather yields the value of that expression. (To create an empty tuple, use an empty pair of parentheses: `()`.)

<span id="expressions--evalorder"></span>

## 6.16. Evaluation order {#expressions--evaluation-order}

Python evaluates expressions from left to right. Notice that while evaluating an assignment, the right-hand side is evaluated before the left-hand side.

In the following lines, expressions will be evaluated in the arithmetic order of their suffixes:

    expr1, expr2, expr3, expr4
    (expr1, expr2, expr3, expr4)
    {expr1: expr2, expr3: expr4}
    expr1 + expr2 * (expr3 - expr4)
    expr1(expr2, expr3, *expr4, **expr5)
    expr3, expr4 = expr1, expr2

<span id="expressions--operator-summary"></span>

## 6.17. Operator precedence {#expressions--operator-precedence}

The following table summarizes the operator precedence in Python, from highest precedence (most binding) to lowest precedence (least binding). Operators in the same box have the same precedence. Unless the syntax is explicitly given, operators are binary. Operators in the same box group left to right (except for exponentiation and conditional expressions, which group from right to left).

Note that comparisons, membership tests, and identity tests, all have the same precedence and have a left-to-right chaining feature as described in the [Comparisons](#expressions--comparisons) section.

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr class="header">
<th><p>Operator</p></th>
<th><p>Description</p></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><p><code>(expressions...)</code>,</p>
<p><code>[expressions...]</code>, <code>{key: value...}</code>, <code>{expressions...}</code></p></td>
<td><p>Binding or parenthesized expression, list display, dictionary display, set display</p></td>
</tr>
<tr class="even">
<td><p><code>x[index]</code>, <code>x[index:index]</code> <code>x(arguments...)</code>, <code>x.attribute</code></p></td>
<td><p>Subscription (including slicing), call, attribute reference</p></td>
</tr>
<tr class="odd">
<td><p><a href="#expressions--await"><code>await x</code></a></p></td>
<td><p>Await expression</p></td>
</tr>
<tr class="even">
<td><p><code>**</code></p></td>
<td><p>Exponentiation <a href="#expressions--id22" id="expressions--id16">[5]</a></p></td>
</tr>
<tr class="odd">
<td><p><code>+x</code>, <code>-x</code>, <code>~x</code></p></td>
<td><p>Positive, negative, bitwise NOT</p></td>
</tr>
<tr class="even">
<td><p><code>*</code>, <code>@</code>, <code>/</code>, <code>//</code>, <code>%</code></p></td>
<td><p>Multiplication, matrix multiplication, division, floor division, remainder <a href="#expressions--id23" id="expressions--id17">[6]</a></p></td>
</tr>
<tr class="odd">
<td><p><code>+</code>, <code>-</code></p></td>
<td><p>Addition and subtraction</p></td>
</tr>
<tr class="even">
<td><p><code>&lt;&lt;</code>, <code>&gt;&gt;</code></p></td>
<td><p>Shifts</p></td>
</tr>
<tr class="odd">
<td><p><code>&amp;</code></p></td>
<td><p>Bitwise AND</p></td>
</tr>
<tr class="even">
<td><p><code>^</code></p></td>
<td><p>Bitwise XOR</p></td>
</tr>
<tr class="odd">
<td><p><code>|</code></p></td>
<td><p>Bitwise OR</p></td>
</tr>
<tr class="even">
<td><p><a href="#expressions--in"><code>in</code></a>, <a href="#expressions--not-in"><code>not in</code></a>, <a href="#expressions--is"><code>is</code></a>, <a href="#expressions--is-not"><code>is not</code></a>, <code>&lt;</code>, <code>&lt;=</code>, <code>&gt;</code>, <code>&gt;=</code>, <code>!=</code>, <code>==</code></p></td>
<td><p>Comparisons, including membership tests and identity tests</p></td>
</tr>
<tr class="odd">
<td><p><a href="#expressions--not"><code>not x</code></a></p></td>
<td><p>Boolean NOT</p></td>
</tr>
<tr class="even">
<td><p><a href="#expressions--and"><code>and</code></a></p></td>
<td><p>Boolean AND</p></td>
</tr>
<tr class="odd">
<td><p><a href="#expressions--or"><code>or</code></a></p></td>
<td><p>Boolean OR</p></td>
</tr>
<tr class="even">
<td><p><a href="#expressions--if-expr"><code>if</code></a> – <code>else</code></p></td>
<td><p>Conditional expression</p></td>
</tr>
<tr class="odd">
<td><p><a href="#expressions--lambda"><code>lambda</code></a></p></td>
<td><p>Lambda expression</p></td>
</tr>
<tr class="even">
<td><p><code>:=</code></p></td>
<td><p>Assignment expression</p></td>
</tr>
</tbody>
</table>

Footnotes

\[[1](#expressions--id9)\]

While `abs(x%y) < abs(y)` is true mathematically, for floats it may not be true numerically due to roundoff. For example, and assuming a platform on which a Python float is an IEEE 754 double-precision number, in order that `-1e-100 % 1e100` have the same sign as `1e100`, the computed result is `-1e-100 + 1e100`, which is numerically exactly equal to `1e100`. The function [`math.fmod()`](https://docs.python.org/3/library/math.html#math.fmod) returns a result whose sign matches the sign of the first argument instead, and so returns `-1e-100` in this case. Which approach is more appropriate depends on the application.

\[[2](#expressions--id10)\]

If x is very close to an exact integer multiple of y, it’s possible for `x//y` to be one larger than `(x-x%y)//y` due to rounding. In such cases, Python returns the latter result, in order to preserve that `divmod(x,y)[0] * y + x % y` be very close to `x`.

\[[3](#expressions--id12)\]

The Unicode standard distinguishes between *code points* (e.g. U+0041) and *abstract characters* (e.g. “LATIN CAPITAL LETTER A”). While most abstract characters in Unicode are only represented using one code point, there is a number of abstract characters that can in addition be represented using a sequence of more than one code point. For example, the abstract character “LATIN CAPITAL LETTER C WITH CEDILLA” can be represented as a single *precomposed character* at code position U+00C7, or as a sequence of a *base character* at code position U+0043 (LATIN CAPITAL LETTER C), followed by a *combining character* at code position U+0327 (COMBINING CEDILLA).

The comparison operators on strings compare at the level of Unicode code points. This may be counter-intuitive to humans. For example, `"\u00C7" == "\u0043\u0327"` is `False`, even though both strings represent the same abstract character “LATIN CAPITAL LETTER C WITH CEDILLA”.

To compare strings at the level of abstract characters (that is, in a way intuitive to humans), use [`unicodedata.normalize()`](https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize).

\[[4](#expressions--id13)\]

Due to automatic garbage-collection, free lists, and the dynamic nature of descriptors, you may notice seemingly unusual behaviour in certain uses of the [`is`](#expressions--is) operator, like those involving comparisons between instance methods, or constants. Check their documentation for more info.

\[[5](#expressions--id16)\]

The power operator `**` binds less tightly than an arithmetic or bitwise unary operator on its right, that is, `2**-1` is `0.5`.

\[[6](#expressions--id17)\]

The `%` operator is also used for string formatting; the same precedence applies.

<span id="simple_stmts--simple"></span>

# 7. Simple statements {#simple_stmts--simple-statements}

A simple statement is comprised within a single logical line. Several simple statements may occur on a single line separated by semicolons. The syntax for simple statements is:

    simple_stmt: expression_stmt
                 | assert_stmt
                 | assignment_stmt
                 | augmented_assignment_stmt
                 | annotated_assignment_stmt
                 | pass_stmt
                 | del_stmt
                 | return_stmt
                 | yield_stmt
                 | raise_stmt
                 | break_stmt
                 | continue_stmt
                 | import_stmt
                 | future_stmt
                 | global_stmt
                 | nonlocal_stmt
                 | type_stmt

<span id="simple_stmts--exprstmts"></span>

## 7.1. Expression statements {#simple_stmts--expression-statements}

<span id="simple_stmts--index-1"></span>Expression statements are used (mostly interactively) to compute and write a value, or (usually) to call a procedure (a function that returns no meaningful result; in Python, procedures return the value `None`). Other uses of expression statements are allowed and occasionally useful. The syntax for an expression statement is:

    expression_stmt: starred_expression

An expression statement evaluates the expression list (which may be a single expression).

In interactive mode, if the value is not `None`, it is converted to a string using the built-in [`repr()`](https://docs.python.org/3/library/functions.html#repr) function and the resulting string is written to standard output on a line by itself (except if the result is `None`, so that procedure calls do not cause any output.)

<span id="simple_stmts--assignment"></span>

## 7.2. Assignment statements {#simple_stmts--assignment-statements}

Assignment statements are used to (re)bind names to values and to modify attributes or items of mutable objects:

    assignment_stmt: (target_list "=")+ (starred_expression | yield_expression)
    target_list:     target ("," target)* [","]
    target:          identifier
                     | "(" [target_list] ")"
                     | "[" [target_list] "]"
                     | attributeref
                     | subscription
                     | "*" target

(See section [Primaries](#expressions--primaries) for the syntax definitions for *attributeref* and *subscription*.)

An assignment statement evaluates the expression list (remember that this can be a single expression or a comma-separated list, the latter yielding a tuple) and assigns the single resulting object to each of the target lists, from left to right.

Assignment is defined recursively depending on the form of the target (list). When a target is part of a mutable object (an attribute reference or subscription), the mutable object must ultimately perform the assignment and decide about its validity, and may raise an exception if the assignment is unacceptable. The rules observed by various types and the exceptions raised are given with the definition of the object types (see section [The standard type hierarchy](#datamodel--types)).

Assignment of an object to a target list, optionally enclosed in parentheses or square brackets, is recursively defined as follows.

- If the target list is a single target with no trailing comma, optionally in parentheses, the object is assigned to that target.

- Else:

  - If the target list contains one target prefixed with an asterisk, called a “starred” target: The object must be an iterable with at least as many items as there are targets in the target list, minus one. The first items of the iterable are assigned, from left to right, to the targets before the starred target. The final items of the iterable are assigned to the targets after the starred target. A list of the remaining items in the iterable is then assigned to the starred target (the list can be empty).

  - Else: The object must be an iterable with the same number of items as there are targets in the target list, and the items are assigned, from left to right, to the corresponding targets.

Assignment of an object to a single target is recursively defined as follows.

- If the target is an identifier (name):

  - If the name does not occur in a [`global`](#simple_stmts--global) or [`nonlocal`](#simple_stmts--nonlocal) statement in the current code block: the name is bound to the object in the current local namespace.

  - Otherwise: the name is bound to the object in the global namespace or the outer namespace determined by [`nonlocal`](#simple_stmts--nonlocal), respectively.

  The name is rebound if it was already bound. This may cause the reference count for the object previously bound to the name to reach zero, causing the object to be deallocated and its destructor (if it has one) to be called.

- <div id="simple_stmts--index-8">

  If the target is an attribute reference: The primary expression in the reference is evaluated. It should yield an object with assignable attributes; if this is not the case, [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) is raised. That object is then asked to assign the assigned object to the given attribute; if it cannot perform the assignment, it raises an exception (usually but not necessarily [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError)).

  Note: If the object is a class instance and the attribute reference occurs on both sides of the assignment operator, the right-hand side expression, `a.x` can access either an instance attribute or (if no instance attribute exists) a class attribute. The left-hand side target `a.x` is always set as an instance attribute, creating it if necessary. Thus, the two occurrences of `a.x` do not necessarily refer to the same attribute: if the right-hand side expression refers to a class attribute, the left-hand side creates a new instance attribute as the target of the assignment:

      class Cls:
          x = 3             # class variable
      inst = Cls()
      inst.x = inst.x + 1   # writes inst.x as 4 leaving Cls.x as 3

  This description does not necessarily apply to descriptor attributes, such as properties created with [`@property`](https://docs.python.org/3/library/functions.html#property).

  </div>

- <div id="simple_stmts--index-9">

  If the target is a subscription: The primary expression in the reference is evaluated. Next, the subscript expression is evaluated. Then, the primary’s [`__setitem__()`](#datamodel--object.__setitem__) method is called with two arguments: the subscript and the assigned object.

  Typically, [`__setitem__()`](#datamodel--object.__setitem__) is defined on mutable sequence objects (such as lists) and mapping objects (such as dictionaries), and behaves as follows.

  If the primary is a mutable sequence object (such as a list), the subscript must yield an integer. If it is negative, the sequence’s length is added to it. The resulting value must be a nonnegative integer less than the sequence’s length, and the sequence is asked to assign the assigned object to its item with that index. If the index is out of range, [`IndexError`](https://docs.python.org/3/library/exceptions.html#IndexError) is raised (assignment to a subscripted sequence cannot add new items to a list).

  If the primary is a mapping object (such as a dictionary), the subscript must have a type compatible with the mapping’s key type, and the mapping is then asked to create a key/value pair which maps the subscript to the assigned object. This can either replace an existing key/value pair with the same key value, or insert a new key/value pair (if no key with the same value existed).

  If the target is a slicing: The primary expression should evaluate to a mutable sequence object (such as a list). The assigned object should be [iterable](https://docs.python.org/3/glossary.html#term-iterable). The slicing’s lower and upper bounds should be integers; if they are `None` (or not present), the defaults are zero and the sequence’s length. If either bound is negative, the sequence’s length is added to it. The resulting bounds are clipped to lie between zero and the sequence’s length, inclusive. Finally, the sequence object is asked to replace the slice with the items of the assigned sequence. The length of the slice may be different from the length of the assigned sequence, thus changing the length of the target sequence, if the target sequence allows it.

  </div>

Although the definition of assignment implies that overlaps between the left-hand side and the right-hand side are ‘simultaneous’ (for example `a, b = b, a` swaps two variables), overlaps *within* the collection of assigned-to variables occur left-to-right, sometimes resulting in confusion. For instance, the following program prints `[0, 2]`:

    x = [0, 1]
    i = 0
    i, x[i] = 1, 2         # i is updated, then x[i] is updated
    print(x)

See also

<span id="simple_stmts--index-13"></span>[**PEP 3132**](https://peps.python.org/pep-3132/) - Extended Iterable Unpacking  
The specification for the `*target` feature.

<span id="simple_stmts--augassign"></span>

### 7.2.1. Augmented assignment statements {#simple_stmts--augmented-assignment-statements}

Augmented assignment is the combination, in a single statement, of a binary operation and an assignment statement:

    augmented_assignment_stmt: augtarget augop (expression_list | yield_expression)
    augtarget:                 identifier | attributeref | subscription
    augop:                     "+=" | "-=" | "*=" | "@=" | "/=" | "//=" | "%=" | "**="
                               | ">>=" | "<<=" | "&=" | "^=" | "|="

(See section [Primaries](#expressions--primaries) for the syntax definitions of the last three symbols.)

An augmented assignment evaluates the target (which, unlike normal assignment statements, cannot be an unpacking) and the expression list, performs the binary operation specific to the type of assignment on the two operands, and assigns the result to the original target. The target is only evaluated once.

An augmented assignment statement like `x += 1` can be rewritten as `x = x + 1` to achieve a similar, but not exactly equal effect. In the augmented version, `x` is only evaluated once. Also, when possible, the actual operation is performed *in-place*, meaning that rather than creating a new object and assigning that to the target, the old object is modified instead.

Unlike normal assignments, augmented assignments evaluate the left-hand side *before* evaluating the right-hand side. For example, `a[i] += f(x)` first looks-up `a[i]`, then it evaluates `f(x)` and performs the addition, and lastly, it writes the result back to `a[i]`.

With the exception of assigning to tuples and multiple targets in a single statement, the assignment done by augmented assignment statements is handled the same way as normal assignments. Similarly, with the exception of the possible *in-place* behavior, the binary operation performed by augmented assignment is the same as the normal binary operations.

For targets which are attribute references, the same [caveat about class and instance attributes](#simple_stmts--attr-target-note) applies as for regular assignments.

<span id="simple_stmts--annassign"></span>

### 7.2.2. Annotated assignment statements {#simple_stmts--annotated-assignment-statements}

[Annotation](https://docs.python.org/3/glossary.html#term-variable-annotation) assignment is the combination, in a single statement, of a variable or attribute annotation and an optional assignment statement:

    annotated_assignment_stmt: augtarget ":" expression
                               ["=" (starred_expression | yield_expression)]

The difference from normal [Assignment statements](#simple_stmts--assignment) is that only a single target is allowed.

The assignment target is considered “simple” if it consists of a single name that is not enclosed in parentheses. For simple assignment targets, if in class or module scope, the annotations are gathered in a lazily evaluated [annotation scope](#executionmodel--annotation-scopes). The annotations can be evaluated using the [`__annotations__`](#datamodel--object.__annotations__) attribute of a class or module, or using the facilities in the [`annotationlib`](https://docs.python.org/3/library/annotationlib.html#module-annotationlib) module.

If the assignment target is not simple (an attribute, subscript node, or parenthesized name), the annotation is never evaluated.

If a name is annotated in a function scope, then this name is local for that scope. Annotations are never evaluated and stored in function scopes.

If the right hand side is present, an annotated assignment performs the actual assignment as if there was no annotation present. If the right hand side is not present for an expression target, then the interpreter evaluates the target except for the last [`__setitem__()`](#datamodel--object.__setitem__) or [`__setattr__()`](#datamodel--object.__setattr__) call.

See also

<span id="simple_stmts--index-16"></span>[**PEP 526**](https://peps.python.org/pep-0526/) - Syntax for Variable Annotations  
The proposal that added syntax for annotating the types of variables (including class variables and instance variables), instead of expressing them through comments.

<span id="simple_stmts--index-17"></span>[**PEP 484**](https://peps.python.org/pep-0484/) - Type hints  
The proposal that added the [`typing`](https://docs.python.org/3/library/typing.html#module-typing) module to provide a standard syntax for type annotations that can be used in static analysis tools and IDEs.

Changed in version 3.8: Now annotated assignments allow the same expressions in the right hand side as regular assignments. Previously, some expressions (like un-parenthesized tuple expressions) caused a syntax error.

Changed in version 3.14: Annotations are now lazily evaluated in a separate [annotation scope](#executionmodel--annotation-scopes). If the assignment target is not simple, annotations are never evaluated.

<span id="simple_stmts--assert"></span>

## 7.3. The `assert` statement {#simple_stmts--the-assert-statement}

Assert statements are a convenient way to insert debugging assertions into a program:

    assert_stmt: "assert" expression ["," expression]

The simple form, `assert expression`, is equivalent to

    if __debug__:
        if not expression: raise AssertionError

The extended form, `assert expression1, expression2`, is equivalent to

    if __debug__:
        if not expression1: raise AssertionError(expression2)

These equivalences assume that [`__debug__`](https://docs.python.org/3/library/constants.html#debug__) and [`AssertionError`](https://docs.python.org/3/library/exceptions.html#AssertionError) refer to the built-in variables with those names. In the current implementation, the built-in variable `__debug__` is `True` under normal circumstances, `False` when optimization is requested (command line option [`-O`](https://docs.python.org/3/using/cmdline.html#cmdoption-O)). The current code generator emits no code for an [`assert`](#simple_stmts--assert) statement when optimization is requested at compile time. Note that it is unnecessary to include the source code for the expression that failed in the error message; it will be displayed as part of the stack trace.

Assignments to [`__debug__`](https://docs.python.org/3/library/constants.html#debug__) are illegal. The value for the built-in variable is determined when the interpreter starts.

<span id="simple_stmts--pass"></span>

## 7.4. The `pass` statement {#simple_stmts--the-pass-statement}

``` {#simple_stmts--index-20}
pass_stmt: "pass"
```

[`pass`](#simple_stmts--pass) is a null operation — when it is executed, nothing happens. It is useful as a placeholder when a statement is required syntactically, but no code needs to be executed, for example:

    def f(arg): pass    # a function that does nothing (yet)

    class C: pass       # a class with no methods (yet)

<span id="simple_stmts--del"></span>

## 7.5. The `del` statement {#simple_stmts--the-del-statement}

``` {#simple_stmts--index-21}
del_stmt: "del" target_list
```

Deletion is recursively defined very similar to the way assignment is defined. Rather than spelling it out in full details, here are some hints.

Deletion of a target list recursively deletes each target, from left to right.

Deletion of a name removes the binding of that name from the local or global namespace, depending on whether the name occurs in a [`global`](#simple_stmts--global) statement in the same code block. Trying to delete an unbound name raises a [`NameError`](https://docs.python.org/3/library/exceptions.html#NameError) exception.

Deletion of attribute references and subscriptions is passed to the primary object involved; deletion of a slicing is in general equivalent to assignment of an empty slice of the right type (but even this is determined by the sliced object).

Changed in version 3.2: Previously it was illegal to delete a name from the local namespace if it occurs as a free variable in a nested block.

<span id="simple_stmts--return"></span>

## 7.6. The `return` statement {#simple_stmts--the-return-statement}

``` {#simple_stmts--index-24}
return_stmt: "return" [expression_list]
```

[`return`](#simple_stmts--return) may only occur syntactically nested in a function definition, not within a nested class definition.

If an expression list is present, it is evaluated, else `None` is substituted.

[`return`](#simple_stmts--return) leaves the current function call with the expression list (or `None`) as return value.

When [`return`](#simple_stmts--return) passes control out of a [`try`](#compound_stmts--try) statement with a [`finally`](#compound_stmts--finally) clause, that `finally` clause is executed before really leaving the function.

In a generator function, the [`return`](#simple_stmts--return) statement indicates that the generator is done and will cause [`StopIteration`](https://docs.python.org/3/library/exceptions.html#StopIteration) to be raised. The returned value (if any) is used as an argument to construct `StopIteration` and becomes the [`StopIteration.value`](https://docs.python.org/3/library/exceptions.html#StopIteration.value) attribute.

In an asynchronous generator function, an empty [`return`](#simple_stmts--return) statement indicates that the asynchronous generator is done and will cause [`StopAsyncIteration`](https://docs.python.org/3/library/exceptions.html#StopAsyncIteration) to be raised. A non-empty `return` statement is a syntax error in an asynchronous generator function.

<span id="simple_stmts--yield"></span>

## 7.7. The `yield` statement {#simple_stmts--the-yield-statement}

``` {#simple_stmts--index-26}
yield_stmt: yield_expression
```

A [`yield`](#simple_stmts--yield) statement is semantically equivalent to a [yield expression](#expressions--yieldexpr). The `yield` statement can be used to omit the parentheses that would otherwise be required in the equivalent yield expression statement. For example, the yield statements

    yield <expr>
    yield from <expr>

are equivalent to the yield expression statements

    (yield <expr>)
    (yield from <expr>)

Yield expressions and statements are only used when defining a [generator](https://docs.python.org/3/glossary.html#term-generator) function, and are only used in the body of the generator function. Using [`yield`](#simple_stmts--yield) in a function definition is sufficient to cause that definition to create a generator function instead of a normal function.

For full details of [`yield`](#simple_stmts--yield) semantics, refer to the [Yield expressions](#expressions--yieldexpr) section.

<span id="simple_stmts--raise"></span>

## 7.8. The `raise` statement {#simple_stmts--the-raise-statement}

``` {#simple_stmts--index-27}
raise_stmt: "raise" [expression ["from" expression]]
```

If no expressions are present, [`raise`](#simple_stmts--raise) re-raises the exception that is currently being handled, which is also known as the *active exception*. If there isn’t currently an active exception, a [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) exception is raised indicating that this is an error.

Otherwise, [`raise`](#simple_stmts--raise) evaluates the first expression as the exception object. It must be either a subclass or an instance of [`BaseException`](https://docs.python.org/3/library/exceptions.html#BaseException). If it is a class, the exception instance will be obtained when needed by instantiating the class with no arguments.

The *type* of the exception is the exception instance’s class, the *value* is the instance itself.

A traceback object is normally created automatically when an exception is raised and attached to it as the [`__traceback__`](https://docs.python.org/3/library/exceptions.html#BaseException.__traceback__) attribute. You can create an exception and set your own traceback in one step using the [`with_traceback()`](https://docs.python.org/3/library/exceptions.html#BaseException.with_traceback) exception method (which returns the same exception instance, with its traceback set to its argument), like so:

    raise Exception("foo occurred").with_traceback(tracebackobj)

The `from` clause is used for exception chaining: if given, the second *expression* must be another exception class or instance. If the second expression is an exception instance, it will be attached to the raised exception as the [`__cause__`](https://docs.python.org/3/library/exceptions.html#BaseException.__cause__) attribute (which is writable). If the expression is an exception class, the class will be instantiated and the resulting exception instance will be attached to the raised exception as the `__cause__` attribute. If the raised exception is not handled, both exceptions will be printed:

    >>> try:
    ...     print(1 / 0)
    ... except Exception as exc:
    ...     raise RuntimeError("Something bad happened") from exc
    ...
    Traceback (most recent call last):
      File "<stdin>", line 2, in <module>
        print(1 / 0)
              ~~^~~
    ZeroDivisionError: division by zero

    The above exception was the direct cause of the following exception:

    Traceback (most recent call last):
      File "<stdin>", line 4, in <module>
        raise RuntimeError("Something bad happened") from exc
    RuntimeError: Something bad happened

A similar mechanism works implicitly if a new exception is raised when an exception is already being handled. An exception may be handled when an [`except`](#compound_stmts--except) or [`finally`](#compound_stmts--finally) clause, or a [`with`](#compound_stmts--with) statement, is used. The previous exception is then attached as the new exception’s [`__context__`](https://docs.python.org/3/library/exceptions.html#BaseException.__context__) attribute:

    >>> try:
    ...     print(1 / 0)
    ... except:
    ...     raise RuntimeError("Something bad happened")
    ...
    Traceback (most recent call last):
      File "<stdin>", line 2, in <module>
        print(1 / 0)
              ~~^~~
    ZeroDivisionError: division by zero

    During handling of the above exception, another exception occurred:

    Traceback (most recent call last):
      File "<stdin>", line 4, in <module>
        raise RuntimeError("Something bad happened")
    RuntimeError: Something bad happened

Exception chaining can be explicitly suppressed by specifying [`None`](https://docs.python.org/3/library/constants.html#None) in the `from` clause:

    >>> try:
    ...     print(1 / 0)
    ... except:
    ...     raise RuntimeError("Something bad happened") from None
    ...
    Traceback (most recent call last):
      File "<stdin>", line 4, in <module>
    RuntimeError: Something bad happened

Additional information on exceptions can be found in section [Exceptions](#executionmodel--exceptions), and information about handling exceptions is in section [The try statement](#compound_stmts--try).

Changed in version 3.3: [`None`](https://docs.python.org/3/library/constants.html#None) is now permitted as `Y` in `raise X from Y`.

Added the [`__suppress_context__`](https://docs.python.org/3/library/exceptions.html#BaseException.__suppress_context__) attribute to suppress automatic display of the exception context.

Changed in version 3.11: If the traceback of the active exception is modified in an [`except`](#compound_stmts--except) clause, a subsequent `raise` statement re-raises the exception with the modified traceback. Previously, the exception was re-raised with the traceback it had when it was caught.

<span id="simple_stmts--break"></span>

## 7.9. The `break` statement {#simple_stmts--the-break-statement}

``` {#simple_stmts--index-30}
break_stmt: "break"
```

[`break`](#simple_stmts--break) may only occur syntactically nested in a [`for`](#compound_stmts--for) or [`while`](#compound_stmts--while) loop, but not nested in a function or class definition within that loop.

It terminates the nearest enclosing loop, skipping the optional `else` clause if the loop has one.

If a [`for`](#compound_stmts--for) loop is terminated by [`break`](#simple_stmts--break), the loop control target keeps its current value.

When [`break`](#simple_stmts--break) passes control out of a [`try`](#compound_stmts--try) statement with a [`finally`](#compound_stmts--finally) clause, that `finally` clause is executed before really leaving the loop.

<span id="simple_stmts--continue"></span>

## 7.10. The `continue` statement {#simple_stmts--the-continue-statement}

``` {#simple_stmts--index-33}
continue_stmt: "continue"
```

[`continue`](#simple_stmts--continue) may only occur syntactically nested in a [`for`](#compound_stmts--for) or [`while`](#compound_stmts--while) loop, but not nested in a function or class definition within that loop. It continues with the next cycle of the nearest enclosing loop.

When [`continue`](#simple_stmts--continue) passes control out of a [`try`](#compound_stmts--try) statement with a [`finally`](#compound_stmts--finally) clause, that `finally` clause is executed before really starting the next loop cycle.

<span id="simple_stmts--from"></span> <span id="simple_stmts--import"></span>

## 7.11. The `import` statement {#simple_stmts--the-import-statement}

``` {#simple_stmts--index-34}
import_stmt:     "import" module ["as" identifier] ("," module ["as" identifier])*
                 | "from" relative_module "import" identifier ["as" identifier]
                 ("," identifier ["as" identifier])*
                 | "from" relative_module "import" "(" identifier ["as" identifier]
                 ("," identifier ["as" identifier])* [","] ")"
                 | "from" relative_module "import" "*"
module:          (identifier ".")* identifier
relative_module: "."* module | "."+
```

The basic import statement (no [`from`](#simple_stmts--from) clause) is executed in two steps:

1.  find a module, loading and initializing it if necessary

2.  define a name or names in the current namespace for the scope where the [`import`](#simple_stmts--import) statement occurs, just as an assignment statement would (including [`global`](#simple_stmts--global) and [`nonlocal`](#simple_stmts--nonlocal) semantics).

When the statement contains multiple clauses (separated by commas) the two steps are carried out separately for each clause, just as though the clauses had been separated out into individual import statements.

The details of the first step, finding and loading modules, are described in greater detail in the section on the [import system](#import--importsystem), which also describes the various types of packages and modules that can be imported, as well as all the hooks that can be used to customize the import system. Note that failures in this step may indicate either that the module could not be located, *or* that an error occurred while initializing the module, which includes execution of the module’s code.

If the requested module is retrieved successfully, it will be made available in the local namespace in one of three ways:

- If the module name is followed by `as`, then the name following `as` is bound directly to the imported module.

- If no other name is specified, and the module being imported is a top level module, the module’s name is bound in the local namespace as a reference to the imported module

- If the module being imported is *not* a top level module, then the name of the top level package that contains the module is bound in the local namespace as a reference to the top level package. The imported module must be accessed using its full qualified name rather than directly

The [`from`](#simple_stmts--from) form uses a slightly more complex process:

1.  find the module specified in the [`from`](#simple_stmts--from) clause, loading and initializing it if necessary;

2.  for each of the identifiers specified in the [`import`](#simple_stmts--import) clauses:

    1.  check if the imported module has an attribute by that name

    2.  if not, attempt to import a submodule with that name and then check the imported module again for that attribute

    3.  if the attribute is not found, [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError) is raised.

    4.  otherwise, a reference to that value is stored in the current namespace, using the name in the `as` clause if it is present, otherwise using the attribute name

Examples:

    import foo                 # foo imported and bound locally
    import foo.bar.baz         # foo, foo.bar, and foo.bar.baz imported, foo bound locally
    import foo.bar.baz as fbb  # foo, foo.bar, and foo.bar.baz imported, foo.bar.baz bound as fbb
    from foo.bar import baz    # foo, foo.bar, and foo.bar.baz imported, foo.bar.baz bound as baz
    from foo import attr       # foo imported and foo.attr bound as attr

If the list of identifiers is replaced by a star (`'*'`), all public names defined in the module are bound in the local namespace for the scope where the [`import`](#simple_stmts--import) statement occurs.

<span id="simple_stmts--index-38"></span>The *public names* defined by a module are determined by checking the module’s namespace for a variable named `__all__`; if defined, it must be a sequence of strings which are names defined or imported by that module. Names containing non-ASCII characters must be in the [normalization form](https://www.unicode.org/reports/tr15/#Norm_Forms) NFKC; see [Non-ASCII characters in names](#lexical_analysis--lexical-names-nonascii) for details. The names given in `__all__` are all considered public and are required to exist. If `__all__` is not defined, the set of public names includes all names found in the module’s namespace which do not begin with an underscore character (`'_'`). `__all__` should contain the entire public API. It is intended to avoid accidentally exporting items that are not part of the API (such as library modules which were imported and used within the module).

The wild card form of import — `from module import *` — is only allowed at the module level. Attempting to use it in class or function definitions will raise a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError).

When specifying what module to import you do not have to specify the absolute name of the module. When a module or package is contained within another package it is possible to make a relative import within the same top package without having to mention the package name. By using leading dots in the specified module or package after [`from`](#simple_stmts--from) you can specify how high to traverse up the current package hierarchy without specifying exact names. One leading dot means the current package where the module making the import exists. Two dots means up one package level. Three dots is up two levels, etc. So if you execute `from . import mod` from a module in the `pkg` package then you will end up importing `pkg.mod`. If you execute `from ..subpkg2 import mod` from within `pkg.subpkg1` you will import `pkg.subpkg2.mod`. The specification for relative imports is contained in the [Package Relative Imports](#import--relativeimports) section.

[`importlib.import_module()`](https://docs.python.org/3/library/importlib.html#importlib.import_module) is provided to support applications that determine dynamically the modules to be loaded.

Raises an [auditing event](https://docs.python.org/3/library/sys.html#auditing) `import` with arguments `module`, `filename`, `sys.path`, `sys.meta_path`, `sys.path_hooks`.

<span id="simple_stmts--future"></span>

### 7.11.1. Future statements {#simple_stmts--future-statements}

A *future statement* is a directive to the compiler that a particular module should be compiled using syntax or semantics that will be available in a specified future release of Python where the feature becomes standard.

The future statement is intended to ease migration to future versions of Python that introduce incompatible changes to the language. It allows use of the new features on a per-module basis before the release in which the feature becomes standard.

    future_stmt: "from" "__future__" "import" feature ["as" identifier]
                 ("," feature ["as" identifier])*
                 | "from" "__future__" "import" "(" feature ["as" identifier]
                 ("," feature ["as" identifier])* [","] ")"
    feature:     identifier

A future statement must appear near the top of the module. The only lines that can appear before a future statement are:

- the module docstring (if any),

- comments,

- blank lines, and

- other future statements.

The only feature that requires using the future statement is `annotations` (see <span id="simple_stmts--index-41"></span>[**PEP 563**](https://peps.python.org/pep-0563/)).

All historical features enabled by the future statement are still recognized by Python 3. The list includes `absolute_import`, `division`, `generators`, `generator_stop`, `unicode_literals`, `print_function`, `nested_scopes` and `with_statement`. They are all redundant because they are always enabled, and only kept for backwards compatibility.

A future statement is recognized and treated specially at compile time: Changes to the semantics of core constructs are often implemented by generating different code. It may even be the case that a new feature introduces new incompatible syntax (such as a new reserved word), in which case the compiler may need to parse the module differently. Such decisions cannot be pushed off until runtime.

For any given release, the compiler knows which feature names have been defined, and raises a compile-time error if a future statement contains a feature not known to it.

The direct runtime semantics are the same as for any import statement: there is a standard module [`__future__`](https://docs.python.org/3/library/__future__.html#module-__future__), described later, and it will be imported in the usual way at the time the future statement is executed.

The interesting runtime semantics depend on the specific feature enabled by the future statement.

Note that there is nothing special about the statement:

    import __future__ [as name]

That is not a future statement; it’s an ordinary import statement with no special semantics or syntax restrictions.

Code compiled by calls to the built-in functions [`exec()`](https://docs.python.org/3/library/functions.html#exec) and [`compile()`](https://docs.python.org/3/library/functions.html#compile) that occur in a module `M` containing a future statement will, by default, use the new syntax or semantics associated with the future statement. This can be controlled by optional arguments to `compile()` — see the documentation of that function for details.

A future statement typed at an interactive interpreter prompt will take effect for the rest of the interpreter session. If an interpreter is started with the [`-i`](https://docs.python.org/3/using/cmdline.html#cmdoption-i) option, is passed a script name to execute, and the script includes a future statement, it will be in effect in the interactive session started after the script is executed.

See also

<span id="simple_stmts--index-42"></span>[**PEP 236**](https://peps.python.org/pep-0236/) - Back to the \_\_future\_\_  
The original proposal for the \_\_future\_\_ mechanism.

<span id="simple_stmts--global"></span>

## 7.12. The `global` statement {#simple_stmts--the-global-statement}

``` {#simple_stmts--index-43}
global_stmt: "global" identifier ("," identifier)*
```

The [`global`](#simple_stmts--global) statement causes the listed identifiers to be interpreted as globals. It would be impossible to assign to a global variable without `global`, although free variables may refer to globals without being declared global.

The `global` statement applies to the entire current scope (module, function body or class definition). A [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) is raised if a variable is used or assigned to prior to its global declaration in the scope.

At the module level, all variables are global, so a `global` statement has no effect. However, variables must still not be used or assigned to prior to their `global` declaration. This requirement is relaxed in the interactive prompt ([REPL](https://docs.python.org/3/glossary.html#term-REPL)).

**Programmer’s note:** [`global`](#simple_stmts--global) is a directive to the parser. It applies only to code parsed at the same time as the `global` statement. In particular, a `global` statement contained in a string or code object supplied to the built-in [`exec()`](https://docs.python.org/3/library/functions.html#exec) function does not affect the code block *containing* the function call, and code contained in such a string is unaffected by `global` statements in the code containing the function call. The same applies to the [`eval()`](https://docs.python.org/3/library/functions.html#eval) and [`compile()`](https://docs.python.org/3/library/functions.html#compile) functions.

<span id="simple_stmts--nonlocal"></span>

## 7.13. The `nonlocal` statement {#simple_stmts--the-nonlocal-statement}

``` {#simple_stmts--index-45}
nonlocal_stmt: "nonlocal" identifier ("," identifier)*
```

When the definition of a function or class is nested (enclosed) within the definitions of other functions, its nonlocal scopes are the local scopes of the enclosing functions. The [`nonlocal`](#simple_stmts--nonlocal) statement causes the listed identifiers to refer to names previously bound in nonlocal scopes. It allows encapsulated code to rebind such nonlocal identifiers. If a name is bound in more than one nonlocal scope, the nearest binding is used. If a name is not bound in any nonlocal scope, or if there is no nonlocal scope, a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) is raised.

The [`nonlocal`](#simple_stmts--nonlocal) statement applies to the entire scope of a function or class body. A [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) is raised if a variable is used or assigned to prior to its nonlocal declaration in the scope.

See also

<span id="simple_stmts--index-46"></span>[**PEP 3104**](https://peps.python.org/pep-3104/) - Access to Names in Outer Scopes  
The specification for the [`nonlocal`](#simple_stmts--nonlocal) statement.

**Programmer’s note:** [`nonlocal`](#simple_stmts--nonlocal) is a directive to the parser and applies only to code parsed along with it. See the note for the [`global`](#simple_stmts--global) statement.

<span id="simple_stmts--type"></span>

## 7.14. The `type` statement {#simple_stmts--the-type-statement}

``` {#simple_stmts--index-47}
type_stmt: 'type' identifier [type_params] "=" expression
```

The `type` statement declares a type alias, which is an instance of [`typing.TypeAliasType`](https://docs.python.org/3/library/typing.html#typing.TypeAliasType).

For example, the following statement creates a type alias:

    type Point = tuple[float, float]

This code is roughly equivalent to:

    annotation-def VALUE_OF_Point():
        return tuple[float, float]
    Point = typing.TypeAliasType("Point", VALUE_OF_Point())

`annotation-def` indicates an [annotation scope](#executionmodel--annotation-scopes), which behaves mostly like a function, but with several small differences.

The value of the type alias is evaluated in the annotation scope. It is not evaluated when the type alias is created, but only when the value is accessed through the type alias’s `__value__` attribute (see [Lazy evaluation](#executionmodel--lazy-evaluation)). This allows the type alias to refer to names that are not yet defined.

Type aliases may be made generic by adding a [type parameter list](#compound_stmts--type-params) after the name. See [Generic type aliases](#compound_stmts--generic-type-aliases) for more.

`type` is a [soft keyword](#lexical_analysis--soft-keywords).

Added in version 3.12.

See also

<span id="simple_stmts--index-48"></span>[**PEP 695**](https://peps.python.org/pep-0695/) - Type Parameter Syntax  
Introduced the `type` statement and syntax for generic classes and functions.

<span id="compound_stmts--compound"></span>

# 8. Compound statements {#compound_stmts--compound-statements}

Compound statements contain (groups of) other statements; they affect or control the execution of those other statements in some way. In general, compound statements span multiple lines, although in simple incarnations a whole compound statement may be contained in one line.

The [`if`](#compound_stmts--if), [`while`](#compound_stmts--while) and [`for`](#compound_stmts--for) statements implement traditional control flow constructs. [`try`](#compound_stmts--try) specifies exception handlers and/or cleanup code for a group of statements, while the [`with`](#compound_stmts--with) statement allows the execution of initialization and finalization code around a block of code. Function and class definitions are also syntactically compound statements.

A compound statement consists of one or more ‘clauses.’ A clause consists of a header and a ‘suite.’ The clause headers of a particular compound statement are all at the same indentation level. Each clause header begins with a uniquely identifying keyword and ends with a colon. A suite is a group of statements controlled by a clause. A suite can be one or more semicolon-separated simple statements on the same line as the header, following the header’s colon, or it can be one or more indented statements on subsequent lines. Only the latter form of a suite can contain nested compound statements; the following is illegal, mostly because it wouldn’t be clear to which [`if`](#compound_stmts--if) clause a following [`else`](#compound_stmts--else) clause would belong:

    if test1: if test2: print(x)

Also note that the semicolon binds tighter than the colon in this context, so that in the following example, either all or none of the [`print()`](https://docs.python.org/3/library/functions.html#print) calls are executed:

    if x < y < z: print(x); print(y); print(z)

Summarizing:

    compound_stmt: if_stmt
                   | while_stmt
                   | for_stmt
                   | try_stmt
                   | with_stmt
                   | match_stmt
                   | funcdef
                   | classdef
                   | async_with_stmt
                   | async_for_stmt
                   | async_funcdef
    suite:         stmt_list NEWLINE | NEWLINE INDENT statement+ DEDENT
    statement:     stmt_list NEWLINE | compound_stmt
    stmt_list:     simple_stmt (";" simple_stmt)* [";"]

Note that statements always end in a `NEWLINE` possibly followed by a `DEDENT`. Also note that optional continuation clauses always begin with a keyword that cannot start a statement, thus there are no ambiguities (the ‘dangling [`else`](#compound_stmts--else)’ problem is solved in Python by requiring nested [`if`](#compound_stmts--if) statements to be indented).

The formatting of the grammar rules in the following sections places each clause on a separate line for clarity.

<span id="compound_stmts--else"></span> <span id="compound_stmts--elif"></span> <span id="compound_stmts--if"></span>

## 8.1. The `if` statement {#compound_stmts--the-if-statement}

The [`if`](#compound_stmts--if) statement is used for conditional execution:

    if_stmt: "if" assignment_expression ":" suite
             ("elif" assignment_expression ":" suite)*
             ["else" ":" suite]

It selects exactly one of the suites by evaluating the expressions one by one until one is found to be true (see section [Boolean operations](#expressions--booleans) for the definition of true and false); then that suite is executed (and no other part of the [`if`](#compound_stmts--if) statement is executed or evaluated). If all expressions are false, the suite of the [`else`](#compound_stmts--else) clause, if present, is executed.

<span id="compound_stmts--while"></span>

## 8.2. The `while` statement {#compound_stmts--the-while-statement}

The [`while`](#compound_stmts--while) statement is used for repeated execution as long as an expression is true:

    while_stmt: "while" assignment_expression ":" suite
                ["else" ":" suite]

This repeatedly tests the expression and, if it is true, executes the first suite; if the expression is false (which may be the first time it is tested) the suite of the `else` clause, if present, is executed and the loop terminates.

A [`break`](#simple_stmts--break) statement executed in the first suite terminates the loop without executing the `else` clause’s suite. A [`continue`](#simple_stmts--continue) statement executed in the first suite skips the rest of the suite and goes back to testing the expression.

<span id="compound_stmts--for"></span>

## 8.3. The `for` statement {#compound_stmts--the-for-statement}

The [`for`](#compound_stmts--for) statement is used to iterate over the elements of a sequence (such as a string, tuple or list) or other iterable object:

    for_stmt: "for" target_list "in" starred_expression_list ":" suite
              ["else" ":" suite]

The [`starred_expression_list`](#expressions--grammar-token-python-grammar-starred_expression_list) expression is evaluated once; it should yield an [iterable](https://docs.python.org/3/glossary.html#term-iterable) object. An [iterator](https://docs.python.org/3/glossary.html#term-iterator) is created for that iterable. The first item provided by the iterator is then assigned to the target list using the standard rules for assignments (see [Assignment statements](#simple_stmts--assignment)), and the suite is executed. This repeats for each item provided by the iterator. When the iterator is [exhausted](https://docs.python.org/3/glossary.html#term-exhausted), the suite in the `else` clause, if present, is executed, and the loop terminates.

A [`break`](#simple_stmts--break) statement executed in the first suite terminates the loop without executing the `else` clause’s suite. A [`continue`](#simple_stmts--continue) statement executed in the first suite skips the rest of the suite and continues with the next item, or with the `else` clause if there is no next item.

The for-loop makes assignments to the variables in the target list. This overwrites all previous assignments to those variables including those made in the suite of the for-loop:

    for i in range(10):
        print(i)
        i = 5             # this will not affect the for-loop
                          # because i will be overwritten with the next
                          # index in the range

Names in the target list are not deleted when the loop is finished, but if the sequence is empty, they will not have been assigned to at all by the loop. Hint: the built-in type [`range()`](https://docs.python.org/3/library/stdtypes.html#range) represents immutable arithmetic sequences of integers. For instance, iterating `range(3)` successively yields 0, 1, and then 2.

Changed in version 3.11: Starred elements are now allowed in the expression list.

<span id="compound_stmts--try"></span>

## 8.4. The `try` statement {#compound_stmts--the-try-statement}

The `try` statement specifies exception handlers and/or cleanup code for a group of statements:

    try_stmt:  try1_stmt | try2_stmt | try3_stmt
    try1_stmt: "try" ":" suite
               ("except" [expression ["as" identifier]] ":" suite)+
               ["else" ":" suite]
               ["finally" ":" suite]
    try2_stmt: "try" ":" suite
               ("except" "*" expression ["as" identifier] ":" suite)+
               ["else" ":" suite]
               ["finally" ":" suite]
    try3_stmt: "try" ":" suite
               "finally" ":" suite

Additional information on exceptions can be found in section [Exceptions](#executionmodel--exceptions), and information on using the [`raise`](#simple_stmts--raise) statement to generate exceptions may be found in section [The raise statement](#simple_stmts--raise).

Changed in version 3.14: Support for optionally dropping grouping parentheses when using multiple exception types. See <span id="compound_stmts--index-10"></span>[**PEP 758**](https://peps.python.org/pep-0758/).

<span id="compound_stmts--except"></span>

### 8.4.1. `except` clause {#compound_stmts--except-clause}

The `except` clause(s) specify one or more exception handlers. When no exception occurs in the [`try`](#compound_stmts--try) clause, no exception handler is executed. When an exception occurs in the `try` suite, a search for an exception handler is started. This search inspects the `except` clauses in turn until one is found that matches the exception. An expression-less `except` clause, if present, must be last; it matches any exception.

For an `except` clause with an expression, the expression must evaluate to an exception type or a tuple of exception types. Parentheses can be dropped if multiple exception types are provided and the `as` clause is not used. The raised exception matches an `except` clause whose expression evaluates to the class or a [non-virtual base class](https://docs.python.org/3/glossary.html#term-abstract-base-class) of the exception object, or to a tuple that contains such a class.

If no `except` clause matches the exception, the search for an exception handler continues in the surrounding code and on the invocation stack. [\[1\]](#compound_stmts--id21){#compound_stmts--id1}

If the evaluation of an expression in the header of an `except` clause raises an exception, the original search for a handler is canceled and a search starts for the new exception in the surrounding code and on the call stack (it is treated as if the entire [`try`](#compound_stmts--try) statement raised the exception).

When a matching `except` clause is found, the exception is assigned to the target specified after the `as` keyword in that `except` clause, if present, and the `except` clause’s suite is executed. All `except` clauses must have an executable block. When the end of this block is reached, execution continues normally after the entire [`try`](#compound_stmts--try) statement. (This means that if two nested handlers exist for the same exception, and the exception occurs in the `try` clause of the inner handler, the outer handler will not handle the exception.)

When an exception has been assigned using `as target`, it is cleared at the end of the `except` clause. This is as if:

    except E as N:
        foo

was translated to:

    except E as N:
        try:
            foo
        finally:
            del N

This means the exception must be assigned to a different name to be able to refer to it after the `except` clause. Exceptions are cleared because with the traceback attached to them, they form a reference cycle with the stack frame, keeping all locals in that frame alive until the next garbage collection occurs.

Before an `except` clause’s suite is executed, the exception is stored in the [`sys`](https://docs.python.org/3/library/sys.html#module-sys) module, where it can be accessed from within the body of the `except` clause by calling [`sys.exception()`](https://docs.python.org/3/library/sys.html#sys.exception). When leaving an exception handler, the exception stored in the `sys` module is reset to its previous value:

    >>> print(sys.exception())
    None
    >>> try:
    ...     raise TypeError
    ... except:
    ...     print(repr(sys.exception()))
    ...     try:
    ...          raise ValueError
    ...     except:
    ...         print(repr(sys.exception()))
    ...     print(repr(sys.exception()))
    ...
    TypeError()
    ValueError()
    TypeError()
    >>> print(sys.exception())
    None

<span id="compound_stmts--index-13"></span> <span id="compound_stmts--id2"></span>

### 8.4.2. `except*` clause {#compound_stmts--except-star}

The `except*` clause(s) specify one or more handlers for groups of exceptions ([`BaseExceptionGroup`](https://docs.python.org/3/library/exceptions.html#BaseExceptionGroup) instances). A [`try`](#compound_stmts--try) statement can have either [`except`](#compound_stmts--except) or `except*` clauses, but not both. The exception type for matching is mandatory in the case of `except*`, so `except*:` is a syntax error. The type is interpreted as in the case of `except`, but matching is performed on the exceptions contained in the group that is being handled. A [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) is raised if a matching type is a subclass of `BaseExceptionGroup`, because that would have ambiguous semantics.

When an exception group is raised in the try block, each `except*` clause splits (see [`split()`](https://docs.python.org/3/library/exceptions.html#BaseExceptionGroup.split)) it into the subgroups of matching and non-matching exceptions. If the matching subgroup is not empty, it becomes the handled exception (the value returned from [`sys.exception()`](https://docs.python.org/3/library/sys.html#sys.exception)) and assigned to the target of the `except*` clause (if there is one). Then, the body of the `except*` clause executes. If the non-matching subgroup is not empty, it is processed by the next `except*` in the same manner. This continues until all exceptions in the group have been matched, or the last `except*` clause has run.

After all `except*` clauses execute, the group of unhandled exceptions is merged with any exceptions that were raised or re-raised from within `except*` clauses. This merged exception group propagates on:

    >>> try:
    ...     raise ExceptionGroup("eg",
    ...         [ValueError(1), TypeError(2), OSError(3), OSError(4)])
    ... except* TypeError as e:
    ...     print(f'caught {type(e)} with nested {e.exceptions}')
    ... except* OSError as e:
    ...     print(f'caught {type(e)} with nested {e.exceptions}')
    ...
    caught <class 'ExceptionGroup'> with nested (TypeError(2),)
    caught <class 'ExceptionGroup'> with nested (OSError(3), OSError(4))
      + Exception Group Traceback (most recent call last):
      |   File "<doctest default[0]>", line 2, in <module>
      |     raise ExceptionGroup("eg",
      |         [ValueError(1), TypeError(2), OSError(3), OSError(4)])
      | ExceptionGroup: eg (1 sub-exception)
      +-+---------------- 1 ----------------
        | ValueError: 1
        +------------------------------------

If the exception raised from the [`try`](#compound_stmts--try) block is not an exception group and its type matches one of the `except*` clauses, it is caught and wrapped by an exception group with an empty message string. This ensures that the type of the target `e` is consistently [`BaseExceptionGroup`](https://docs.python.org/3/library/exceptions.html#BaseExceptionGroup):

    >>> try:
    ...     raise BlockingIOError
    ... except* BlockingIOError as e:
    ...     print(repr(e))
    ...
    ExceptionGroup('', (BlockingIOError(),))

[`break`](#simple_stmts--break), [`continue`](#simple_stmts--continue) and [`return`](#simple_stmts--return) cannot appear in an `except*` clause.

<span id="compound_stmts--except-else"></span> <span id="compound_stmts--index-14"></span>

### 8.4.3. `else` clause {#compound_stmts--else-clause}

The optional `else` clause is executed if the control flow leaves the [`try`](#compound_stmts--try) suite, no exception was raised, and no [`return`](#simple_stmts--return), [`continue`](#simple_stmts--continue), or [`break`](#simple_stmts--break) statement was executed. Exceptions in the `else` clause are not handled by the preceding [`except`](#compound_stmts--except) clauses.

<span id="compound_stmts--finally"></span> <span id="compound_stmts--index-15"></span>

### 8.4.4. `finally` clause {#compound_stmts--finally-clause}

If `finally` is present, it specifies a ‘cleanup’ handler. The [`try`](#compound_stmts--try) clause is executed, including any [`except`](#compound_stmts--except) and [`else`](#compound_stmts--except-else) clauses. If an exception occurs in any of the clauses and is not handled, the exception is temporarily saved. The `finally` clause is executed. If there is a saved exception it is re-raised at the end of the `finally` clause. If the `finally` clause raises another exception, the saved exception is set as the context of the new exception. If the `finally` clause executes a [`return`](#simple_stmts--return), [`break`](#simple_stmts--break) or [`continue`](#simple_stmts--continue) statement, the saved exception is discarded. For example, this function returns 42.

    def f():
        try:
            1/0
        finally:
            return 42

The exception information is not available to the program during execution of the `finally` clause.

When a [`return`](#simple_stmts--return), [`break`](#simple_stmts--break) or [`continue`](#simple_stmts--continue) statement is executed in the [`try`](#compound_stmts--try) suite of a `try`…`finally` statement, the `finally` clause is also executed ‘on the way out.’

The return value of a function is determined by the last [`return`](#simple_stmts--return) statement executed. Since the `finally` clause always executes, a `return` statement executed in the `finally` clause will always be the last one executed. The following function returns ‘finally’.

    def foo():
        try:
            return 'try'
        finally:
            return 'finally'

Changed in version 3.8: Prior to Python 3.8, a [`continue`](#simple_stmts--continue) statement was illegal in the `finally` clause due to a problem with the implementation.

Changed in version 3.14: The compiler emits a [`SyntaxWarning`](https://docs.python.org/3/library/exceptions.html#SyntaxWarning) when a [`return`](#simple_stmts--return), [`break`](#simple_stmts--break) or [`continue`](#simple_stmts--continue) appears in a `finally` block (see <span id="compound_stmts--index-17"></span>[**PEP 765**](https://peps.python.org/pep-0765/)).

<span id="compound_stmts--as"></span> <span id="compound_stmts--with"></span>

## 8.5. The `with` statement {#compound_stmts--the-with-statement}

The [`with`](#compound_stmts--with) statement is used to wrap the execution of a block with methods defined by a context manager (see section [With Statement Context Managers](#datamodel--context-managers)). This allows common [`try`](#compound_stmts--try)…[`except`](#compound_stmts--except)…[`finally`](#compound_stmts--finally) usage patterns to be encapsulated for convenient reuse.

    with_stmt:          "with" ( "(" with_stmt_contents ","? ")" | with_stmt_contents ) ":" suite
    with_stmt_contents: with_item ("," with_item)*
    with_item:          expression ["as" target]

The execution of the [`with`](#compound_stmts--with) statement with one “item” proceeds as follows:

1.  The context expression (the expression given in the [`with_item`](#compound_stmts--grammar-token-python-grammar-with_item)) is evaluated to obtain a context manager.

2.  The context manager’s [`__enter__()`](#datamodel--object.__enter__) is loaded for later use.

3.  The context manager’s [`__exit__()`](#datamodel--object.__exit__) is loaded for later use.

4.  The context manager’s [`__enter__()`](#datamodel--object.__enter__) method is invoked.

5.  If a target was included in the [`with`](#compound_stmts--with) statement, the return value from [`__enter__()`](#datamodel--object.__enter__) is assigned to it.

    Note

    The [`with`](#compound_stmts--with) statement guarantees that if the [`__enter__()`](#datamodel--object.__enter__) method returns without an error, then [`__exit__()`](#datamodel--object.__exit__) will always be called. Thus, if an error occurs during the assignment to the target list, it will be treated the same as an error occurring within the suite would be. See step 7 below.

6.  The suite is executed.

7.  The context manager’s [`__exit__()`](#datamodel--object.__exit__) method is invoked. If an exception caused the suite to be exited, its type, value, and traceback are passed as arguments to `__exit__()`. Otherwise, three [`None`](https://docs.python.org/3/library/constants.html#None) arguments are supplied.

    If the suite was exited due to an exception, and the return value from the [`__exit__()`](#datamodel--object.__exit__) method was false, the exception is reraised. If the return value was true, the exception is suppressed, and execution continues with the statement following the [`with`](#compound_stmts--with) statement.

    If the suite was exited for any reason other than an exception, the return value from [`__exit__()`](#datamodel--object.__exit__) is ignored, and execution proceeds at the normal location for the kind of exit that was taken.

The following code:

    with EXPRESSION as TARGET:
        SUITE

is semantically equivalent to:

    manager = (EXPRESSION)
    enter = manager.__enter__
    exit = manager.__exit__
    value = enter()
    hit_except = False

    try:
        TARGET = value
        SUITE
    except:
        hit_except = True
        if not exit(*sys.exc_info()):
            raise
    finally:
        if not hit_except:
            exit(None, None, None)

except that implicit [special method lookup](#datamodel--special-lookup) is used for [`__enter__()`](#datamodel--object.__enter__) and [`__exit__()`](#datamodel--object.__exit__).

With more than one item, the context managers are processed as if multiple [`with`](#compound_stmts--with) statements were nested:

    with A() as a, B() as b:
        SUITE

is semantically equivalent to:

    with A() as a:
        with B() as b:
            SUITE

You can also write multi-item context managers in multiple lines if the items are surrounded by parentheses. For example:

    with (
        A() as a,
        B() as b,
    ):
        SUITE

Changed in version 3.1: Support for multiple context expressions.

Changed in version 3.10: Support for using grouping parentheses to break the statement in multiple lines.

See also

<span id="compound_stmts--index-19"></span>[**PEP 343**](https://peps.python.org/pep-0343/) - The “with” statement  
The specification, background, and examples for the Python [`with`](#compound_stmts--with) statement.

<span id="compound_stmts--case"></span> <span id="compound_stmts--match"></span>

## 8.6. The `match` statement {#compound_stmts--the-match-statement}

Added in version 3.10.

The match statement is used for pattern matching. Syntax:

    match_stmt:   'match' subject_expr ":" NEWLINE INDENT case_block+ DEDENT
    subject_expr: flexible_expression "," [flexible_expression_list [',']]
                  | assignment_expression
    case_block:   'case' patterns [guard] ":" suite

Note

This section uses single quotes to denote [soft keywords](#lexical_analysis--soft-keywords).

Pattern matching takes a pattern as input (following `case`) and a subject value (following `match`). The pattern (which may contain subpatterns) is matched against the subject value. The outcomes are:

- A match success or failure (also termed a pattern success or failure).

- Possible binding of matched values to a name. The prerequisites for this are further discussed below.

The `match` and `case` keywords are [soft keywords](#lexical_analysis--soft-keywords).

See also

- <span id="compound_stmts--index-21"></span>[**PEP 634**](https://peps.python.org/pep-0634/) – Structural Pattern Matching: Specification

- <span id="compound_stmts--index-22"></span>[**PEP 636**](https://peps.python.org/pep-0636/) – Structural Pattern Matching: Tutorial

### 8.6.1. Overview {#compound_stmts--overview}

Here’s an overview of the logical flow of a match statement:

1.  The subject expression `subject_expr` is evaluated and a resulting subject value obtained. If the subject expression contains a comma, a tuple is constructed using [the standard rules](https://docs.python.org/3/library/stdtypes.html#typesseq-tuple).

2.  Each pattern in a `case_block` is attempted to match with the subject value. The specific rules for success or failure are described below. The match attempt can also bind some or all of the standalone names within the pattern. The precise pattern binding rules vary per pattern type and are specified below. **Name bindings made during a successful pattern match outlive the executed block and can be used after the match statement**.

    Note

    During failed pattern matches, some subpatterns may succeed. Do not rely on bindings being made for a failed match. Conversely, do not rely on variables remaining unchanged after a failed match. The exact behavior is dependent on implementation and may vary. This is an intentional decision made to allow different implementations to add optimizations.

3.  If the pattern succeeds, the corresponding guard (if present) is evaluated. In this case all name bindings are guaranteed to have happened.

    - If the guard evaluates as true or is missing, the `block` inside `case_block` is executed.

    - Otherwise, the next `case_block` is attempted as described above.

    - If there are no further case blocks, the match statement is completed.

Note

Users should generally never rely on a pattern being evaluated. Depending on implementation, the interpreter may cache values or use other optimizations which skip repeated evaluations.

A sample match statement:

    >>> flag = False
    >>> match (100, 200):
    ...    case (100, 300):  # Mismatch: 200 != 300
    ...        print('Case 1')
    ...    case (100, 200) if flag:  # Successful match, but guard fails
    ...        print('Case 2')
    ...    case (100, y):  # Matches and binds y to 200
    ...        print(f'Case 3, y: {y}')
    ...    case _:  # Pattern not attempted
    ...        print('Case 4, I match anything!')
    ...
    Case 3, y: 200

In this case, `if flag` is a guard. Read more about that in the next section.

### 8.6.2. Guards {#compound_stmts--guards}

``` {#compound_stmts--index-23}
guard: "if" assignment_expression
```

A `guard` (which is part of the `case`) must succeed for code inside the `case` block to execute. It takes the form: [`if`](#compound_stmts--if) followed by an expression.

The logical flow of a `case` block with a `guard` follows:

1.  Check that the pattern in the `case` block succeeded. If the pattern failed, the `guard` is not evaluated and the next `case` block is checked.

2.  If the pattern succeeded, evaluate the `guard`.

    - If the `guard` condition evaluates as true, the case block is selected.

    - If the `guard` condition evaluates as false, the case block is not selected.

    - If the `guard` raises an exception during evaluation, the exception bubbles up.

Guards are allowed to have side effects as they are expressions. Guard evaluation must proceed from the first to the last case block, one at a time, skipping case blocks whose pattern(s) don’t all succeed. (I.e., guard evaluation must happen in order.) Guard evaluation must stop once a case block is selected.

<span id="compound_stmts--irrefutable-case"></span>

### 8.6.3. Irrefutable Case Blocks {#compound_stmts--irrefutable-case-blocks}

An irrefutable case block is a match-all case block. A match statement may have at most one irrefutable case block, and it must be last.

A case block is considered irrefutable if it has no guard and its pattern is irrefutable. A pattern is considered irrefutable if we can prove from its syntax alone that it will always succeed. Only the following patterns are irrefutable:

- [AS Patterns](#compound_stmts--as-patterns) whose left-hand side is irrefutable

- [OR Patterns](#compound_stmts--or-patterns) containing at least one irrefutable pattern

- [Capture Patterns](#compound_stmts--capture-patterns)

- [Wildcard Patterns](#compound_stmts--wildcard-patterns)

- parenthesized irrefutable patterns

### 8.6.4. Patterns {#compound_stmts--patterns}

Note

This section uses grammar notations beyond standard EBNF:

- the notation `SEP.RULE+` is shorthand for `RULE (SEP RULE)*`

- the notation `!RULE` is shorthand for a negative lookahead assertion

The top-level syntax for `patterns` is:

    patterns:       open_sequence_pattern | pattern
    pattern:        as_pattern | or_pattern
    closed_pattern: | literal_pattern
                    | capture_pattern
                    | wildcard_pattern
                    | value_pattern
                    | group_pattern
                    | sequence_pattern
                    | mapping_pattern
                    | class_pattern

The descriptions below will include a description “in simple terms” of what a pattern does for illustration purposes (credits to Raymond Hettinger for a document that inspired most of the descriptions). Note that these descriptions are purely for illustration purposes and **may not** reflect the underlying implementation. Furthermore, they do not cover all valid forms.

<span id="compound_stmts--id3"></span>

#### 8.6.4.1. OR Patterns {#compound_stmts--or-patterns}

An OR pattern is two or more patterns separated by vertical bars `|`. Syntax:

    or_pattern: "|".closed_pattern+

Only the final subpattern may be [irrefutable](#compound_stmts--irrefutable-case), and each subpattern must bind the same set of names to avoid ambiguity.

An OR pattern matches each of its subpatterns in turn to the subject value, until one succeeds. The OR pattern is then considered successful. Otherwise, if none of the subpatterns succeed, the OR pattern fails.

In simple terms, `P1 | P2 | ...` will try to match `P1`, if it fails it will try to match `P2`, succeeding immediately if any succeeds, failing otherwise.

<span id="compound_stmts--id4"></span>

#### 8.6.4.2. AS Patterns {#compound_stmts--as-patterns}

An AS pattern matches an OR pattern on the left of the [`as`](#compound_stmts--as) keyword against a subject. Syntax:

    as_pattern: or_pattern "as" capture_pattern

If the OR pattern fails, the AS pattern fails. Otherwise, the AS pattern binds the subject to the name on the right of the as keyword and succeeds. `capture_pattern` cannot be a `_`.

In simple terms `P as NAME` will match with `P`, and on success it will set `NAME = <subject>`.

<span id="compound_stmts--id5"></span>

#### 8.6.4.3. Literal Patterns {#compound_stmts--literal-patterns}

A literal pattern corresponds to most [literals](#lexical_analysis--literals) in Python. Syntax:

    literal_pattern: signed_number
                     | signed_number "+" NUMBER
                     | signed_number "-" NUMBER
                     | strings
                     | "None"
                     | "True"
                     | "False"
    signed_number:   ["-"] NUMBER

The rule `strings` and the token `NUMBER` are defined in the [standard Python grammar](#grammar--full-grammar-specification). Triple-quoted strings are supported. Raw strings and byte strings are supported. [f-strings](#lexical_analysis--f-strings) and [t-strings](#lexical_analysis--t-strings) are not supported.

The forms `signed_number '+' NUMBER` and `signed_number '-' NUMBER` are for expressing [complex numbers](#lexical_analysis--imaginary); they require a real number on the left and an imaginary number on the right. E.g. `3 + 4j`.

In simple terms, `LITERAL` will succeed only if `<subject> == LITERAL`. For the singletons `None`, `True` and `False`, the [`is`](#expressions--is) operator is used.

<span id="compound_stmts--id6"></span>

#### 8.6.4.4. Capture Patterns {#compound_stmts--capture-patterns}

A capture pattern binds the subject value to a name. Syntax:

    capture_pattern: !'_' NAME

A single underscore `_` is not a capture pattern (this is what `!'_'` expresses). It is instead treated as a [`wildcard_pattern`](#compound_stmts--grammar-token-python-grammar-wildcard_pattern).

In a given pattern, a given name can only be bound once. E.g. `case x, x: ...` is invalid while `case [x] | x: ...` is allowed.

Capture patterns always succeed. The binding follows scoping rules established by the assignment expression operator in <span id="compound_stmts--index-26"></span>[**PEP 572**](https://peps.python.org/pep-0572/); the name becomes a local variable in the closest containing function scope unless there’s an applicable [`global`](#simple_stmts--global) or [`nonlocal`](#simple_stmts--nonlocal) statement.

In simple terms `NAME` will always succeed and it will set `NAME = <subject>`.

<span id="compound_stmts--id7"></span>

#### 8.6.4.5. Wildcard Patterns {#compound_stmts--wildcard-patterns}

A wildcard pattern always succeeds (matches anything) and binds no name. Syntax:

    wildcard_pattern: '_'

`_` is a [soft keyword](#lexical_analysis--soft-keywords) within any pattern, but only within patterns. It is an identifier, as usual, even within `match` subject expressions, `guard`s, and `case` blocks.

In simple terms, `_` will always succeed.

<span id="compound_stmts--id8"></span>

#### 8.6.4.6. Value Patterns {#compound_stmts--value-patterns}

A value pattern represents a named value in Python. Syntax:

    value_pattern: attr
    attr:          name_or_attr "." NAME
    name_or_attr:  attr | NAME

The dotted name in the pattern is looked up using standard Python [name resolution rules](#executionmodel--resolve-names). The pattern succeeds if the value found compares equal to the subject value (using the `==` equality operator).

In simple terms `NAME1.NAME2` will succeed only if `<subject> == NAME1.NAME2`

Note

If the same value occurs multiple times in the same match statement, the interpreter may cache the first value found and reuse it rather than repeat the same lookup. This cache is strictly tied to a given execution of a given match statement.

<span id="compound_stmts--id9"></span>

#### 8.6.4.7. Group Patterns {#compound_stmts--group-patterns}

A group pattern allows users to add parentheses around patterns to emphasize the intended grouping. Otherwise, it has no additional syntax. Syntax:

    group_pattern: "(" pattern ")"

In simple terms `(P)` has the same effect as `P`.

<span id="compound_stmts--id10"></span>

#### 8.6.4.8. Sequence Patterns {#compound_stmts--sequence-patterns}

A sequence pattern contains several subpatterns to be matched against sequence elements. The syntax is similar to the unpacking of a list or tuple.

    sequence_pattern:       "[" [maybe_sequence_pattern] "]"
                            | "(" [open_sequence_pattern] ")"
    open_sequence_pattern:  maybe_star_pattern "," [maybe_sequence_pattern]
    maybe_sequence_pattern: ",".maybe_star_pattern+ ","?
    maybe_star_pattern:     star_pattern | pattern
    star_pattern:           "*" (capture_pattern | wildcard_pattern)

There is no difference if parentheses or square brackets are used for sequence patterns (i.e. `(...)` vs `[...]` ).

Note

A single pattern enclosed in parentheses without a trailing comma (e.g. `(3 | 4)`) is a [group pattern](#compound_stmts--group-patterns). While a single pattern enclosed in square brackets (e.g. `[3 | 4]`) is still a sequence pattern.

At most one star subpattern may be in a sequence pattern. The star subpattern may occur in any position. If no star subpattern is present, the sequence pattern is a fixed-length sequence pattern; otherwise it is a variable-length sequence pattern.

The following is the logical flow for matching a sequence pattern against a subject value:

1.  If the subject value is not a sequence [\[2\]](#compound_stmts--id22){#compound_stmts--id11}, the sequence pattern fails.

2.  If the subject value is an instance of `str`, `bytes` or `bytearray` the sequence pattern fails.

3.  The subsequent steps depend on whether the sequence pattern is fixed or variable-length.

    If the sequence pattern is fixed-length:

    1.  If the length of the subject sequence is not equal to the number of subpatterns, the sequence pattern fails

    2.  Subpatterns in the sequence pattern are matched to their corresponding items in the subject sequence from left to right. Matching stops as soon as a subpattern fails. If all subpatterns succeed in matching their corresponding item, the sequence pattern succeeds.

    Otherwise, if the sequence pattern is variable-length:

    1.  If the length of the subject sequence is less than the number of non-star subpatterns, the sequence pattern fails.

    2.  The leading non-star subpatterns are matched to their corresponding items as for fixed-length sequences.

    3.  If the previous step succeeds, the star subpattern matches a list formed of the remaining subject items, excluding the remaining items corresponding to non-star subpatterns following the star subpattern.

    4.  Remaining non-star subpatterns are matched to their corresponding subject items, as for a fixed-length sequence.

    Note

    The length of the subject sequence is obtained via [`len()`](https://docs.python.org/3/library/functions.html#len) (i.e. via the [`__len__()`](#datamodel--object.__len__) protocol). This length may be cached by the interpreter in a similar manner as [value patterns](#compound_stmts--value-patterns).

In simple terms `[P1, P2, P3,` … `, P<N>]` matches only if all the following happens:

- check `<subject>` is a sequence

- `len(subject) == <N>`

- `P1` matches `<subject>[0]` (note that this match can also bind names)

- `P2` matches `<subject>[1]` (note that this match can also bind names)

- … and so on for the corresponding pattern/element.

<span id="compound_stmts--id12"></span>

#### 8.6.4.9. Mapping Patterns {#compound_stmts--mapping-patterns}

A mapping pattern contains one or more key-value patterns. The syntax is similar to the construction of a dictionary. Syntax:

    mapping_pattern:     "{" [items_pattern] "}"
    items_pattern:       ",".key_value_pattern+ ","?
    key_value_pattern:   (literal_pattern | value_pattern) ":" pattern
                         | double_star_pattern
    double_star_pattern: "**" capture_pattern

At most one double star pattern may be in a mapping pattern. The double star pattern must be the last subpattern in the mapping pattern.

Duplicate keys in mapping patterns are disallowed. Duplicate literal keys will raise a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError). Two keys that otherwise have the same value will raise a [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError) at runtime.

The following is the logical flow for matching a mapping pattern against a subject value:

1.  If the subject value is not a mapping [\[3\]](#compound_stmts--id23){#compound_stmts--id13},the mapping pattern fails.

2.  If every key given in the mapping pattern is present in the subject mapping, and the pattern for each key matches the corresponding item of the subject mapping, the mapping pattern succeeds.

3.  If duplicate keys are detected in the mapping pattern, the pattern is considered invalid. A [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) is raised for duplicate literal values; or a [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError) for named keys of the same value.

Note

Key-value pairs are matched using the two-argument form of the mapping subject’s `get()` method. Matched key-value pairs must already be present in the mapping, and not created on-the-fly via [`__missing__()`](#datamodel--object.__missing__) or [`__getitem__()`](#datamodel--object.__getitem__).

In simple terms `{KEY1: P1, KEY2: P2, ... }` matches only if all the following happens:

- check `<subject>` is a mapping

- `KEY1 in <subject>`

- `P1` matches `<subject>[KEY1]`

- … and so on for the corresponding KEY/pattern pair.

<span id="compound_stmts--id14"></span>

#### 8.6.4.10. Class Patterns {#compound_stmts--class-patterns}

A class pattern represents a class and its positional and keyword arguments (if any). Syntax:

    class_pattern:       name_or_attr "(" [pattern_arguments ","?] ")"
    pattern_arguments:   positional_patterns ["," keyword_patterns]
                         | keyword_patterns
    positional_patterns: ",".pattern+
    keyword_patterns:    ",".keyword_pattern+
    keyword_pattern:     NAME "=" pattern

The same keyword should not be repeated in class patterns.

The following is the logical flow for matching a class pattern against a subject value:

1.  If `name_or_attr` is not an instance of the builtin [`type`](https://docs.python.org/3/library/functions.html#type) , raise [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError).

2.  If the subject value is not an instance of `name_or_attr` (tested via [`isinstance()`](https://docs.python.org/3/library/functions.html#isinstance)), the class pattern fails.

3.  If no pattern arguments are present, the pattern succeeds. Otherwise, the subsequent steps depend on whether keyword or positional argument patterns are present.

    For a number of built-in types (specified below), a single positional subpattern is accepted which will match the entire subject; for these types keyword patterns also work as for other types.

    If only keyword patterns are present, they are processed as follows, one by one:

    1.  The keyword is looked up as an attribute on the subject.

        - If this raises an exception other than [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError), the exception bubbles up.

        - If this raises [`AttributeError`](https://docs.python.org/3/library/exceptions.html#AttributeError), the class pattern has failed.

        - Else, the subpattern associated with the keyword pattern is matched against the subject’s attribute value. If this fails, the class pattern fails; if this succeeds, the match proceeds to the next keyword.

    2.  If all keyword patterns succeed, the class pattern succeeds.

    If any positional patterns are present, they are converted to keyword patterns using the [`__match_args__`](#datamodel--object.__match_args__) attribute on the class `name_or_attr` before matching:

    1.  The equivalent of `getattr(cls, "__match_args__", ())` is called.

        - If this raises an exception, the exception bubbles up.

        - If the returned value is not a tuple, the conversion fails and [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) is raised.

        - If there are more positional patterns than `len(cls.__match_args__)`, [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) is raised.

        - Otherwise, positional pattern `i` is converted to a keyword pattern using `__match_args__[i]` as the keyword. `__match_args__[i]` must be a string; if not [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) is raised.

        - If there are duplicate keywords, [`TypeError`](https://docs.python.org/3/library/exceptions.html#TypeError) is raised.

        See also

        [Customizing positional arguments in class pattern matching](#datamodel--class-pattern-matching)

    2.  Once all positional patterns have been converted to keyword patterns, the match proceeds as if there were only keyword patterns.

    For the following built-in types the handling of positional subpatterns is different:

    - [`bool`](https://docs.python.org/3/library/functions.html#bool)

    - [`bytearray`](https://docs.python.org/3/library/stdtypes.html#bytearray)

    - [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes)

    - [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

    - [`float`](https://docs.python.org/3/library/functions.html#float)

    - [`frozenset`](https://docs.python.org/3/library/stdtypes.html#frozenset)

    - [`int`](https://docs.python.org/3/library/functions.html#int)

    - [`list`](https://docs.python.org/3/library/stdtypes.html#list)

    - [`set`](https://docs.python.org/3/library/stdtypes.html#set)

    - [`str`](https://docs.python.org/3/library/stdtypes.html#str)

    - [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)

    These classes accept a single positional argument, and the pattern there is matched against the whole object rather than an attribute. For example `int(0|1)` matches the value `0`, but not the value `0.0`.

In simple terms `CLS(P1, attr=P2)` matches only if the following happens:

- `isinstance(<subject>, CLS)`

- convert `P1` to a keyword pattern using `CLS.__match_args__`

- For each keyword argument `attr=P2`:

  - `hasattr(<subject>, "attr")`

  - `P2` matches `<subject>.attr`

- … and so on for the corresponding keyword argument/pattern pair.

See also

- <span id="compound_stmts--index-27"></span>[**PEP 634**](https://peps.python.org/pep-0634/) – Structural Pattern Matching: Specification

- <span id="compound_stmts--index-28"></span>[**PEP 636**](https://peps.python.org/pep-0636/) – Structural Pattern Matching: Tutorial

<span id="compound_stmts--def"></span> <span id="compound_stmts--function"></span> <span id="compound_stmts--index-29"></span>

## 8.7. Function definitions {#compound_stmts--function-definitions}

A function definition defines a user-defined function object (see section [The standard type hierarchy](#datamodel--types)):

    funcdef:                   [decorators] "def" funcname [type_params] "(" [parameter_list] ")"
                               ["->" expression] ":" suite
    decorators:                decorator+
    decorator:                 "@" assignment_expression NEWLINE
    parameter_list:            defparameter ("," defparameter)* "," "/" ["," [parameter_list_no_posonly]]
                                 | parameter_list_no_posonly
    parameter_list_no_posonly: defparameter ("," defparameter)* ["," [parameter_list_starargs]]
                               | parameter_list_starargs
    parameter_list_starargs:   "*" star_parameter ("," defparameter)* ["," [parameter_star_kwargs]]
                               | "*" ("," defparameter)+ ["," [parameter_star_kwargs]]
                               | parameter_star_kwargs
    parameter_star_kwargs:     "**" parameter [","]
    parameter:                 identifier [":" expression]
    star_parameter:            identifier [":" ["*"] expression]
    defparameter:              parameter ["=" expression]
    funcname:                  identifier

A function definition is an executable statement. Its execution binds the function name in the current local namespace to a function object (a wrapper around the executable code for the function). This function object contains a reference to the current global namespace as the global namespace to be used when the function is called.

The function definition does not execute the function body; this gets executed only when the function is called. [\[4\]](#compound_stmts--id24){#compound_stmts--id15}

A function definition may be wrapped by one or more [decorator](https://docs.python.org/3/glossary.html#term-decorator) expressions. Decorator expressions are evaluated when the function is defined, in the scope that contains the function definition. The result must be a callable, which is invoked with the function object as the only argument. The returned value is bound to the function name instead of the function object. Multiple decorators are applied in nested fashion. For example, the following code

    @f1(arg)
    @f2
    def func(): pass

is roughly equivalent to

    def func(): pass
    func = f1(arg)(f2(func))

except that the original function is not temporarily bound to the name `func`.

Changed in version 3.9: Functions may be decorated with any valid [`assignment_expression`](#expressions--grammar-token-python-grammar-assignment_expression). Previously, the grammar was much more restrictive; see <span id="compound_stmts--index-32"></span>[**PEP 614**](https://peps.python.org/pep-0614/) for details.

A list of [type parameters](#compound_stmts--type-params) may be given in square brackets between the function’s name and the opening parenthesis for its parameter list. This indicates to static type checkers that the function is generic. At runtime, the type parameters can be retrieved from the function’s [`__type_params__`](#datamodel--function.__type_params__) attribute. See [Generic functions](#compound_stmts--generic-functions) for more.

Changed in version 3.12: Type parameter lists are new in Python 3.12.

When one or more [parameters](https://docs.python.org/3/glossary.html#term-parameter) have the form *parameter* `=` *expression*, the function is said to have “default parameter values.” For a parameter with a default value, the corresponding [argument](https://docs.python.org/3/glossary.html#term-argument) may be omitted from a call, in which case the parameter’s default value is substituted. If a parameter has a default value, all following parameters up until the “`*`” must also have a default value — this is a syntactic restriction that is not expressed by the grammar.

**Default parameter values are evaluated from left to right when the function definition is executed.** This means that the expression is evaluated once, when the function is defined, and that the same “pre-computed” value is used for each call. This is especially important to understand when a default parameter value is a mutable object, such as a list or a dictionary: if the function modifies the object (e.g. by appending an item to a list), the default parameter value is in effect modified. This is generally not what was intended. A way around this is to use `None` as the default, and explicitly test for it in the body of the function, for example:

    def whats_on_the_telly(penguin=None):
        if penguin is None:
            penguin = []
        penguin.append("property of the zoo")
        return penguin

Function call semantics are described in more detail in section [Calls](#expressions--calls). A function call always assigns values to all parameters mentioned in the parameter list, either from positional arguments, from keyword arguments, or from default values. If the form “`*identifier`” is present, it is initialized to a tuple receiving any excess positional parameters, defaulting to the empty tuple. If the form “`**identifier`” is present, it is initialized to a new ordered mapping receiving any excess keyword arguments, defaulting to a new empty mapping of the same type. Parameters after “`*`” or “`*identifier`” are keyword-only parameters and may only be passed by keyword arguments. Parameters before “`/`” are positional-only parameters and may only be passed by positional arguments.

Changed in version 3.8: The `/` function parameter syntax may be used to indicate positional-only parameters. See <span id="compound_stmts--index-35"></span>[**PEP 570**](https://peps.python.org/pep-0570/) for details.

Parameters may have an [annotation](https://docs.python.org/3/glossary.html#term-function-annotation) of the form “`: expression`” following the parameter name. Any parameter may have an annotation, even those of the form `*identifier` or `**identifier`. (As a special case, parameters of the form `*identifier` may have an annotation “`: *expression`”.) Functions may have “return” annotation of the form “`-> expression`” after the parameter list. These annotations can be any valid Python expression. The presence of annotations does not change the semantics of a function. See [Annotations](#compound_stmts--annotations) for more information on annotations.

Changed in version 3.11: Parameters of the form “`*identifier`” may have an annotation “`: *expression`”. See <span id="compound_stmts--index-37"></span>[**PEP 646**](https://peps.python.org/pep-0646/).

It is also possible to create anonymous functions (functions not bound to a name), for immediate use in expressions. This uses lambda expressions, described in section [Lambdas](#expressions--lambda). Note that the lambda expression is merely a shorthand for a simplified function definition; a function defined in a “[`def`](#compound_stmts--def)” statement can be passed around or assigned to another name just like a function defined by a lambda expression. The “`def`” form is actually more powerful since it allows the execution of multiple statements and annotations.

**Programmer’s note:** Functions are first-class objects. A “`def`” statement executed inside a function definition defines a local function that can be returned or passed around. Free variables used in the nested function can access the local variables of the function containing the def. See section [Naming and binding](#executionmodel--naming) for details.

See also

<span id="compound_stmts--index-39"></span>[**PEP 3107**](https://peps.python.org/pep-3107/) - Function Annotations  
The original specification for function annotations.

<span id="compound_stmts--index-40"></span>[**PEP 484**](https://peps.python.org/pep-0484/) - Type Hints  
Definition of a standard meaning for annotations: type hints.

<span id="compound_stmts--index-41"></span>[**PEP 526**](https://peps.python.org/pep-0526/) - Syntax for Variable Annotations  
Ability to type hint variable declarations, including class variables and instance variables.

<span id="compound_stmts--index-42"></span>[**PEP 563**](https://peps.python.org/pep-0563/) - Postponed Evaluation of Annotations  
Support for forward references within annotations by preserving annotations in a string form at runtime instead of eager evaluation.

<span id="compound_stmts--index-43"></span>[**PEP 318**](https://peps.python.org/pep-0318/) - Decorators for Functions and Methods  
Function and method decorators were introduced. Class decorators were introduced in <span id="compound_stmts--index-44"></span>[**PEP 3129**](https://peps.python.org/pep-3129/).

<span id="compound_stmts--class"></span>

## 8.8. Class definitions {#compound_stmts--class-definitions}

A class definition defines a class object (see section [The standard type hierarchy](#datamodel--types)):

    classdef:    [decorators] "class" classname [type_params] [inheritance] ":" suite
    inheritance: "(" [argument_list] ")"
    classname:   identifier

A class definition is an executable statement. The inheritance list usually gives a list of base classes (see [Metaclasses](#datamodel--metaclasses) for more advanced uses), so each item in the list should evaluate to a class object which allows subclassing. Classes without an inheritance list inherit, by default, from the base class [`object`](https://docs.python.org/3/library/functions.html#object); hence,

    class Foo:
        pass

is equivalent to

    class Foo(object):
        pass

The class’s suite is then executed in a new execution frame (see [Naming and binding](#executionmodel--naming)), using a newly created local namespace and the original global namespace. (Usually, the suite contains mostly function definitions.) When the class’s suite finishes execution, its execution frame is discarded but its local namespace is saved. [\[5\]](#compound_stmts--id25){#compound_stmts--id16} A class object is then created using the inheritance list for the base classes and the saved local namespace for the attribute dictionary. The class name is bound to this class object in the original local namespace.

The order in which attributes are defined in the class body is preserved in the new class’s [`__dict__`](#datamodel--type.__dict__). Note that this is reliable only right after the class is created and only for classes that were defined using the definition syntax.

Class creation can be customized heavily using [metaclasses](#datamodel--metaclasses).

Classes can also be decorated: just like when decorating functions,

    @f1(arg)
    @f2
    class Foo: pass

is roughly equivalent to

    class Foo: pass
    Foo = f1(arg)(f2(Foo))

The evaluation rules for the decorator expressions are the same as for function decorators. The result is then bound to the class name.

Changed in version 3.9: Classes may be decorated with any valid [`assignment_expression`](#expressions--grammar-token-python-grammar-assignment_expression). Previously, the grammar was much more restrictive; see <span id="compound_stmts--index-47"></span>[**PEP 614**](https://peps.python.org/pep-0614/) for details.

A list of [type parameters](#compound_stmts--type-params) may be given in square brackets immediately after the class’s name. This indicates to static type checkers that the class is generic. At runtime, the type parameters can be retrieved from the class’s [`__type_params__`](#datamodel--type.__type_params__) attribute. See [Generic classes](#compound_stmts--generic-classes) for more.

Changed in version 3.12: Type parameter lists are new in Python 3.12.

**Programmer’s note:** Variables defined in the class definition are class attributes; they are shared by instances. Instance attributes can be set in a method with `self.name = value`. Both class and instance attributes are accessible through the notation “`self.name`”, and an instance attribute hides a class attribute with the same name when accessed in this way. Class attributes can be used as defaults for instance attributes, but using mutable values there can lead to unexpected results. [Descriptors](#datamodel--descriptors) can be used to create instance variables with different implementation details.

See also

<span id="compound_stmts--index-48"></span>[**PEP 3115**](https://peps.python.org/pep-3115/) - Metaclasses in Python 3000  
The proposal that changed the declaration of metaclasses to the current syntax, and the semantics for how classes with metaclasses are constructed.

<span id="compound_stmts--index-49"></span>[**PEP 3129**](https://peps.python.org/pep-3129/) - Class Decorators  
The proposal that added class decorators. Function and method decorators were introduced in <span id="compound_stmts--index-50"></span>[**PEP 318**](https://peps.python.org/pep-0318/).

<span id="compound_stmts--async"></span>

## 8.9. Coroutines {#compound_stmts--coroutines}

Added in version 3.5.

<span id="compound_stmts--async-def"></span> <span id="compound_stmts--index-51"></span>

### 8.9.1. Coroutine function definition {#compound_stmts--coroutine-function-definition}

    async_funcdef: [decorators] "async" "def" funcname "(" [parameter_list] ")"
                   ["->" expression] ":" suite

Execution of Python coroutines can be suspended and resumed at many points (see [coroutine](https://docs.python.org/3/glossary.html#term-coroutine)). [`await`](#expressions--await) expressions, [`async for`](#compound_stmts--async-for) and [`async with`](#compound_stmts--async-with) can only be used in the body of a coroutine function.

Functions defined with `async def` syntax are always coroutine functions, even if they do not contain `await` or `async` keywords.

It is a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) to use a `yield from` expression inside the body of a coroutine function.

An example of a coroutine function:

    async def func(param1, param2):
        do_stuff()
        await some_coroutine()

Changed in version 3.7: `await` and `async` are now keywords; previously they were only treated as such inside the body of a coroutine function.

<span id="compound_stmts--async-for"></span> <span id="compound_stmts--index-53"></span>

### 8.9.2. The `async for` statement {#compound_stmts--the-async-for-statement}

    async_for_stmt: "async" for_stmt

An [asynchronous iterable](https://docs.python.org/3/glossary.html#term-asynchronous-iterable) provides an `__aiter__` method that directly returns an [asynchronous iterator](https://docs.python.org/3/glossary.html#term-asynchronous-iterator), which can call asynchronous code in its `__anext__` method.

The `async for` statement allows convenient iteration over asynchronous iterables.

The following code:

    async for TARGET in ITER:
        SUITE
    else:
        SUITE2

Is semantically equivalent to:

    iter = (ITER).__aiter__()
    running = True

    while running:
        try:
            TARGET = await iter.__anext__()
        except StopAsyncIteration:
            running = False
        else:
            SUITE
    else:
        SUITE2

except that implicit [special method lookup](#datamodel--special-lookup) is used for [`__aiter__()`](#datamodel--object.__aiter__) and [`__anext__()`](#datamodel--object.__anext__).

It is a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) to use an `async for` statement outside the body of a coroutine function.

<span id="compound_stmts--async-with"></span> <span id="compound_stmts--index-54"></span>

### 8.9.3. The `async with` statement {#compound_stmts--the-async-with-statement}

    async_with_stmt: "async" with_stmt

An [asynchronous context manager](https://docs.python.org/3/glossary.html#term-asynchronous-context-manager) is a [context manager](https://docs.python.org/3/glossary.html#term-context-manager) that is able to suspend execution in its *enter* and *exit* methods.

The following code:

    async with EXPRESSION as TARGET:
        SUITE

is semantically equivalent to:

    manager = (EXPRESSION)
    aenter = manager.__aenter__
    aexit = manager.__aexit__
    value = await aenter()
    hit_except = False

    try:
        TARGET = value
        SUITE
    except:
        hit_except = True
        if not await aexit(*sys.exc_info()):
            raise
    finally:
        if not hit_except:
            await aexit(None, None, None)

except that implicit [special method lookup](#datamodel--special-lookup) is used for [`__aenter__()`](#datamodel--object.__aenter__) and [`__aexit__()`](#datamodel--object.__aexit__).

It is a [`SyntaxError`](https://docs.python.org/3/library/exceptions.html#SyntaxError) to use an `async with` statement outside the body of a coroutine function.

See also

<span id="compound_stmts--index-55"></span>[**PEP 492**](https://peps.python.org/pep-0492/) - Coroutines with async and await syntax  
The proposal that made coroutines a proper standalone concept in Python, and added supporting syntax.

<span id="compound_stmts--type-params"></span>

## 8.10. Type parameter lists {#compound_stmts--type-parameter-lists}

Added in version 3.12.

Changed in version 3.13: Support for default values was added (see <span id="compound_stmts--index-56"></span>[**PEP 696**](https://peps.python.org/pep-0696/)).

``` {#compound_stmts--index-57}
type_params:  "[" type_param ("," type_param)* "]"
type_param:   typevar | typevartuple | paramspec
typevar:      identifier (":" expression)? ("=" expression)?
typevartuple: "*" identifier ("=" expression)?
paramspec:    "**" identifier ("=" expression)?
```

[Functions](#compound_stmts--def) (including [coroutines](#compound_stmts--async-def)), [classes](#compound_stmts--class) and [type aliases](#simple_stmts--type) may contain a type parameter list:

    def max[T](args: list[T]) -> T:
        ...

    async def amax[T](args: list[T]) -> T:
        ...

    class Bag[T]:
        def __iter__(self) -> Iterator[T]:
            ...

        def add(self, arg: T) -> None:
            ...

    type ListOrSet[T] = list[T] | set[T]

Semantically, this indicates that the function, class, or type alias is generic over a type variable. This information is primarily used by static type checkers, and at runtime, generic objects behave much like their non-generic counterparts.

Type parameters are declared in square brackets (`[]`) immediately after the name of the function, class, or type alias. The type parameters are accessible within the scope of the generic object, but not elsewhere. Thus, after a declaration `def func[T](): pass`, the name `T` is not available in the module scope. Below, the semantics of generic objects are described with more precision. The scope of type parameters is modeled with a special function (technically, an [annotation scope](#executionmodel--annotation-scopes)) that wraps the creation of the generic object.

Generic functions, classes, and type aliases have a [`__type_params__`](https://docs.python.org/3/library/stdtypes.html#definition.__type_params__) attribute listing their type parameters.

Type parameters come in three kinds:

- [`typing.TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar), introduced by a plain name (e.g., `T`). Semantically, this represents a single type to a type checker.

- [`typing.TypeVarTuple`](https://docs.python.org/3/library/typing.html#typing.TypeVarTuple), introduced by a name prefixed with a single asterisk (e.g., `*Ts`). Semantically, this stands for a tuple of any number of types.

- [`typing.ParamSpec`](https://docs.python.org/3/library/typing.html#typing.ParamSpec), introduced by a name prefixed with two asterisks (e.g., `**P`). Semantically, this stands for the parameters of a callable.

[`typing.TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar) declarations can define *bounds* and *constraints* with a colon (`:`) followed by an expression. A single expression after the colon indicates a bound (e.g. `T: int`). Semantically, this means that the `typing.TypeVar` can only represent types that are a subtype of this bound. A parenthesized tuple of expressions after the colon indicates a set of constraints (e.g. `T: (str, bytes)`). Each member of the tuple should be a type (again, this is not enforced at runtime). Constrained type variables can only take on one of the types in the list of constraints.

For `typing.TypeVar`s declared using the type parameter list syntax, the bound and constraints are not evaluated when the generic object is created, but only when the value is explicitly accessed through the attributes `__bound__` and `__constraints__`. To accomplish this, the bounds or constraints are evaluated in a separate [annotation scope](#executionmodel--annotation-scopes).

[`typing.TypeVarTuple`](https://docs.python.org/3/library/typing.html#typing.TypeVarTuple)s and [`typing.ParamSpec`](https://docs.python.org/3/library/typing.html#typing.ParamSpec)s cannot have bounds or constraints.

All three flavors of type parameters can also have a *default value*, which is used when the type parameter is not explicitly provided. This is added by appending a single equals sign (`=`) followed by an expression. Like the bounds and constraints of type variables, the default value is not evaluated when the object is created, but only when the type parameter’s `__default__` attribute is accessed. To this end, the default value is evaluated in a separate [annotation scope](#executionmodel--annotation-scopes). If no default value is specified for a type parameter, the `__default__` attribute is set to the special sentinel object [`typing.NoDefault`](https://docs.python.org/3/library/typing.html#typing.NoDefault).

The following example indicates the full set of allowed type parameter declarations:

    def overly_generic[
       SimpleTypeVar,
       TypeVarWithDefault = int,
       TypeVarWithBound: int,
       TypeVarWithConstraints: (str, bytes),
       *SimpleTypeVarTuple = (int, float),
       **SimpleParamSpec = (str, bytearray),
    ](
       a: SimpleTypeVar,
       b: TypeVarWithDefault,
       c: TypeVarWithBound,
       d: Callable[SimpleParamSpec, TypeVarWithConstraints],
       *e: SimpleTypeVarTuple,
    ): ...

<span id="compound_stmts--id17"></span>

### 8.10.1. Generic functions {#compound_stmts--generic-functions}

Generic functions are declared as follows:

    def func[T](arg: T): ...

This syntax is equivalent to:

    annotation-def TYPE_PARAMS_OF_func():
        T = typing.TypeVar("T")
        def func(arg: T): ...
        func.__type_params__ = (T,)
        return func
    func = TYPE_PARAMS_OF_func()

Here `annotation-def` indicates an [annotation scope](#executionmodel--annotation-scopes), which is not actually bound to any name at runtime. (One other liberty is taken in the translation: the syntax does not go through attribute access on the [`typing`](https://docs.python.org/3/library/typing.html#module-typing) module, but creates an instance of [`typing.TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar) directly.)

The annotations of generic functions are evaluated within the annotation scope used for declaring the type parameters, but the function’s defaults and decorators are not.

The following example illustrates the scoping rules for these cases, as well as for additional flavors of type parameters:

    @decorator
    def func[T: int, *Ts, **P](*args: *Ts, arg: Callable[P, T] = some_default):
        ...

Except for the [lazy evaluation](#executionmodel--lazy-evaluation) of the [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar) bound, this is equivalent to:

    DEFAULT_OF_arg = some_default

    annotation-def TYPE_PARAMS_OF_func():

        annotation-def BOUND_OF_T():
            return int
        # In reality, BOUND_OF_T() is evaluated only on demand.
        T = typing.TypeVar("T", bound=BOUND_OF_T())

        Ts = typing.TypeVarTuple("Ts")
        P = typing.ParamSpec("P")

        def func(*args: *Ts, arg: Callable[P, T] = DEFAULT_OF_arg):
            ...

        func.__type_params__ = (T, Ts, P)
        return func
    func = decorator(TYPE_PARAMS_OF_func())

The capitalized names like `DEFAULT_OF_arg` are not actually bound at runtime.

<span id="compound_stmts--id18"></span>

### 8.10.2. Generic classes {#compound_stmts--generic-classes}

Generic classes are declared as follows:

    class Bag[T]: ...

This syntax is equivalent to:

    annotation-def TYPE_PARAMS_OF_Bag():
        T = typing.TypeVar("T")
        class Bag(typing.Generic[T]):
            __type_params__ = (T,)
            ...
        return Bag
    Bag = TYPE_PARAMS_OF_Bag()

Here again `annotation-def` (not a real keyword) indicates an [annotation scope](#executionmodel--annotation-scopes), and the name `TYPE_PARAMS_OF_Bag` is not actually bound at runtime.

Generic classes implicitly inherit from [`typing.Generic`](https://docs.python.org/3/library/typing.html#typing.Generic). The base classes and keyword arguments of generic classes are evaluated within the type scope for the type parameters, and decorators are evaluated outside that scope. This is illustrated by this example:

    @decorator
    class Bag(Base[T], arg=T): ...

This is equivalent to:

    annotation-def TYPE_PARAMS_OF_Bag():
        T = typing.TypeVar("T")
        class Bag(Base[T], typing.Generic[T], arg=T):
            __type_params__ = (T,)
            ...
        return Bag
    Bag = decorator(TYPE_PARAMS_OF_Bag())

<span id="compound_stmts--id19"></span>

### 8.10.3. Generic type aliases {#compound_stmts--generic-type-aliases}

The [`type`](#simple_stmts--type) statement can also be used to create a generic type alias:

    type ListOrSet[T] = list[T] | set[T]

Except for the [lazy evaluation](#executionmodel--lazy-evaluation) of the value, this is equivalent to:

    annotation-def TYPE_PARAMS_OF_ListOrSet():
        T = typing.TypeVar("T")

        annotation-def VALUE_OF_ListOrSet():
            return list[T] | set[T]
        # In reality, the value is lazily evaluated
        return typing.TypeAliasType("ListOrSet", VALUE_OF_ListOrSet(), type_params=(T,))
    ListOrSet = TYPE_PARAMS_OF_ListOrSet()

Here, `annotation-def` (not a real keyword) indicates an [annotation scope](#executionmodel--annotation-scopes). The capitalized names like `TYPE_PARAMS_OF_ListOrSet` are not actually bound at runtime.

<span id="compound_stmts--id20"></span>

## 8.11. Annotations {#compound_stmts--annotations}

Changed in version 3.14: Annotations are now lazily evaluated by default.

Variables and function parameters may carry [annotations](https://docs.python.org/3/glossary.html#term-annotation), created by adding a colon after the name, followed by an expression:

    x: annotation = 1
    def f(param: annotation): ...

Functions may also carry a return annotation following an arrow:

    def f() -> annotation: ...

Annotations are conventionally used for [type hints](https://docs.python.org/3/glossary.html#term-type-hint), but this is not enforced by the language, and in general annotations may contain arbitrary expressions. The presence of annotations does not change the runtime semantics of the code, except if some mechanism is used that introspects and uses the annotations (such as [`dataclasses`](https://docs.python.org/3/library/dataclasses.html#module-dataclasses) or [`@functools.singledispatch`](https://docs.python.org/3/library/functools.html#functools.singledispatch)).

By default, annotations are lazily evaluated in an [annotation scope](#executionmodel--annotation-scopes). This means that they are not evaluated when the code containing the annotation is evaluated. Instead, the interpreter saves information that can be used to evaluate the annotation later if requested. The [`annotationlib`](https://docs.python.org/3/library/annotationlib.html#module-annotationlib) module provides tools for evaluating annotations.

If the [future statement](#simple_stmts--future) `from __future__ import annotations` is present, all annotations are instead stored as strings:

    >>> from __future__ import annotations
    >>> def f(param: annotation): ...
    >>> f.__annotations__
    {'param': 'annotation'}

This future statement will be deprecated and removed in a future version of Python, but not before Python 3.13 reaches its end of life (see <span id="compound_stmts--index-58"></span>[**PEP 749**](https://peps.python.org/pep-0749/)). When it is used, introspection tools like [`annotationlib.get_annotations()`](https://docs.python.org/3/library/annotationlib.html#annotationlib.get_annotations) and [`typing.get_type_hints()`](https://docs.python.org/3/library/typing.html#typing.get_type_hints) are less likely to be able to resolve annotations at runtime.

Footnotes

\[[1](#compound_stmts--id1)\]

The exception is propagated to the invocation stack unless there is a [`finally`](#compound_stmts--finally) clause which happens to raise another exception. That new exception causes the old one to be lost.

\[[2](#compound_stmts--id11)\]

In pattern matching, a sequence is defined as one of the following:

- a class that inherits from [`collections.abc.Sequence`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)

- a Python class that has been registered as [`collections.abc.Sequence`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)

- a builtin class that has its (CPython) [`Py_TPFLAGS_SEQUENCE`](https://docs.python.org/3/c-api/typeobj.html#c.Py_TPFLAGS_SEQUENCE) bit set

- a class that inherits from any of the above

The following standard library classes are sequences:

- [`array.array`](https://docs.python.org/3/library/array.html#array.array)

- [`collections.deque`](https://docs.python.org/3/library/collections.html#collections.deque)

- [`list`](https://docs.python.org/3/library/stdtypes.html#list)

- [`memoryview`](https://docs.python.org/3/library/stdtypes.html#memoryview)

- [`range`](https://docs.python.org/3/library/stdtypes.html#range)

- [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)

Note

Subject values of type `str`, `bytes`, and `bytearray` do not match sequence patterns.

\[[3](#compound_stmts--id13)\]

In pattern matching, a mapping is defined as one of the following:

- a class that inherits from [`collections.abc.Mapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)

- a Python class that has been registered as [`collections.abc.Mapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)

- a builtin class that has its (CPython) [`Py_TPFLAGS_MAPPING`](https://docs.python.org/3/c-api/typeobj.html#c.Py_TPFLAGS_MAPPING) bit set

- a class that inherits from any of the above

The standard library classes [`dict`](https://docs.python.org/3/library/stdtypes.html#dict) and [`types.MappingProxyType`](https://docs.python.org/3/library/types.html#types.MappingProxyType) are mappings.

\[[4](#compound_stmts--id15)\]

A string literal appearing as the first statement in the function body is transformed into the function’s [`__doc__`](#datamodel--function.__doc__) attribute and therefore the function’s [docstring](https://docs.python.org/3/glossary.html#term-docstring).

\[[5](#compound_stmts--id16)\]

A string literal appearing as the first statement in the class body is transformed into the namespace’s [`__doc__`](#datamodel--type.__doc__) item and therefore the class’s [docstring](https://docs.python.org/3/glossary.html#term-docstring).

<span id="toplevel_components--top-level"></span>

# 9. Top-level components {#toplevel_components--top-level-components}

The Python interpreter can get its input from a number of sources: from a script passed to it as standard input or as program argument, typed in interactively, from a module source file, etc. This chapter gives the syntax used in these cases.

<span id="toplevel_components--programs"></span>

## 9.1. Complete Python programs {#toplevel_components--complete-python-programs}

<span id="toplevel_components--index-1"></span>While a language specification need not prescribe how the language interpreter is invoked, it is useful to have a notion of a complete Python program. A complete Python program is executed in a minimally initialized environment: all built-in and standard modules are available, but none have been initialized, except for [`sys`](https://docs.python.org/3/library/sys.html#module-sys) (various system services), [`builtins`](https://docs.python.org/3/library/builtins.html#module-builtins) (built-in functions, exceptions and `None`) and [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__). The latter is used to provide the local and global namespace for execution of the complete program.

The syntax for a complete Python program is that for file input, described in the next section.

The interpreter may also be invoked in interactive mode; in this case, it does not read and execute a complete program but reads and executes one statement (possibly compound) at a time. The initial environment is identical to that of a complete program; each statement is executed in the namespace of [`__main__`](https://docs.python.org/3/library/__main__.html#module-__main__).

A complete program can be passed to the interpreter in three forms: with the [`-c`](https://docs.python.org/3/using/cmdline.html#cmdoption-c) *string* command line option, as a file passed as the first command line argument, or as standard input. If the file or standard input is a tty device, the interpreter enters interactive mode; otherwise, it executes the file as a complete program.

<span id="toplevel_components--id1"></span>

## 9.2. File input {#toplevel_components--file-input}

All input read from non-interactive files has the same form:

    file_input: (NEWLINE | statement)* ENDMARKER

This syntax is used in the following situations:

- when parsing a complete Python program (from a file or from a string);

- when parsing a module;

- when parsing a string passed to the [`exec()`](https://docs.python.org/3/library/functions.html#exec) function;

<span id="toplevel_components--interactive"></span>

## 9.3. Interactive input {#toplevel_components--interactive-input}

Input in interactive mode is parsed using the following grammar:

    interactive_input: [stmt_list] NEWLINE | compound_stmt NEWLINE | ENDMARKER

Note that a (top-level) compound statement must be followed by a blank line in interactive mode; this is needed to help the parser detect the end of the input.

<span id="toplevel_components--id2"></span>

## 9.4. Expression input {#toplevel_components--expression-input}

<span id="toplevel_components--index-5"></span>[`eval()`](https://docs.python.org/3/library/functions.html#eval) is used for expression input. It ignores leading whitespace. The string argument to `eval()` must have the following form:

    eval_input: expression_list NEWLINE* ENDMARKER

<span id="grammar--id1"></span>

# 10. Full Grammar specification {#grammar--full-grammar-specification}

This is the full Python grammar, derived directly from the grammar used to generate the CPython parser (see [Grammar/python.gram](https://github.com/python/cpython/tree/3.14/Grammar/python.gram)). The version here omits details related to code generation and error recovery.

The notation used here is the same as in the preceding docs, and is described in the [notation](#introduction--notation) section, except for an extra complication:

- `~` (“cut”): commit to the current alternative; fail the rule if the alternative fails to parse

  Python mainly uses cuts for optimizations or improved error messages. They often appear to be useless in the listing below.

  Cuts currently don’t appear inside parentheses, brackets, lookaheads and similar. Their behavior in these contexts is deliberately left unspecified.

<!-- -->

    # PEG grammar for Python



    # ========================= START OF THE GRAMMAR =========================

    # General grammatical elements and rules:
    #
    # * Strings with double quotes (") denote SOFT KEYWORDS
    # * Strings with single quotes (') denote KEYWORDS
    # * Upper case names (NAME) denote tokens in the Grammar/Tokens file
    # * Rule names starting with "invalid_" are used for specialized syntax errors
    #     - These rules are NOT used in the first pass of the parser.
    #     - Only if the first pass fails to parse, a second pass including the invalid
    #       rules will be executed.
    #     - If the parser fails in the second phase with a generic syntax error, the
    #       location of the generic failure of the first pass will be used (this avoids
    #       reporting incorrect locations due to the invalid rules).
    #     - The order of the alternatives involving invalid rules matter
    #       (like any rule in PEG).
    #
    # Grammar Syntax (see PEP 617 for more information):
    #
    # rule_name: expression
    #   Optionally, a type can be included right after the rule name, which
    #   specifies the return type of the C or Python function corresponding to the
    #   rule:
    # rule_name[return_type]: expression
    #   If the return type is omitted, then a void * is returned in C and an Any in
    #   Python.
    # e1 e2
    #   Match e1, then match e2.
    # e1 | e2
    #   Match e1 or e2.
    #   The first alternative can also appear on the line after the rule name for
    #   formatting purposes. In that case, a | must be used before the first
    #   alternative, like so:
    #       rule_name[return_type]:
    #            | first_alt
    #            | second_alt
    # ( e )
    #   Match e (allows also to use other operators in the group like '(e)*')
    # [ e ] or e?
    #   Optionally match e.
    # e*
    #   Match zero or more occurrences of e.
    # e+
    #   Match one or more occurrences of e.
    # s.e+
    #   Match one or more occurrences of e, separated by s. The generated parse tree
    #   does not include the separator. This is otherwise identical to (e (s e)*).
    # &e
    #   Succeed if e can be parsed, without consuming any input.
    # !e
    #   Fail if e can be parsed, without consuming any input.
    # ~
    #   Commit to the current alternative, even if it fails to parse.
    # &&e
    #   Eager parse e. The parser will not backtrack and will immediately
    #   fail with SyntaxError if e cannot be parsed.
    #

    # STARTING RULES
    # ==============

    file: [statements] ENDMARKER 
    interactive: statement_newline 
    eval: expressions NEWLINE* ENDMARKER 
    func_type: '(' [type_expressions] ')' '->' expression NEWLINE* ENDMARKER 

    # GENERAL STATEMENTS
    # ==================

    statements: statement+ 

    statement:
        | compound_stmt 
        | simple_stmts 

    single_compound_stmt:
        | compound_stmt 

    statement_newline:
        | single_compound_stmt NEWLINE 
        | simple_stmts
        | NEWLINE 
        | ENDMARKER 

    simple_stmts:
        | simple_stmt !';' NEWLINE  # Not needed, there for speedup
        | ';'.simple_stmt+ [';'] NEWLINE 

    # NOTE: assignment MUST precede expression, else parsing a simple assignment
    # will throw a SyntaxError.
    simple_stmt:
        | assignment
        | type_alias
        | star_expressions 
        | return_stmt
        | import_stmt
        | raise_stmt
        | pass_stmt
        | del_stmt
        | yield_stmt
        | assert_stmt
        | break_stmt
        | continue_stmt
        | global_stmt
        | nonlocal_stmt

    compound_stmt:
        | function_def
        | if_stmt
        | class_def
        | with_stmt
        | for_stmt
        | try_stmt
        | while_stmt
        | match_stmt

    # SIMPLE STATEMENTS
    # =================

    # NOTE: annotated_rhs may start with 'yield'; yield_expr must start with 'yield'
    assignment:
        | NAME ':' expression ['=' annotated_rhs ] 
        | ('(' single_target ')' 
             | single_subscript_attribute_target) ':' expression ['=' annotated_rhs ] 
        | (star_targets '=' )+ annotated_rhs !'=' [TYPE_COMMENT] 
        | single_target augassign ~ annotated_rhs 

    annotated_rhs: yield_expr | star_expressions

    augassign:
        | '+=' 
        | '-=' 
        | '*=' 
        | '@=' 
        | '/=' 
        | '%=' 
        | '&=' 
        | '|=' 
        | '^=' 
        | '<<=' 
        | '>>=' 
        | '**=' 
        | '//=' 

    return_stmt:
        | 'return' [star_expressions] 

    raise_stmt:
        | 'raise' expression ['from' expression ] 
        | 'raise' 

    pass_stmt:
        | 'pass' 

    break_stmt:
        | 'break' 

    continue_stmt:
        | 'continue' 

    global_stmt: 'global' ','.NAME+ 

    nonlocal_stmt: 'nonlocal' ','.NAME+ 

    del_stmt:
        | 'del' del_targets &(';' | NEWLINE) 

    yield_stmt: yield_expr 

    assert_stmt: 'assert' expression [',' expression ] 

    import_stmt:
        | import_name
        | import_from

    # Import statements
    # -----------------

    import_name: 'import' dotted_as_names 
    # note below: the ('.' | '...') is necessary because '...' is tokenized as ELLIPSIS
    import_from:
        | 'from' ('.' | '...')* dotted_name 'import' import_from_targets 
        | 'from' ('.' | '...')+ 'import' import_from_targets 
    import_from_targets:
        | '(' import_from_as_names [','] ')' 
        | import_from_as_names !','
        | '*' 
    import_from_as_names:
        | ','.import_from_as_name+ 
    import_from_as_name:
        | NAME ['as' NAME ] 

    dotted_as_names:
        | ','.dotted_as_name+ 
    dotted_as_name:
        | dotted_name ['as' NAME ] 

    dotted_name:
        | dotted_name '.' NAME 
        | NAME

    # COMPOUND STATEMENTS
    # ===================

    # Common elements
    # ---------------

    block:
        | NEWLINE INDENT statements DEDENT 
        | simple_stmts

    decorators: ('@' named_expression NEWLINE )+ 

    # Class definitions
    # -----------------

    class_def:
        | decorators class_def_raw 
        | class_def_raw

    class_def_raw:
        | 'class' NAME [type_params] ['(' [arguments] ')' ] ':' block 

    # Function definitions
    # --------------------

    function_def:
        | decorators function_def_raw 
        | function_def_raw

    function_def_raw:
        | 'def' NAME [type_params] '(' [params] ')' ['->' expression ] ':' [func_type_comment] block 
        | 'async' 'def' NAME [type_params] '(' [params] ')' ['->' expression ] ':' [func_type_comment] block 

    # Function parameters
    # -------------------

    params:
        | parameters

    parameters:
        | slash_no_default param_no_default* param_with_default* [star_etc] 
        | slash_with_default param_with_default* [star_etc] 
        | param_no_default+ param_with_default* [star_etc] 
        | param_with_default+ [star_etc] 
        | star_etc 

    # Some duplication here because we can't write (',' | &')'),
    # which is because we don't support empty alternatives (yet).

    slash_no_default:
        | param_no_default+ '/' ',' 
        | param_no_default+ '/' &')' 
    slash_with_default:
        | param_no_default* param_with_default+ '/' ',' 
        | param_no_default* param_with_default+ '/' &')' 

    star_etc:
        | '*' param_no_default param_maybe_default* [kwds] 
        | '*' param_no_default_star_annotation param_maybe_default* [kwds] 
        | '*' ',' param_maybe_default+ [kwds] 
        | kwds 

    kwds:
        | '**' param_no_default 

    # One parameter.  This *includes* a following comma and type comment.
    #
    # There are three styles:
    # - No default
    # - With default
    # - Maybe with default
    #
    # There are two alternative forms of each, to deal with type comments:
    # - Ends in a comma followed by an optional type comment
    # - No comma, optional type comment, must be followed by close paren
    # The latter form is for a final parameter without trailing comma.
    #

    param_no_default:
        | param ',' TYPE_COMMENT? 
        | param TYPE_COMMENT? &')' 
    param_no_default_star_annotation:
        | param_star_annotation ',' TYPE_COMMENT? 
        | param_star_annotation TYPE_COMMENT? &')' 
    param_with_default:
        | param default ',' TYPE_COMMENT? 
        | param default TYPE_COMMENT? &')' 
    param_maybe_default:
        | param default? ',' TYPE_COMMENT? 
        | param default? TYPE_COMMENT? &')' 
    param: NAME annotation? 
    param_star_annotation: NAME star_annotation 
    annotation: ':' expression 
    star_annotation: ':' star_expression 
    default: '=' expression  | invalid_default

    # If statement
    # ------------

    if_stmt:
        | 'if' named_expression ':' block elif_stmt 
        | 'if' named_expression ':' block [else_block] 
    elif_stmt:
        | 'elif' named_expression ':' block elif_stmt 
        | 'elif' named_expression ':' block [else_block] 
    else_block:
        | 'else' ':' block 

    # While statement
    # ---------------

    while_stmt:
        | 'while' named_expression ':' block [else_block] 

    # For statement
    # -------------

    for_stmt:
        | 'for' star_targets 'in' ~ star_expressions ':' [TYPE_COMMENT] block [else_block] 
        | 'async' 'for' star_targets 'in' ~ star_expressions ':' [TYPE_COMMENT] block [else_block] 

    # With statement
    # --------------

    with_stmt:
        | 'with' '(' ','.with_item+ ','? ')' ':' [TYPE_COMMENT] block 
        | 'with' ','.with_item+ ':' [TYPE_COMMENT] block 
        | 'async' 'with' '(' ','.with_item+ ','? ')' ':' block 
        | 'async' 'with' ','.with_item+ ':' [TYPE_COMMENT] block 

    with_item:
        | expression 'as' star_target &(',' | ')' | ':') 
        | expression 

    # Try statement
    # -------------

    try_stmt:
        | 'try' ':' block finally_block 
        | 'try' ':' block except_block+ [else_block] [finally_block] 
        | 'try' ':' block except_star_block+ [else_block] [finally_block] 


    # Except statement
    # ----------------

    except_block:
        | 'except' expression ':' block 
        | 'except' expression 'as' NAME ':' block 
        | 'except' expressions ':' block 
        | 'except' ':' block 
    except_star_block:
        | 'except' '*' expression ':' block 
        | 'except' '*' expression 'as' NAME ':' block 
        | 'except' '*' expressions ':' block 
    finally_block:
        | 'finally' ':' block 

    # Match statement
    # ---------------

    match_stmt:
        | "match" subject_expr ':' NEWLINE INDENT case_block+ DEDENT 

    subject_expr:
        | star_named_expression ',' star_named_expressions? 
        | named_expression

    case_block:
        | "case" patterns guard? ':' block 

    guard: 'if' named_expression 

    patterns:
        | open_sequence_pattern 
        | pattern

    pattern:
        | as_pattern
        | or_pattern

    as_pattern:
        | or_pattern 'as' pattern_capture_target 

    or_pattern:
        | '|'.closed_pattern+ 

    closed_pattern:
        | literal_pattern
        | capture_pattern
        | wildcard_pattern
        | value_pattern
        | group_pattern
        | sequence_pattern
        | mapping_pattern
        | class_pattern

    # Literal patterns are used for equality and identity constraints
    literal_pattern:
        | signed_number !('+' | '-') 
        | complex_number 
        | strings 
        | 'None' 
        | 'True' 
        | 'False' 

    # Literal expressions are used to restrict permitted mapping pattern keys
    literal_expr:
        | signed_number !('+' | '-')
        | complex_number
        | strings
        | 'None' 
        | 'True' 
        | 'False' 

    complex_number:
        | signed_real_number '+' imaginary_number 
        | signed_real_number '-' imaginary_number  

    signed_number:
        | NUMBER
        | '-' NUMBER 

    signed_real_number:
        | real_number
        | '-' real_number 

    real_number:
        | NUMBER 

    imaginary_number:
        | NUMBER 

    capture_pattern:
        | pattern_capture_target 

    pattern_capture_target:
        | !"_" NAME !('.' | '(' | '=') 

    wildcard_pattern:
        | "_" 

    value_pattern:
        | attr !('.' | '(' | '=') 

    attr:
        | name_or_attr '.' NAME 

    name_or_attr:
        | attr
        | NAME

    group_pattern:
        | '(' pattern ')' 

    sequence_pattern:
        | '[' maybe_sequence_pattern? ']' 
        | '(' open_sequence_pattern? ')' 

    open_sequence_pattern:
        | maybe_star_pattern ',' maybe_sequence_pattern? 

    maybe_sequence_pattern:
        | ','.maybe_star_pattern+ ','? 

    maybe_star_pattern:
        | star_pattern
        | pattern

    star_pattern:
        | '*' pattern_capture_target 
        | '*' wildcard_pattern 

    mapping_pattern:
        | '{' '}' 
        | '{' double_star_pattern ','? '}' 
        | '{' items_pattern ',' double_star_pattern ','? '}' 
        | '{' items_pattern ','? '}' 

    items_pattern:
        | ','.key_value_pattern+

    key_value_pattern:
        | (literal_expr | attr) ':' pattern 

    double_star_pattern:
        | '**' pattern_capture_target 

    class_pattern:
        | name_or_attr '(' ')' 
        | name_or_attr '(' positional_patterns ','? ')' 
        | name_or_attr '(' keyword_patterns ','? ')' 
        | name_or_attr '(' positional_patterns ',' keyword_patterns ','? ')' 

    positional_patterns:
        | ','.pattern+ 

    keyword_patterns:
        | ','.keyword_pattern+

    keyword_pattern:
        | NAME '=' pattern 

    # Type statement
    # ---------------

    type_alias:
        | "type" NAME [type_params] '=' expression 

    # Type parameter declaration
    # --------------------------

    type_params:
        | '[' type_param_seq ']' 

    type_param_seq: ','.type_param+ [','] 

    type_param:
        | NAME [type_param_bound] [type_param_default] 
        | '*' NAME [type_param_starred_default] 
        | '**' NAME [type_param_default] 

    type_param_bound: ':' expression 
    type_param_default: '=' expression 
    type_param_starred_default: '=' star_expression 

    # EXPRESSIONS
    # -----------

    expressions:
        | expression (',' expression )+ [','] 
        | expression ',' 
        | expression

    expression:
        | disjunction 'if' disjunction 'else' expression 
        | disjunction
        | lambdef

    yield_expr:
        | 'yield' 'from' expression 
        | 'yield' [star_expressions] 

    star_expressions:
        | star_expression (',' star_expression )+ [','] 
        | star_expression ',' 
        | star_expression

    star_expression:
        | '*' bitwise_or 
        | expression

    star_named_expressions: ','.star_named_expression+ [','] 

    star_named_expression:
        | '*' bitwise_or 
        | named_expression

    assignment_expression:
        | NAME ':=' ~ expression 

    named_expression:
        | assignment_expression
        | expression !':='

    disjunction:
        | conjunction ('or' conjunction )+ 
        | conjunction

    conjunction:
        | inversion ('and' inversion )+ 
        | inversion

    inversion:
        | 'not' inversion 
        | comparison

    # Comparison operators
    # --------------------

    comparison:
        | bitwise_or compare_op_bitwise_or_pair+ 
        | bitwise_or

    compare_op_bitwise_or_pair:
        | eq_bitwise_or
        | noteq_bitwise_or
        | lte_bitwise_or
        | lt_bitwise_or
        | gte_bitwise_or
        | gt_bitwise_or
        | notin_bitwise_or
        | in_bitwise_or
        | isnot_bitwise_or
        | is_bitwise_or

    eq_bitwise_or: '==' bitwise_or 
    noteq_bitwise_or:
        | ('!=' ) bitwise_or 
    lte_bitwise_or: '<=' bitwise_or 
    lt_bitwise_or: '<' bitwise_or 
    gte_bitwise_or: '>=' bitwise_or 
    gt_bitwise_or: '>' bitwise_or 
    notin_bitwise_or: 'not' 'in' bitwise_or 
    in_bitwise_or: 'in' bitwise_or 
    isnot_bitwise_or: 'is' 'not' bitwise_or 
    is_bitwise_or: 'is' bitwise_or 

    # Bitwise operators
    # -----------------

    bitwise_or:
        | bitwise_or '|' bitwise_xor 
        | bitwise_xor

    bitwise_xor:
        | bitwise_xor '^' bitwise_and 
        | bitwise_and

    bitwise_and:
        | bitwise_and '&' shift_expr 
        | shift_expr

    shift_expr:
        | shift_expr '<<' sum 
        | shift_expr '>>' sum 
        | sum

    # Arithmetic operators
    # --------------------

    sum:
        | sum '+' term 
        | sum '-' term 
        | term

    term:
        | term '*' factor 
        | term '/' factor 
        | term '//' factor 
        | term '%' factor 
        | term '@' factor 
        | factor

    factor:
        | '+' factor 
        | '-' factor 
        | '~' factor 
        | power

    power:
        | await_primary '**' factor 
        | await_primary

    # Primary elements
    # ----------------

    # Primary elements are things like "obj.something.something", "obj[something]", "obj(something)", "obj" ...

    await_primary:
        | 'await' primary 
        | primary

    primary:
        | primary '.' NAME 
        | primary genexp 
        | primary '(' [arguments] ')' 
        | primary '[' slices ']' 
        | atom

    slices:
        | slice !',' 
        | ','.(slice | starred_expression)+ [','] 

    slice:
        | [expression] ':' [expression] [':' [expression] ] 
        | named_expression 

    atom:
        | NAME
        | 'True' 
        | 'False' 
        | 'None' 
        | strings
        | NUMBER
        | (tuple | group | genexp)
        | (list | listcomp)
        | (dict | set | dictcomp | setcomp)
        | '...' 

    group:
        | '(' (yield_expr | named_expression) ')' 

    # Lambda functions
    # ----------------

    lambdef:
        | 'lambda' [lambda_params] ':' expression 

    lambda_params:
        | lambda_parameters

    # lambda_parameters etc. duplicates parameters but without annotations
    # or type comments, and if there's no comma after a parameter, we expect
    # a colon, not a close parenthesis.  (For more, see parameters above.)
    #
    lambda_parameters:
        | lambda_slash_no_default lambda_param_no_default* lambda_param_with_default* [lambda_star_etc] 
        | lambda_slash_with_default lambda_param_with_default* [lambda_star_etc] 
        | lambda_param_no_default+ lambda_param_with_default* [lambda_star_etc] 
        | lambda_param_with_default+ [lambda_star_etc] 
        | lambda_star_etc 

    lambda_slash_no_default:
        | lambda_param_no_default+ '/' ',' 
        | lambda_param_no_default+ '/' &':' 

    lambda_slash_with_default:
        | lambda_param_no_default* lambda_param_with_default+ '/' ',' 
        | lambda_param_no_default* lambda_param_with_default+ '/' &':' 

    lambda_star_etc:
        | '*' lambda_param_no_default lambda_param_maybe_default* [lambda_kwds] 
        | '*' ',' lambda_param_maybe_default+ [lambda_kwds] 
        | lambda_kwds 

    lambda_kwds:
        | '**' lambda_param_no_default 

    lambda_param_no_default:
        | lambda_param ',' 
        | lambda_param &':' 
    lambda_param_with_default:
        | lambda_param default ',' 
        | lambda_param default &':' 
    lambda_param_maybe_default:
        | lambda_param default? ',' 
        | lambda_param default? &':' 
    lambda_param: NAME 

    # LITERALS
    # ========

    fstring_middle:
        | fstring_replacement_field
        | FSTRING_MIDDLE 
    fstring_replacement_field:
        | '{' annotated_rhs '='? [fstring_conversion] [fstring_full_format_spec] '}' 
    fstring_conversion:
        | "!" NAME 
    fstring_full_format_spec:
        | ':' fstring_format_spec* 
    fstring_format_spec:
        | FSTRING_MIDDLE 
        | fstring_replacement_field
    fstring:
        | FSTRING_START fstring_middle* FSTRING_END 

    tstring_format_spec_replacement_field:
        | '{' annotated_rhs '='? [fstring_conversion] [tstring_full_format_spec] '}' 
    tstring_format_spec:
        | TSTRING_MIDDLE 
        | tstring_format_spec_replacement_field
    tstring_full_format_spec:
        | ':' tstring_format_spec* 
    tstring_replacement_field:
        | '{' annotated_rhs '='? [fstring_conversion] [tstring_full_format_spec] '}' 
    tstring_middle:
        | tstring_replacement_field
        | TSTRING_MIDDLE 
    tstring:
        | TSTRING_START tstring_middle* TSTRING_END 

    string: STRING 
    strings:
        | (fstring|string)+ 
        | tstring+ 

    list:
        | '[' [star_named_expressions] ']' 

    tuple:
        | '(' [star_named_expression ',' [star_named_expressions]  ] ')' 

    set: '{' star_named_expressions '}' 

    # Dicts
    # -----

    dict:
        | '{' [double_starred_kvpairs] '}' 

    double_starred_kvpairs: ','.double_starred_kvpair+ [','] 

    double_starred_kvpair:
        | '**' bitwise_or 
        | kvpair

    kvpair: expression ':' expression 

    # Comprehensions & Generators
    # ---------------------------

    for_if_clauses:
        | for_if_clause+ 

    for_if_clause:
        | 'async' 'for' star_targets 'in' ~ disjunction ('if' disjunction )* 
        | 'for' star_targets 'in' ~ disjunction ('if' disjunction )* 

    listcomp:
        | '[' named_expression for_if_clauses ']' 

    setcomp:
        | '{' named_expression for_if_clauses '}' 

    genexp:
        | '(' ( assignment_expression | expression !':=') for_if_clauses ')' 

    dictcomp:
        | '{' kvpair for_if_clauses '}' 

    # FUNCTION CALL ARGUMENTS
    # =======================

    arguments:
        | args [','] &')' 

    args:
        | ','.(starred_expression | ( assignment_expression | expression !':=') !'=')+ [',' kwargs ] 
        | kwargs 

    kwargs:
        | ','.kwarg_or_starred+ ',' ','.kwarg_or_double_starred+ 
        | ','.kwarg_or_starred+
        | ','.kwarg_or_double_starred+

    starred_expression:
        | '*' expression 

    kwarg_or_starred:
        | NAME '=' expression 
        | starred_expression 

    kwarg_or_double_starred:
        | NAME '=' expression 
        | '**' expression 

    # ASSIGNMENT TARGETS
    # ==================

    # Generic targets
    # ---------------

    # NOTE: star_targets may contain *bitwise_or, targets may not.
    star_targets:
        | star_target !',' 
        | star_target (',' star_target )* [','] 

    star_targets_list_seq: ','.star_target+ [','] 

    star_targets_tuple_seq:
        | star_target (',' star_target )+ [','] 
        | star_target ',' 

    star_target:
        | '*' (!'*' star_target) 
        | target_with_star_atom

    target_with_star_atom:
        | t_primary '.' NAME !t_lookahead 
        | t_primary '[' slices ']' !t_lookahead 
        | star_atom

    star_atom:
        | NAME 
        | '(' target_with_star_atom ')' 
        | '(' [star_targets_tuple_seq] ')' 
        | '[' [star_targets_list_seq] ']' 

    single_target:
        | single_subscript_attribute_target
        | NAME 
        | '(' single_target ')' 

    single_subscript_attribute_target:
        | t_primary '.' NAME !t_lookahead 
        | t_primary '[' slices ']' !t_lookahead 

    t_primary:
        | t_primary '.' NAME &t_lookahead 
        | t_primary '[' slices ']' &t_lookahead 
        | t_primary genexp &t_lookahead 
        | t_primary '(' [arguments] ')' &t_lookahead 
        | atom &t_lookahead 

    t_lookahead: '(' | '[' | '.'

    # Targets for del statements
    # --------------------------

    del_targets: ','.del_target+ [','] 

    del_target:
        | t_primary '.' NAME !t_lookahead 
        | t_primary '[' slices ']' !t_lookahead 
        | del_t_atom

    del_t_atom:
        | NAME 
        | '(' del_target ')' 
        | '(' [del_targets] ')' 
        | '[' [del_targets] ']' 

    # TYPING ELEMENTS
    # ---------------

    # type_expressions allow */** but ignore them
    type_expressions:
        | ','.expression+ ',' '*' expression ',' '**' expression 
        | ','.expression+ ',' '*' expression 
        | ','.expression+ ',' '**' expression 
        | '*' expression ',' '**' expression 
        | '*' expression 
        | '**' expression 
        | ','.expression+ 

    func_type_comment:
        | NEWLINE TYPE_COMMENT &(NEWLINE INDENT)   # Must be followed by indented block
        | TYPE_COMMENT

    # ========================= END OF THE GRAMMAR ===========================



    # ========================= START OF INVALID RULES =======================
