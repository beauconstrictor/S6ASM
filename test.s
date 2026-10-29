  .include <stdlib>

  .const c 0x0000
  .const i 0x0001

  mov #('B' 1 -) c
  mov #(13 2 *) i
loop:
  out c
  inc c
  djnz i loop
  halt
