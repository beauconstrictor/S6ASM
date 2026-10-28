  .include <stdlib>

  .const c 0x0000

  mov message c
print:
  add #4 c
  out c
  halt

message:
  .asciiz "Hello, world!"
