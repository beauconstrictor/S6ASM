.PHONY: run
run:
	python3 src/main.py < test.s > temp.bin
	s6emu temp.bin

