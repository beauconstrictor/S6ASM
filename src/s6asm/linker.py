from collections.abc import Iterator

from .errs import *
from .tokeniser import make_expr, Token, Expression
from .preprocessor import preprocessor, find_labels

# TODO: local labels with @ sign, scoped to last global label

# - remove all labels and expressions from the program
def evaluate(source: str, path: str="<unknown>") -> Iterator[Token]:
    tokens = list(preprocessor(source, path))
    labels = find_labels(tokens)

    initial_origin = None
    emitted = 0

    for tok in tokens:
        if tok.directive == "org":
            target = make_expr(tok.operands[0]).evaluate(labels, tok)

            if not (0x0000 <= target <= 0xffff):
                raise AsmOriginError("origin out of range for 16-bit address space", tok)

            if initial_origin is None:
                initial_origin = target
            else:
                if target - initial_origin < emitted:
                    raise AsmOriginError("origin directives must come in order", tok)
                for _ in range(target - initial_origin - emitted):
                    yield Token.using("  .byte 0", tok)
                    emitted += 1

        if initial_origin is None:
            raise AsmOriginError(f"{tok.path}: file must start with an org directive", tok)

        if tok.a is not None and tok.b is not None and tok.c is not None:
            tok.a = Expression(str(tok.a.evaluate(labels, tok)))
            tok.b = Expression(str(tok.b.evaluate(labels, tok)))
            tok.c = Expression(str(tok.c.evaluate(labels, tok)))
            emitted += 6

        elif tok.directive == "byte":
            value = make_expr(tok.operands[0]).evaluate(labels, tok)
            if -128 <= value <= -1:
                value &= 0xff
            if not (0 <= value <= 255):
                raise AsmWordWidthError(f"{value!r} out of range for an 8-bit expression", tok)
            tok.operands = [Expression(str(value))]
            emitted += 1

        elif tok.directive == "word":
            value = make_expr(tok.operands[0]).evaluate(labels, tok)
            emitted += 2

            if -32768 <= value <= -1:
                value &= 0xffff
            if not (0 <= value <= 65535):
                raise AsmWordWidthError(f"{value!r} out of range for an 16-bit expression", tok)

            hi = value >> 8
            lo = value & 0xff

            yield Token.using(f"  .byte {hi}", tok)
            yield Token.using(f"  .byte {lo}", tok)
            continue

        elif tok.directive == "asciiz" or tok.directive == "ascii":
            assert not isinstance(tok.operands[0], Expression)
            s = tok.operands[0][1:][:-1]
            if tok.directive == "asciiz": s += "\0"
            for c in s:
                yield Token.using(f"  .byte {ord(c)}", tok)
            emitted += len(s)

        else:
            # we can discard labels and constants now
            continue

        tok.label = None
        yield tok

def extend_with_word(binary: bytearray, word: int) -> None:
    word &= 0xffff
    # big endian
    binary.extend([word >> 8, word & 0xff])

# - turn a program into an actual binary
def assemble(source: str, path: str="<unknown>") -> bytearray:
    binary = bytearray()

    for tok in evaluate(source, path):
        if tok.directive == "byte":
            binary.extend([make_expr(tok.operands[0]).evaluate(None, tok)])
        elif tok.a and tok.b and tok.c:
            extend_with_word(binary, tok.a.evaluate(None, tok))
            extend_with_word(binary, tok.b.evaluate(None, tok))
            extend_with_word(binary, tok.c.evaluate(None, tok))

    return binary

