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

def visualise(emu: Emulator, step: int) -> None:
    print("\033[2J\033[H", end="")

    print(f"step {step}:")
    print(f"output: {emu.out}")
    print("ram:")

    for addr in sorted(emu.writes):
        print(f"0x{addr:04x} = 0x{emu.fetch(addr):02x}")
    input()

def debug(emu: Emulator) -> None:
    step = 1
    while True:
        if not emu.halted():
            emu.step()
            step += 1
        visualise(emu, step)

def error(summary: object, desc: object="", traceback: list[str]|None=None) -> None:
    red = "\033[31m" if stderr.isatty() and not getenv("NO_COLOR") else ""
    yellow = "\033[33m" if red else ""
    purple = "\033[35m" if red else ""
    reset = "\033[0m" if red else ""
    bold = "\033[1m" if red else ""
    dim = "\033[2m" if red else ""
    print(f"{red}s6asm: {yellow}{bold}{summary if desc else ''}{': ' if desc else ''}{reset}{desc if desc else summary}", file=stderr)

    if traceback:
        print(f"\ntraceback (deepest macro last):\n")
        i = 2
        print(f"{purple}{traceback[0]}")
        for t in traceback[1:]:
            print(f"{reset}{dim}{' '*i}|\n{' '*i}+-- {reset}{purple}{t}")
            i += 6
        print(reset)


def main() -> None:
    parser = ArgumentParser(
            prog="s6asm",
            description="A macro assembler for S6 assembly language.",
            epilog="Use a hyphen instead of a filepath to use stdin.")

    parser.add_argument("program", type=Path)

    parser.add_argument("-v", "--version", action="version",
                      version=f"%(prog)s {version('s6asm')}")
    parser.add_argument("--traceback", action="store_true",
                        help="show python tracebacks")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-t", "--tokeniser", action="store_true",
                      help="convert the program into a simpler form.")
    mode.add_argument("-p", "--preprocessor", action="store_true",
                      help="expand macros and includes in the program.")
    mode.add_argument("-l", "--linker", action="store_true",
                      help="convert the program into a series of subleq instructions and byte directives.")
    mode.add_argument("-e", "--emulator", action="store_true",
                      help="execute the program using a built-in S6 emulator.")
    mode.add_argument("-d", "--debug", action="store_true",
                      help="emulate the program and watch what it does, step by step.")

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
            return
        elif args.preprocessor:
            for tok in preprocessor(file, path=path):
                print(tok)
            return
        elif args.linker:
            for tok in evaluate(file, path=path):
                print(tok)
            return

        binary = assemble(file, path)

        if args.emulator:
            Emulator(binary).run_until_halt()
        elif args.debug:
            emu = Emulator(binary)
            debug(emu)
        else:
            stdout.buffer.write(binary)
    except AsmError as e:
        if args.traceback:
            raise
        else:
            if args.debug:
                raise
            elif e.traceback:
                assert e.location is not None
                error(e.location, e.message, [e.location, *e.traceback])
            elif e.location:
                error(e.location, e.message)
            else:
                error(e.message) 
            parser.exit(1)
    except NotImplementedError as e:
        error(e)
        parser.exit(1)
    except KeyboardInterrupt:
        if args.traceback:
            raise
        else:
            error("interrupt.")

if __name__ == "__main__":
    main()
