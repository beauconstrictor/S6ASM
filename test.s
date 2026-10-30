  .include <stdlib>

  .res 1 c
  .res 2 s

print:
  lptr msg s
@loop:
  ld s c
  ble c input
  out c
  incw s
  jmp @loop

  movw 0x0000 0x0000

input:
  pin c
  bcp c #'q' halt
  out c
  jmp input

msg:
  .string "Enter text:"
  .byte 0x0a
  .asciiz "> "
