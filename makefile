.PHONY: run
run:
	s6asm -m test.s > temp.s
	# s6emu temp.bin

