  .include <stdlib>
  .include <stdhex>

  ; this is a massive unit test for most the stdlib. run it and follow
  ; this instructions.

  .res 2 print_str
  .res 2 print_char

  .res 1 byte

  .macro print msg
    lptr msg print_str
loop:
    ld print_str print_char
    ble print_char done
    out print_char
    incw print_str
    jmp loop
done:
  .endmacro

get_input:
  print @prompt
 
  ; TODO: actual hex input
  pin _
  out #'e'
  pin _
  out #'a'

  mov #0xea byte
  jmp received
@prompt:
  .asciiz "Enter a byte in hex: "

received:
  print @msg
  hex_out byte
  out #0x0a
  halt
@msg:
  .byte 0x0a
  .asciiz "You typed: "
