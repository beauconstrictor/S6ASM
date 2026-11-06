  .require <stdlib>

  ; semantics:
  ; - stdstacks grow downwards.
  ; - these macros happily accept underflows and overflows.

  ; store x into ptr y, then decrement y
  .macro push x y
    st x y
    decw y
  .endmacro

  ; increment y, load from ptr y into x
  .macro pull x y
    incw x
    ld x y
  .endmacro

  ; store word x into ptr y, then decrement y
  .macro pushw x y
    push x y
    push (x 1 +) y
  .endmacro

  ; increment y, load from ptr y into word x
  .macro pullw x y
    pull x (y 1 +)
    pull x y
  .endmacro

  ; call subroutine at label x
  .macro call x
    lptr return stdlib_tmpw7
    pushw return sp
    jmp x
return:
  .endmacro

  .macro ret
    pullw sp stdlib_tmpw7
    jtp stdlib_tmpw7
  .endmacro

  jmp stdlib_after_ret
ret:
  ret
stdlib_after_ret:
