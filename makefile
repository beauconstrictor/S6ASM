.PHONY: run
run:
	s6asm < test.s > temp.bin
	s6emu temp.bin

