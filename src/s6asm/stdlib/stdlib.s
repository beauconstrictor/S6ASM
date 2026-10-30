  .org 0x8000 

  ; MEMORY MAP
  .const in 0xffff
  .const out 0xfffe
  .const halt 0xfffe

  ; ram addresses from 0x7f00 onward are reserved for the stdlib

  ; REGISTERS

  ; increasing layers of macros have to use the registers increasingly
  ; low in this list
  .const stdlib_zero 0x7f00    ; 1B
  .const stdlib_tmp1 0x7f01    ; 1B
  .const stdlib_tmp2 0x7f02    ; 1B

  ; SELF-MODIFIERS
  ;
  .const ijp  0x7f80 ; -0x7f85 6B
  .const ld   0x7f86 ; -0x7f82 12B

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
    clear stdlib_zero
    sub x stdlib_zero
    sub stdlib_zero y
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
    subleq stdlib_zero stdlib_zero x
  .endmacro

  ; doesn't jump to addr, jumps to the address at addr,
  ; where addr contains the high byte and addr + 1 contains the low
  ; byte
  .macro ijp addr
    mov (addr) (ijp 4 +)
    mov (addr 1 +) (ijp 5 +)
    jmp _ijp
  .endmacro

  ; the value in ((*x << 8)| *(x + 1)) points to the value to move into y
  .macro ld x y
    clear stdlib_tmp1
    ; writes this:
    ;         *x     0x7f01 0x7f0c
    ; 0x7f0c: 0x7f00 0x7f00 done
    mov x ld
    mov (x 1 +)            (ld 1 +)
    mov #0x7f              (ld 4 +)
    mov #0x8c              (ld 5 +)
    ; the 1 ... * is a hack to make 'done' get substituted properly
    ; during acro expansion. live laugh love s6asm
    mov #(1 done 8 >> *)   (ld 10 +)
    mov #(1 done 0xff & *) (ld 11 +)
    jmp ld
done:
    ; the value we want is now in stdlib_tmp1, negated
    clear y
    sub stdlib_tmp1 y
  .endmacro

  ; BRANCHING OPERATIONS

  ; branches to y if x is <= stdlib_zeroero
  .macro ble x y
    subleq #0 x y
  .endmacro
  
  ; branchs to y if x is > stdlib_zeroero
  .macro bgt x y
    ble x done
    jmp y
done:
  .endmacro

  ; branches to y if x == 0
  .macro beq x y
    bgt x done
    mov x stdlib_tmp1
    inc stdlib_tmp1
    ble stdlib_tmp1 done
    jmp y
done:
  .endmacro

  ; decrements x, then branches to y if x is greater than stdlib_zeroero
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

  mov #0x7f (ld 2 +)
  mov #0x01 (ld 3 +)
  mov #0x7f (ld 6 +)
  clear     (ld 7 +)
  mov #0x7f (ld 8 +)
  clear     (ld 9 +)
