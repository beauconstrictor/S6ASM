  .include <stdlib>

  .res 1 c
  .res 2 s

  .macro print msg
    lptr msg s
loop:
    ld s c
    ble c done
    out c
    incw s
    jmp loop
done:
  .endmacro

  print prompt
input:
  pin c
  bcp c #'q' bye
  out c
  jmp input
bye:
  print bye_msg
  halt

prompt:
  .string "Enter text:"
  .byte 0x0a
  .asciiz "> "
bye_msg:
   .byte 0x0a
   .string "Bye!"
   .word 0x0a00
