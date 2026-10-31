  .org 0x8000 

  ; MEMORY MAP
  .const in 0xffff
  .const out 0xfffe
  .const halt 0xfffe

  ; ram addresses from 0x7f00 onward are reserved for the stdlib

  ; REGISTERS

  ; increasing layers of macros have to use the registers increasingly
  ; low in this list
  .bank 0x7f00
  .res 1 stdlib_zero
  .res 1 stdlib_tmp1
  .res 1 stdlib_tmp2

  ; SELF-MODIFIERS
  ; i could use bank and res here, but const makes the actual
  ; addresses clearer, which is good when using them directly
  .const jtp 0x7f80 ; -0x7f85  6B
  .const ld  0x7f86 ; -0x7f91 12B
  .const st  0x7F92 ; -0x7fa3 18B

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

  ; branches to y if x != 0
  .macro bne x y
    bgt x y
    mov x stdlib_tmp1
    inc stdlib_tmp1
    ble stdlib_tmp1 y
  .endmacro

  ; decrements x, then branches to y if x is greater than stdlib_zeroero
  .macro dbgt x y
    ; could implement this using dec and bgt, but it would be bigger
    ; than necessary
    subleq #1 x done
    jmp y
done:
  .endmacro

  ; branches to z if x = y
  .macro bcp x y z
    mov x stdlib_tmp2
    sub y stdlib_tmp2
    beq stdlib_tmp2 z
  .endmacro

  ; SPECIAL OEPRATIONS

  .macro halt
    jmp halt
  .endmacro

  .macro out x
    add x out
  .endmacro

  ; write an inputted char to x, or 0 if there isn't one
  ; char is always < 128, so you can use bgt
  .macro in x
    mov in x
  .endmacro

  ; pause and wait for a char
  .macro pin x
wait:
    in x
    beq x wait
  .endmacro

  .macro freeze
    jmp freeze
  .endmacro

  ; 16-BIT HELPERS

  ; load the address of label x into y
  .macro lptr x y
    mov #(1 x 8 >> *) y
    mov #(1 x 0xff & *) (y 1 +)
  .endmacro

  ; move word x into word y
  .macro movw x y
    mov x y
    mov (x 1 +) (y 1 +)
  .endmacro

  .macro incw x
    inc (x 1 +)
    bne x done
    inc x
done:
  .endmacro

  .macro decw x
    beq x wont_carry
    dec (x 1 +)
    dec x
    jmp done
wont_carry:
    dec (x 1 +)
done:
  .endmacro

  ; SELF-MODIFIERS

  ; doesn't jump to addr, jumps to the address at addr,
  ; where addr contains the high byte and addr + 1 contains the low
  ; byte
  .macro jtp x
    ; writes this:
    ;         0x7f00 0x7f00 x
    movw x (jtp 4 +)
    jmp jtp
  .endmacro

  ; the value in x points to the value to move into y
  .macro ld x y
    clear stdlib_tmp1
    ; writes this:
    ;         x      0x7f01 0x7f8c
    ; 0x7f8c: 0x7f00 0x7f00 done
    movw x ld
    lptr done (ld 10 +)
    jmp ld
done:
    ; the value we want is now in stdlib_tmp1, negated
    clear y
    sub stdlib_tmp1 y
  .endmacro

  ; the value in x is moved to what the value in y points to
  .macro st x y
    clear stdlib_tmp2
    sub x stdlib_tmp2
    ; writes this:
    ;       y      y      jmp1
    ; jmp1: 0x7f01 y      jmp2
    ; jmp2: 0x7f00 0x7f00 done
    movw y           (st  0 +)
    movw y           (st  2 +)
    movw y           (st  8 +)
    lptr done        (st 16 +)
    jmp st
done:
  .endmacro

  ; SETUP CODE

  mov #0x7f  jtp
  clear     (jtp 1 +)
  mov #0x7f (jtp 2 +)
  clear     (jtp 3 +)

  lptr stdlib_tmp1 (ld 2 +)
  lptr (ld 6 +)    (ld 4 +)
  mov #0x7f        (ld 6 +)
  clear            (ld 7 +)
  mov #0x7f        (ld 8 +)
  clear            (ld 9 +)

  lptr (st  6 +)   (st  4 +)
  lptr stdlib_tmp2 (st  6 +)
  lptr (st 12 +)   (st 10 +)
  mov  #0x7f       (st 12 +)
  clear            (st 13 +)
  mov  #0x7f       (st 14 +)
  clear            (st 15 +)

  jmp _start

freeze:
  jmp freeze

  .bank 0x0000
_start:
