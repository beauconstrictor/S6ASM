  .require <stdlib>

  ; stdstacks grow downwards.

  ; store x into ptr y, then decrement y
  .macro push x y
    st x y
    decw y
  .endmacro

  ; increment y, load from ptr y into x
  .macro pull x y
    incw y
    ld x y
  .endmacro

  ; store word x into ptr y, then decrement y
  .macro pushw x y
    stw x y
    sub #2 y
  .endmacro

  ; increment y, load from ptr y into word x
  .macro pullw x y
    sub #-2 y
    ldw x y
  .endmacro
