from pathlib import Path
from itertools import chain
from dataclasses import dataclass
from collections import defaultdict
from importlib.resources import files
from collections.abc import Iterable, Iterator

from .errs import *
from .tokeniser import make_expr, tokenise, Token, Expression, Literal

# TODO: record the original location in the macro definition as well

@dataclass
class Macro:
    tokens: list[Token]
    name: str
    labels: set[str]
    parameters: list[str]

macro_invocation_idx = 0

def resolve_local_labels(source: str, path: str="<unknown>") -> Iterator[Token]:
    last_global = None
    global_in_macro = False
    in_macro = False

    def ensure_correct(tok: Token) -> None:
        if not last_global:
            raise AsmSyntaxError("local label before first global label", tok)
        if global_in_macro and not in_macro:
            raise AsmSyntaxError("last global label was within a macro definition", tok)
        if not global_in_macro and in_macro:
            raise AsmSyntaxError("last global label was not within a macro definition", tok)

    for tok in tokenise(source, path):
        if tok.directive == "macro":
            in_macro = True
        elif tok.directive == "endmacro":
            in_macro = False

        if tok.label:
            if not tok.label.startswith("@"):
                last_global = tok.label
                global_in_macro = in_macro
            else:
                ensure_correct(tok)
                assert isinstance(last_global, str)
                tok.label = last_global + tok.label

        for exp in chain(tok.operands, (tok.a, tok.b, tok.c)):
            if not isinstance(exp, Expression): continue
            for subtok in exp.tokens:
                if not isinstance(subtok, Literal): continue
                if not subtok.text.startswith("@"): continue
                ensure_correct(tok)
                assert isinstance(last_global, str)
                subtok.text = last_global + subtok.text

        yield tok

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

    prefix = f"{tok.macro}/{macro_invocation_idx}@"
    macro_invocation_idx += 1

    for subtok in macro.tokens:
        subtok = subtok.duplicate()
        subtok.path = tok.path
        subtok.lineno = tok.lineno

        # macro local labels
        if subtok.label: subtok.label = prefix + subtok.label

        if subtok.directive:
            raise AsmSyntaxError("cannot use directives inside macros", subtok)

        for i, o in enumerate(subtok.operands):
            for l in macro.labels:
                if isinstance(o, str): continue
                o.substitute(l, prefix + l)

        for l in macro.labels:
            for i in (subtok.a, subtok.b, subtok.c):
                if i is None: continue
                i.substitute(l, prefix + l)

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

    for tok in resolve_local_labels(source, path):
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
            if tok.directive:
                raise AsmSyntaxError("directives are not allowed inside macros", tok)
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
           
            new_exp = Expression("")
            new_exp.tokens = [Literal(s[1:])]
            value = new_exp.evaluate(labels, tok)
            if -128 <= value <= -1:
                value &= 0xff
            if not (0 <= value <= 255):
                raise AsmWordWidthError(f"{exp!r} is out of range for an 8-bit value", tok)
            immediates[value].add(s)

    line = 0
    for value in sorted(immediates.keys()):
        for exp in sorted(immediates[value]):
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
                raise AsmSyntaxError(f"{tok.operands[0]!r} is already defined", tok)
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

def preprocessor(source: str, path: str="<unknown>") -> Iterator[Token]:
    global macro_invocation_idx
    macro_invocation_idx = 0

    tokens = list(expand_macros(source, path=path))
    yield from tokens
    labels = find_labels(tokens)
    yield from generate_immediates(tokens, labels)

