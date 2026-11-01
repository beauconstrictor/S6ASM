  .include <stdlib>

  .res 2 hex_lookup
  .res 1 hex_nibble

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

  mov #00 byte
loop:
  hex_out byte
  inc byte
  beq byte freeze
  jmp loop

  .org 0x9002
  .include "hex_lookup_table.s"
