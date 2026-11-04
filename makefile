.PHONY: run
run:
	s6asm -se src/s6asm/monitor.s

.PHONY: install
install:
	python3 -m pip install -e .
