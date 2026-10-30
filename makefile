.PHONY: run
run:
	s6asm -p test.s

.PHONY: install
install:
	python3 -m pip install -e .
