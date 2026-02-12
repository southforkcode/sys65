import unittest
from io import StringIO
from lib.asm import Assembler
from lib.compiler import CompilerError

class TestAbsolute(unittest.TestCase):
    def setUp(self):
        self.asm = Assembler()

    def assemble(self, code):
        self.asm = Assembler()
        self.asm.assemble_stream(StringIO(code))
        self.asm.parse()
        return self.asm.bytes

    def test_abs_arithmetic(self):
        # ADC ABS $1234 -> 6D 34 12
        code = ".org $1000\nADC $1234\n"
        b = self.assemble(code)
        self.assertEqual(len(b), 3)
        self.assertEqual(b[0], 0x6D)
        self.assertEqual(b[1], 0x34)
        self.assertEqual(b[2], 0x12)

    def test_abs_store(self):
        # STA ABS $2000 -> 8D 00 20
        code = ".org $1000\nSTA $2000\n"
        b = self.assemble(code)
        self.assertEqual(b[0], 0x8D)
        
    def test_zp_optimization_supported(self):
        # LDA $10 -> ZP mode (A5) for LDA
        code = ".org $1000\nLDA $10\n"
        b = self.assemble(code)
        self.assertEqual(len(b), 2)
        self.assertEqual(b[0], 0xA5) # LDA ZP
        self.assertEqual(b[1], 0x10)
        
    def test_zp_optimization_not_supported(self):
        # JMP $0010 -> JMP does not have ZP mode, must be ABS (4C 10 00)
        code = ".org $1000\nJMP $0010\n"
        b = self.assemble(code)
        self.assertEqual(len(b), 3)
        self.assertEqual(b[0], 0x4C) # JMP ABS
        self.assertEqual(b[1], 0x10)
        self.assertEqual(b[2], 0x00)

    def test_branch_forward(self):
        # BNE target
        # $1000: BNE (2 bytes) -> $1002
        # $1002: ...
        # $1005: target
        # Offset = $1005 - $1002 = 3
        code = """
        .org $1000
        BNE target
        .byte $EA, $EA, $EA
        target: .byte $00
        """
        b = self.assemble(code)
        self.assertEqual(len(b), 2 + 3 + 1)
        self.assertEqual(b[0], 0xD0) # BNE
        self.assertEqual(b[1], 0x03) # Offset +3

    def test_branch_backward(self):
        # loop: NOP
        # BNE loop
        # $1000: NOP
        # $1001: BNE ($1003)
        # Target = $1000
        # Offset = $1000 - $1003 = -3 = $FD
        code = """
        .org $1000
        loop: NOP
        BNE loop
        """
        b = self.assemble(code)
        self.assertEqual(b[0], 0xEA)
        self.assertEqual(b[1], 0xD0)
        self.assertEqual(b[2], 0xFD) # -3 int8

    def test_branch_out_of_range(self):
        # Too far forward
        code = """
        .org $1000
        BNE target
        .fill 130, $EA
        target: .byte $00
        """
        with self.assertRaises(CompilerError):
            self.assemble(code)

if __name__ == '__main__':
    unittest.main()
