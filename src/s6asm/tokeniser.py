from enum import Enum
from typing import override, Self, final
from collections.abc import Iterator, Sequence

from .errs import *

BRACKET_CHARS = ("(", ")", ";")

ALLOWED_DIRECTIVES = {
        None,
        "org",
        "byte",
        "word",
        "const",
        "macro",
        "ascii",
        "asciiz",
        "include",
        "endmacro"}

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

        if self.directive not in ALLOWED_DIRECTIVES:
            raise AsmSyntaxError(f"unsupported directive: {self.directive!r}", self)

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
