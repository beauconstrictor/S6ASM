  .include <stdlib>

  .const c 0x0000
  .const i 0x0001

alphabet:
  mov #'a' c
  mov #26 i
@loop:
  out c
  inc c
  dbgt i @loop
  halt

test:
  out #'A'
@loop:
  out #'B'
  jmp @loop
