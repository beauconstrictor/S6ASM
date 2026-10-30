  .include <stdlib>

  .res 1 c
  .res 2 s

  lptr msg s
loop:
  ld s c
  ble c done
  out c
  inc (s 1 +)
  jmp loop
done:
  halt

msg:
  .string "Hello, world!"
  .word 0x0a00
