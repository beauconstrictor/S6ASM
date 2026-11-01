from typing import Protocol

class HasLocation(Protocol):
    path: str
    lineno: int
    traceback: list[tuple[str, str, int]]

class AsmError(Exception):
    code: int = 1

    def __init__(self, message: str, token: HasLocation|None=None) -> None:
        self.message: str = message
        self.location: str|None = None
        self.traceback: list[str]= []
        if token is not None:
            self.location = f"{token.path}:{token.lineno}"

            for file, macro, lineno in token.traceback:
                self.traceback.append(f"{file}:{macro}:{lineno}")

            if len(token.traceback) > 0:
                message += "\n\ntraceback (deepest macro last):\n"
                i = 2
                message += f"\n{self.location}"
                for t in self.traceback:
                    message += f"\n{' '*i}|\n{' '*i}+-- {t}"
                    i += 6

            super().__init__(f"{self.location}: {message}")
        else:
            super().__init__(message)

class AsmRomError(AsmError):
    code: int = 3
class AsmBankError(AsmError):
    code: int = 4
class AsmSyntaxError(AsmError):
    code: int = 5
class AsmOriginError(AsmError):
    code: int = 6
class AsmIncludeError(AsmError):
    code: int = 7
class AsmRecursionError(AsmError):
    code: int = 8
class AsmWordWidthError(AsmError):
    code: int = 9
class AsmExpressionError(AsmError):
    code: int = 10
