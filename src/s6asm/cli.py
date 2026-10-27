import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator, Iterable
from importlib.resources import files
from importlib.metadata import version

# TODO: expressions with operators
# TODO: line numbers in error messages!
# TODO: support labels attached to macro calls
# TODO: semicolon and space in character literals

ESCAPE_SEQUENCES = {
        "s": " ",
        "e": "\033",
        "n": "\n",
        "sc": ";"}

class AsmError(Exception):
    def __init__(self, message: str, token: Token|None=None) -> None:
        if token:
            super().__init__(f"{token.path}:{token.lineno}: {message}")
        else:
            super().__init__(message)
class AsmSyntaxError(AsmError): ...
class AsmOriginError(AsmError): ...
class AsmIncludeError(AsmError): ...
class AsmRecursionError(AsmError): ...
class AsmWordWidthError(AsmError): ...

# [label:] [(macro|.directive) [operands]...|subleq a b [c]]
class Token:
    def __init__(self, line: str, path: str="<unknown>", lineno: int=-1) -> None:
        if ";" in line: line = line.split(";")[0]
        words = line.split()

        self.path = path
        self.lineno = lineno

        self.label     = None

        self.a         = None
        self.b         = None
        self.c         = None

        self.macro     = None
        self.directive = None
        self.operands = []

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
                self.a = words[1]
                self.b = words[2]
                self.c = words[3]
            else:
                raise AsmSyntaxError("unexpected operands")
        else:
            self.macro = words[0]
            self.operands = words[1:]

    def duplicate(self) -> Token:
        tok = Token("")
        tok.label = self.label
        tok.a = self.a
        tok.b = self.b
        tok.c = self.c
        tok.macro = self.macro
        tok.directive = self.directive
        tok.operands = [*self.operands]
        tok.path = self.path
        tok.lineno = self.lineno
        return tok

    def __repr__(self) -> str:
        s = ""
        if self.label is not None: s += f"{self.label}: "
        else: s += "  "
        if self.directive is not None: s += f".{self.directive} "
        elif self.macro is not None: s += f"{self.macro} "
        elif self.a is not None: s += f"subleq {self.a} {self.b} {self.c}"
        if self.operands: s += " ".join(self.operands)
        return s

def tokenise(source: str, path: str="<unknown>") -> Iterator[Token]:
    for i, l in enumerate(source.splitlines()):
        if not l.strip(): continue
        yield Token(l, path, i)

@dataclass
class Macro:
    tokens: list[Token]
    name: str
    labels: set[str]
    parameters: list[str]


macro_invocation_idx = 0

def expand_single_macro(tok: Token, macros: dict[str, Macro]) -> Iterator[Token]:
    global macro_invocation_idx

    try:
        macro = macros[tok.macro]
    except KeyError:
        raise AsmSyntaxError(f"undefined macro: {tok.macro}", tok)

    if len(tok.operands) != len(macro.parameters):
        raise AsmSyntaxError(f"incorrect macro argument count", tok)

    suffix = f"___macro{macro_invocation_idx}"
    macro_invocation_idx += 1

    for subtok in macro.tokens:
        subtok = subtok.duplicate()
        subtok.path = tok.path
        subtok.lineno = tok.lineno

        # macro local labels
        if subtok.label: subtok.label += suffix
        for i, o in enumerate(subtok.operands):
            if o in macro.labels:
                subtok.operands[i] += suffix
        if subtok.a in macro.labels: subtok.a += suffix
        if subtok.b in macro.labels: subtok.b += suffix
        if subtok.c in macro.labels: subtok.c += suffix

        # macro parameters
        for i, o in enumerate(subtok.operands):
            if o in macro.parameters:
                value = tok.operands[macro.parameters.index(o)]
                subtok.operands[i] = value
        if subtok.a in macro.parameters:
            subtok.a = tok.operands[macro.parameters.index(subtok.a)]
        if subtok.b in macro.parameters:
            subtok.b = tok.operands[macro.parameters.index(subtok.b)]
        if subtok.c in macro.parameters:
            subtok.c = tok.operands[macro.parameters.index(subtok.c)]

        if subtok.macro is not None:
            yield from expand_single_macro(subtok, macros)
        else:
            yield subtok

def is_printable_ascii(c: int) -> bool:
    return 32 <= c <= 126

def generate_immediates() -> Iterator[Token]:
    labels = set()

    for i in range(0x100):
        if is_printable_ascii(i) and chr(i) not in (" ", ";"):
            l = f"#'{chr(i)}':"
            if l in labels: continue
            labels.add(l)
            yield Token(l)

        for prefix, max_width in (("x", 2), ("b", 8)):
            for w in range(1, max_width + 1):
                l = f"#0{prefix}{i:0{w}{prefix}}:"
                if l in labels:
                    continue
                labels.add(l)
                yield Token(l)

        for w in range(1,6):
            l = f"#{i:0{w}d}:"
            if l in labels: continue
            labels.add(l)
            yield Token(l)

        yield Token(f"  .byte {i}")

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

            macro_definition = tok
            current_macro = Macro([], tok.operands[0], set(), tok.operands[1:])
            if tok.label:
                current_macro.tokens.append(Token(f"{tok.label}:"))
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
            if len(ident) < 2 or (ident[0] not in ('"', "'") and ident[0] != "<" and ident[-1] != ">"):
                raise AsmSyntaxError("include path must be surrounded by angled brackets or quotes", tok)
            stdlib = ident[0] == "<"
            path = ident[1:-1]

            if stdlib and not allow_stdlib:
                raise AsmIncludeError("cannot include <stdlib> outside of the root file", tok)
            elif stdlib:
                if path == "stdlib": immediates = True
                file = files("s6asm").joinpath("stdlib", path + ".s")
            else:
                file = Path(path)

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
                yield Token(f"{tok.label}:")
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

def evaluate(s: str, labels: dict[str, int]|None, token: Token|None=None) -> int:
    if len(s) == 3 and s[0] == "'" and s[-1] == "'":
        return ord(s[1])
    if len(s) > 3 and s[0] == "'" and s[1] == "\\" and s[-1] == "'":
        try:
            return ord(ESCAPE_SEQUENCES[s[2:-1]])
        except KeyError:
            raise AsmSyntaxError(f"invalid escape sequence: {s}", token)

    try:
        return int(s, 0)
    except ValueError:
        if labels is not None and labels.get(s) is not None:
            return labels[s]

    raise AsmSyntaxError(f"unsupported expression form: '{s}'", token)

def find_labels(tokens: Iterable[Token]) -> dict[str, int]:
    labels = {}
    pc = 0

    for tok in tokens:
        if tok.label:
            if tok.label in labels:
                raise AsmSyntaxError(f"redefinition of label: {tok.label}", tok)
            labels[tok.label] = pc

        if tok.a is not None:
            pc += 6
        elif tok.directive == "org":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected address in org directive", tok)
            elif len(tok.operands) > 1:
                raise AsmSyntaxError("unexpected operands in org directive", tok)
            pc = evaluate(tok.operands[0], None, tok)
        elif tok.directive == "byte":
            pc += 1
        elif tok.directive == "word":
            pc += 2

    return labels

def extend_with_word(binary: bytearray, word: int) -> None:
    word &= 0xffff
    # big endian
    binary.extend([word >> 8, word & 0xff])

def assemble(source: str) -> bytearray:
    tokens = list(expand_macros(source))
    labels = find_labels(tokens)
    binary = bytearray()

    initial_origin = None

    for tok in tokens:
        if tok.directive == "org":
            if tok.label:
                raise AsmOriginError("cannot apply a label to an org directive", tok)
            addr   = len(binary)
            # we've already verified the right amount of arguments
            # during find_labels
            target = evaluate(tok.operands[0], labels, tok)
            if initial_origin is None:
                initial_origin = target
            else:
                if target - initial_origin < addr:
                    raise AsmOriginError("origin directives must come in order", tok)
                binary.extend(b"\0" * (target - initial_origin - addr))

        if initial_origin is None:
            raise AsmOriginError(f"{tok.path}: file must start with an org directive")

        if tok.a is not None:
            extend_with_word(binary, evaluate(tok.a, labels, tok))
            extend_with_word(binary, evaluate(tok.b, labels, tok))
            extend_with_word(binary, evaluate(tok.c, labels, tok))

        elif tok.directive == "byte":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected argument in byte directive", tok)
            elif len(tok.operands) > 1:
                raise AsmSyntaxError("unexpected arguments in byte directive", tok)
            try:
                binary.append(evaluate(tok.operands[0], included, tok))
            except ValueError:
                raise AsmWordWidthError("byte directives must be in the range 0 <-> 255 (inclusive)", tok)
        elif tok.directive == "word":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected argument in word directive", tok)
            elif len(tok.operands) > 1:
                raise AsmSyntaxError("unexpected arguments in word directive", tok)
            extend_with_word(binary, evaluate(tok.operands[0], labels, tok))
        elif tok.directive == "const":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected variable name and value in const directive", tok)
            elif len(tok.operands) == 1:
                raise AsmSyntaxError("expected variable value in const directive", tok)
            elif len(tok.operands) > 2:
                raise AsmSyntaxError("unexpected arguments in const directive", tok)
            labels[tok.operands[0]] = evaluate(tok.operands[1], labels, tok)

    return binary

def main() -> None:
    parser = argparse.ArgumentParser(
            prog="s6asm")
    
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-n", "--normalise", action="store_true")
    mode.add_argument("-m", "--expand-macros", action="store_true")
    mode.add_argument("-a", "--assemble", default=True, action="store_true")
    mode.add_argument("-v", "--version", action="version",
                      version=f"%(prog)s {version('s6asm')}")

    args = parser.parse_args()

    file = sys.stdin.read()
    
    try:
        if args.normalise:
            for tok in tokenise(file, "<stdin>"):
                print(tok)
        elif args.expand_macros:
            for tok in expand_macros(file, "<stdin>"):
                print(tok)
        elif args.assemble:
            sys.stdout.buffer.write(assemble(file))
    except AsmError as e:
        parser.error(e)

if __name__ == "__main__":
    main()
