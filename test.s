  .include <stdlib>

  .const i 0x0001

  mov #0 i
loop:
  beq i zero
  out #32 
  jmp next
zero:
  out #'#'
next:
  inc i
  jmp loop
