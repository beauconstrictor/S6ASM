from __future__ import annotations

from os import getenv
from pathlib import Path
from argparse import ArgumentParser
from sys import stdout, stderr, stdin
from importlib.metadata import version

from .errs import *
from .tokeniser import tokenise
from .preprocessor import preprocessor
from .linker import evaluate, assemble
from .emulator import Emulator

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
            for tok in preprocessor(file, path=path):
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
