import unittest
from io import StringIO
from lib.asm import Assembler, AssemblyError

class TestDirectives(unittest.TestCase):
    def setUp(self):
        self.asm = Assembler()

    def parse(self, code):
        self.asm = Assembler()
        self.asm.assemble_stream(StringIO(code))
        self.asm.parse()

    def test_org(self):
        self.parse(".org $1000\n")
        self.assertEqual(self.asm.origin, 0x1000)
        self.assertEqual(self.asm.offset, 0)
        
    def test_byte(self):
        self.parse(".org $1000\n.byte $01, $02, $FF\n")
        self.assertGreater(len(self.asm.bytes), 2, f"Origin={self.asm.origin}, len={len(self.asm.bytes)}")
        # Check bytes (relative to origin)
        self.assertEqual(self.asm.bytes[0], 0x01)
        self.assertEqual(self.asm.bytes[1], 0x02)
        self.assertEqual(self.asm.bytes[2], 0xFF)
        
    def test_byte_string(self):
        self.parse('.org $1000\n.byte "hello"\n')
        # 'h' = 0x68
        self.assertEqual(self.asm.bytes[0], 0x68)
        self.assertEqual(self.asm.bytes[4], 0x6F) # 'o'

    def test_word(self):
        self.parse(".org $1000\n.word $1234, $ABCD\n")
        # Little endian
        self.assertEqual(self.asm.bytes[0], 0x34)
        self.assertEqual(self.asm.bytes[1], 0x12)
        
        self.assertEqual(self.asm.bytes[2], 0xCD)
        self.assertEqual(self.asm.bytes[3], 0xAB)
        
    def test_fill(self):
        self.parse(".org $1000\n.fill 4, $EE\n")
        for i in range(4):
            self.assertEqual(self.asm.bytes[i], 0xEE)
            
    def test_fill_default(self):
        self.parse(".org $1000\n.fill 4\n")
        for i in range(4):
            # asm.py implementation defaults value to 0 if not provided
            self.assertEqual(self.asm.bytes[i], 0)

if __name__ == '__main__':
    unittest.main()
