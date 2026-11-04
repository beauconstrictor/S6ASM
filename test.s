  .org 0x1000

  .include <stdlib>

  .res 1 i
  .res 1 c

  mov #26 i
  mov #'A' c

loop:
  out c
  inc c
  dbgt c loop
  jmp 0x8000
