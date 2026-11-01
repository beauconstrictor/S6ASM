  .include <stdlib>

  ; this is a massive unit test for most the stdlib. run it and follow
  ; this instructions.

  .res 2 hex_lookup
  .res 1 hex_nibble

  .res 2 print_str
  .res 2 print_char

  .res 1 byte

  .macro hex_out x
    lptr hex_lookup_table_msn hex_lookup
    addbw x hex_lookup
    ld hex_lookup hex_nibble
    out hex_nibble
    lptr hex_lookup_table_lsn hex_lookup
    addbw x hex_lookup
    ld hex_lookup hex_nibble
    out hex_nibble
  .endmacro

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

welcome:
  print @msg
  pin _
  jmp @done
@msg:
  .string "Welcome to the test program! This program verifies many"
  .byte 0x0a
  .string "of the macros in the s6asm stdlib. Press any key."
  .byte 0x0a
  .word 0x0a00
@done:

check_beq:
  print @msg
  pin _
  mov #0 byte
@loop:
  hex_out byte
  out #32
  beq byte @isequal
  out #'!'
  jmp @next
@isequal:
  out #'='
@next:
  out #'='
  out #32
  out #'0'
  out #0x0a
  inc byte
  beq byte @done
  jmp @loop
@msg:
  .string "Ensure that all of the following statements are true (press any key):"
  .word 0x0a00
@done:
  out #0x0a

all_tested:
  print @msg
  pin _
  halt
@msg:
  .string "All tests complete. Press any key to exit."
  .word 0x0a00

  .include "hex_lookup_table.s"
