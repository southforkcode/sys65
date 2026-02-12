# asm65 User Guide

`asm65` is a Python-based assembler for the MOS Technology 6502 microprocessor. It supports standard 6502 syntax, all addressing modes, and a set of directives for code organization and data definition.

## Running the Assembler

To assemble a source file, run the `asm65.py` script from the command line:

```bash
python3 tools/asm65/asm65.py <input_file> [<input_file>...] <output_file>
```

- `<input_file>`: One or more assembly source files (`.asm`). If multiple files are provided, they are processed in order.
- `<output_file>`: The destination path for the compiled binary file (`.bin` or `.prg`).

### Example

```bash
python3 tools/asm65/asm65.py game.asm game.bin
```

## Syntax Reference

### Comments
Comments start with a semicolon `;` and continue to the end of the line.

```asm
lda #$00 ; This is a comment
```

### Numbers
- **Decimal**: `123`
- **Hexadecimal**: `$FF`, `0xFF`
- **Binary**: `%10101010`, `0b10101010`
- **Character**: `'A'` (converts to ASCII value)

### Strings
Strings are enclosed in double quotes `"`.

```asm
.byte "Hello, World!", 0
```

### Labels
Labels are identifiers followed by a colon `:`. They can be used as jump targets or data addresses.

```asm
start:
    jmp loop
loop:
    jmp start
```

### Assignments
Constants can be defined using the `=` operator.

```asm
MAX_LIVES = 3
lda #MAX_LIVES
```

### Addressing Modes

| Mode | Syntax | Example |
|------|--------|---------|
| Implied | - | `tax`, `nop` |
| Accumulator | `A` | `lsr A`, `rol A` |
| Immediate | `#value` | `lda #$10` |
| Zero Page | `addr` | `lda $F0` |
| Zero Page, X | `addr, X` | `lda $F0, X` |
| Zero Page, Y | `addr, Y` | `ldx $F0, Y` |
| Absolute | `addr` | `lda $1234` |
| Absolute, X | `addr, X` | `lda $1234, X` |
| Absolute, Y | `addr, Y` | `lda $1234, Y` |
| Indirect | `(addr)` | `jmp ($1234)` |
| Indexed Indirect | `(addr, X)` | `lda ($F0, X)` |
| Indirect Indexed | `(addr), Y` | `lda ($F0), Y` |

> Note: The assembler automatically selects Zero Page addressing if the operand value is known to be in the `$00-$FF` range.

### Expressions
Basic expressions are supported:
- `<` : Low byte of a 16-bit value (`<label`)
- `>` : High byte of a 16-bit value (`>label`)

## Directives

Directives control the assembly process and data generation. All directives start with a dot `.`.

### .org
Sets the program counter (origin) to a specific address.

```asm
.org $C000
```

### .byte
Inserts one or more 8-bit bytes into the output. Supports numbers and strings.

```asm
.byte $01, $02, "Text"
```

### .word
Inserts one or more 16-bit words (Little Endian) into the output.

```asm
.word $1234, label_address
```

### .fill
Fills a block of memory with a specific byte value.
Syntax: `.fill <count>, <value>`

```asm
.fill 256, $EA ; Fill 256 bytes with NOPs
```

### .include / .inc
Includes another source file at the current position. The path is relative to the current file.

```asm
.include "macros.asm"
.inc "data.inc"
```
