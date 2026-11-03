  .include <stdlib>
  .include <stdhex>
  .include <stdio>

  .res 1 byte

  .res 256 buf

start:
  print prompt
  gets buf

received:
  cne (buf 2 +) #0 fail
  from_hex buf byte fail
  print received_msg
  hex_out byte
  out #0x0a
  jmp start

fail:
  print fail_msg
  jmp start

prompt:
  .asciiz "Enter a byte in hex: "
received_msg:
  .asciiz "You typed: "
fail_msg:
  .string "Enter a single hex byte!"
  .word 0x0a00
