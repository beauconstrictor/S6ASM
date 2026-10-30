  .include <stdlib>

  .const c 0x0000
  .const s 0x0001

  mov #(1 msg 8 >> *) s
  mov #(1 msg 0xff & *) (s 1 +)
loop:
  ld s c
  ble c done
  out c
  inc (s 1 +)
  jmp loop
done:
  halt

msg:
  .ascii "Hello, world!"
  .word 0x0a00
