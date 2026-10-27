  .org 0x8000 

; constants
  .const in 0xffff
  .const out 0xfffe
  .const halt 0xfffe

  ; ram addresses from 0x7f00 onward are reserved for the stdlib
  .const z    0x7f00

  .const ijp     0x7f01

  .macro clear x
    subleq x x done
done:
  .endmacro

  ; stores in y
  .macro add x y
    clear z
    subleq x z negated
negated:
    subleq z y done 
done:
  .endmacro

  .macro inc x
    add #1 x
  .endmacro

  ; stores in y
  .macro sub x y
    subleq x y done
done:
  .endmacro

  .macro dec x
    sub #1 x
  .endmacro

  ; stores in y
  .macro mov x y
    clear y
    add x y
  .endmacro

  .macro out x
    add x out
  .endmacro

  .macro jmp x
    subleq z z x
  .endmacro

  ; indirect jump to 0x
  .macro ijp addr
    mov (addr) (ijp 4 +)
    mov (addr 1 +) (ijp 5 +)
    jmp _ijp
  .endmacro

  .macro halt
    jmp halt
  .endmacro

  ; decrement x, jump to y
  .macro djnz x y
    subleq #1 x done
    jmp y
done:
  .endmacro

_start:
  ; a jmp instruction is effectively 0x0000 0x0000 0xADDR
  ; so we just encode that here in memory, for indirects
  clear ijp
  clear (ijp 1 +)
  clear (ijp 2 +)
  clear (ijp 3 +)
