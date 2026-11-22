  .org 0x8000

  .include <stdascii>

  .include <stdlib>
  .include <stdstack>
  .include <stdhex>
  .include <stdio>

  .const OPCODE_RET   0x00
  .const OPCODE_CALL  0x01
  .const OPCODE_PUSH  0x02
  
  .const OPCODE_IF    0x03
  .const OPCODE_WHIL  0x04
  
  .const OPCODE_ADD   0x05
  .const OPCODE_SUB   0x06
  
  .const OPCODE_GT    0x07
  
  .const OPCODE_DUP   0x08
  .const OPCODE_DROP  0x09
  .const OPCODE_SWAP  0x0a
  .const OPCODE_ROT   0x0b
  
  .const OPCODE_GET   0x0c
  .const OPCODE_PUT   0x0d
  .const OPCODE_LOAD  0x0e
  .const OPCODE_STORE 0x0f
  
  .const OPCODE_PUTC  0x10
  .const OPCODE_GETS  0x11

  .res 2 buf
  .res 2 pc
  .res 1 byte
  .res 2 word
  .res 2 word2
  .res 2 word3
  .res 2 dsp

start:
  mov 0x07ff dsp
  print welcome
@wait:
  pin buf
  cne buf #'T' @wait
  out #LF

load:
  pin buf

  ceq buf #':' @goto
  ceq buf #SEMICOLON load
  ceq buf #SPACE load
  ceq buf #'!' @run

  pin (buf 1 +)
  from_hex buf byte @fail
  st byte pc

  jmp load
@goto:
  pin buf
  pin (buf 1 +)
  from_hex buf pc @fail
  pin buf
  pin (buf 1 +)
  from_hex buf (pc 1 +) @fail
  jmp load
@run:
  call func
  jmp load
@fail:
  print @msg
  jmp load
@msg:
  .string "parse error"
  .word 0x0a00

; execute a bytecode function
func:
  ld pc byte
  incw pc
  
  ceq byte #OPCODE_RET ret
  ceq byte #OPCODE_CALL @call
  ceq byte #OPCODE_PUSH @push

  ceq byte #OPCODE_IF @if
  
  jmp @fail
@call:
  pushw pc sp
  pullw dsp pc
  call func
  pullw sp pc
  jmp func
@push:
  ld pc word
  incw pc
  incw pc
  pushw word dsp
  jmp func
@if:
  pullw dsp word3
  pullw dsp word2
  pullw dsp word

  pushw pc sp

  ceq word #0 @if_false

  movw word2 pc
  jmp @if_call
@if_false:
  movw word3 pc
@if_call:
  call func
  pullw sp pc
  jmp func
@fail:
  print @msg
  jmp load
@msg:
  .string "bytecode error"
  .word 0x0a00

welcome:
  .asciiz "Insert tape."
