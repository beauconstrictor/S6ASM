import sys

if sys.platform.startswith("win"):
    import msvcrt

    def readc() -> str | None:
        if msvcrt.kbhit():
            c = msvcrt.getwch()
            if c == '\r': c = '\n'
            return c
        return None

else:
    import select
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    def readc() -> str | None:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            return sys.stdin.read(1)
        return None

    import atexit
    
    atexit.register(lambda: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings))

def writec(c: str) -> None:
    sys.stdout.write(c)
    sys.stdout.flush()
