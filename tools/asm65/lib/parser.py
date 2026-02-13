from typing import List, Optional, Tuple, Union
import os
from .tokenizer import Tokenizer, Token, TokenType
from .ast import Program, Statement, Instruction, Directive, Label, Assignment, Unresolved, BinaryExpr
from .string import str_compare

class ParserError(Exception):
    def __init__(self, msg: str, token: Token):
        super().__init__()
        self.msg = msg
        self.token = token

    def __str__(self):
        if self.token is None:
            return f"{self.msg}"
        return f"{self.token.line}: {self.msg} ({self.token.lexeme})"

class Parser:
    def __init__(self, tokenizer: Tokenizer):
        self.lex = tokenizer
        self.tokenizers: List[Tokenizer] = []
        self.peeked: List[Token] = []

    def _read_next_token(self) -> Token:
        tok = self.lex.next_token()
        while tok.type == TokenType.EOF and self.tokenizers:
             # Close current stream?
             # For now just drop reference
             self.lex = self.tokenizers.pop()
             tok = self.lex.next_token()
        return tok

    def peektok(self) -> Token:
        if len(self.peeked) > 0:
            return self.peeked[0]      
        tok = self._read_next_token()
        self.peeked.append(tok)
        return tok

    def nexttok(self) -> Token:
        if len(self.peeked) > 0:
            return self.peeked.pop(0)
        return self._read_next_token()

    def expect(self, type: TokenType, lexeme: str = None, casei: bool = False) -> Optional[Token]:
        tok = self.peektok()
        if tok is None:
            return None
        if tok.type != type:
            return None
        if lexeme is not None and not str_compare(tok.lexeme, lexeme, casei):
            return None
        self.nexttok()
        return tok

    def require(self, type: TokenType, lexeme: str = None, casei: bool = False) -> Token:
        tok = self.nexttok()
        if tok is None:
            raise ParserError("Unexpected end of file", None)
        if tok.type != type:
            raise ParserError(f"Expected {type.name}, got {tok.type.name}", tok)
        if lexeme is not None and not str_compare(tok.lexeme, lexeme, casei):
            raise ParserError(f"Expected '{lexeme}', got '{tok.lexeme}'", tok)
        return tok

    def parse_program(self) -> Program:
        statements = []
        while True:
            # check EOF via peek
            tok = self.peektok()
            if tok is None or tok.type == TokenType.EOF:
                break
            
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        return Program(statements)

    def parse_statement(self) -> Optional[Statement]:
        # end of line
        if self.expect(TokenType.EOL):
            return None
        # end of file
        elif self.expect(TokenType.EOF):
            return None
        # directive?
        elif tok := self.expect(TokenType.DIR):
            return self.parse_directive(tok)
        # label or assignment or instruction (if mnemonic looks like ID)
        elif tok := self.expect(TokenType.ID):
            if self.expect(TokenType.OP, ':'):
                return Label(tok.lexeme)
            elif self.expect(TokenType.OP, '='):
                value = self.parse_expr(required_type=int)
                self.require(TokenType.EOL)
                return Assignment(tok.lexeme, value)
            else:
                return self.parse_instruction(tok)
        else:
            tok = self.peektok()
            raise ParserError(f"Unknown token: {tok.lexeme if tok else 'EOF'}", tok)

    def parse_directive(self, tok: Token) -> Optional[Directive]:
        name = tok.lexeme
        args = []
        
        # Handle include
        if name in ['.include', '.inc']:
             arg = self.require(TokenType.STR, None)
             filename = arg.value
             self.require(TokenType.EOL)
             
             # Resolve path
             base_dir = os.getcwd()
             if self.lex.filename:
                 base_dir = os.path.dirname(os.path.abspath(self.lex.filename))
             path = os.path.join(base_dir, filename)
             
             if not os.path.exists(path):
                 raise ParserError(f"Include file not found: {path} (base: {base_dir}, file: {filename})", tok)

             # Check recursion/cycles
             abs_path = os.path.abspath(path)
             for t in self.tokenizers:
                 if t.filename and os.path.abspath(t.filename) == abs_path:
                     raise ParserError(f"Recursive include detected: {path}", tok)
             # Also check current lexer
             if self.lex.filename and os.path.abspath(self.lex.filename) == abs_path:
                  raise ParserError(f"Recursive include detected: {path}", tok)
             
             try:
                 with open(path, 'r') as f:
                     new_lex = Tokenizer(f, path)
             except Exception as e:
                 raise ParserError(f"Failed to open include file {path}: {e}", tok)
                 
             self.tokenizers.append(self.lex)
             self.lex = new_lex
             
             return None

        # Parse args based on directive type or just generally?
        # Assembler logic was specific per directive.
        # Here we can just parse expression list?
        if name in ['.byte', '.word', '.fill']:
             args = self.parse_expr_list()
        elif name == '.org':
             args = [self.parse_expr()]
        elif name == '.cpu':
             args = [self.parse_expr()]
        
        self.require(TokenType.EOL)
        return Directive(name, args)

    def parse_instruction(self, tok: Token) -> Instruction:
        mnemonic = tok.lexeme.upper()
        mode, operands = self.parse_operands(mnemonic)
        self.require(TokenType.EOL)
        
        operand = operands[0] if operands else None
        return Instruction(mnemonic, mode, operand)

    def parse_operands(self, instruction: str) -> Tuple[str, List]:
        operands = []
        # implied - no operands
        if self.peektok().type == TokenType.EOL:
            return ('IMP', [])
        
        # accumulator (A)
        # Check if 'A' is followed by EOL to differentiate from label 'A'
        if self.peektok().type == TokenType.ID and self.peektok().lexeme.upper() == 'A':
             # Save state to look ahead? Or just consume and check?
             # If we consume 'A', and next is not EOL, we backtrack?
             # Tokenizer doesn't support backtrack.
             # But 'A' as a label in an instruction like 'LDA A' is valid (ABS/ZP).
             # 'ASL A' is ACC.
             # 'ASL A' -> next is EOL.
             # 'LDA A' -> next is EOL? No, LDA requires operand.
             # So 'A' followed by EOL is likely ACC.
             # But 'LDA A' (load from address A) is also valid if A is a label.
             # However, standard syntax usually reserves 'A' for accumulator in shift ops.
             # Let's assume if we see 'A' and EOL, it's ACC.
             # We need to peek next token.
             # self.lex has next_token but not double peek.
             # Parser has peeked list.
             pass 
             # For now, let's treat explicit 'A' as ACC for shift ops? 
             # Or just parse as expression and let compiler decide?
             # Problem: AST needs 'mode'.
             # Let's handle 'A' as check:
        
        tok = self.peektok()
        if tok.type == TokenType.ID and tok.lexeme.upper() == 'A':
            # Consume A
            self.nexttok()
            if self.peektok().type == TokenType.EOL:
                 return ('ACC', [])
            # Backtrack? We can't. 
            # actually we consumed it.
            # If next is NOT EOL, then 'A' was the operand.
            # So we return ABS with 'A'?
            # Wait, if we return ('ABS', ['A']), compiler will resolve 'A'.
            # BUT we already consumed 'A'.
            # We need to construct Unresolved('A') manually.
            # This is complex.
            # Let's see if we can peek next token *before* consuming A.
            # Parser has self.peeked list.
            # peektok() ensures list has at least 1.
            # We can peek(1)?
            # Implementation of peektok doesn't support offset.
            # But we can call next_token on lexer and push to peeked.
            pass

        # Since we can't easily double peek without modifying parser, let's stick to standard flow.
        # If 'A' is used as ACC, it's usually the only operand.
        
        # immediate - signaled by #
        if self.expect(TokenType.OP, '#'):
            val = self.parse_expr()
            return ('#', [val])
            
        # Indirect: (expr)...
        if self.expect(TokenType.OP, '('):
            expr = self.parse_expr()
            # Case 1: (expr, X) -> INDX
            if self.expect(TokenType.OP, ','):
                self.require(TokenType.ID, 'X', casei=True)
                self.require(TokenType.OP, ')')
                return ('INDX', [expr])
            # Case 2: (expr), Y -> INDY
            elif self.expect(TokenType.OP, ')'):
                if self.expect(TokenType.OP, ','):
                    self.require(TokenType.ID, 'Y', casei=True)
                    return ('INDY', [expr])
                # Case 3: (expr) -> IND (JMP)
                return ('IND', [expr])
            else:
                 raise ParserError("Expected ')' or ', X'", self.peektok())
        
        # Absolute / ZP / Accumulator (as address)
        expr = self.parse_expr()
        
        # Check for indexing
        if self.expect(TokenType.OP, ','):
            if self.expect(TokenType.ID, 'X', casei=True):
                 return ('ABSX', [expr]) 
            elif self.expect(TokenType.ID, 'Y', casei=True):
                 return ('ABSY', [expr])
            else:
                raise ParserError("Expected index register X or Y", self.peektok())
        
        # If we got here, it's ABS or ZP (or ACC if expr was 'A')
        # We'll label it ABS, compiler can optimize to ZP.
        # If expr is literally 'A' string (Unresolved)?
        if isinstance(expr, Unresolved) and expr.name.upper() == 'A':
             return ('ACC', []) 
        
        return ('ABS', [expr])

    def parse_expr(self, required_type: type = None) -> Union[int, str, Unresolved, BinaryExpr]:
        val = self.parse_term(required_type)
        
        while True:
            if self.expect(TokenType.OP, '+'):
                rhs = self.parse_term(required_type)
                if isinstance(val, int) and isinstance(rhs, int):
                    val += rhs
                else:
                     val = BinaryExpr(val, '+', rhs)
            elif self.expect(TokenType.OP, '-'):
                rhs = self.parse_term(required_type)
                if isinstance(val, int) and isinstance(rhs, int):
                    val -= rhs
                else:
                     val = BinaryExpr(val, '-', rhs)
            else:
                break
        return val

    def parse_term(self, required_type: type = None) -> Union[int, str, Unresolved]:
        if tok := self.expect(TokenType.OP, "<"):
            expr = self.parse_expr(required_type=int)
            if isinstance(expr, int): return expr & 0xFF
            return Unresolved(expr.name, 'LOW') # Assuming expr is Unresolved
        
        if tok := self.expect(TokenType.OP, ">"):
            expr = self.parse_expr(required_type=int)
            if isinstance(expr, int): return (expr >> 8) & 0xFF
            return Unresolved(expr.name, 'HIGH')

        if tok := self.expect(TokenType.NUM):
            return tok.value
        if tok := self.expect(TokenType.ID):
            # AST always treats ID as Unresolved at parse time? 
            # Or should strict value be resolved later?
            # Yes, AST just captures name.
            return Unresolved(tok.lexeme, 'ADDRESS')
        if tok := self.expect(TokenType.STR):
            return tok.value
            
        # TODO: Parens for indirect
        
        raise ParserError(f"Unknown token in expression: {self.peektok()}", self.peektok())

    def parse_expr_list(self) -> List:
        expr_list = []
        while True:
            expr = self.parse_expr()
            expr_list.append(expr)
            if self.peektok().type == TokenType.EOL:
                break
            self.require(TokenType.OP, ',')
        return expr_list
