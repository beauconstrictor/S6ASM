  .include <stdlib>

  .res 1 c
  .res 2 s

print:
  lptr msg s
@loop:
  ld s c
  ble c freeze
  out c
  incw s
  jmp @loop

input:
  pin c
  out c
  jmp input

msg:
  .string "Enter text:"
  .byte 0x0a
  .asciiz "> "
