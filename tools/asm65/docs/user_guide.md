# asm65 User Guide

`asm65` is a Python-based assembler for the MOS Technology 6502 microprocessor. It supports standard 6502 syntax, all addressing modes, and a set of directives for code organization and data definition.

## Running the Assembler

To assemble a source file, run the `asm65.py` script from the command line:

```bash
python3 tools/asm65/asm65.py [-f {bin,hex}] <input_file> [<input_file>...] <output_file>
```

- `<input_file>`: One or more assembly source files (`.asm`).
- `<output_file>`: The destination path.
- `-f, --format`: Output format.
    - `bin` (default): Raw binary file.
    - `hex`: Text file with hex dump (`ADDRESS: B1 B2 ...`).
- `-D <name>[=value]`: Define a symbol to be used in the assembly process.
    - If no value is provided, the symbol is defined with a value of `1`.
    - Multiple definitions can be provided by repeating the flag (e.g., `-D DEBUG -D VERSION=2`).

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

### .cpu
Sets the target CPU mode. Supported values are "6502" (default) and "65c02".
When in "65c02" mode, additional instructions (like `bra`, `phx`, `phy`, etc.) are available.

```asm
.cpu "65c02"
```

### .align
Aligns the current program counter to the next multiple of the specified value.
This is useful for aligning data or code to page boundaries or other specific alignments.
It fills the gap with zeros.

```asm
.align 256 ; Align to next page boundary
```

### .include / .inc
Includes another source file at the current position. The path is relative to the current file.

```asm
.include "macros.asm"
.inc "data.inc"
```

### Conditional Compilation (.ifdef, .else, .endif)
These directives allow you to conditionally include or exclude blocks of code based on whether a symbol is defined.

- `.ifdef <symbol>`: Checks if `<symbol>` is defined. if it is, the code block following it is assembled.
- `.else`: Optional. Specifies a block of code to assemble if the `.ifdef` condition was false.
- `.endif`: Marks the end of the conditional block.

Example:

```asm
.ifdef DEBUG
    lda #$01
    sta $D020 ; Change border color to white in debug mode
.else
    lda #$00
    sta $D020 ; Change border color to black in release mode
.endif
```
