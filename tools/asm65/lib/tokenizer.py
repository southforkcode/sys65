import re
import re
from enum import Enum

class TokenType(Enum):
  UNKNOWN = 0
  EOL = 1
  EOF = 2
  ID = 3
  DIR = 4
  NUM = 5
  STR = 6
  OP = 7
  LOCAL_LABEL_REF = 8

class Token:
  def __init__(self, type: TokenType, lexeme: str, value: str|int|None, line: int):
    self.type = type
    self.lexeme = lexeme
    self.value = value
    self.line = line

  def isa(self, type: TokenType, lexeme: str = None) -> bool:
    return self.type.name == type.name and (lexeme is None or self.lexeme == lexeme)

  def isa_op(self, lexeme: str = None) -> bool:
    return self.type.name == TokenType.OP.name and (lexeme is None or self.lexeme == lexeme)

  def __str__(self):
    return f"Token({self.type.name}: {repr(self.lexeme)} = {self.value} @ {self.line})"

  def __repr__(self):
    return self.__str__()

class Tokenizer:
    def __init__(self, stream, filename: str = None):
        self.text = stream.read()
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.len = len(self.text)
        self.peek_token = None
        self.last_token = None
        
        # Regex patterns
        self.patterns = [
            (TokenType.EOL, r'\n'),
            (TokenType.DIR, r'\.[a-zA-Z0-9_]+'),
            (TokenType.NUM, r'\$[0-9a-fA-F]+'),      # Hex $12
            (TokenType.NUM, r'0x[0-9a-fA-F]+'),      # Hex 0x12
            (TokenType.NUM, r'%[01]+'),              # Binary %101
            (TokenType.NUM, r'0b[01]+'),             # Binary 0b101
            (TokenType.LOCAL_LABEL_REF, r'[0-9]+[fb]'), # Local label reference 1f, 1b
            (TokenType.NUM, r'[0-9]+'),              # Decimal
            # Only support simple chars for now
            (TokenType.STR, r'"[^"]*"'),             # String "..."
            (TokenType.NUM, r"'[^']'"),              # Char 'c' -> treated as NUM usually but kept as STR/NUM flexibility
            (TokenType.OP,  r'[#=<>(),@:+\-*\/]'),   # Operators
            (TokenType.ID,  r'[a-zA-Z_][a-zA-Z0-9_]*') # Identifiers
        ]

    def next_token(self) -> Token:
        if self.peek_token:
            tok = self.peek_token
            self.peek_token = None
            self.last_token = tok
            return tok

        self._skip_whitespace()
        
        if self.pos >= self.len:
            tok = Token(TokenType.EOF, "", None, self.line)
            self.last_token = tok
            return tok
            
        # Check for comments
        if self.text[self.pos] == ';':
            self._skip_comment()
            return self.next_token() # Recursively get next token after comment
            
        remaining = self.text[self.pos:]
        
        for type, pattern in self.patterns:
            match = re.match(pattern, remaining)
            if match:
                lexeme = match.group(0)
                self.pos += len(lexeme)
                if type == TokenType.EOL:
                    self.line += 1
                    tok = Token(type, lexeme, None, self.line - 1)
                    self.last_token = tok
                    return tok
                
                value = self._parse_value(type, lexeme)
                tok = Token(type, lexeme, value, self.line)
                self.last_token = tok
                return tok
                
        # Unknown character
        char = self.text[self.pos]
        self.pos += 1
        tok = Token(TokenType.UNKNOWN, char, None, self.line)
        self.last_token = tok
        return tok

    def _skip_whitespace(self):
        while self.pos < self.len:
            char = self.text[self.pos]
            if char in ' \t\r':
                self.pos += 1
            else:
                break
                
    def _skip_comment(self):
        # consume until newline or EOF
        while self.pos < self.len:
            char = self.text[self.pos]
            if char == '\n':
                # Don't consume newline here, let next_token handle it as EOL
                break
            self.pos += 1

    def _parse_value(self, type, lexeme):
        if type == TokenType.NUM:
            if lexeme.startswith('$'): return int(lexeme[1:], 16)
            if lexeme.startswith('0x'): return int(lexeme[2:], 16)
            if lexeme.startswith('%'): return int(lexeme[1:], 2)
            if lexeme.startswith('0b'): return int(lexeme[2:], 2)
            if lexeme.startswith("'") and lexeme.endswith("'"): return ord(lexeme[1])
            return int(lexeme)
        if type == TokenType.STR:
            return lexeme[1:-1]
        return None
