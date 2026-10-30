  .org 0x8000 

  ; MEMORY MAP
  .const in 0xffff
  .const out 0xfffe
  .const halt 0xfffe

  .const alloc 0x0000

  ; REGISTERS

  ; ram addresses from 0x7f00 onward are reserved for the stdlib
  .const z 0x7f00    ; 1B
  .const ijp  0x7f01 ; 6B
  .const ld   0x7f07 ; 6B

  ; FUNDAMENTAL OPERATIONS

  ; stores in y
  .macro sub x y
    subleq x y done
done:
  .endmacro

  .macro clear x
    sub x x
  .endmacro

  ; stores in y
  .macro add x y
    clear z
    sub x z
    sub z y
  .endmacro

  .macro inc x
    sub #-1 x
  .endmacro

  .macro dec x
    sub #1 x
  .endmacro

  ; stores in y
  .macro mov x y
    clear y
    add x y
  .endmacro

  .macro jmp x
    subleq z z x
  .endmacro

  ; doesn't jump to addr, jumps to the address at addr,
  ; where addr contains the high byte and addr + 1 contains the low
  ; byte
  .macro ijp addr
    mov (addr) (ijp 4 +)
    mov (addr 1 +) (ijp 5 +)
    jmp _ijp
  .endmacro

  ; BRANCHING OPERATIONS

  ; jumps to y if x is <= zero
  .macro ble x y
    subleq #0 x y
  .endmacro
  
  ; jumps to y if x is > zero
  .macro bgt x y
    ble x done
    jmp y
done:
  .endmacro

  ; decrements x, then branches to y if x is greater than zero
  .macro dbgt x y
    ; could implement this using dec and bgt, but it would be bigger
    ; than necessary
    subleq #1 x done
    jmp y
done:
  .endmacro

  ; SPECIAL OEPRATIONS

  .macro halt
    jmp halt
  .endmacro

  .macro out x
    add x out
  .endmacro

  ; SETUP CODE

_start:
  ; a jmp instruction is effectively 0x7f00 0x7f00 0xADDR
  ; so we just encode that here in memory, for indirects
  mov #0x7f  ijp
  clear     (ijp 1 +)
  mov #0x7f (ijp 2 +)
  clear     (ijp 3 +)
