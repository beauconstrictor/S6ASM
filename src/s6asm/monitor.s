  ; syntax:
  ;
  ; :1234 12 34 56 78
  ; :1234?
  ; :1234>56
  ; 
  ; read a char and then:
  ; - if a ?, print in hex the byte at addr and increment addr
  ; - if a ~, print in ascii the byte at addr and increment addr
  ; - if a !, jmp to addr
  ; - if a ., halt
  ; - if a /, print the addr as hex
  ; - if a space, skip to next char
  ; - if a null, read a new line
  ; - if a ':', read 4 chars as hex to set addr
  ; - if a l, ensure they typed 'load' and set tape to 0x01
  ; - if a r, set tape to 0x00
  ; - if a >, read 4 chars as hex and dump the addresses to the value, exclusive, leaving addr as the value
  ; - otherwise, read 2 chars and write them to addr, then increment addr
  ; then, repeat.
  
  .org 0x8000

  .include <stdlib>
  .include <stdhex>
  .include <stdio>

  .res 1 counter
  .res 256 buf
  .res 2 parse
  .res 2 addr
  .res 2 target
  .res 1 byte
  .res 1 tape
  .res 2 c

  .macro readc x y
    ld x y
    incw x
  .endmacro

start:
  lptr 0x1000 addr
  mov 0x00 tape
  print welcome

readline:
  lptr buf parse
  ble tape not_in_tape
  gets_t buf
  jmp execute
not_in_tape:
  out #0x0a
  gets buf

execute:
  readc parse c
  ceq c #'.' halt
  ceq c #0x20 execute
  ceq c #'?' read_byte
  ceq c #'~' read_ascii
  ceq c #'!' jump_to
  ceq c #'/' read_addr
  ceq c #':' goto
  ceq c #'l' begin_tape_read
  ceq c #'r' return_from_tape
  ceq c #'>' dump
  ceq c #0x00 readline

; falls through to here
write_byte:
  readc parse (c 1 +)
  from_hex c byte fail
  st byte addr
  incw addr
  jmp execute

fail:
  print fail_msg
  jmp readline

read_byte:
  ld addr byte
  hex_out byte
  incw addr
  out #0x20
  jmp execute

read_ascii:
  ld addr byte
  incw addr
  cgt byte #126 @not_ascii
  cle byte #31  @not_ascii
  out byte
  out #0x20
  jmp execute
@not_ascii:
  out #0x5c
  out #'x'
  hex_out byte
  out #0x20
  jmp execute

jump_to:
  jtp addr

read_addr:
  hexw_out addr
  out #0x20
  jmp execute

goto:
  readc parse c
  readc parse (c 1 +)
  from_hex c addr fail
  readc parse c
  readc parse (c 1 +)
  from_hex c (addr 1 +) fail
  jmp execute

begin_tape_read:
  readc parse c
  cne c #'o' fail
  readc parse c
  cne c #'a' fail
  readc parse c
  cne c #'d' fail
  readc parse c
  cne c #0x00 fail
  mov #0x01 tape
  print tape_msg
@wait_for_dot:
  pin byte
  cne byte #'.' @wait_for_dot
  print loading_msg
  jmp readline

return_from_tape:
   mov #0x00 tape
   print loaded_msg
   jmp readline

dump:
  readc parse c
  readc parse (c 1 +)
  from_hex c target fail
  readc parse c
  readc parse (c 1 +)
  from_hex c (target 1 +) fail
@line:
  mov #16 counter
  hex_out addr
  hex_out (addr 1 +)
  out #0x20
  out #0x20
@loop:
  ld addr byte
  incw addr
  hex_out byte
  out #0x20
  cne addr target @not_done
  ceq (addr 1 +) (target 1 +) execute
@not_done:
  djnz counter @loop
  out #0x0a
  ; TODO: implement ascii output
  jmp @line

welcome:
  .string "S6MON v0.1.0"
  .word 0x0a0a
  .string "OK"
  .byte 0x00
fail_msg:
  .string "SORRY?"
  .byte 0x00
tape_msg:
  .asciiz "[ INSERT TAPE ]"
loading_msg:
  .byte 0x0d
  .asciiz "[   LOADING   ]"
loaded_msg:
  .byte 0x0d
  .string "[    DONE.    ]"
