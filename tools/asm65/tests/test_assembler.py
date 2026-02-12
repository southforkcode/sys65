import unittest
from io import StringIO
from lib.asm import Assembler

class TestAssembler(unittest.TestCase):
    def setUp(self):
        self.asm = Assembler()

    def assemble(self, asm_code):
        self.asm = Assembler()
        self.asm.assemble_stream(StringIO(asm_code))
        self.asm.parse()
        # return bytes as hex string
        return "".join(f"{b:02x}" for b in self.asm.bytes)

    def assemble_file(self, filepath):
        self.asm = Assembler()
        with open(filepath, 'r') as f:
            self.asm.assemble_stream(f)
        self.asm.parse()
        return "".join(f"{b:02x}" for b in self.asm.bytes)

    def test_assemble_test0(self):
        self.assemble_file("tools/asm65/tests/data/test0.asm")
        # Expected output approximate check or exact bytes?
        # The original tests.py just printed output.
        # We should at least check it doesn't crash and produces bytes.
        self.assertTrue(len(self.asm.bytes) > 0)

    def test_assemble_test1(self):
        self.assemble_file("tools/asm65/tests/data/test1.asm")
        self.assertTrue(len(self.asm.bytes) > 0)

    def test_assemble_imm(self):
        # test_imm.asm contains immediate mode instructions
        self.assemble_file("tools/asm65/tests/data/test_imm.asm")
        self.assertTrue(len(self.asm.bytes) > 0)
        
    def test_forward_ref(self):
        self.assemble_file("tools/asm65/tests/data/test_ref1.asm")
        self.assertTrue(len(self.asm.bytes) > 0)

    def test_immediate_mode(self):
        code = """
        .org $1000
        LDA #$01
        LDX #$02
        LDY #$03
        ADC #$04
        AND #$05
        EOR #$06
        ORA #$07
        SBC #$08
        CMP #$09
        CPX #$0A
        CPY #$0B
        """
        # Expected from previous tests.py: a901a202a0036904290549060907e908c909e00ac00b
        # Note: assemble() returns ONLY the bytes generated, not the addresses.
        # But wait, Assembler.bytes includes the padding from .org?
        # Let's check Assembler.init: self.bytes = []
        # .org sets origin. self.offset increments.
        # Assembler logic: self.bytes[self.origin + offset] = value.
        # If .org $1000 is used, does self.bytes encompass 0-$1000? 
        # Assembler.bytes is initialized as empty list.
        # When writing, we do self.bytes[origin+offset] = value.
        # So yes, it will likely try to index out of bounds if not pre-filled.
        # Wait, let's check .org implementation in asm.py
        
        # Checking asm.py:
        # if directive == '.ORG': ... self.origin = value; self.offset = 0;
        # self.add_bytes(value, size):
        #   idx = self.origin + self.offset
        #   while len(self.bytes) <= idx + size: self.bytes.append(0)
        #   ...
        
        # So yes, it pads with 0s up to $1000.
        # output_hex will be 1000 bytes of 0s followed by code.
        # We should slice it.
        
        # Actually, let's just create a helper that strips leading zeros or checks suffix.
        # Or better, check specific ranges.
        
        # For this test, let's just check the suffix.
        expected = "a901a202a0036904290549060907e908c909e00ac00b"
        output = self.assemble(code)
        self.assertTrue(output.endswith(expected), f"Expected suffix {expected}, got {output[-50:]}")

    def test_forward_ref_resolution(self):
        code = """
        .org $1000
        start:
            .byte $4C       ; JMP opcode
            .word target    ; Forward reference (WORD)
            
            .byte $A9       ; LDA # opcode
            .byte <target   ; Forward reference (LOW)
            
            .byte $A9       ; LDA # opcode
            .byte >target   ; Forward reference (HIGH)
            
        target:
            .byte $EA       ; NOP
        """
        # start: 4C 07 10 (JMP $1007)
        #        A9 07    (LDA #$07)
        #        A9 10    (LDA #$10)
        # target: EA      (NOP) @ $1007
        expected = "4c0710a907a910ea"
        output = self.assemble(code)
        self.assertTrue(output.endswith(expected), f"Expected suffix {expected}, got {output[-20:]}")

if __name__ == '__main__':
    unittest.main()
