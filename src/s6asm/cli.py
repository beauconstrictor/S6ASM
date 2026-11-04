from __future__ import annotations

from os import getenv
from time import sleep
from pathlib import Path
from argparse import ArgumentParser
from sys import stdout, stderr, stdin
from importlib.metadata import version

from .errs import *
from .tokeniser import tokenise
from .emulator import Emulator, Tape
from .preprocessor import preprocessor
from .linker import evaluate, assemble
from .serial import init_term, restore_term, readc

GOTO_TAPE = "\x14" # <c-t>

def select_tape(emu: Emulator) -> None:
    print("\033[?1049h\033[H", end="")
    stdout.flush()

    print("S6ASM TAPE MANAGER")
    print("------------------")
    print()
    if emu.tape:
        print(f"Tape: {emu.tape.path}")
        print(f"Head: {emu.tape.pos} / {len(emu.tape.text)}")
        print()
        print("[r] Rewind")
        print("[d] Detach")
    print("[a] Attach new tape")
    print("[q] Return to the emulator")

    choice = readc()
    while choice is None: choice = readc()

    match choice:
        case "r":
            assert emu.tape
            emu.tape.rewind()
        case "d":
            emu.attach(None)
        case "a":
            restore_term()
            path = input("\n[path to tape] ")
            init_term()
            if not Path(path).is_file():
                print(f"{path!r} is not a file")
                sleep(1.2)
                return select_tape(emu)
            emu.attach(Tape(path))
            return select_tape(emu)
        case "q":
            pass
        case _:
            return select_tape(emu)

    print("\033[?1049l", end="")
    stdout.flush()

def emulate(binary: bytearray) -> None:
    init_term()

    emu = Emulator(binary)
    while not emu.halted():
        c = readc()
        if c == GOTO_TAPE:
            emu.attach(select_tape(emu))
        else:
            emu.step(c)

    restore_term()

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
                      help="read and interpret source code. catches only syntax errors.")
    mode.add_argument("-p", "--preprocessor", action="store_true",
                      help="expand macros and includes in the program.")
    mode.add_argument("-l", "--linker", action="store_true",
                      help="convert the program into a series of subleq instructions and byte directives.")
    mode.add_argument("-e", "--emulator", action="store_true",
                      help="execute the program using a built-in S6 emulator.")

    parser.add_argument("-s", "--slow-emu", action="store_true",
                      help="slows down the emulator, to make it easier to identify performance issues.")

    args = parser.parse_args()
    path = str(args.program)

    if args.slow_emu and not args.emulator:
        parser.error("--slow-emu requires --emulator")

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
            emulate(binary)
        else:
            stdout.buffer.write(binary)
    except AsmError as e:
        if args.traceback:
            raise
        else:
            if e.traceback:
                assert e.location is not None
                error(e.location, e.message, [e.location, *e.traceback])
            elif e.location:
                error(e.location, e.message)
            else:
                error(e.message) 
            parser.exit(e.code)
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
