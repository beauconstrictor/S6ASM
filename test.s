  .include <stdlib>

  .const c 0x0000
  .const s 0x0001

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
