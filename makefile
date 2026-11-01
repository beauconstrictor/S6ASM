.PHONY: run
run:
	s6asm -se test.s

.PHONY: install
install:
	python3 -m pip install -e .
