  .org 0x8000

  ; constants
  .const halt 0xfffe
  .const seri 0xfffe
  .const sero 0xffff

  ; variables
  .const z    0x0000

  .macro clear_z
    subleq z z done
done:
  .endmacro

  .macro halt
    subleq z z halt
  .endmacro

start:
  clear_z
  ; negate a and put it in z
  subleq a z after_first_negate
after_first_negate:
  ; negate z (so positive a) and put it in serial
  subleq z seri halt
done:
  halt

  ; constants
a: .byte 'A'
