.PHONY: test test-python

test: test-python

test-python:
	PYTHONPATH=tools/asm65 python3 -m unittest discover -s tools/asm65/tests -t tools/asm65
