  .org 0x1000

  .include <stdlib>

  .res 1 i
  .res 1 c

  mov #26 i
  mov #'a' c

loop:
  out c
  inc c
  dbgt i loop
  out #0x0a
  jmp 0x8000
