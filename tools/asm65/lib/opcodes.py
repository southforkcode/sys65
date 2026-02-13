
# 6502 Opcodes
# Structure: { Mnemonic: { AddressingMode: Opcode } }

OPCODES_6502 = {
    # Load/Store
    'LDA': { '#': 0xA9, 'ZP': 0xA5, 'ZPX': 0xB5, 'ABS': 0xAD, 'ABSX': 0xBD, 'ABSY': 0xB9, 'INDX': 0xA1, 'INDY': 0xB1 },
    'LDX': { '#': 0xA2, 'ZP': 0xA6, 'ZPY': 0xB6, 'ABS': 0xAE, 'ABSY': 0xBE },
    'LDY': { '#': 0xA0, 'ZP': 0xA4, 'ZPX': 0xB4, 'ABS': 0xAC, 'ABSX': 0xBC },
    'STA': { 'ZP': 0x85, 'ZPX': 0x95, 'ABS': 0x8D, 'ABSX': 0x9D, 'ABSY': 0x99, 'INDX': 0x81, 'INDY': 0x91 },
    'STX': { 'ZP': 0x86, 'ZPY': 0x96, 'ABS': 0x8E },
    'STY': { 'ZP': 0x84, 'ZPX': 0x94, 'ABS': 0x8C },

    # Arithmetic
    'ADC': { '#': 0x69, 'ZP': 0x65, 'ZPX': 0x75, 'ABS': 0x6D, 'ABSX': 0x7D, 'ABSY': 0x79, 'INDX': 0x61, 'INDY': 0x71 },
    'SBC': { '#': 0xE9, 'ZP': 0xE5, 'ZPX': 0xF5, 'ABS': 0xED, 'ABSX': 0xFD, 'ABSY': 0xF9, 'INDX': 0xE1, 'INDY': 0xF1 },
    
    # Compare
    'CMP': { '#': 0xC9, 'ZP': 0xC5, 'ZPX': 0xD5, 'ABS': 0xCD, 'ABSX': 0xDD, 'ABSY': 0xD9, 'INDX': 0xC1, 'INDY': 0xD1 },
    'CPX': { '#': 0xE0, 'ZP': 0xE4, 'ABS': 0xEC },
    'CPY': { '#': 0xC0, 'ZP': 0xC4, 'ABS': 0xCC },

    # Logical
    'AND': { '#': 0x29, 'ZP': 0x25, 'ZPX': 0x35, 'ABS': 0x2D, 'ABSX': 0x3D, 'ABSY': 0x39, 'INDX': 0x21, 'INDY': 0x31 },
    'ORA': { '#': 0x09, 'ZP': 0x05, 'ZPX': 0x15, 'ABS': 0x0D, 'ABSX': 0x1D, 'ABSY': 0x19, 'INDX': 0x01, 'INDY': 0x11 },
    'EOR': { '#': 0x49, 'ZP': 0x45, 'ZPX': 0x55, 'ABS': 0x4D, 'ABSX': 0x5D, 'ABSY': 0x59, 'INDX': 0x41, 'INDY': 0x51 },
    'BIT': { 'ZP': 0x24, 'ABS': 0x2C },

    # Increment/Decrement
    'INC': { 'ZP': 0xE6, 'ZPX': 0xF6, 'ABS': 0xEE, 'ABSX': 0xFE },
    'DEC': { 'ZP': 0xC6, 'ZPX': 0xD6, 'ABS': 0xCE, 'ABSX': 0xDE },
    'INX': { 'IMP': 0xE8 },
    'DEX': { 'IMP': 0xCA },
    'INY': { 'IMP': 0xC8 },
    'DEY': { 'IMP': 0x88 },

    # Shifts
    'ASL': { 'ACC': 0x0A, 'ZP': 0x06, 'ZPX': 0x16, 'ABS': 0x0E, 'ABSX': 0x1E },
    'LSR': { 'ACC': 0x4A, 'ZP': 0x46, 'ZPX': 0x56, 'ABS': 0x4E, 'ABSX': 0x5E },
    'ROL': { 'ACC': 0x2A, 'ZP': 0x26, 'ZPX': 0x36, 'ABS': 0x2E, 'ABSX': 0x3E },
    'ROR': { 'ACC': 0x6A, 'ZP': 0x66, 'ZPX': 0x76, 'ABS': 0x6E, 'ABSX': 0x7E },

    # Jumps/Calls
    'JMP': { 'ABS': 0x4C, 'IND': 0x6C },
    'JSR': { 'ABS': 0x20 },
    'RTS': { 'IMP': 0x60 },

    # Branching (Relative) - Compiler needs to handle REL specially? 
    # Or strict assembler just emits signed byte?
    # asm.py parser maps REL to relative offset?
    'BCC': { 'REL': 0x90 },
    'BCS': { 'REL': 0xB0 },
    'BEQ': { 'REL': 0xF0 },
    'BMI': { 'REL': 0x30 },
    'BNE': { 'REL': 0xD0 },
    'BPL': { 'REL': 0x10 },
    'BVC': { 'REL': 0x50 },
    'BVS': { 'REL': 0x70 },

    # Stack/Flags
    'PHA': { 'IMP': 0x48 },
    'PLA': { 'IMP': 0x68 },
    'PHP': { 'IMP': 0x08 },
    'PLP': { 'IMP': 0x28 },
    'CLC': { 'IMP': 0x18 },
    'SEC': { 'IMP': 0x38 },
    'CLI': { 'IMP': 0x58 },
    'SEI': { 'IMP': 0x78 },
    'CLV': { 'IMP': 0xB8 },
    'CLD': { 'IMP': 0xD8 },
    'SED': { 'IMP': 0xF8 },
    'BRK': { 'IMP': 0x00 },
    'NOP': { 'IMP': 0xEA },
    
    # Register Transfers
    'TAX': { 'IMP': 0xAA },
    'TXA': { 'IMP': 0x8A },
    'TAY': { 'IMP': 0xA8 },
    'TYA': { 'IMP': 0x98 },
    'TSX': { 'IMP': 0xBA },
    'TXS': { 'IMP': 0x9A },
}

OPCODES = OPCODES_6502

import copy
OPCODES_65C02 = copy.deepcopy(OPCODES_6502)

# Add 65C02 specific opcodes
# BRA
OPCODES_65C02['BRA'] = { 'REL': 0x80 }
# Push/Pop index
OPCODES_65C02['PHX'] = { 'IMP': 0xDA }
OPCODES_65C02['PLX'] = { 'IMP': 0xFA }
OPCODES_65C02['PHY'] = { 'IMP': 0x5A }
OPCODES_65C02['PLY'] = { 'IMP': 0x7A }
# STZ
OPCODES_65C02['STZ'] = { 'ZP': 0x64, 'ZPX': 0x74, 'ABS': 0x9C, 'ABSX': 0x9E }
# TRB/TSB
OPCODES_65C02['TRB'] = { 'ZP': 0x14, 'ABS': 0x1C }
OPCODES_65C02['TSB'] = { 'ZP': 0x04, 'ABS': 0x0C }
# BIT (immediate, ZPX, ABSX)
OPCODES_65C02['BIT']['#'] = 0x89
OPCODES_65C02['BIT']['ZPX'] = 0x34
OPCODES_65C02['BIT']['ABSX'] = 0x3C
# INC/DEC Accumulator
OPCODES_65C02['INC']['ACC'] = 0x1A
OPCODES_65C02['DEC']['ACC'] = 0x3A

# Indirect (zp) support for ADC, AND, CMP, EOR, LDA, ORA, SBC, STA
OPCODES_65C02['ADC']['IND'] = 0x72
OPCODES_65C02['AND']['IND'] = 0x32
OPCODES_65C02['CMP']['IND'] = 0xD2
OPCODES_65C02['EOR']['IND'] = 0x52
OPCODES_65C02['LDA']['IND'] = 0xB2
OPCODES_65C02['ORA']['IND'] = 0x12
OPCODES_65C02['SBC']['IND'] = 0xF2
OPCODES_65C02['STA']['IND'] = 0x92

# JMP (abs,X)
# We will use 'INDX' mode logic but force 2-byte operand in compiler
OPCODES_65C02['JMP']['INDX'] = 0x7C
