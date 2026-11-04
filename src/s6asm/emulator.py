from pathlib import Path

from .errs import *
from .serial import readc, writec

RAM = (0x0000, 0x8000)
ROM = (0x8000, 0x8000)

HALT = 0xfffe
SERO = 0xfffe
SERI = 0xffff

def within(addr: int, region: tuple[int, int]) -> bool:
    start, size = region
    return start <= addr < start + size

class Tape:
    def __init__(self, path: str) -> None:
        self.path: str = path
        self.text: bytes = Path(path).read_bytes()
        self.pos: int = 0

    def read(self) -> int|None:
        if self.pos == len(self.text):
            return None

        self.pos += 1
        return self.text[self.pos - 1]

    def rewind(self) -> None:
        self.pos = 0

class Emulator:
    def __init__(self, image: bytearray) -> None:
        if len(image) > ROM[1]:
            raise AsmRomError("program too large to fit into 32K.")

        self.rom: bytearray = image.copy()
        self.rom.extend(b'\00' * (ROM[1] - len(image)))
        self.ram: bytearray = bytearray(RAM[1])

        self.pc: int = ROM[0]

        self.out: str = ""
        self.writes: set[int] = set()

        self.last_key: str|None = None
        self.tape: Tape|None = None

    def attach(self, tape: Tape|None) -> None:
        self.tape = tape

    def read_key(self) -> str|None:
        if self.tape:
            i = self.tape.read()
            return i if i is None else chr(i)
        key = self.last_key
        self.last_key = None
        return key

    def halted(self) -> bool:
        return self.pc == HALT

    def fetch(self, addr: int) -> int:
        addr &= 0xffff

        if addr == SERI:
            return ord(self.read_key() or '\0')
        elif within(addr, RAM):
            return self.ram[addr]
        elif within(addr, ROM):
            return self.rom[addr - ROM[0]]
        raise ValueError("memory read out of range")

    def fetchw(self, addr: int) -> int:
        return (self.fetch(addr) << 8) | (self.fetch(addr+1))

    def write(self, addr: int, value: int) -> None:
        addr &= 0xffff
        value &= 0xff

        self.writes.add(addr)

        if addr == SERO:
            writec(chr(value))
            self.out += chr(value)
        elif within(addr, RAM):
            self.ram[addr] = value
        elif within(addr, ROM):
            pass
        else:
            raise ValueError("memory write out of range")

    def step(self, uart_in: str|None) -> None:
        if uart_in:
            self.last_key = uart_in

        a = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff
        b = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff
        c = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff

        r = (self.fetch(b) - self.fetch(a)) & 0xff
        self.write(b, r)

        if r == 0 or (r & (1 << 7)):
            self.pc = c

    def run_until_halt(self) -> None:
        while not self.halted(): self.step(readc())
