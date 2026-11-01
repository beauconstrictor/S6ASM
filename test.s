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

  .macro hex_outw x
    hex_out x
    hex_out (x 1 +)
  .endmacro

  mov #00 byte
loop:
  hex_out byte
  out #0x0a
  inc byte
  jmp loop

  .include "hex_lookup_table.s"
