  .include <stdlib>

  .const c 0x0000
  .const i 0x0001

  mov #26  i
  mov #'A' c
loop:
  out c
  inc c
  djnz i loop
  jmp halt
