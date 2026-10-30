from sys import stdout

from .errs import *

RAM = (0x0000, 0x8000)
ROM = (0x8000, 0x8000)

HALT = 0xfffe
SERO = 0xfffe
SERI = 0xffff

def within(addr: int, region: tuple[int, int]) -> bool:
    start, size = region
    return start <= addr < start + size

# - emulate a binary
class Emulator:
    def __init__(self, image: bytearray) -> None:
        if len(image) > ROM[1]:
            raise AsmRomError("program too large to fit into 32K.")

        self.rom: bytearray = image.copy()
        self.rom.extend(b'\00' * (ROM[1] - len(image)))
        self.ram: bytearray = bytearray(RAM[1])

        self.pc: int = ROM[0]

    def halted(self) -> bool:
        return self.pc == HALT

    def fetch(self, addr: int) -> int:
        addr &= 0xffff

        if addr == SERI:
            raise NotImplementedError("the integrated emulator does not yet support input")
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

        if addr == SERO:
            stdout.write(chr(value))
            stdout.flush()
        elif within(addr, RAM):
            self.ram[addr] = value
        elif within(addr, ROM):
            pass
        else:
            raise ValueError("memory write out of range")

    def step(self) -> None:
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
        while not self.halted(): self.step()
