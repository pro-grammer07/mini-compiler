from dataclasses import dataclass
from typing import List, Optional

from ast_nodes import (
    ArrayRef,
    Assign,
    BinaryOp,
    Block,
    Call,
    ExprStmt,
    ForStmt,
    FuncDecl,
    IfStmt,
    Literal,
    Program,
    ReturnStmt,
    UnaryOp,
    VarRef,
    WhileStmt,
)


@dataclass
class Instr:
    op: str
    a1: Optional[str] = None
    a2: Optional[str] = None
    res: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.op:<10} {self.a1 or '_':<10} {self.a2 or '_':<10} {self.res or '_'}"


class IRGenerator:
    def __init__(self):
        self.code: List[Instr] = []
        self.t = 0
        self.l = 0

    def new_temp(self) -> str:
        self.t += 1
        return f"t{self.t}"

    def new_label(self) -> str:
        self.l += 1
        return f"L{self.l}"

    def emit(self, op, a1=None, a2=None, res=None):
        self.code.append(Instr(op, a1, a2, res))

    def generate(self, program: Program) -> List[Instr]:
        for d in program.decls:
            if isinstance(d, FuncDecl):
                self.emit("FUNC", d.name)
                self.gen_block(d.body)
                self.emit("END_FUNC", d.name)
        return self.code

    def gen_block(self, block: Block):
        for item in block.items:
            if isinstance(item, FuncDecl):
                continue
            if hasattr(item, "var_type"):
                continue
            self.gen_stmt(item)

    def gen_stmt(self, stmt):
        if isinstance(stmt, Block):
            self.gen_block(stmt)
        elif isinstance(stmt, ExprStmt):
            if stmt.expr:
                self.gen_expr(stmt.expr)
        elif isinstance(stmt, ReturnStmt):
            val = self.gen_expr(stmt.expr) if stmt.expr else None
            self.emit("RET", val)
        elif isinstance(stmt, IfStmt):
            else_l = self.new_label()
            end_l = self.new_label()
            c = self.gen_expr(stmt.cond)
            self.emit("IFZ", c, None, else_l)
            self.gen_stmt(stmt.then_branch)
            self.emit("GOTO", None, None, end_l)
            self.emit("LABEL", else_l)
            if stmt.else_branch:
                self.gen_stmt(stmt.else_branch)
            self.emit("LABEL", end_l)
        elif isinstance(stmt, WhileStmt):
            start = self.new_label()
            end = self.new_label()
            self.emit("LABEL", start)
            c = self.gen_expr(stmt.cond)
            self.emit("IFZ", c, None, end)
            self.gen_stmt(stmt.body)
            self.emit("GOTO", None, None, start)
            self.emit("LABEL", end)
        elif isinstance(stmt, ForStmt):
            if stmt.init:
                self.gen_expr(stmt.init)
            start = self.new_label()
            end = self.new_label()
            self.emit("LABEL", start)
            if stmt.cond:
                c = self.gen_expr(stmt.cond)
                self.emit("IFZ", c, None, end)
            self.gen_stmt(stmt.body)
            if stmt.step:
                self.gen_expr(stmt.step)
            self.emit("GOTO", None, None, start)
            self.emit("LABEL", end)

    def gen_expr(self, expr) -> str:
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, VarRef):
            return expr.name
        if isinstance(expr, ArrayRef):
            idx = self.gen_expr(expr.index)
            t = self.new_temp()
            self.emit("LOADARR", expr.name, idx, t)
            return t
        if isinstance(expr, Assign):
            rhs = self.gen_expr(expr.value)
            if isinstance(expr.target, ArrayRef):
                idx = self.gen_expr(expr.target.index)
                self.emit("STOREARR", rhs, idx, expr.target.name)
                return rhs
            self.emit("MOV", rhs, None, expr.target.name)
            return expr.target.name
        if isinstance(expr, UnaryOp):
            val = self.gen_expr(expr.operand)
            t = self.new_temp()
            self.emit(f"U{expr.op}", val, None, t)
            return t
        if isinstance(expr, BinaryOp):
            l = self.gen_expr(expr.left)
            r = self.gen_expr(expr.right)
            t = self.new_temp()
            self.emit(expr.op, l, r, t)
            return t
        if isinstance(expr, Call):
            for a in expr.args:
                self.emit("ARG", self.gen_expr(a))
            t = self.new_temp()
            self.emit("CALL", expr.name, str(len(expr.args)), t)
            return t
        raise RuntimeError(f"Unknown expr {type(expr).__name__}")
