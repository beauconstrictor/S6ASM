from __future__ import annotations

import sys
import argparse
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from importlib.resources import files
from importlib.metadata import version
from typing import override, Self, final
from collections.abc import Iterator, Iterable, Sequence

ALLOWED_DIRECTIVES = {
        "org",
        "byte",
        "word",
        "const",
        "macro",
        "asciiz",
        "endmacro"}

class AsmError(Exception):
    def __init__(self, message: str, token: Token|None=None) -> None:
        if token:
            super().__init__(f"{token.path}:{token.lineno}: {message}")
        else:
            super().__init__(message)

class AsmRomError(AsmError): ...
class AsmSyntaxError(AsmError): ...
class AsmOriginError(AsmError): ...
class AsmIncludeError(AsmError): ...
class AsmRecursionError(AsmError): ...
class AsmWordWidthError(AsmError): ...
class AsmExpressionError(AsmError): ...

# [label:] [(macro|.directive) [operands]...|subleq a b c]
class Token:
    def __init__(self, line: str, path: str="<unknown>", lineno: int=-1) -> None:
        acc = ""
        words: list[str] = []
        in_paren = False
        in_quote = False

        for c in line + " ":
            if c == "(" and not in_paren and not in_quote:
                in_paren = True
                continue
            if c == ")" and in_paren and not in_quote:
                in_paren = False
                continue
            if c in ("'", '"'):
                in_quote = not in_quote
            if c == ";" and not in_quote and not in_paren:
                break
            if c.isspace() and not in_quote and not in_paren:
                if acc:
                    words.append(acc)
                acc = ""
                continue

            acc += c

        words = [w.strip() for w in words]

        self.path:   str = path
        self.lineno: int = lineno

        self.label:     str|None = None

        self.a:         Expression|None = None
        self.b:         Expression|None = None
        self.c:         Expression|None = None

        self.macro:     str|None = None
        self.directive: str|None = None
        self.operands: Sequence[Expression|str] = []

        if len(words) == 0:
            return

        if not line[0].isspace():
            self.label = words.pop(0)
            if not self.label.endswith(":"):
                raise AsmSyntaxError(f"expected ':' after label in {line!r}")
            self.label = self.label[:-1]
            if len(words) == 0:
                return

        if words[0].startswith("."):
            self.directive = words[0][1:]
            self.operands = words[1:]
        elif words[0] == "subleq":
            if len(words) < 4:
                raise AsmSyntaxError("expected 3 operands")
            elif len(words) == 4:
                self.a = Expression(words[1])
                self.b = Expression(words[2])
                self.c = Expression(words[3])
            else:
                raise AsmSyntaxError("unexpected operands")
        else:
            self.macro = words[0]
            self.operands = [Expression(w) for w in words[1:]]

    @staticmethod
    def using(line: str, tok: Token) -> Token:
        return Token(line, tok.path, tok.lineno)

    def duplicate(self) -> Self:
        tok           = type(self)("")
        tok.label     = self.label
        tok.a         = self.a.duplicate() if self.a else None
        tok.b         = self.b.duplicate() if self.b else None
        tok.c         = self.c.duplicate() if self.c else None
        tok.macro     = self.macro
        tok.directive = self.directive
        tok.operands  = [o.duplicate() if isinstance(o, Expression) else o for o in self.operands]
        tok.path      = self.path
        tok.lineno    = self.lineno
        return tok

    @override
    def __repr__(self) -> str:
        s = ""
        if self.label is not None: s += f"{self.label}: "
        else: s += "  "

        if self.directive is not None:
            s += f".{self.directive} "

        elif self.macro is not None:
            s += f"{self.macro} "

        elif self.a is not None:
            s += f"subleq {self.a!r} {self.b!r} {self.c!r}"

        if self.operands:
            for o in self.operands:
                s += f"{o} "

        s += f" ; [{self.path}:{self.lineno}]"
        return s

class Literal:
    def __init__(self, text: str) -> None:
        self.text: str = text

    def evaluate(self, labels: dict[str, int]|None=None, token: Token|None=None) -> int:
        s = self.text

        if len(s) == 3 and s[0] == "'" and s[-1] == "'":
            return ord(s[1])

        try:
            return int(s, 0)
        except ValueError:
            if labels is not None and labels.get(s) is not None:
                return labels[s]

        raise AsmSyntaxError(f"unsupported expression form: '{s}'", token)

    def substitute(self, label: str, new_value: str) -> None:
        if self.text != label: return
        self.text = new_value

    def duplicate(self) -> Self:
        return type(self)(self.text)

    @override
    def __str__(self) -> str:
        return self.text

@final
class Operation(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    LSR = ">>"
    LSL = "<<"
    XOR = "^"
    MOD = "%"

class Expression:
    def __init__(self, text: str) -> None:
        self.tokens: list[Literal|Operation] = []

        for word in text.split():
            if word in {op.value for op in Operation}:
                self.tokens.append(Operation(word))
            else:
                self.tokens.append(Literal(word))

    def evaluate(self, labels: dict[str, int]|None=None, token: Token|None=None) -> int:
        stack: list[int] = []

        try:
            for tok in self.tokens:
                if isinstance(tok, Literal):
                    stack.append(tok.evaluate(labels, token))
                else:
                    try:
                        b = stack.pop()
                        a = stack.pop()
                    except IndexError:
                        raise AsmSyntaxError("expression underflows", token)
                    match tok:
                        case Operation.ADD:
                            stack.append(a + b)
                        case Operation.SUB:
                            stack.append(a - b)
                        case Operation.MUL:
                            stack.append(a * b)
                        case Operation.DIV:
                            stack.append(a // b)
                        case Operation.LSR:
                            stack.append(a >> b)
                        case Operation.LSL:
                            stack.append(a << b)
                        case Operation.XOR:
                            stack.append(a ^ b)
                        case Operation.MOD:
                            stack.append(a % b)
        except ZeroDivisionError:
            raise AsmExpressionError("division by zero", token)

        if len(stack) < 1:
            raise AsmSyntaxError("expression is empty", token)
        elif len(stack) > 1:
            raise AsmSyntaxError("expression returns multiple many values", token)

        return stack[0]

    def substitute(self, label: str, new_value: str | Self) -> None:
        result: list[Literal | Operation] = []

        for tok in self.tokens:
            if isinstance(tok, Literal) and tok.text == label:
                if isinstance(new_value, str):
                    result.append(Literal(new_value))
                else:
                    result.extend(new_value.duplicate().tokens)
            else:
                result.append(tok)

        self.tokens = result

    def duplicate(self) -> Self:
        new_toks: list[Literal | Operation] = []

        for tok in self.tokens:
            if isinstance(tok, Literal):
                new_toks.append(tok.duplicate())
            else:
                new_toks.append(tok)

        duplicate = type(self)("")
        duplicate.tokens = new_toks
        return duplicate

    @override
    def __repr__(self) -> str:
        return f"({' '.join(str(tok) for tok in self.tokens)}) "

def tokenise(source: str, path: str="<unknown>") -> Iterator[Token]:
    for i, l in enumerate(source.splitlines(), start=1):
        if not l.strip(): continue
        yield Token(l, path, i)

def make_expr(s: str | Expression) -> Expression:
    if isinstance(s, Expression): return s
    return Expression(s)

@dataclass
class Macro:
    tokens: list[Token]
    name: str
    labels: set[str]
    parameters: list[str]


macro_invocation_idx = 0

def expand_single_macro(tok: Token, macros: dict[str, Macro]) -> Iterator[Token]:
    global macro_invocation_idx

    if not tok.macro:
        raise ValueError("not a macro token")

    try:
        macro = macros[tok.macro]
    except KeyError:
        raise AsmSyntaxError(f"undefined macro: {tok.macro}", tok)

    if len(tok.operands) != len(macro.parameters):
        raise AsmSyntaxError("incorrect macro argument count", tok)

    suffix = f"___macro{macro_invocation_idx}"
    macro_invocation_idx += 1

    for subtok in macro.tokens:
        subtok = subtok.duplicate()
        subtok.path = tok.path
        subtok.lineno = tok.lineno

        # macro local labels
        if subtok.label: subtok.label += suffix

        if subtok.directive:
            raise AsmSyntaxError("cannot use directives inside macros", subtok)

        for i, o in enumerate(subtok.operands):
            for l in macro.labels:
                if isinstance(o, str): continue
                o.substitute(l, l + suffix)

        for l in macro.labels:
            for i in (subtok.a, subtok.b, subtok.c):
                if i is None: continue
                i.substitute(l, l + suffix)

        # macro parameters
        for i, o in enumerate(subtok.operands):
            if isinstance(o, str): continue
            for i2, p in enumerate(macro.parameters):
                v = tok.operands[i2]
                o.substitute(p, v)
    

        for i, p in enumerate(macro.parameters):
            if subtok.a is not None: subtok.a.substitute(p, tok.operands[i])
            if subtok.b is not None: subtok.b.substitute(p, tok.operands[i])
            if subtok.c is not None: subtok.c.substitute(p, tok.operands[i])

        if subtok.macro is not None:
            yield from expand_single_macro(subtok, macros)
        else:
            yield subtok

def is_printable_ascii(c: int) -> bool:
    return 32 <= c <= 126

def generate_immediates() -> Iterator[Token]:
    labels: set[str] = set()

    def make_tok(l: str) -> Iterator[Token]:
        if l in labels: return
        labels.add(l)
        yield Token(l, "stdlib", -1)

    for i in range(0x100):
        if is_printable_ascii(i) and chr(i) not in ("'"):
            yield from make_tok(f"#'{chr(i)}':")

        for prefix, max_width in (("x", 2), ("b", 8)):
            for w in range(1, max_width + 1):
                l = f"#0{prefix}{i:0{w}{prefix}}:"
                yield from make_tok(l)

        for w in range(1,4):
            l = f"#{i:0{w}d}:"
            yield from make_tok(l)

        yield from make_tok(f"  .byte {i}")

# - recursively expand macros to their contents
# - insert contents of includes
def expand_macros(source: str, macros: dict[str, Macro]|None=None, path: str="<unknown>", allow_stdlib: bool=True) -> Iterator[Token]:
    if macros is None: macros = {}
    current_macro = None
    macro_definition = None

    immediates = False

    for tok in tokenise(source, path):
        if tok.directive == "macro":
            if current_macro:
                raise AsmSyntaxError("cannot nest macro definitions", tok)
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected macro name", tok)

            operands: list[str] = []
            macro_definition = tok
            for o in tok.operands:
                assert not isinstance(o, Expression)
                operands.append(o)
            current_macro = Macro([], operands[0], set(), operands[1:])

            if tok.label:
                current_macro.tokens.append(Token.using(f"{tok.label}:", tok))
                current_macro.labels.add(tok.label)

        elif tok.directive == "endmacro":
            if not current_macro:
                raise AsmSyntaxError("endmacro directive outside of a macro definition", tok)
            macro = current_macro
            macros[macro.name] = macro
            current_macro = None
            macro_definition = None

        elif tok.directive == "include":
            if len(tok.operands) != 1:
                raise AsmSyntaxError("incorrect argument count in include directive", tok)

            ident = tok.operands[0]
            assert not isinstance(ident, Expression)
            if len(ident) < 2 or not (
               (ident[0] == ident[-1] and ident[0] in ('"', "'"))
               or (ident[0] == "<" and ident[-1] == ">")):
                raise AsmSyntaxError("include path must be surrounded by angled brackets or quotes", tok)
            stdlib = ident[0] == "<"
            path = ident[1:-1]

            if stdlib and not allow_stdlib:
                raise AsmIncludeError("cannot include <stdlib> outside of the root file", tok)
            elif stdlib:
                if path == "stdlib": immediates = True
                file = files("s6asm").joinpath("stdlib", path + ".s")
            else:
                file = Path(tok.path).parent / Path(path)
            

            if not file.is_file():
                raise AsmIncludeError(f"file '{file}' could not be found", tok)
            yield from expand_macros(file.read_text(encoding="utf-8"), macros, path=path, allow_stdlib=False)

        # part of a macro definition
        elif current_macro:
            current_macro.tokens.append(tok)
            if tok.label: current_macro.labels.add(tok.label)

        # a macro call
        elif tok.macro is not None:
            if tok.label:
                yield Token.using(f"{tok.label}:", tok)
            try:
                yield from expand_single_macro(tok, macros)
            except RecursionError:
                raise AsmRecursionError("macro recursion too deep", tok)

        # instruction/label/directive
        else:
            yield tok

    if current_macro is not None:
        raise AsmSyntaxError("macro definition is unterminated", macro_definition)

    if immediates:
        yield from generate_immediates()


def ensure_args(tok: Token, count: int) -> None:
    if len(tok.operands) == count - 1:
        raise AsmSyntaxError("missing operand", tok)
    elif len(tok.operands) < count:
        raise AsmSyntaxError("missing operands", tok)
    elif len(tok.operands) == count + 1:
        raise AsmSyntaxError("unexpected operand", tok)
    elif len(tok.operands) > count:
        raise AsmSyntaxError("unexpected operands", tok)

# - calculate the addresses of all the labels
# - verify the arguments of directives
def find_labels(tokens: Iterable[Token]) -> dict[str, int]:
    labels: dict[str, int] = {}
    pc = 0

    for tok in tokens:
        if tok.label:
            if tok.label in labels:
                raise AsmSyntaxError(f"redefinition of label: {tok.label}", tok)
            labels[tok.label] = pc

        if tok.a is not None:
            pc += 6
        elif tok.directive == "org":
            if tok.label:
                raise AsmOriginError("cannot apply a label to an org directive", tok)
            ensure_args(tok, 1)
            assert not isinstance(tok.operands[0], Expression)
            pc = Expression(tok.operands[0]).evaluate(labels, tok)
        elif tok.directive == "byte":
            ensure_args(tok, 1)
            pc += 1
        elif tok.directive == "word":
            ensure_args(tok, 1)
            pc += 2
        elif tok.directive == "const":
            ensure_args(tok, 2)
            assert not isinstance(tok.operands[0], Expression)
            if tok.operands[0] in labels:
                raise AsmSyntaxError(f"redefinition of label: {tok.label}", tok)
            labels[tok.operands[0]] = make_expr(tok.operands[1]).evaluate(labels, tok)

        elif tok.directive == "asciiz":
            ensure_args(tok, 1)
            assert not isinstance(tok.operands[0], Expression)
            s = tok.operands[0]
            quotes = ("'", '"')
            if len(s) < 2 or s[0] not in quotes or s[-1] not in quotes:
                raise AsmSyntaxError("expected quotes around string argument", tok)
            assert not isinstance(s, Expression)

            pc += len(s) - 1

    return labels

# - remove all labels and expressions from the program
def evaluate(source: str, path: str="<unknown>") -> Iterator[Token]:
    tokens = list(expand_macros(source, path=path))
    labels = find_labels(tokens)

    initial_origin = None
    emitted = 0

    for tok in tokens:
        # all these directives are verified as correct in
        # find_labels, so we can just use them here

        if tok.directive and tok.directive not in ALLOWED_DIRECTIVES:
            raise AsmSyntaxError(f"unknown directive: '{tok.directive}'", tok)

        if tok.directive == "org":
            target = make_expr(tok.operands[0]).evaluate(labels, tok)

            if initial_origin is None:
                initial_origin = target
            else:
                if target - initial_origin < emitted:
                    raise AsmOriginError("origin directives must come in order", tok)
                for _ in range(target - initial_origin - emitted):
                    yield Token.using("  .byte 0", tok)

        if initial_origin is None:
            raise AsmOriginError(f"{tok.path}: file must start with an org directive")

        if tok.a is not None and tok.b is not None and tok.c is not None:
            tok.a = Expression(str(tok.a.evaluate(labels, tok)))
            tok.b = Expression(str(tok.b.evaluate(labels, tok)))
            tok.c = Expression(str(tok.c.evaluate(labels, tok)))
            emitted += 6

        elif tok.directive == "byte":
            tok.operands = [Expression(str(make_expr(tok.operands[0]).evaluate(labels, tok)))]

        elif tok.directive == "word":
            value = make_expr(tok.operands[0]).evaluate(labels, tok) & 0xffff

            hi = value >> 8
            lo = value & 0xff

            yield Token.using(f"  .byte {hi}", tok)
            yield Token.using(f"  .byte {lo}", tok)
            continue

        elif tok.directive == "asciiz":
            assert not isinstance(tok.operands[0], Expression)
            for c in tok.operands[0][1:][:-1] + "\0":
                yield Token.using(f"  .byte {ord(c)}", tok)

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

# - emulate a binary
class Emulate:
    def __init__(self, image: bytearray) -> None:
        if len(image) > 0x8000:
            raise AsmRomError("program too large to fit into 32K.")

        self.rom: bytearray = image.copy()
        self.rom.extend(b'\00' * (0x8000 - len(image)))
        self.ram: bytearray = bytearray(0x8000)

        self.pc: int = 0x8000

        while self.pc != 0xfffe:
            self.execute()
    
    def fetch(self, addr: int) -> int:
        if addr == 0xffff:
            raise NotImplementedError("the integrated emulator does not yet support input")
        elif addr < 0x8000:
            return self.ram[addr]
        elif addr < 0x10000:
            return self.rom[addr - 0x8000]
        raise ValueError("memory read out of range")

    def fetchw(self, addr: int) -> int:
        return (self.fetch(addr) << 8) | (self.fetch(addr+1))

    def write(self, addr: int, value: int) -> None:
        if addr == 0xfffe:
            sys.stdout.write(chr(value))
        elif addr < 0x8000:
            self.ram[addr] = value
        elif addr < 0x10000:
            pass
        else:
            raise ValueError("memory write out of range")

    def execute(self) -> None:
        a = self.fetchw(self.pc)
        self.pc += 2
        b = self.fetchw(self.pc)
        self.pc += 2
        c = self.fetchw(self.pc)
        self.pc += 2

        r = (self.fetch(b) - self.fetch(a)) & 0xff
        self.write(b, r)

        if r == 0 or (r & 0x80):
            self.pc = c

def main() -> None:
    parser = argparse.ArgumentParser(
            prog="s6asm",
            description="A macro assembler for S6 assembly language.")

    parser.add_argument("program", type=Path)

    parser.add_argument("-v", "--version", action="version",
                      version=f"%(prog)s {version('s6asm')}")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-t", "--tokeniser", action="store_true",
                      help="convert the program into a simpler form.")
    mode.add_argument("-p", "--preprocessor", action="store_true",
                      help="expand macros and includes in the program.")
    mode.add_argument("-l", "--linker", action="store_true",
                      help="convert the program into a series of subleq instructions and byte directives.")
    mode.add_argument("-a", "--assembler", default=True, action="store_true",
                      help="assemble the program into a ROM image.")
    mode.add_argument("-e", "--emulator", action="store_true",
                      help="execute the program using a built-in S6 emulator.")

    args = parser.parse_args()
    file = args.program.read_text(encoding="utf-8")
    path = str(args.program)

    try:
        if args.tokeniser:
            for tok in tokenise(file, path=path):
                print(tok)
        elif args.preprocessor:
            for tok in expand_macros(file, path=path):
                print(tok)
        elif args.linker:
            for tok in evaluate(file, path=path):
                print(tok)
        elif args.emulator:
            Emulate(assemble(file, path))
        elif args.assembler:
            sys.stdout.buffer.write(assemble(file, path))
    except (AsmError, NotImplementedError) as e:
        parser.error(str(e))

if __name__ == "__main__":
    main()
