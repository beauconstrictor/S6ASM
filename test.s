  .org 0x8000

  .include <base.s>

  ; constants
  .const seri 0xffff
  .const sero 0xfffe
  .const halt 0xfffe

  ; registers, ordered in descending order of lifetime
  .const z    0x0000
  .const r    0x0001
  .const s    0x0002

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

  ; stores in y
  .macro mov x y
    clear y
    add x y
  .endmacro

  .macro jmp x
    subleq z z x
  .endmacro

  ; decrement x, jump to y
  .macro djnz x y
    subleq #1 x done
    jmp y
done:
  .endmacro

  .macro inc x
    add #1 x
  .endmacro

  .macro dec x
    add #0xff x
  .endmacro

start:
  mov #26 r
  mov #'A' s
loop:
  mov s sero
  inc s
  djnz r loop
  jmp halt

  ; immediates
#1:
  .byte 1
#26:
  .byte 26
#'A':
  .byte 'A'
#0xff:
  .byte 0xff
