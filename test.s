  ; syntax:
  ;
  ; :1234 12 34 56 78
  ; :1234?
  ; :1234>5678
  ; 
  ; read a char and then:
  ; - if a ?, print in hex the byte at addr and increment addr
  ; - if a a, print in ascii the byte at addr and increment addr
  ; - if a !, jmp to addr
  ; - if a ., halt
  ; - if a /, print the addr as hex
  ; - if a space, skip to next char
  ; - if a null, read a new line
  ; - if a ':', read 4 chars as hex to set addr
  ;   if a >, read 4 chars as hex and TODO
  ; - otherwise, read 2 chars and write them to addr, then increment addr
  ; then, repeat.

  .include <stdlib>
  .include <stdhex>
  .include <stdio>

  .res 256 buf
  .res 2 parse
  .res 2 addr
  .res 1 byte
  .res 2 c

  .macro readc x y
    ld x y
    incw x
  .endmacro

start:
  lptr 0x1000 addr
  print welcome

readline:
  out #0x0a
  gets buf
  lptr buf parse

execute:
  readc parse c
  ceq c #'.' halt
  ceq c #0x20 execute
  ceq c #'?' @read_byte
  ceq c #'a' @read_ascii
  ceq c #'!' @jump_to
  ceq c #'/' @read_addr
  ceq c #':' @goto
  ceq c #0x00 readline

; falls through to here
@write_byte:
  readc parse (c 1 +)
  from_hex c byte @fail
  st byte addr
  incw addr
  jmp execute

@fail:
  print fail_msg
  jmp readline

@read_byte:
  ld addr byte
  hex_out byte
  out #0x20
  incw addr
  jmp execute

@read_ascii:
  ld addr byte
  out byte
  out #0x20
  incw addr
  jmp execute

@jump_to:
  jtp addr

@read_addr:
  hexw_out addr
  out #0x20
  jmp execute

@goto:
  readc parse c
  readc parse (c 1 +)
  from_hex c addr @fail
  readc parse c
  readc parse (c 1 +)
  from_hex c (addr 1 +) @fail
  jmp execute

welcome:
  .string "S6MON v0.1.0"
  .word 0x0a0a
  .string "OK"
  .byte 0x00
fail_msg:
  .string "SORRY?"
  .byte 0x00
