.PHONY: run
run:
	python3 src/main.py -m < test.s # > temp.bin
	# s6emu temp.bin

