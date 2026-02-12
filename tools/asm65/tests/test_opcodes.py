import unittest
from lib.opcodes import OPCODES

class TestOpcodes(unittest.TestCase):
    def test_structure(self):
        for mnemonic, modes in OPCODES.items():
            self.assertIsInstance(mnemonic, str)
            self.assertIsInstance(modes, dict)
            for mode, opcode in modes.items():
                self.assertIsInstance(opcode, int)
                self.assertTrue(0 <= opcode <= 255)

    def test_immediate_mode(self):
        # LDA #$00 -> A9
        self.assertIn("LDA", OPCODES)
        self.assertIn("#", OPCODES["LDA"])
        self.assertEqual(OPCODES["LDA"]["#"], 0xA9)

    def test_jmp_absolute(self):
        # JMP $1234 -> 4C
        self.assertIn("JMP", OPCODES)
        self.assertIn("ABS", OPCODES["JMP"])
        self.assertEqual(OPCODES["JMP"]["ABS"], 0x4C)
        
if __name__ == '__main__':
    unittest.main()
