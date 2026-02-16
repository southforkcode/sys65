from typing import List, Union, Optional
from dataclasses import dataclass

@dataclass
class Node:
    pass

@dataclass
class Unresolved(Node):
    name: str
    type: str # 'ADDRESS', 'LOW', 'HIGH'

    def __repr__(self):
        return f"Unresolved({self.name}, {self.type})"

class Statement(Node):
    filename: Optional[str] = None

@dataclass
class Program(Node):
    statements: List[Statement]

@dataclass
class Label(Statement):
    name: str
    line: int = 0

@dataclass
class Assignment(Statement):
    name: str
    value: int
    line: int = 0

@dataclass
class Directive(Statement):
    name: str
    args: List[Union[int, str, Unresolved]]
    line: int = 0

@dataclass
class Instruction(Statement):
    mnemonic: str
    mode: str
    operand: Union[int, str, Unresolved, None]
    line: int = 0

@dataclass
class BinaryExpr(Node):
    left: Union[int, str, Unresolved, 'BinaryExpr']
    op: str
    right: Union[int, str, Unresolved, 'BinaryExpr']

@dataclass
class IfDef(Statement):
    condition: str
    then_block: List[Statement]
    else_block: List[Statement]
    line: int = 0

@dataclass
class EnumDef(Statement):
    name: Optional[str]
    size: int # 1 or 2
    members: List[tuple] # (name, value_expr|None)
    line: int = 0

