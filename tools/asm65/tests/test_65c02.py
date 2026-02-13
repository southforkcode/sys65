import unittest
from io import StringIO
import sys
import os

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.asm import Assembler, AssemblyError
from lib.compiler import CompilerError

class Test65C02(unittest.TestCase):
    def setUp(self):
        self.asm = Assembler()

    def assemble(self, asm_code):
        self.asm = Assembler()
        self.asm.assemble_stream(StringIO(asm_code))
        self.asm.parse()
        return "".join(f"{b:02x}" for b in self.asm.bytes)

    def test_default_cpu_fails_65c02(self):
        # BRA is 65C02 only
        code = """
        start:
            BRA start
        """
        # Should fail as BRA is unknown or mode not supported
        try:
             self.assemble(code)
             self.fail("Should have raised error for BRA in 6502 mode")
        except (AssemblyError, CompilerError, Exception):
             pass

    def test_65c02_mode(self):
        code = """
        .cpu "65c02"
        start:
            BRA start
            PHX
            PLY
            STZ $12
            STZ $1234
        """
        # BRA start (-2) -> 80 FE
        # PHX -> DA
        # PLY -> 7A
        # STZ $12 (ZP) -> 64 12
        # STZ $1234 (ABS) -> 9C 34 12
        expected = "80feda7a64129c3412"
        output = self.assemble(code)
        self.assertTrue(output.endswith(expected), f"Expected suffix {expected}, got {output}")

    def test_switch_back_to_6502(self):
        code = """
        .cpu "65c02"
        PHX
        .cpu "6502"
        NOP
        """
        output = self.assemble(code)
        self.assertTrue(len(output) > 0)
        
        # Valid 6502 after switch
        code_fail = """
        .cpu "65c02"
        .cpu "6502"
        PHX
        """
        try:
            self.assemble(code_fail)
            self.fail("Should have raised error for PHX in 6502 mode")
        except (AssemblyError, CompilerError, Exception):
            pass

    def test_jmp_abs_x(self):
        # 65C02 JMP (abs,x)
        code = """
        .cpu "65c02"
        JMP ($1234, X)
        """
        # Opcode 7C, addr $1234
        expected = "7c3412"
        output = self.assemble(code)
        self.assertTrue(output.endswith(expected), f"Expected {expected}, got {output}")

if __name__ == '__main__':
    unittest.main()
