
import unittest
from io import StringIO
from lib.asm import Assembler

class TestLocalLabels(unittest.TestCase):
    def setUp(self):
        self.asm = Assembler()

    def assemble(self, asm_code):
        self.asm = Assembler()
        # Mock file name for include resolution etc if needed (not needed here)
        # Tokenizer accepts stream.
        # Tokenizer signature: (stream, filename=None)
        # Assembler.assemble_stream(stream, filename=None)
        self.asm.assemble_stream(StringIO(asm_code))
        self.asm.parse()
        return "".join(f"{b:02x}" for b in self.asm.bytes)

    def test_local_forward(self):
        # 1: lda #0
        #    beq 1f
        #    brk
        # 1: rts
        code = """
        1:
            lda #0
            beq 1f
            brk
        1:
            rts
        """
        # LDA #0 -> A9 00
        # BEQ 1f -> F0 01 (skip BRK)
        # BRK -> 00
        # RTS -> 60
        # 1: (start) @ 0
        # 1f -> (next 1) @ 4 (A9=1, 00=1, F0=1, 01=1 -> 4 bytes. BRK is 5th byte?)
        # Let's count bytes:
        # A9 00 (2)
        # F0 xx (2)
        # 00    (1)
        # 60    (1)
        # Total 6 bytes.
        # BEQ is at offset 2. Next instruction (BRK) is at 4.
        # Target (RTS) is at 5.
        # Offset = 5 - 4 = 1.
        
        expected = "a900f0010060"
        output = self.assemble(code)
        self.assertEqual(output, expected)

    def test_local_backward(self):
        # 1: dex
        #    bne 1b
        #    rts
        code = """
        1:
            dex
            bne 1b
            rts
        """
        # DEX -> CA (1)
        # BNE 1b -> D0 xx (2)
        # RTS -> 60 (1)
        # Label 1 is at 0.
        # BNE is at 1. Next instr (RTS) is at 3.
        # Target is 0.
        # Offset = 0 - 3 = -3 (0xFD)
        
        expected = "cad0fd60"
        output = self.assemble(code)
        self.assertEqual(output, expected)

    def test_mixed_directions(self):
        # 1:
        #   ldx #10
        # 2:
        #   dex
        #   bne 2b  ; Backward to 2
        #   beq 1f  ; Forward to 1 (exit)
        #   jmp 1b  ; Backward to 1 (start)
        # 1:
        #   rts
        code = """
        1:
            ldx #10
        2:
            dex
            bne 2b
            beq 1f
            jmp 1b
        1:
            rts
        """
        # 1: @ 0
        # LDX #10 -> A2 0A (2)
        # 2: @ 2
        # DEX -> CA (1)
        # BNE 2b -> D0 xx (2)  ; Target 2 (@2). PC_next=5. Offset= 2-5 = -3 (FD)
        # BEQ 1f -> F0 xx (2)  ; Target 1 (next, @10). PC_next=7. Offset= 10-7 = 3
        # JMP 1b -> 4C xx xx (3) ; Target 1 (prev, @0).
        # 1: @ 10
        # RTS -> 60 (1)
        
        # Bytes:
        # A2 0A
        # CA
        # D0 FD
        # F0 03
        # 4C 00 00  ; JMP abs 0000 (assumes origin 0)
        # 60
        
        expected = "a20acad0fdf0034c000060"
        output = self.assemble(code)
        self.assertEqual(output, expected)

    def test_numeric_label_ref_error(self):
        # Reference a label that doesn't exist
        code = """
        1:
            beq 2f
        """
        with self.assertRaises(Exception): # CompileError
             self.assemble(code)

if __name__ == '__main__':
    unittest.main()
