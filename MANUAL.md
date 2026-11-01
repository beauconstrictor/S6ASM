# S6ASM Complete Manual

___This manual is unfinished.__

S6ASM is a comprehensive, albeit immature, macro assembler and development toolchain for the Ozpex S6 platform.

## Outline

- Introduction
    - What S6ASM is
    - How to install it
    - First program
- The Pipeline
    - Parser
    - Preprocessor
    - Linker
    - Emulator
- Syntax
    - Parsing
    - Directives
    - Macros
    - Expressions
    - Labels
- Architecture
    - SUBLEQ
    - Memory map
    - Serial I/O
    - Tape I/O
- Error Reporting
    - Messages
    - Tracebacks
    - Exit Codes
- Standard Library
    - Memory layout
    - Fundamental macros
    - Branches
    - Comparisons
    - 16-bit helpers
    - Special macros

## Introduction

### What S6ASM is

S6ASM is primarily a simple macro assembler for the Ozpex S6 platform, but with considerable surrounding machinery, and a powerful preprocessor that handles macros, locals and other conveniences.

The [Ozpex S6](https://github.com/beauconstrictor/s6emu) is a minimal computer architecture and platform, designed to demonstrate the smallest possible set of functionality that constitutes a computer, eschewing hardware complexity in favour of software.

S6ASM takes your source code through a short pipeline, each stage building on the last and transforming the code, until you eventually end up with a binary image. There is then an optional final stage that simulates an S6 in software and loads your binary image into it. You can explicitly stop the assembly at any point in this pipeline to view it's output.

### How to install it

S6ASM is written in Python, and requires version 3.12 or above. To install it with `pip`:

```
python -m pip install git+https://github.com/beauconstrictor/s6asm.git
```

Once you've installed `s6asm`, try running it like this:

```
s6asm -v
```

This shold output your installed version of `s6asm`.

### First program
