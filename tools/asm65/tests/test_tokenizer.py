import unittest
from io import StringIO
from lib.tokenizer import Tokenizer, TokenType, Token

class TestTokenizer(unittest.TestCase):
    def tokenize(self, text):
        t = Tokenizer(StringIO(text))
        tokens = []
        while True:
            tok = t.next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens

    def test_simple_tokens(self):
        tokens = self.tokenize("LDA #$01")
        # ID LDA, OP #, NUM $01, EOL, EOF (maybe EOL depending on implementation, let's check)
        # Tokenizer emits EOL for newlines.
        # "LDA #$01" -> ID("LDA"), OP("#"), NUM(1), EOF
        
        self.assertEqual(tokens[0].type, TokenType.ID)
        self.assertEqual(tokens[0].lexeme, "LDA")
        
        self.assertEqual(tokens[1].type, TokenType.OP)
        self.assertEqual(tokens[1].lexeme, "#")
        
        self.assertEqual(tokens[2].type, TokenType.NUM)
        self.assertEqual(tokens[2].value, 1)
        
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_comments(self):
        tokens = self.tokenize("LDA $01 ; load accumulator\n")
        # ID, NUM, EOL, EOF
        self.assertEqual(tokens[0].lexeme, "LDA")
        self.assertEqual(tokens[1].value, 1)
        self.assertEqual(tokens[2].type, TokenType.EOL)
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_eol_handling(self):
        # Comments should NOT swallow EOL if they are at end of line
        tokens = self.tokenize(".byte $01 ; comment\n.byte $02")
        # DIR, NUM, EOL, DIR, NUM, EOF
        
        types = [t.type for t in tokens]
        self.assertEqual(types, [
            TokenType.DIR, TokenType.NUM, TokenType.EOL,
            TokenType.DIR, TokenType.NUM, TokenType.EOF
        ])

    def test_literals(self):
        tokens = self.tokenize('"hello" \'a\'')
        self.assertEqual(tokens[0].type, TokenType.STR)
        self.assertEqual(tokens[0].value, "hello")
        
        self.assertEqual(tokens[1].type, TokenType.NUM) # 'a' is parsed as NUM in our tokenizer logic
        self.assertEqual(tokens[1].value, 97) # ord('a')

if __name__ == '__main__':
    unittest.main()
