  .include <stdlib>

  .res 1 c
  .res 2 s

  lptr msg s
loop:
  ld s c
  ble c done
  out c
  incw s
  jmp loop
done:
  halt

msg:
  .string "Hello, world!"
  .word 0x0a00
