  .include <stdlib>

  .const c 0x0000
  .const i 0x0001

  mov #'a' c
  mov #26 i
loop:
  out c
  inc c
  djgt i loop
  halt
