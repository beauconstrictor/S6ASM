# S6ASM

`s6asm` is an assembler (and integrated emulator) for the [Ozpex S6](https://github.com/beauconstrictor/s6emu), a computer architecture built around a single 6-byte instruction, called `subleq`.

This assembler is a very simple macro assembler that compiles to raw binary output that you can load into an [emulator](https://beauconstrictor/s6emu). The assembler features a 'standard library' of sorts, which includes a large array of macros to make developing for this otherwise very esoteric architecture more manageable.

# Getting Started

First, install S6ASM using `pip`:

```
python -m pip install git+https://github.com/beauconstrictor/s6asm.git
```

This sample program prints the uppercase alphabet:

```
  .include <stdlib>

  .const c 0x0000
  .const i 0x0001

  mov #26  i
  mov #'A' c
loop:
  out c
  inc c
  dbgt i loop
  jmp halt
```

You'll notice that there isn't a single `subleq` instruction in sight; this is because, while the instruction is available to you, it is much more common to use one of the macros the stdlib provides, which all expand ultimately to a series of `subleq`s anyway.

To assemble this program, assuming you have saved the sample program as 'test.s':

```
s6asm test.s > test.bin
```

You can then load the binary into an S6 emulator. This is how you would do that in `s6emu`:

```
s6emu test.bin
```

S6ASM also includes an integrated S6 emulator, so you can run an assembly program directly:

```
s6asm -e test.s
```

This emulator has considerably worse performance than `s6emu`, so it is recommended to switch to it once your program grows.

## Syntax

This assembler uses a very simple syntax. Lines are either indented with whitespace, or start with a `:`-terminated label, like this:

```
label: subleq a b c
  subleq a b c
```

Then, instructions are either preceeded by a `.`, in which case they are a *directive*, which signals something to the assembler itself, or not. In that case, the instruction can be `subleq`, or a macro (optionally followed by some number of operands), which will be expanded to a series of `subleq`s.

Comments are marked with a `;`. Anything after a semicolon, assuming that semicolon is not inside quotes or parentheses will be ignored by the assembler.

### Directives

The assembler includes various directives (instructions prefixed with a `.`), which allow you to do things that aren't regular instructions. Here is a list of the common ones:

- `.byte x`: Insert a single byte of data.
- `.word x`: Insert a 16-bit word of data (big endian).
- `.const x y`: Replace instances of `x` later in the program with instances of `y`.
- `.include "path"`: include the contents of another source file.
- `.org`: Move forward to a new address, inserting NULLs as needed.

### Literals and Expressions

Where a number is expected, you can enter it in one of 3 formats:

- Characters: Surround a character in single quotes, and it's ASCII value is used
- Hex: Preceed a number with `0x` to express it in hex 
- Binary: Preceed a number with `0b` to express it in binary 
- Decimal: Write a number as-is to express it in decimal

You can also use expressions on these literals. To mark an expression, wrap it in parentheses. You must use spaces between your operators and numbers.

Notably, expressions they must be written in [postfix notation](https://en.wikipedia.org/wiki/Reverse_Polish_notation). For example, to jump to a label, but skipping the first instruction after that label (remember that instructions are 6 bytes long):

```
  .const INST_WIDTH 6
  jmp (label INST_WIDTH +)
```

### Immediates

`subleq` instructions (and usually the macros built on top of them) expect values to be passed as memory addresses. For instance, if you want to subtract a 1 from a value in memory, there has to be a one stored somewhere in memory for you to use. You can achieve this directly, using a label and a `.byte` directive, but `s6asm` makes it much more direct: prefix any 8-bit expression with a `#`, and the assembler will arrange for the result of that expression to be included in the binary, after your program code, and the expression will be substituted with the memory address of the resulting value. Here is an example:

```
add #1 x
add #(1 4 <<) y
```

Some examples:

```
  mov #0x0a x
  out #'A'
  add #1 y
```

### Macros, Constants and  Namespaces

The assembler has two main namespaces: one for macros, and one for labels and constants. These namespaces are entirely separate, meaning you can have two different things in both namespaces with the same name. The standard library uses this to create constants referencing memory addresses, and macros that use those addresses:

```
  mov #'A' out ; writing something to out prints it
  out #'A'     ; the out macro does that for you
```

The labels & constants namespace contains a map of names to 16-bit numbers (almost always addresses, although not always, if they are passed to directives, for example), which are ultimately passed as operands to `subleq` instructions. You can create one of these directly, as a constant like this:

```
  .const something 5
  add something x ; adds whatever is in address 5 to x
```

You can also use a label, which represents the address that a certain instruction will end up in memory. This is usually useful for jumps or storing some data to be referenced in code:

```
loop:
  out #'A'
  jmp loop ; will jump to the address of the 'out' macro.

hi:
  .byte 'H'
  .byte 'i'
  .byte '\0'
```

If you prefix the name of a label with a `@`, then it becomes a 'local' label. This means that it only remains in scope until the next normal label, allowing you to use reuse common label names like this:

```
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

The macros namespace contains a map of names to a sequence of lines of code, as well as a list of parameters. This allows you to call a macro and pass it some arguments, wherever the original macro definition used it's parameters:

```
  .macro sub x y
    subleq x y done
done:
  .endmacro

  sub #3 a

  ; will expand to:

  subleq #3 a done
done:
```

It is worth nothing that labls are macro-local. This means that you can reuse the same label name in multiple macros, and use a single macro more than once. None of these will cause a name collision. This is because, under the hood, the assembler actually changes the name of labels when expanding macros to ensure that they stay unique.

### Tokenisation

When a line of assembly is being tokenised, it is first split into *words*. The position of these words then indicates it's meaning (i.e. a label, a directive, an operand, etc.). Ordinarily, words are simply separated by spaces, but there are 3 special characters that change this:

- `(` & `)` - Between two parentheses, spaces do not delimit words, and the parentheses themselves are not included in the words. This means a line like `(2 1 +) (3 4)` will become two words: `2 1 +` and `3 4`.
- `'` - Between two quotes, spaces do not delimit words, but the spaces are still included in the word. This means a line like `(#' ' 3 +)` will become the single word `#' ' 3 +`.

## The Standard Library

The standard library, included with `  .include <stdlib>`, provides a comprehensive set of macros that make development for the S6 feel more like developing for a conventional 8-bit computer.

For example, if you wanted to clear a register (memory address) without the `stdlib`:

```
  subleq x x done
done:
```

With the `stdlib`:

```
  clear x
```

The biggest advantage of macros is that it avoids `subleq`'s characteristic 'death by labels'. You see, `subleq` encodes 4 distinct actions into a single instruction:

1. Negation
2. Addition
3. Jumping
4. Conditionals

Much of the `stdlib` centres around isolating those actions (addition by double negation, jumping by ensuring the condition is always true, etc.) into reusable macros. Without those macros, whenever you want a `subleq` without a jump, you actually just jump to the next instruction. The problem with this is that is means you need a label. For almost every instruction. As you can imagine, this gets ugly fast, so the macro system hides this from you. Even without the `stdlib`, you will find yourself writing a very large number of macros as your code grows.

### Foregoing the `stdlib`

You *can* use this assembler without the standard library. Without it, you have to start with program with an `.org` directive, which tells the compiler where the program will be loaded in memory. This should usually be `0x8000`:

```
  .org 0x8000
```

And finally, you will need to define constants for the various features of the S6's memory map:

```
  .const out 0xfffe
  .const in  0xffff
  ; etc...
```

## Pipeline

The assembler transforms the code into a binary in several distinct steps.:

1. Tokenisation - Converts the plaintext program into structured data for the assembler to use.
2. Preprocessing - Expands macros and adds the contents of included files.
3. Linking - The assembler decided where in memory instructions and data will be placed.
4. Assembly - The assembler produces a final binary image.
5. (Optionally) Emulation - The assembler loads the binary into a simulated S6 and executes it.

Using command line flags, you can tell the assembler to stop at any particular stage, in which case it will output an intermediate representation.

## License

This project is licensed under the GNU GPL-2.0
