  .macro clear x
    subleq x x done
done:
  .endmacro

  .macro mov a b
    clear z
    subleq a z negated
negated:
    subleq z b done
done:
  .endmacro

  .org 0x8000
  mov a seri

;   .org 0x8000
; 
;   ; constants
;   .const halt 0xfffe
;   .const seri 0xfffe
;   .const sero 0xffff
; 
;   ; variables
;   .const z    0x0000
; 
;   .macro clear x
;     subleq x x done
; done:
;   .endmacro
; 
;   .macro halt
;     subleq z z halt
;   .endmacro
; 
;   .macro mov a b
;     clear z
;     subleq a z negated
; negated:
;     subleq z b done
; done:
;   .endmacro
; 
; start:
;   mov a seri
;   mov a seri
;   halt
; 
;   ; constants
; a: .byte 'A'
