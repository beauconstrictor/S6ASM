# S6ASM

`s6asm` is an assembler for the SUBLEQ-6, a computer architecture that uses the [SUBLEQ ISA](https://esolangs.org/wiki/Subleq); essentially an ISA that uses only a single instruction (meaning the actual opcode is implied leaving only the 3 16-bit operands - hence SUBLEQ-6, after the 6-byte fixed width instructions).

This assembler is a very simple macro assembler that compiles to raw binary output that you can load into an [emulator](https://beauconstrictor/s6emu). The assembler features a 'standard library' of sorts, which includes a large array of macros to make developing for this otherwise very esoteric architecture more manageable.
