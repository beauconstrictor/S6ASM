.PHONY: run
run:
	python3 src/main.py < test.s > temp.bin
	../emu/build/s6 temp.bin

