  .require <stdlib>

  .macro print msg
    lptr msg stdlib_tmpw7
loop:
    ld stdlib_tmpw7 stdlib_tmp7  
    ble stdlib_tmp7 done
    out stdlib_tmp7
    incw stdlib_tmpw7
    jmp loop
done:
  .endmacro

  ; does NOT and WILL NOT prevent buffer overflows
  .macro gets buf
    lptr buf stdlib_tmpw7
loop:
    pin stdlib_tmp7
    ceq stdlib_tmp7 #0x08 bksp ; backspace
    ceq stdlib_tmp7 #0x7f bksp ; or delete
    out stdlib_tmp7
    ceq stdlib_tmp7 #0x0a done
    st stdlib_tmp7 stdlib_tmpw7
    incw stdlib_tmpw7
    jmp loop
    jmp done
bksp:
    decw stdlib_tmpw7
    ; TODO: you can backspace past the start of the buffer
    out #0x08
    out #0x20
    out #0x08
    jmp loop
done:
    st #0 stdlib_tmpw7
  .endmacro

  ; write a single byte from ptr x into y and increment x
  .macro readc x y
    ld x y
    incw x
  .endmacro
