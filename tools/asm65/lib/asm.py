import os

from .lex import Token, TokenType, Lexer
from .symtab import SymbolTable
from .bytes import ByteConverter
from .string import str_compare

class AssemblyError(Exception):
  def __init__(self, msg: str, token: Token):
    super().__init__()
    self.msg = msg
    self.token = token

  def __str__(self):
    if self.token is None:
      return f"{self.msg}"
    return f"{self.token.line}: {self.msg} ({self.token.lexeme})"

class Assembler:
  def __init__(self):
    self._symbols : SymbolTable = SymbolTable()
    self.origin : int | None = None
    self.offset : int = 0
    self.bytes : list[int] = []
    self.unresolved : list[tuple[str, int]] = []
    self.reset_lexer()

  def reset_lexer(self):
    self.lex : Lexer = None
    self.peeked : list[Token] = []

  @property
  def symbols(self) -> SymbolTable:
    return self._symbols

  def add_bytes(self, value, size: int):
    if isinstance(value, int):
      self.bytes.extend(ByteConverter.convert_int(value, size))
      self.offset += size
    elif isinstance(value, str):
      self.bytes.extend(ByteConverter.convert_str(value))
      self.offset += len(value)
    else:
      raise AssemblyError(f"Invalid value: {value}", None)

  def get_symbol_value(self, name: str) -> int:
    if name not in self._symbols or self._symbols[name] is None:
      # add symbol to unresolved list
      self.unresolved.append((name, self.offset))
      return 0
    value = self._symbols[name]
    assert isinstance(value, int)
    return value

  def resolve(self, name: str, value: int):
    self._symbols.set(name, value)
    # create a stable copy of unresolved
    unresolved = list(self.unresolved)
    for i, (sym, offset) in enumerate(unresolved):
      if sym == name:
        self.unresolved.pop(i)
        self.bytes[self.origin + offset] = value

  def peektok(self) -> Token:
    if len(self.peeked) > 0:
      return self.peeked[0]      
    tok = self.lex.next_token()
    self.peeked.append(tok)
    return tok

  def nexttok(self) -> Token:
    if len(self.peeked) > 0:
      return self.peeked.pop(0)
    return self.lex.next_token()

  def expect(self, type: TokenType, lexeme: str = None, casei: bool = False) -> Token|None:
    tok = self.peektok()
    if tok is None:
      return None
    if tok.type != type:
      return None
    if lexeme is not None and not str_compare(tok.lexeme, lexeme, casei):
      return None
    self.nexttok()
    return tok

  def require(self, type: TokenType, lexeme: str = None, casei: bool = False):
    tok = self.nexttok()
    if tok is None:
      raise AssemblyError("Unexpected end of file", None)
    if tok.type != type:
      raise AssemblyError(f"Expected {type.name}, got {tok.type.name}", tok)
    if lexeme is not None and not str_compare(tok.lexeme, lexeme, casei):
      raise AssemblyError(f"Expected '{lexeme}', got '{tok.lexeme}'", tok)
    return tok

  def assemble_stream(self, stream):
    assert self.lex is None
    self.lex = Lexer(stream)

  def parse(self):
    assert self.lex is not None
    while self.lex.last_token is None or not self.lex.last_token.isa(TokenType.EOF):
      self.parse_line()

  def parse_line(self) -> None:
    # end of line
    if self.expect(TokenType.EOL):
      return
    # end of file
    elif self.expect(TokenType.EOF):
      return
    # directive?
    elif tok := self.expect(TokenType.DIR):
      self.parse_directive_or_label(tok)
    # label or equ
    elif tok := self.expect(TokenType.ID):
      if self.expect(TokenType.OP, ':'):
        label = tok.lexeme
        # labels require an address
        if self.origin is None:
          raise AssemblyError(f"Label '{label}' requires an address", tok)
        self.resolve(label, self.origin + self.offset)
        self.parse_line() # continue parsing the rest of the line
      elif self.expect(TokenType.OP, '='):
        label = tok.lexeme
        value = self.parse_expr(required_type=int)
        self.resolve(label, value)
        self.require(TokenType.EOL) # must be full line
      else:
        self.parse_instruction(tok)
    else:
      raise AssemblyError(f"Unknown token: {tok.lexeme}", tok)

  def parse_directive_or_label(self, tok: Token) -> None:
    directive = tok.lexeme
    # .org (origin)
    if directive == '.org':
      expr = self.parse_expr()
      if not isinstance(expr, int):
        raise AssemblyError(f"Expected number, got {expr}", None)
      self.require(TokenType.EOL)
      self.origin = expr
      self.offset = 0
      return

    # .byte
    if directive == '.byte':
      expr_list = self.parse_expr_list()
      self.require(TokenType.EOL)
      for expr in expr_list:
        self.add_bytes(expr, 1)        
      return

    # .word
    if directive == '.word':
      expr_list = self.parse_expr_list()
      self.require(TokenType.EOL)
      for expr in expr_list:
        self.add_bytes(expr, 2)        
      return

    # .fill
    if directive == '.fill':
      value = 0
      count_tok = self.require(TokenType.NUM)
      if self.expect(TokenType.OP, ','):
        value_tok = self.require(TokenType.NUM)
        value = value_tok.value
      self.require(TokenType.EOL)
      for _ in range(count_tok.value):
        self.add_bytes(value, 1)
      return

    # otherwise it's a label if a colon follows
    if self.expect(TokenType.OP, ':'):
      self.resolve(tok.lexeme, self.address)
      return self.parse_line()

    raise AssemblyError(f"Unknown directive: {directive}", tok)

  def parse_instruction(self, tok: Token) -> None:
    instruction = tok.lexeme
    # parse operands
    operands = self.parse_operands(instruction)
    self.require(TokenType.EOL)
    self.offset += 1

  def parse_expr(self, required_type: type = None) -> int | str | None:
    if tok := self.expect(TokenType.OP, "<"):
      # low byte
      assert required_type == int or required_type is None
      expr = self.parse_expr(required_type = int)
      return expr & 0xFF
    if tok := self.expect(TokenType.OP, ">"):
      # high byte
      assert required_type == int or required_type is None
      expr = self.parse_expr(required_type = int)
      return (expr >> 8) & 0xFF
    if tok := self.expect(TokenType.NUM):
      assert required_type == int or required_type is None
      return tok.value
    if tok := self.expect(TokenType.ID):
      value = self.get_symbol_value(tok.lexeme)
      if isinstance(value, int) and (required_type == int or required_type is None):
        return value
      raise AssemblyError(f"Symbol '{tok.lexeme}' is not an integer", tok)
    if tok := self.expect(TokenType.STR):
      return tok.value
    raise AssemblyError(f"Unknown token: {tok.lexeme}", tok)

  def parse_expr_list(self):
    expr_list = []
    while True:
      expr = self.parse_expr()
      expr_list.append(expr)
      if self.peektok().type == TokenType.EOL:
        break
      self.require(TokenType.OP, ',')
    return expr_list

  def parse_operands(self, instruction: str) -> list[Token]:
    operands = []
    # implied - no operands
    if self.peektok().type == TokenType.EOL:
      return []
    # accumulator (A) - this is just implied
    elif self.expect(TokenType.ID, 'A'):
      return []
    # immediate - signaled by #
    elif self.expect(TokenType.OP, '#'):
      expr = self.parse_expr()
      operands.append(expr)
      return operands
    elif self.expect(TokenType.OP, '('):
      # zero page indexed indirect
      # absolute indexed indirect
      # indirect indexed
      expr = self.parse_expr()
      operands.append(expr)
      if self.expect(TokenType.OP, ','):
        self.require(TokenType.ID, 'X', casei=True)
        operands.append('X')
      else:
        self.require(TokenType.OP, ')')
        if self.expect(TokenType.OP, ','):
          self.require(TokenType.ID, 'Y', casei=True)          
          operands.append('Y')
      return operands
    else:
      # zero page or absolute with possible index
      # zero page resolves to a number < 256
      # absolute resolves to a number >= 256
      # mnemonic make have asymmetric support for zp and absolute
      # so we may need to try both and pick the shortest one
      expr = self.parse_expr()
      operands.append(expr)
      if self.expect(TokenType.OP, ','):
        index = self.require(TokenType.ID)
        operands.append(index.value)
      return operands

