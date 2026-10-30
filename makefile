.PHONY: run
run:
	s6asm -l test.s

.PHONY: install
install:
	python3 -m pip install -e .
