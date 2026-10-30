  .include <stdlib>

  .const c 0x0001
  
  ld char_addr c
  out c
  halt

char_addr:
  .word char

char:
  .byte 'A'
