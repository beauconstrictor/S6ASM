import sys
import argparse
from typing import Iterator, Iterable

# TODO: support macro arguments
# TODO: semicolon in character literals

VERSION = "0.1.0"

ESCAPE_SEQUENCES = {
        "s": " ",
        "e": "\033",
        "n": "\n",
        "sc": ";"}

class AsmError(Exception): ...
class AsmSyntaxError(AsmError): ...
class AsmOriginError(AsmError): ...

# [label:] [(macro|.directive) [operands]...|subleq a b [c]]
class Token:
    def __init__(self, line: str) -> None:
        if ";" in line: line = line.split(";")[0]
        words = line.split()

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
                raise AsmSyntaxError("expected ':' after label")
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
        return tok

    def __repr__(self) -> str:
        s = ""
        if self.label: s += f"{self.label}: "
        else: s += "  "
        if self.directive: s += f".{self.directive} "
        elif self.macro: s += f"{self.macro} "
        elif self.a: s += f"subleq {self.a} {self.b} {self.c}"
        if self.operands: s += " ".join(self.operands)
        return s

def tokenise(source: str) -> Iterator[Token]:
    for l in source.splitlines():
        if not l.strip(): continue
        yield Token(l)

def expand_macros(source: str) -> Iterator[Token]:
    macros = {}
    current_macro = None
    macro_invocation_idx = 0

    for tok in tokenise(source):
        if tok.directive == "macro":
            if current_macro:
                raise AsmSyntaxError("cannot nest macro definitions")
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected macro name")
            elif len(tok.operands) > 1:
                raise AsmSyntaxError("unexpected operands in macro directive")

            current_macro = [], tok.operands[0], set()
            if tok.label:
                current_macro[0].append(Token(f"{tok.label}:"))
                current_macro[2].add(tok.label)
            continue
        elif tok.directive == "endmacro":
            if not current_macro:
                raise AsmSyntaxError("endmacro directive outside of a macro definition")
            macro, name, labels = current_macro
            macros[name] = macro, labels
            current_macro = None
            continue

        if tok.macro is not None:
            try:
                macro, labels = macros[tok.macro]
            except KeyError:
                raise AsmSyntaxError(f"undefined macro, {tok.macro}")

            suffix = f"___macro{macro_invocation_idx}"
            macro_invocation_idx += 1

            for subtok in macro:
                subtok = subtok.duplicate()
                if subtok.label: subtok.label += suffix
                for i, o in enumerate(subtok.operands):
                    if o in labels:
                        subtok.operands[i] += suffix
                if subtok.a in labels: subtok.a += suffix
                if subtok.b in labels: subtok.b += suffix
                if subtok.c in labels: subtok.c += suffix
                yield subtok

            continue

        if current_macro:
            current_macro[0].append(tok)
            if tok.label: current_macro[2].add(tok.label)
        else:
            yield tok

    if current_macro is not None:
        raise AsmSyntaxError("macro definition is unterminated")

def evaluate(s: str, labels: dict[str, int]|None) -> int:
    if len(s) == 3 and s[0] == "'" and s[-1] == "'":
        return ord(s[1])
    if len(s) > 3 and s[0] == "'" and s[1] == "\\" and s[-1] == "'":
        try:
            return ord(ESCAPE_SEQUENCES[s[2:-1]])
        except KeyError:
            raise AsmSyntaxError(f"invalid escape sequence: {s}")

    try:
        return int(s, 0)
    except ValueError:
        if labels is not None and labels.get(s) is not None:
            return labels[s]

    raise AsmSyntaxError(f"unsupported expression form: '{s}'")

def find_labels(tokens: Iterable[Token]) -> dict[str, int]:
    labels = {}
    pc = 0

    for tok in tokens:
        if tok.label:
            labels[tok.label] = pc

        if tok.a is not None:
            pc += 6
        elif tok.directive == "org":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected address in org directive")
            elif len(tok.operands) > 1:
                raise AsmSyntaxError("unexpected operands in org directive")
            pc = evaluate(tok.operands[0], None)
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
                raise AsmOriginError("cannot apply a label to an org directive")
            addr   = len(binary)
            # we've already verified the right amount of arguments
            # during find_labels
            target = evaluate(tok.operands[0], labels)
            if initial_origin is None:
                initial_origin = target
            else:
                if target - initial_origin < addr:
                    raise AsmOriginError("origin directives must come in order")
                binary.extend(b"\0" * (target - initial_origin - addr))

        if initial_origin is None:
            raise AsmOriginError("file must start with an org directive")

        if tok.a is not None:
            extend_with_word(binary, evaluate(tok.a, labels))
            extend_with_word(binary, evaluate(tok.b, labels))
            extend_with_word(binary, evaluate(tok.c, labels))

        elif tok.directive == "byte":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected argument in byte directive")
            elif len(tok.operands) > 1:
                raise AsmSyntaxError("unexpected arguments in byte directive")
            binary.append(evaluate(tok.operands[0], labels))
        elif tok.directive == "word":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected argument in word directive")
            elif len(tok.operands) > 1:
                raise AsmSyntaxError("unexpected arguments in word directive")
            extend_with_word(binary, evaluate(tok.operands[0], labels))
        elif tok.directive == "const":
            if len(tok.operands) < 1:
                raise AsmSyntaxError("expected variable name and value in const directive")
            elif len(tok.operands) == 1:
                raise AsmSyntaxError("expected variable value in const directive")
            elif len(tok.operands) > 2:
                raise AsmSyntaxError("unexpected arguments in const directive")
            labels[tok.operands[0]] = evaluate(tok.operands[1], labels)

    return binary

def main() -> None:
    parser = argparse.ArgumentParser(
            prog="s6asm")
    
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-n", "--normalise", action="store_true")
    mode.add_argument("-m", "--expand-macros", action="store_true")
    mode.add_argument("-a", "--assemble", default=True, action="store_true")
    mode.add_argument("-v", "--version", action="version",
                      version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    file = sys.stdin.read()
    
    try:
        if args.normalise:
            for tok in tokenise(file):
                print(tok)
        elif args.expand_macros:
            for tok in expand_macros(file):
                print(tok)
        elif args.assemble:
            sys.stdout.buffer.write(assemble(file))
    except AsmError as e:
        parser.error(e)

if __name__ == "__main__":
    main()
