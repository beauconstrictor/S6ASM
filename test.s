  .include <stdlib>

  .const c 0x0000

  mov #'A' c
print:
  out c
  halt

message:
  .asciiz "Hello, world!"
