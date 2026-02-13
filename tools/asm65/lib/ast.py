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

@dataclass
class Statement(Node):
    pass

@dataclass
class Program(Node):
    statements: List[Statement]

@dataclass
class Label(Statement):
    name: str

@dataclass
class Assignment(Statement):
    name: str
    value: int

@dataclass
class Directive(Statement):
    name: str
    args: List[Union[int, str, Unresolved]]

@dataclass
class Instruction(Statement):
    mnemonic: str
    mode: str
    operand: Union[int, str, Unresolved, None]

@dataclass
class BinaryExpr(Node):
    left: Union[int, str, Unresolved, 'BinaryExpr']
    op: str
    right: Union[int, str, Unresolved, 'BinaryExpr']
