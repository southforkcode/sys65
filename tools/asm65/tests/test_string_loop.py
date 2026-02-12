import unittest
from io import StringIO
from lib.asm import Assembler

class TestStringLoop(unittest.TestCase):
    def test_visit_string(self):
        # 1. Defined Assembly Code with a null-terminated string
        code = """
        .org $2000
        str: .byte "Hello, World!", $00
        """
        
        # 2. Assemble
        asm = Assembler()
        asm.assemble_stream(StringIO(code))
        asm.parse()
        
        # 3. Locate the string using the symbol table
        # asm.symbols.get('str') returns the address
        address = asm.symbols.get('str')
        self.assertIsNotNone(address, "Symbol 'str' not found")
        
        print(f"DEBUG: String starts at ${address:04X}")
        
        # 4. Visit every character until $00
        # Since asm.bytes is a compact list relative to start_origin in our current implementation,
        # we need to map address to index.
        # asm.origin gives the start address.
        
        start_origin = asm.origin
        # If address is $2000 and start_origin is $2000, index is 0.
        
        index = address - start_origin
        
        output_string = ""
        while True:
            # Check bounds
            if index >= len(asm.bytes):
                self.fail("Buffer overrun while reading string")
                
            char_code = asm.bytes[index]
            
            # Print current character code
            # print(f"[{index:02X}] = ${char_code:02X} {chr(char_code) if 32 <= char_code <= 126 else '.'}")
            
            if char_code == 0x00:
                break
                
            output_string += chr(char_code)
            index += 1
            
        print(f"Traversed String: '{output_string}'")
        
        # 5. Solve/Verify
        self.assertEqual(output_string, "Hello, World!")

if __name__ == '__main__':
    unittest.main()
