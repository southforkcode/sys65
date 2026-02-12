
import unittest
import os
from lib.asm import Assembler, AssemblyError, Tokenizer
from lib.parser import Parser

class TestInclude(unittest.TestCase):
    def setUp(self):
        self.asm = Assembler()
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.test_dir, 'data')

    def assemble_file(self, filename):
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'r') as f:
            # We need to manually invoke parser because asm.assemble_stream just sets up tokenizer
            # and asm.parse() calls parser.
            # But wait, asm.assemble_stream() takes a stream. The parser needs to know the filename
            # to resolve relative includes.
            # Currently Tokenizer doesn't store filename. 
            # We need to modify Tokenizer to store filename first.
            # For this test, valid implementation relies on parser changes.
            self.asm.assemble_stream(f)
            # Inject filename into tokenizer if possible (monkey patch for now if property exists, or rely on implementation update)
            # The implementation plan says we will add filename to Tokenizer.
            if hasattr(self.asm.lex, 'filename'):
                 self.asm.lex.filename = filepath
            else:
                 # If implementation not done yet, we might fail effectively or we can pass it
                 # We are writing the test primarily to verify the implementation.
                 pass
        
        self.asm.parse()
        return "".join(f"{b:02x}" for b in self.asm.bytes)

    def test_include_main(self):
        # include_main.asm:
        # .org $1000
        # ldx #$01 (a2 01)
        # .include "include_sub.asm" -> lda #$FF (a9 ff)
        # ldy #$02 (a0 02)
        # Result: a2 01 a9 ff a0 02
        expected = "a201a9ffa002"
        output = self.assemble_file("include_main.asm")
        self.assertTrue(output.endswith(expected), f"Expected {expected}, got {output[-20:]}")

    def test_include_nested(self):
        # include_deep.asm:
        # .org $1000
        # ldx #$01
        # .include "include_nested.asm" -> .include "include_sub.asm" -> lda #$FF
        # ldy #$02
        # Result: a2 01 a9 ff a0 02
        expected = "a201a9ffa002"
        output = self.assemble_file("include_deep.asm")
        self.assertTrue(output.endswith(expected), f"Expected {expected}, got {output[-20:]}")

    def test_include_cycle(self):
        with self.assertRaises(Exception) as cm:
            self.assemble_file("include_cycle_a.asm")
        # Check error message
        self.assertIn("Recursive include detected", str(cm.exception))

    def test_include_missing(self):
        with self.assertRaises(Exception) as cm:
            self.assemble_file("include_missing.asm")
        self.assertIn("Include file not found", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
