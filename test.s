  .include <stdlib>

  .const c 0x0000

  mov message c
print:
  out c
  halt

message:
  .asciiz "Hello, world!"
