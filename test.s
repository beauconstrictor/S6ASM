  .org 0x8000

  ; constants
  .const halt 0xfffe
  .const seri 0xfffe
  .const sero 0xffff

  ; variables
  .const z    0x0000

  .macro clear x
    subleq x x done
done:
  .endmacro

  .macro clear_z
    clear z
test:
    subleq z z test
  .endmacro

  .macro halt
    subleq z z halt
  .endmacro

  .macro mov a b
    subleq z z cleared
cleared:
    subleq a z negated
negated:
    subleq z b done
done:
  .endmacro

start:
  clear z
  mov a seri
  mov a seri
  halt

  ; constants
a: .byte 'A'
