import shlex
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

class Lexer(shlex.shlex):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, punctuation_chars="=+<>-", **kwargs)
    self.commenters = ";"
    self.whitespace = " \t"
    self.wordchars += ".$%"
    self.quotes = "\"\'"
    self.last_token : Token | None = None

  def accept(self, type: TokenType, lexeme: str = None, value: str|int|None = None, line: int = None) -> Token | None:
    # create a new token and set last_token
    token = Token(type, lexeme, value, line or self.lineno)
    self.last_token = token
    return token

  def next_token(self):
    assert self.last_token is None or not self.last_token.isa(TokenType.EOF)
    # check for end of file
    lexeme = super().get_token()
    if lexeme is None or lexeme == self.eof:
      return self.accept(TokenType.EOF, "", None, self.lineno)
    if lexeme == "\n":
      return self.accept(TokenType.EOL, "", None, self.lineno)
    if lexeme.startswith("."):
      return self.accept(TokenType.DIR, lexeme, None, self.lineno)
    if lexeme.startswith("0"):
      if lexeme.startswith("0x"):
        return self.accept(TokenType.NUM, lexeme, int(lexeme[2:], 16), self.lineno)
      if lexeme.startswith("0b"):
        return self.accept(TokenType.NUM, lexeme, int(lexeme[2:], 2), self.lineno)
      return self.accept(TokenType.NUM, lexeme, int(lexeme, 8), self.lineno)
    if lexeme.startswith("$"):
      return self.accept(TokenType.NUM, lexeme, int(lexeme[1:], 16), self.lineno)
    if lexeme.startswith("%"):
      return self.accept(TokenType.NUM, lexeme, int(lexeme[1:], 2), self.lineno)
    if len(lexeme) > 0 and lexeme[0].isdigit():
      return self.accept(TokenType.NUM, lexeme, int(lexeme), self.lineno)
    if lexeme.startswith("'") and lexeme.endswith("'"):
      return self.accept(TokenType.NUM, lexeme, ord(lexeme[1:-1]), self.lineno)
    if lexeme.startswith("\"") and lexeme.endswith("\""):
      return self.accept(TokenType.STR, lexeme, lexeme[1:-1], self.lineno)
    if lexeme in ["#", "+", "-", "*", "/", "=", "<", ">", "(", ")", "@", ",", ":"]:
      return self.accept(TokenType.OP, lexeme, lexeme, self.lineno)
    return self.accept(TokenType.ID, lexeme, lexeme, self.lineno)
