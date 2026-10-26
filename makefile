.PHONY: run
run:
	s6asm -m < test.s > temp.bin
	# s6emu temp.bin

