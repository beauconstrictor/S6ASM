.PHONY: run
run:
	s6asm -e test.s

.PHONY: install
install:
	python3 -m pip install -e .
