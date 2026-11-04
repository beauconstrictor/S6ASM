# S6ASM Reference Manual

__This manual is unfinished.__

S6ASM is a comprehensive, albeit immature, macro assembler and development toolchain for the Ozpex S6 platform.

## Outline

- Introduction
    - What S6ASM is
    - How to install it
    - First program
- The Pipeline
    - Tokeniser
    - Preprocessor
    - Linker
    - Assembler
    - Emulator
- Syntax
    - Parsing
    - Identifiers
    - Macros
    - Expressions
    - Directives
    - Immediates
- Architecture
    - SUBLEQ
    - Memory map
    - Tape I/O
- Error Reporting
    - Tracebacks
    - Exit Codes
- Standard Library
    - Memory layout
    - Fundamental macros
    - Branches
    - Comparisons
    - Special macros
    - 16-bit helpers
    - Self-modifiers
    - Bitwise macros
    - Constants

## Introduction

### What S6ASM is

S6ASM is primarily a macro assembler for the Ozpex S6 platform, but with considerable surrounding machinery, and a powerful preprocessor that handles macros, locals and other conveniences.

The [Ozpex S6](https://github.com/beauconstrictor/s6emu) is a minimal computer architecture and platform, designed to demonstrate the smallest possible set of functionality that constitutes a computer, eschewing hardware complexity in favour of software.

S6ASM takes your source code through a short pipeline, each stage building on the last and transforming the code, until you eventually end up with a binary image. There is then an optional final stage that simulates an S6 in software and loads your binary image into it. You can explicitly stop the assembly at any point in this pipeline to view its output.

### How to install it

S6ASM is written in Python, and requires version 3.12 or above. To install it with `pip`:

```sh
python -m pip install git+https://github.com/beauconstrictor/s6asm.git
```

Once you've installed `s6asm`, try running it like this:

```sh
s6asm -v
```

This should output your installed version of `s6asm`.

### First program

The S6ASM program we will write will be loaded directly into ROM, so we can easily test it. This means we need to start our program with this line:

```asm
  .org 0x8000
```

This tells the assembler that our program starts at address `0x8000`, which is where the ROM is mapped on an S6.

Most S6ASM programs that you write will begin with an `.include` directive referencing the standard library, which adds functionality to your program and makes development significantly easier:

```asm
  .include <stdlib>
```

Notice that this line is indented. How much indentation you use is irrelevant, but lines that don't begin with a label _must_ be indented.

Next, we will create some variables, using `.res`. This directive allocates memory addresses starting from `0x0000` to names, allowing you to easily manage your globals. To find out more about these directives, see _Syntax_ > _Directives_. We will allocate two variables, each 1 byte in size:

```asm
  .res 1 letter
  .res 1 counter
```

It's probably time to explain what we're going to build. This is probably the simplest program you can write for the S6, while still giving you a good feel for the machine. It prints the alphabet, like this:

```
ABCDEFGHIJKLMNOPQRSTUVWXYZ
```

Now, we need to move some starting values into our variables (referred to as 'registers' from here on). We will move the letter 'A' into our `letter` register, and the number 26 into our `counter`:

```asm
  mov #'A' letter
  mov #26 counter
```

Here, we have our first taste of _macros_, which are the tools we use to actually build our program. Later on, we will learn to build our own macros from existing ones. The macros we will use here come from the standard library, which we included right at the start of our program. The `mov` macro you see here copies a value from one place to another. Usually, this is from a register into another, but in this case, the `#` sign indicates that it will move a hardcoded value into a register instead - this is how we put our initial values in our registers.

Our program will print our letter and move to the next letter, decrease the counter and check if it is zero. If it's not yet zero, we go back to the start and repeat. If it is, we are done.

The first step of that is printing our letter, which we can do like this:

```asm
loop:
  out letter
```

`out` is another macro, which takes our letter and prints it to the screen. The _label_, `loop`, is effectively a named place in our program. We use one here so that we can jump back to this point in our program later (to perform the loop). Next, we need to move to the next letter in the alphabet. To do that, we use the `inc` macro, which increases the value in a register by one. This works because letters in assembly are actually just numbers! Each symbol (letters, digits, spaces, etc.) is assigned a special number, and `out` converts that number back to a character to display. You don't need to memorise any of these numbers, because the assembler does that for us: whenever we surround a character in single quotes (`'`), it is automatically replaced with its number. This system is called [ASCII](https://en.wikipedia.org/wiki/ASCII). What is useful to know, however, is that letters are assigned ascending numbers in this system, meaning, if we increase a number by one, it effectively moves to the next letter, which is exactly what our program needs:

```asm
  inc letter
```

See! Assembly is easy. Now, our counter will come into play. The next macro is the most complex one yet - it decrements (decreases by one, the reverse of `inc`) a register and, if the result is greater than zero, the program jumps to a label. This allows us to perform a loop a specific number of times (26 in our case, by initially setting `counter` to 26, and letting it decrease one by one). We use it like this:

```asm
  dbgt counter loop
```

The first operand that we pass is the register to decrement. The second is the label we want to jump to. The name stands for 'Decrement and Branch if Greater than Zero'. This means that, if our program continues to execute past this macro, the counter must have reached zero and we have finished printing the alphabet. To exit the program, we use the `halt` macro, like this:

```asm
 halt
```

If you want to try this program out, save it as `test.s`, and run it using this command in the terminal (assuming you have installed `s6asm` - see the section above, if not):

```asm
s6asm -e test.s
```

Your completed program should look like this:

```asm
  .org 0x8000

  .include <stdlib> ; gives us some starting macros to use

  .res 1 letter     ; creates a register, 1-byte in size
  .res 1 counter    ; creates another 1-byte register

  mov #'A' letter   ; stores the letter 'A' into our first register
  mov #26 counter   ; stores the number 26 into our second

loop:               ; creates a named location in our program to jump
                    ; back to
  out letter        ; prints our letter to the screen
  inc letter        ; moves to the next letter in the alphabet (by
                    ; increasing its ASCII value by one)
  dbgt counter loop ; decreases our counter by one, and jumps back up
                    ; to the label if it is still greater than 0

  halt              ; exits the program, once the loop is finished
```

Note: The blank lines are not required, but they make the code easier
to read. Also, anything after the ';' is ignored by the assembler,
and is used to explain our code.

That's all it takes to start writing assembly with S6ASM. The rest of this manual contains thorough reference documentation for S6ASM, so you can always find information on the different macros and directives at your disposal, as well as everything else the assembler has to offer.

## The Pipeline

S6ASM transforms your source through a series of steps, together referred to as the _pipeline_, starting with parsing, and ending with your code actually executing in an emulator. Using command-line arguments, you can terminate the process at any one of these distinct steps. The steps are as follows:

1. Tokenisation, `-t`, - Your source code is parsed, and some syntax errors are caught.
2. Preprocessing, `-p` - Macros, local labels, immediates and other conveniences are expanded.
3. Linking, `-l` - Symbols are resolved, expressions are evaluated and some directives interpreted. The code is now made up entirely of `.byte` directives, and `subleq` instructions.
4. Assembly (default) - This simplified code is then turned into the final binary image.
5. Emulation `-e` - The image is loaded into ROM in an emulated S6, and executed.

If you choose to stop the pipeline at any point _before_ emulation, the intermediate representation, or binary image, is sent to the standard output, where you can redirect it to a file using your shell.

### Tokeniser

The tokeniser is first step in the pipeline, and is what interprets and understands your source syntax and translates it into a structured form. The tokeniser is probably the least useful part of S6ASM in isolation, despite being essential to all the subsequent stages.

How to invoke:

```sh
s6asm -t test.s
```

A line like `mov #26 a` in source would become this after tokenisation:

```asm
  mov #26 a
```

Notice that there is no change! This is because the tokeniser simply reads and parses your code. When outputting the intermediate representation, this structured form then has to be converted back to a string for display.

### Preprocessor

The preprocessor is the most significant part of S6ASM, as it is what handles most of what makes the S6 practical to program: macros, local labels, immediate values and includes.

How to invoke:

```sh
s6asm -p test.s
```

A line like `mov #26 a` in source would become this after preprocessing:

```asm
  subleq a a sub/149@done
sub/149@done:
  subleq stdlib_tmp0 stdlib_tmp0 sub/152@done
sub/152@done:
  subleq #26 stdlib_tmp0 sub/153@done
sub/153@done:
  subleq stdlib_tmp0 a sub/154@done
sub/154@done:

#26:
  .byte 26
```

There are two main sections here: the macro-expanded version of `mov`, and the immediate constants table at the bottom.

You will notice that this code is quite unreadable. That is because the preprocessor has to prefix the labels that were inside macros with something unique so that they do not collide with other macros that use the same name, or even other places where the same macro is used. In this example, the preprocessor uses this format:

```
<macro name>/<global macro invocation number>@<original label>:
```

The global macro invocation number starts at zero, and is increased by one any time a macro is used.

### Linker

The linker is what resolves labels and expressions into their final numeric values. As a result, most directives are implemented by the linker, such as `.const`, `.bank`, `.res`, and `.org`.

How to invoke:

```sh
s6asm -l test.s
```

Assuming `a` has been defined as the address `0x1234`, a line like `mov #26 a` in source would become this after linking:

```asm
  subleq 4660 4660 33206
  subleq 32512 32512 33212
  subleq 33226 32512 33218
  subleq 32512 4660 33224
  
  .byte 26
```

As you can see, there are no longer any labels, as everything has been evaluated down to their final addresses. These addresses will vary depending on where in your program the code was located.

### Assembler

The assembler is smallest part of S6ASM as a whole. Usually, when people refer to 'the assembler' in the context of S6ASM, they mean all the stages of the pipeline, together, as the assembler itself actually does very little; it simply converts the code produced by the linker into an actual binary image.

How to invoke:

```sh
s6asm test.s
```

Assuming `a` has been defined as the address `0x1234`, a line like `mov #26 a` in source would become this after assembly:

```asm
00000000: 12 34 12 34 81 b6 7f 00  .4.4....
00000008: 7f 00 81 bc 81 ca 7f 00  ........
00000010: 81 c2 7f 00 12 34 81 c8  .....4..
00000018: 1a                       .
```

By now, the S6ASM has finished with your source code and has converted it to its final binary form, ready to be loaded into ROM.

### Emulator

The emulator is often treated separately from the rest of the assembler, as it is not enabled by default, despite being a part of the pipeline. It is not a general S6 emulator, as it does not accept arbitrary binary images and is integrated into the `s6asm` CLI, instead, it automatically loads and runs the output of the assembler. This helps facilitate rapid iteration, as you can assemble and run programs immediately, with a single command, without producing any artefacts.

How to invoke:

```sh
s6asm -e test.s
```

## Syntax

S6ASM uses a very simple line-oriented syntax.

First, any line (execpt one with an `.org` directive) may be prefixed with a label. Lines with labels may not be indented, and the label must end with a colon and a space. If a label is not used, the line must be indented by any amount (this can vary arbitrarily between lines).

The rest of the line is the split into _words_, which are whitespace separated tokens. The significance of these words is decided only once the entire line is tokenised. If you need whitespace within a word, wrap that word in parentheses. You can also wrap it in single quotes, but the quotes will themselves be included in the word (character escapes are _not_ supported, and `\'` will immediately terminate the quotation). You can also include parentheses or quotes within a word. For instance, `a b(c d)` will become two words. The first contains exactly `a` and the second contains exactly `bc d`. Finally, if a semicolon is encountered outside of parentheses or quotes, then the rest of the line (including the semicolon) is discarded as a comment.

Once the line is split into words, it's meaning is decided. If the first word is exactly `subleq`, and there are 3 following words, then the line is treated as a SUBLEQ instruction, taking 3 expressions as operands (which should evaluate to valid memory addresses).

If the first word begins with a `.`, then it is treated as a directive, and it's operands are not immediately converted as expressions, but left as raw strings until they are interpreted by the respective directive handler.

If the first word is not identified as a directive, then it is instead treated as the name of a macro, and it's operands are converted to expressions.

Examples:

```asm
  .const a 0x1234 ; without a label, a line must be indented

label: subleq a b c ; any line can begin with a label

  mov #26 a ; this is treated as a macro invocation
```

### Identifiers

Any character is allowed in an identifier, with these exceptions in certain cases:

* An identifier may not begin with a '#' character, to distinguish regular identifiers from immediates

Idenfitifers have their own _namespace_, called the label namespace, which is independent of the macro namespace. This means macros and identifiers can share a name. Identifiers are a mapping from a human-readable name to a numeric value, and can be created in a few ways:

1. Labels - if a line begins with a label, then that identifier is set to the address of the line containing the label.
2. Constant - use the `.const ident val` directive to directly set the value of an identifier.
3. Banks - you can create 'registers' (global variables with static memory addresses, SUBLEQ does not have hardware registers) using the `.bank addr` and `.res size ident` directives. Read more about these in the _Syntax_ > _Directives_ section.

Once an identifier is created, it's value cannot be changed.

### Macros

Macro names must not begin with a `.`, to distinguish them from directives.

Macros are created using directives, like this:

```asm
  .macro name ...operands
    <body>
  .endmacro
```

The body of a macro is expanded wherever the macro is used (but cannot contain directives). Labels that are used inside a macro are hygienic, meaning they are automatically uniquified during expansion; see the _The Pipeline_ > _Preprocessor_ for more details on this.

The operands are not expressions, they are string names. Wherever those operands are used inside the macro's body, the values that are passed at the invocation site are substituted in it's place. You can pass arbitrary expressions as operands, and they will be substituted correctly.

### Expressions

S6ASM's expressions are one of the more unconventional features of the syntax. Specifically, they implement [Reverse Polish notation](https://en.wikipedia.org/wiki/Postfix_notation) (effectively meaning operators come after their operands).

Expressions are simply a space separated list of identifiers, literals and operators. This means that, for a simple single-token expression, parentheses are not needed to write it but, for more complex expressions, you need to wrap the entire expression in parentheses. Since RPN eliminates the need for parentheses for grouping, parentheses are treated as regular characters in an expression, and can be part of identifiers.

When an expression is evaluated (usually during the linking phase), they are interpreted using a stack and accumulator. See the article linked above for more details. These are the operators supported:

- `+`:  Addition
- `-`:  Subtraction
- `*`:  Multiplication
- `/`:  Integer division (rounds towards negative infinity)
- `>>`: Shift right
- `<<`: Shift left
- `%`:  Modulus (remainder after division)
- `&`:  Bitwise AND
- `|`:  Bitwise OR
- `^`:  Bitwise XOR

RPN is used for two reasons: to make parsing and whole-expression substitution rules simpler (no operator precedence needs to be specified) and to reduce the need for confusing nested parentheses.

### Directives

Directives are not compiled into the final binary image. Instead, they control some stage of the assembly directly.

#### `.org addr`

The `.org` directive changes the address that the following code will be assembled to. This directive is handled by the linker.

`addr` should be a valid memory address between 0x0000 and 0xffff (inclusive).

Origins should be placed in ascending order in the source code, meaning you cannot move backward. Also, the standard library internally contains an `.org 0x8000`, so, assuming you use the standard library, you are unable to assemble code for earlier addresses (earlier addresses are in RAM, so that wouldn't be particularly useful anyway).

In the final binary, null bytes are emitted between origins to correctly align the code. The first origin dictates the initial address, and padding is only emitted by subsequent origins. Since the standard library includes it's own internal origin directive, any origins in normal code will emit padding bytes.

If you choose not to include the standard library, then your code must use an origin directive before any instructions or macros. The emulator will mount your binary at address `0x8000` (the start of ROM), so that is usually where your first origin should point, or your code will not run properly).

#### `.res size ident` and `.bank addr`

The `.res` and `.bank` directives are used to automatically allocate memory addresses for variables, conventionally referred to as registers (as they are often used where a more conventional architecture would use hardware registers).

These directives are implemented by the linker, which keeps a pointer to a memory address, initialised to `0x0000`. When a `.bank` directive is encountered, this pointer is directly set to it's value. Then, when a `.res` directive is encountered, a new identifier is created with it's value equal to the current value of the linker's allocation pointer, which is then incremented by `size`.

This allows you to easily map identifiers to sequential memory, without accidentally creating overlaps, or leaving gaps.

#### `.byte expr`

The `.byte` directive is handled by the assembler, and is the last directive to be interpreted in the pipeline. At it's location, a single byte is emitted. This means that `expr` must be between -128 to 255 (negative values are represented with two's complement).

#### `.word expr`

The `.word` directive simply outputs two bytes, in big-endian order, and is handled by the linker (which substitutes it for two `.byte` directives, to pass on to the assembler). `expr` must be between -32768 to 65535 (negative values represented with two's complement).

#### `.const ident expr`

The `.const` directive simply directly sets the value of an identifier. The `expr` can be any value, although most places where an identifier can be used have their own specific restrictions on number ranges.

#### `.macro name ...operands` and `.endmacro`

These directives are used to define new macros, and are handled by the preprocessor. See the _Syntax_ > _Macros_ section for more details.

#### `.ascii str` and `.string str`

These directives are handled by the linker, and take a single string argument, which _must_ be surrounded by quotes. The ASCII bytes of the string (no other encodings are supported) are emitted one-by-one (as byte directives for the assembler).

No escape sequences are supported.

#### `.asciiz str` and `.stringz str`

These directives are the same as above, except they append a trailing null byte to the emitted data, useful as a string terminator.

#### `.include path`

The `.include` directive is handled by the preprocessor, and is substituted for the contents of another file. The `path` must either be surrounded by quotes or angled brackets. If quotes are used, then the file is searched for in the current source file's directory (relative paths are allowed), and if angled brackets are used, then the file is searched for within the assembler's standard library collection.

You cannot include the same path more than once, as this can produce duplicate definition errors, so is explicitly prohibited. If you need duplicate code, you can usually achieve this with a macro, potentially in it's own included file, if you prefer.

#### `.require path`

The `.require` directive throws a preprocessor error if a file is not included by the time the require is encountered. By using require and explicitly preventing duplicate includes (see above), consuming code is completely aware of what modules it is importing, and what is contributing to code size increases (a common problem on the S6).

### Immediates

Immediates are another feature implemented by the preprocessor.

Normally, `subleq` instructions take only memory addresses as operands, making it difficult to express operations such as increments and decrements. Without immediates, you would solve this problem by creating a label, and following it with a `.byte` directive, like this:

```asm
twenty-one: .byte 21
```

However, immediates provide a more direct solution: wherever an expression begins with a `#`, it is evaluated by the preprocessor (as opposed to the linker, as usual) and substituted by a label. The preprocessor then emits, at the end of your source, a table mapping all the immediates you used to their evaluated values, like this:

```asm
#21
  .byte 21
```

### Local Labels

S6ASM supports _local labels_ which only remain in scope for a short time, allowing you to reuse common labels names like `loop` and `done`, prefixing them with `@`.

Local labels remain in scope until the next regular label, at which point all existing local labels become innaccessible. Here is an example of local labels in action:

```asm
func1:
  mov #50 i
@loop:
  out #'A'
  dbgt i @loop

func2:
  mov #'9' c
  mov #10 i
@loop:
  out i
  dec i
  dbgt i @loop
```

Local labels _must_ be scoped to a regular label. This means that you cannot use a local label before the first regular label in your program. Macros reset this, meaning that a macro must contain a regular label before any local labels that it uses. Note that it is rare that a macro will be large enough for local labels to be useful, as macros create their own scope for regular labels anyway.

## Architecture

S6ASM is an assembler for the S6 platform. This means that, to fully understand S6ASM, you need to understand it's target machine.

The S6 is an 8-bit computer, with 16-bit addressing, distinctive because it has only a single hardware instruction: `subleq a b c`. The instruction does this:

1. Subtract the contents at address A from the contents at address B.
2. Store the result back in B.
2. If the result was less than or equal to zero (when interpreted using two's complement), the CPU branches to C (and otherwise continues to the next instruction).

Because there is only a single instruction, the S6 doesn't use opcodes. Instead, the operands are simply concatenated and placed in memory as-is. An instruction like `subleq 0x1111 0x2222 0x3333` would literally be placed in memory as `1111 2222 3333`.

This section is mostly a quick reference; for more thorough documentation of the S6 itself, see it's [design document](https://github.com/beauconstrictor/s6emu). This repository also includes a very basic reference emulator, written in C, if you learn best from seeing.

### Memory map

The S6 memory map is extremely simple:

- `0x0000` - `0x7fff`: RAM
- `0x8000` - `0xfffd`: ROM
- `0xfffe`: UART output (writes here go to the serial output)
- `0xfffe`: _Also_ the halt address, when jumped to
- `0xffff`: UART input (returns the last character recieved by the UART, or NUL if no character was recieved since the last read)

### Tape I/O

Inkeeping with the S6's very minimal philosophy, persistent storage is as simple as it possibly could be.

You can insert 'tapes' which temporarily replace the function of the UART, specifically for serial reads. While a tape is connected, serial reads will return a predefined datastream, byte by byte from the tape, rather than the regular keyboard input.

This system is intended for interactive command interpreters (like Forth, or a hex monitor), to allow programs to be installed on the machine without replacing the ROM. The idea is that you put the command interpreter in a special mode where the usual input echoing is disabled and then you can connect the tape. Since the interpreter will be listening for input, it will recieve whatever data is in the tape, and interpret it as commands of some sort. These could be regular commands for the program, or in a special tape-specific format. The tape can then send a final command that returns the interpreter to it's normal mode. This is a possible implementation; a program can use tapes in any way it needs.

There are some obvious flaws in this design (for instance, what happens if a tape is removed before it finishes being read - the software will not know to stop listening for input), but this is inevitable, as tapes are designed to be as simple as possible.

S6ASM's integrated emulator does not currently directly support tapes in any way - you will have to use your terminal emulator's copy & paste feature to approximate them.

## Error Reporting

The `s6asm` library has various internal 'types' of error, which all return different exit codes. This reference does not document exactly what errors are of which type, as that would easily double the size of this reference. To find out, just trigger that error and inspect the return type.

When an error is reported, a 'traceback' may be shown, if the location of the error was inside generated code from within a macro. In that case, the traceback will show the filenames, file numbers and macro names of every macro in the hierarchy. If a traceback is not shown, only a single file name and line number is given.

These are the types of error that `s6asm` may produce:

- Rom Error (code 3)
- Bank Error (code 4)
- Syntax Error (code 5)
- Origin Error (code 6)
- Include Error (code 7)
- Recursion Error (code 8)
- Word Width Error (code 9)
- Expression Error (code 10)
- Require Error (code 11)

To disable ANSI colour output in error messages, set the `NO_COLOR` environment variable.

## Standard Library

The standard library is a comprehensive macro library that makes developing for the S6 considerably easier. You can forego it, but you will likely find yourself creating an ad-hoc library of macros as you develop your program anyway, so it is not recommended.

The standard library turns:

```asm
       subleq z z next0
next0: subleq a z next1
next1: subleq z b next2
next2: 
```

Into:

```asm
add a b
```

In addition, the standard library is divided into various _modules_, which each implement a logical set of functionality. `stdlib` provides the base macro library that you will almost always want to include. Then, other modules provide more specific functionality, such as `stdio` for higher level I/O operations, and `stdhex` for converting to and from hex representations of bytes and words.

### Typing

Most of this section documents the macros that the standard library implements, so you should understand how they are described:

- If a macro accepts an operand and is described as directly manipulating it (such as reading or storing into it), then that operand should be a memory address (usually from an identifier). These operands are referred to as register-type. This is the only type that accepts `#`-prefixed immediates.
- If an operand is described as pointer-type, then it is first read as a register, and the value it stores is used (16-bit, big-endian) as another memory address pointing to the actual target.
- If an operand is described as label-type, then it uses its value directly as an immediate. _Do not_ pass a `#`-prefixed immediate to these operands. Instead, pass a memory address - the memory address will be converted to an immediate internally by the macro. This type is used by `lptr x y`, for example, to load the address of an identifier into a register.

Unless otherwise noted, operands are register-type.

Note that S6ASM itself does not use a typing system, so these are merely conventions, and often incorrect results will be produced if you break them, as opposed to assembler errors.

### Modules

#### `stdlib`

##### Memory layout

The assembler reserves access to RAM addresses `0x7f00` onwards for internal use - unless you absolutely know what you are doing, do not touch these addresses, as how individual macros use them is subject to change between addresses. Also, identifiers prefixed with `stdlib_` should be treated as internal, and not used. This manual does not document those identifiers, but you can see the source code for the standard library if you are curious.

##### Fundamental macros

Much of the standard library is implemented on top of a group of 'fundamental' macros, which implement the most primitive operations. Here is a list:

- `sub x y`: Subtracts X from Y; stores in y
- `clear x`: Sets X to zero.
- `add x y`: Adds X to Y; stores in y
- `inc x`:   Adds one to X; stores in X
- `dec x`:   Subtracts one from X; stores in X
- `mov x y`: Copies the contents in X into Y
- `jmp x`:   Moves program execution to X

##### Branching macros

These macros compare a value to 0. If the comparison is true, they jump to a new address. They are the simplest form of control flow.

These macros interpret X as signed registers.

- `ble x y`: Branches to Y if X <= 0
- `bgt x y`: Branches to Y if X > 0
- `beq x y`: Branches to Y if X = 0
- `bne x y`: Branches to Y if X != 0
- `dbgt x y`: Decrements X. Branches to Y if result > 0

##### Comparison macros

These macros interpret X and Y as signed registers.

- `ceq x y z`: Branches to Z if X = Y
- `cgt x y z`: Branches to Z if X > Y. Expands to an awful lot of code; use it sparingly
- `cle x y z`: Branches to Z if X <= Y. Expands to an awful lot of code; use it sparingly

##### Special macros

These macros perform miscellaenous specialised actions.

- `halt`:   Immediately shuts down the machine by jumping to `halt`
- `freeze`: Enters the machine into an endless loop. You can also jump to `freeze` to do this
- `out x`:  Outputs X as an ASCII value
- `in x`:   Sets X to the value in the serial input register
- `pin x`:  Waits for a character from the serial and sets X to it

##### 16-bit helpers

These macros wrap some of the other macros to implement 16-bit operations. That means that some of these macros take _wide_ registers, which are made up of 2-bytes, in big-endian order. These wide registers are referred to as _words_.

- `lptr x y`:  Load the address X into word Y. X is label-type
- `movw x y`:  Copy word X into word Y
- `incw x`:    Add one to the word X
- `decw x`:    Subtract one from the word X
- `addbw x y`: Add the normal register X to the word Y; stores in Y

##### Self-modifiers

These macros take pointer-type operands, implementing indirect addressing.

They are usually quite slow and expand to a lot of code, so use them sparingly.

- `jtp x`: Jump through pointer X
- `ld x y`: Copy the value in pointer X to register Y.
- `ldw x y`: Copy the word in pointer X to wide register Y.
- `st x y`: Store the value in register X to pointer Y.

##### Bitwise macros

Currently, only bitwise NOT is supported, as bitwise operations are extremely complicated to implement in SUBLEQ. When other operations are supported, they will likely be the slowest, biggest macros in the standard library.

- `not x y`: Store the bitwise NOT of X in Y (Y can be the same as X)

##### Constants

The standard library defines these constants:

- `in`: The serial input register, `0xffff`
- `out`: The serial output register, `0xfffe`
- `halt`: The machine shutdown address, `0xfffe`
- `freeze`: Jump here enter an infinite loop. The value is not fixed.
- `_`: This is a register conventionally used for results that will be discarded. For example, you can use `pin _` to pause for input, but discard the key.

#### `stdhex`

The module requires `stdilb`.

`stdhex` implements conversion macros for hexadecimal. This module currently employs a very large (1K) lookup table to assist in these conversions, so you should be aware of this before including. These macros are implemented:

- `hex_out x`: Output (to the serial port) the register X
- `hexw_out x`: Output (to the serial port) the wide register X
- `from_hex x y z`: Store in Y the byte represented by the two ASCII characters in the wide register X. If the hex is invalid, branches to Z

#### `stdio`

This module requires `stdlib`.

`stdio` implements these high-level I/O macros:

- `print x`: Print the null-terminated string starting at register X
- `iprint x`: Print the null-terminated string starting at ptr X
- `gets x`: Read a line of input from the serial port, and store it in the buffer starting at X. This macro is vulnerable to buffer overflows.
- `gets_t x`: Read a line of input from the serial port, without echoing, and store it in the buffer starting at X. This macro is vulnerable to buffer overflows. This is a variant of `gets x` intended for tape I/O.

## Undocumented Areas

As S6ASM is still in development, new features are arriving faster than documentation can keep up with. As such, some newer features do remain undocumented for a time; here is a list of those features:

- S6ASM programming conventions
