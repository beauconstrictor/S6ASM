from sys import stdout

from .errs import *

# - emulate a binary
# TODO: remove magic numbers
class Emulator:
    def __init__(self, image: bytearray) -> None:
        if len(image) > 0x8000:
            raise AsmRomError("program too large to fit into 32K.")

        self.rom: bytearray = image.copy()
        self.rom.extend(b'\00' * (0x8000 - len(image)))
        self.ram: bytearray = bytearray(0x8000)

        self.pc: int = 0x8000

    def halted(self) -> bool:
        return self.pc == 0xfffe

    def fetch(self, addr: int) -> int:
        addr &= 0xffff

        if addr == 0xffff:
            raise NotImplementedError("the integrated emulator does not yet support input")
        elif addr < 0x8000:
            return self.ram[addr]
        elif addr < 0x10000:
            return self.rom[addr - 0x8000]
        raise ValueError("memory read out of range")

    def fetchw(self, addr: int) -> int:
        return (self.fetch(addr) << 8) | (self.fetch(addr+1))

    def write(self, addr: int, value: int) -> None:
        if addr == 0xfffe:
            stdout.write(chr(value))
        elif addr < 0x8000:
            self.ram[addr] = value
        elif addr < 0x10000:
            pass
        else:
            raise ValueError("memory write out of range")

    def step(self) -> bool:
        a = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff
        b = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff
        c = self.fetchw(self.pc)
        self.pc = (self.pc + 2) & 0xffff

        r = (self.fetch(b) - self.fetch(a)) & 0xff
        self.write(b, r)

        if r == 0 or (r & 0x80):
            self.pc = c
       
        # just for convenience
        return not self.halted()

    def run_until_halt(self) -> None:
        while self.step(): pass
