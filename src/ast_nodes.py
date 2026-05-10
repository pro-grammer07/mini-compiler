from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Program:
    decls: List[object]


@dataclass
class VarDecl:
    var_type: str
    name: str
    size: Optional[int] = None
    line: Optional[int] = None


@dataclass
class Param:
    param_type: str
    name: str
    is_array: bool = False
    line: Optional[int] = None


@dataclass
class FuncDecl:
    ret_type: str
    name: str
    params: List[Param]
    body: "Block"
    line: Optional[int] = None


@dataclass
class Block:
    items: List[object] = field(default_factory=list)


@dataclass
class IfStmt:
    cond: object
    then_branch: object
    else_branch: Optional[object] = None


@dataclass
class WhileStmt:
    cond: object
    body: object


@dataclass
class ForStmt:
    init: Optional[object]
    cond: Optional[object]
    step: Optional[object]
    body: object


@dataclass
class ReturnStmt:
    expr: Optional[object]


@dataclass
class ExprStmt:
    expr: Optional[object]


@dataclass
class Assign:
    target: object
    value: object


@dataclass
class BinaryOp:
    op: str
    left: object
    right: object


@dataclass
class UnaryOp:
    op: str
    operand: object


@dataclass
class Literal:
    value: str
    lit_type: str
    line: Optional[int] = None


@dataclass
class VarRef:
    name: str
    line: Optional[int] = None


@dataclass
class ArrayRef:
    name: str
    index: object
    line: Optional[int] = None


@dataclass
class Call:
    name: str
    args: List[object]
    line: Optional[int] = None
