  .include <stdlib>

  .res 1 c
  .res 2 s

  lptr msg s
loop:
  ld s c
  ble c halt
  out c
  incw s
  jmp loop

msg:
  .string "Hello, world!"
  .word 0x0a00
