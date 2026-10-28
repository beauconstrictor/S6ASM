  .include <stdlib>

  .const c 0x0000

print:
  mov (message 1 +)c
  out c
  halt

message:
  .asciiz "Hello, world!"
