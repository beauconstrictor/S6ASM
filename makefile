.PHONY: run
run:
	s6asm -se cvm.s

.PHONY: install
install:
	python3 -m pip install -e .
