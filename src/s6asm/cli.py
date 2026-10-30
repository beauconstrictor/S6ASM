from __future__ import annotations

from os import getenv
from enum import Enum
from pathlib import Path
from itertools import chain
from dataclasses import dataclass
from argparse import ArgumentParser
from collections import defaultdict
from sys import stdout, stderr, stdin
from importlib.resources import files
from importlib.metadata import version
from typing import override, Self, final
from collections.abc import Iterator, Iterable, Sequence

# TODO: unary operators in expressions, like !
# TODO: local labels with @ sign, scoped to last global label

ALLOWED_DIRECTIVES = {
        "org",
        "byte",
        "word",
        "const",
        "macro",
        "ascii",
        "asciiz",
        "endmacro"}

BRACKET_CHARS = ("(", ")", ";")

class AsmError(Exception):
    def __init__(self, message: str, token: Token|None=None) -> None:
        self.message: str = message
        self.location: str|None = None
        if token is not None:
            self.location = f"{token.path}:{token.lineno}"
            super().__init__(f"{self.location}: {message}")
        else:
            super().__init__(message)

class AsmRomError(AsmError): ...
class AsmSyntaxError(AsmError): ...
class AsmOriginError(AsmError): ...
class AsmIncludeError(AsmError): ...
class AsmRecursionError(AsmError): ...
class AsmWordWidthError(AsmError): ...
class AsmExpressionError(AsmError): ...

def bracketise(s: object) -> str:
    s = str(s)
    if any(c.isspace() or c in BRACKET_CHARS for c in s): return f"({s})"
    return s

# [label:] [(macro|.directive) [operands]...|subleq a b c]
class Token:
    def __init__(self, line: str, path: str="<unknown>", lineno: int=-1) -> None:
        self.path:   str = path
        self.lineno: int = lineno

        acc = ""
        words: list[str] = []
        parens = 0
        quote: str | None = None

        for c in line + " ":
            if c == "(" and quote is None:
                parens += 1
                if parens == 1: continue
            elif c == ")" and quote is None:
                parens -= 1
                if parens < 0:
                    raise AsmSyntaxError("unbalanced parantheses", self)
                if parens == 0: continue
            elif c in ("'", '"'):
                if quote is None: quote = c
                elif c == quote: quote = None
            elif c == ";" and quote is None and not parens:
                break
            elif c.isspace() and quote is None and not parens:
                if acc:
                    words.append(acc)
                acc = ""
                continue

            acc += c

        if parens > 0:
            raise AsmSyntaxError("unbalanced parentheses", self)
        if quote is not None:
            raise AsmSyntaxError("unterminated quote", self)

        words = [w.strip() for w in words]

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
                raise AsmSyntaxError(f"expected ':' after label in {line!r}", self)
            self.label = self.label[:-1]
            if len(words) == 0:
                return

        if words[0].startswith("."):
            self.directive = words[0][1:]
            self.operands = words[1:]
        elif words[0] == "subleq":
            if len(words) < 4:
                raise AsmSyntaxError("expected 3 operands", self)
            elif len(words) == 4:
                self.a = Expression(words[1])
                self.b = Expression(words[2])
                self.c = Expression(words[3])
            else:
                raise AsmSyntaxError("unexpected operands", self)
        else:
            self.macro = words[0]
            self.operands = [Expression(w) for w in words[1:]]

    @staticmethod
    def using(line: str, tok: Token) -> Token:
        return Token(line, tok.path, tok.lineno)

    def is_empty(self) -> bool:
        return not any((self.a, self.b, self.c)) and not self.directive \
                and not self.macro and not self.label

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
        if self.label is not None: s += f"{bracketise(self.label)}: "
        else: s += "  "

        if self.directive is not None:
            s += f".{bracketise(self.directive)} "

        elif self.macro is not None:
            s += f"{bracketise(self.macro)} "

        elif self.a is not None:
            s += f"subleq {self.a!r} {self.b!r} {self.c!r}"

        if self.operands:
            for o in self.operands:
                s += f"{bracketise(o)} "

        s += f" ; <{self.path}:{self.lineno}>"
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

        raise AsmSyntaxError(f"{s!r} is undefined", token)

    def substitute(self, label: str, new_value: str) -> None:
        if self.text != label: return
        self.text = new_value

    def duplicate(self) -> Self:
        return type(self)(self.text)

    @override
    def __str__(self) -> str:
        return bracketise(self.text)

@final
class Operation(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    LSR = ">>"
    LSL = "<<"
    MOD = "%"
    AND = "&"
    OR  = "|"
    XOR = "^"

    @override
    def __str__(self) -> str:
        return self.value

class Expression:
    def __init__(self, text: str) -> None:
        self.tokens: list[Literal|Operation] = [Operation(word)
                                                if word in {op.value for op in Operation}
                                                else Literal(word)
                                                for word in text.split()]

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
                        case Operation.AND:
                            stack.append(a & b)
                        case Operation.OR:
                            stack.append(a | b)

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
        return f"{bracketise(' '.join(str(tok) for tok in self.tokens))}"

def tokenise(source: str, path: str="<unknown>") -> Iterator[Token]:
    for i, l in enumerate(source.splitlines(), start=1):
        if not l.strip(): continue
        tok = Token(l, path, i)
        if not tok.is_empty(): yield tok

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
        raise AsmSyntaxError(f"{macro.name!r} expected {len(macro.parameters)} parameters, got {len(tok.operands)}", tok)

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

        if subtok.macro is None:
            yield subtok
        else:
            yield from expand_single_macro(subtok, macros)

def is_printable_ascii(c: int) -> bool:
    return 32 <= c <= 126

# - recursively expand macros to their contents
# - insert contents of includes
def expand_macros(source: str, macros: dict[str, Macro]|None=None, path: str="<unknown>", allow_stdlib: bool=True) -> Iterator[Token]:
    if macros is None: macros = {}
    current_macro = None
    macro_definition = None

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
                raise AsmSyntaxError("missing argument", tok)

            ident = tok.operands[0]
            assert not isinstance(ident, Expression)
            if len(ident) < 2 or not (
               (ident[0] == ident[-1] and ident[0] in ('"', "'"))
               or (ident[0] == "<" and ident[-1] == ">")):
                raise AsmSyntaxError("include path must be surrounded by angled brackets or quotes", tok)
            stdlib = ident[0] == "<"
            include_path = ident[1:-1]

            if stdlib and not allow_stdlib:
                raise AsmIncludeError("cannot include standard library files inside an included file", tok)
            elif stdlib:
                file = files("s6asm").joinpath("stdlib", include_path + ".s")
            else:
                file = Path(path).parent / Path(include_path)

            if not file.is_file():
                raise AsmIncludeError(f"no such file {str(file)!r}", tok)
            yield from expand_macros(file.read_text(encoding="utf-8"), macros, path=include_path, allow_stdlib=False)

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
                raise AsmRecursionError("macro recurses", tok)

        # instruction/label/directive
        else:
            yield tok

    if current_macro is not None:
        raise AsmSyntaxError("unterminated macro definition", macro_definition)

def generate_immediates(tokens: list[Token], labels: dict[str, int]) -> Iterator[Token]:
    immediates: defaultdict[int, set[str]] = defaultdict(set)

    for tok in tokens:
        for exp in chain(tok.operands, (tok.a, tok.b, tok.c)):
            if not isinstance(exp, Expression): continue
            if len(exp.tokens) < 1: continue
           
            s = str(exp).strip().removeprefix("(").removesuffix(")").strip()
            if not s.startswith("#"): continue
            exp.tokens = [Literal(s)]
            
            value = Expression(s[1:]).evaluate(labels, tok)
            if -128 <= value <= -1:
                value &= 0xff
            if not (0 <= value <= 255):
                raise AsmWordWidthError(f"{exp!r} is out of range for an 8-bit value", tok)
            immediates[value].add(s)

    line = 0
    for value, exps in immediates.items():
        for exp in exps:
            yield Token(f"({exp}):", "immediates", line := line + 1)
        yield Token(f"  .byte {value}", "immediates", line := line + 1)

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
                raise AsmSyntaxError(f"{tok.label!r} is already defined", tok)
            labels[tok.label] = pc

        if tok.a is not None:
            pc += 6

        if tok.directive and tok.directive not in ALLOWED_DIRECTIVES:
            raise AsmSyntaxError(f"unknown directive: {tok.directive!r}", tok)

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
            # you are allowed to rewrite consts (so ig they're not
            # really constants) - this makes for useful macros
            labels[tok.operands[0]] = make_expr(tok.operands[1]).evaluate(labels, tok)

        elif tok.directive == "asciiz" or tok.directive == "ascii":
            ensure_args(tok, 1)
            assert not isinstance(tok.operands[0], Expression)
            s = tok.operands[0]
            quotes = ("'", '"')
            if len(s) < 2 or s[0] not in quotes or s[-1] not in quotes:
                raise AsmSyntaxError("expected quotes around string argument", tok)
            assert not isinstance(s, Expression)
            
            pc += len(s) - 2
            if tok.directive == "asciiz":
                pc += 1

    return labels

# - remove all labels and expressions from the program
def evaluate(source: str, path: str="<unknown>") -> Iterator[Token]:
    tokens = list(expand_macros(source, path=path))
    labels = find_labels(tokens)
    tokens += list(generate_immediates(tokens, labels))
    labels = find_labels(tokens)

    initial_origin = None
    emitted = 0

    for tok in tokens:
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

# - emulate a binary
# TOOD: CONSTANTS!
class Emulator:
    def __init__(self, image: bytearray) -> None:
        if len(image) > 0x8000:
            raise AsmRomError("program too large to fit into 32K.")

        self.rom: bytearray = image.copy()
        self.rom.extend(b'\00' * (0x8000 - len(image)))
        self.ram: bytearray = bytearray(0x8000)

        self.pc: int = 0x8000

    def halted(self) -> bool:
        return self.pc == 0xfffe

    def fetch(self, addr: int) -> int:
        addr &= 0xffff

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
            stdout.write(chr(value))
        elif addr < 0x8000:
            self.ram[addr] = value
        elif addr < 0x10000:
            pass
        else:
            raise ValueError("memory write out of range")

    def step(self) -> bool:
        a = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff
        b = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff
        c = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff

        r = (self.fetch(b) - self.fetch(a)) & 0xff
        self.write(b, r)

        if r == 0 or (r & 0x80):
            self.pc = c
       
        # just for convenience
        return not self.halted()

    def run_until_halt(self) -> None:
        while self.step(): pass

def error(summary: object, desc: object="") -> None:
    red = "\033[31m" if stderr.isatty() and not getenv("NO_COLOR") else ""
    yellow = "\033[33m" if red else ""
    reset = "\033[0m" if red else ""
    print(f"{red}s6asm: {yellow}{summary if desc else ''}{': ' if desc else ''}{reset}{desc if desc else summary}", file=stderr)

def main() -> None:
    parser = ArgumentParser(
            prog="s6asm",
            description="A macro assembler for S6 assembly language.",
            epilog="Use a hyphen instead of a filepath to use stdin.")

    parser.add_argument("program", type=Path)

    parser.add_argument("-v", "--version", action="version",
                      version=f"%(prog)s {version('s6asm')}")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="show python tracebacks")

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
    path = str(args.program)

    if path == "-":
        try:
            file = stdin.read()
        except KeyboardInterrupt:
            error("interrupt.")
            return
        path = "stdin"
    else:
        try:
            file = args.program.read_text(encoding="utf-8")
        except FileNotFoundError:
            error("no such file or directory", repr(str(args.program)))
            parser.exit(1)
        except PermissionError:
            error("no such file or directory", repr(str(args.program)))
            parser.exit(1)
        except OSError as e:
            error(str(e))
            parser.exit(1)

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
            Emulator(assemble(file, path)).run_until_halt()
        elif args.assembler:
            stdout.buffer.write(assemble(file, path))
    except AsmError as e:
        if args.debug: raise
        if e.location: error(e.location, e.message)
        else: error(e.message) 
        parser.exit(1)
    except NotImplementedError as e:
        error(e)
        parser.exit(1)
    except KeyboardInterrupt:
        error("interrupt.")

if __name__ == "__main__":
    main()
