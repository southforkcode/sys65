# asm65 - 6502 Assembler

`asm65` is a Python-based assembler for the MOS Technology 6502 microprocessor. It features a modern AST-based pipeline (`Tokenizer` -> `Parser` -> `Compiler`) and supports standard 6502 syntax, including all addressing modes and common directives.

## Directory Structure

- **`lib/`**: Core implementation files.
  - `asm.py`: Main driver class (`Assembler`).
  - `ast.py`: Abstract Syntax Tree node definitions.
  - `compiler.py`: 2-pass compiler (AST to machine code).
  - `parser.py`: Recursive descent parser (Tokens to AST).
  - `tokenizer.py`: Regex-based lexer.
  - `opcodes.py`: 6502 instruction set and addressing mode definitions.
  - `bytes.py`: Byte conversion utilities (Little Endian).
  - `symtab.py`: Symbol table management.

- **`tests/`**: Unit and integration tests.
  - `test_assembler.py`: Integration tests parsing full files.
  - `test_directives.py`: Unit tests for `.org`, `.byte`, `.word`, `.fill`.
  - `test_opcodes.py`: Verification of opcode tables.
  - `test_tokenizer.py`: Unit tests for tokenization.
  - `test_absolute.py`: Tests for Absolute, Zero Page, and Relative addressing.
  - `test_string_loop.py`: Verification of string generation and memory traversal.
  - **`data/`**: Assembly source files used by tests (e.g., `test0.asm`).

- **`asm65.py`**: Command-line entry point.

## Usage

To assemble a file:

```bash
python3 asm65.py <input.asm> <output.bin>
```

Example:
```bash
python3 asm65.py tests/data/test0.asm output.bin
```

## Testing

The project uses Python's `unittest` framework. A `Makefile` is provided in the root `sys65/` directory for convenience.

### Running the Full Test Suite

From the project root (`sys65/`), run:

```bash
make test
```

This sets the `PYTHONPATH` correctly and discovers all tests in `tools/asm65/tests`.

### Running Individual Tests

You can run individual test files using `python3 -m unittest`. 
**Note:** You must set `PYTHONPATH` to include `tools/asm65`.

Example: Running only the directive tests:

```bash
PYTHONPATH=tools/asm65 python3 -m unittest tools/asm65/tests/test_directives.py
```

Example: Running a specific test case (e.g., `test_org`):

```bash
PYTHONPATH=tools/asm65 python3 -m unittest tools.asm65.tests.test_directives.TestDirectives.test_org
```
