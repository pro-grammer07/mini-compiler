from dataclasses import dataclass
from typing import Dict, List, Optional

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
    VarDecl,
    VarRef,
    WhileStmt,
)


class SemanticError(Exception):
    pass


@dataclass
class Symbol:
    name: str
    kind: str
    typ: str
    size: Optional[int] = None
    params: Optional[List[str]] = None
    line: Optional[int] = None


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.table: Dict[str, Symbol] = {}

    def define(self, sym: Symbol):
        if sym.name in self.table:
            prev = self.table[sym.name]
            if sym.line is not None:
                raise SemanticError(
                    f"Duplicate symbol '{sym.name}' at line {sym.line} (previously declared at line {prev.line})"
                )
            raise SemanticError(f"Duplicate symbol '{sym.name}'")
        self.table[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        cur = self
        while cur:
            if name in cur.table:
                return cur.table[name]
            cur = cur.parent
        return None


class SemanticAnalyzer:
    def __init__(self):
        self.global_scope = Scope()
        self.scope = self.global_scope
        self.current_function: Optional[Symbol] = None
        self.trace: List[str] = []
        self.errors: List[str] = []

    def analyze(self, program: Program) -> List[str]:
        for d in program.decls:
            if isinstance(d, VarDecl):
                try:
                    self.scope.define(Symbol(d.name, "var", d.var_type, size=d.size, line=d.line))
                    self.trace.append(f"[global] define {d.var_type} {d.name}")
                except SemanticError as e:
                    self.errors.append(str(e))
            elif isinstance(d, FuncDecl):
                try:
                    self.scope.define(
                        Symbol(
                            d.name,
                            "func",
                            d.ret_type,
                            params=[p.param_type for p in d.params],
                            line=d.line,
                        )
                    )
                    self.trace.append(
                        f"[global] define function {d.name}({', '.join(p.param_type for p in d.params)})"
                    )
                except SemanticError as e:
                    self.errors.append(str(e))
            else:
                self.errors.append("Unknown top-level declaration")

        main = self.scope.lookup("main")
        if not main or main.kind != "func":
            self.errors.append("main function not found")

        for d in program.decls:
            if isinstance(d, FuncDecl):
                try:
                    self.visit_func(d)
                except SemanticError as e:
                    self.errors.append(str(e))

        return self.trace

    def visit_func(self, fn: FuncDecl):
        self.current_function = self.scope.lookup(fn.name)
        self.scope = Scope(self.global_scope)
        self.trace.append(f"[enter] function {fn.name}")

        for p in fn.params:
            try:
                self.scope.define(Symbol(p.name, "param", p.param_type, line=p.line))
                self.trace.append(f"[param] {p.param_type} {p.name}")
            except SemanticError as e:
                self.errors.append(str(e))

        self.visit_block(fn.body, create_scope=False)
        self.trace.append(f"[exit] function {fn.name}")
        self.scope = self.global_scope
        self.current_function = None

    def visit_block(self, block: Block, create_scope: bool = True):
        if create_scope:
            self.scope = Scope(self.scope)
            self.trace.append("[enter] block")

        for item in block.items:
            if isinstance(item, VarDecl):
                try:
                    self.scope.define(Symbol(item.name, "var", item.var_type, size=item.size, line=item.line))
                    self.trace.append(f"[local] define {item.var_type} {item.name}")
                except SemanticError as e:
                    self.errors.append(str(e))
            else:
                try:
                    self.visit_stmt(item)
                except SemanticError as e:
                    self.errors.append(str(e))

        if create_scope:
            self.scope = self.scope.parent
            self.trace.append("[exit] block")

    def visit_stmt(self, stmt):
        if isinstance(stmt, Block):
            self.visit_block(stmt, create_scope=True)
        elif isinstance(stmt, IfStmt):
            self.type_of(stmt.cond)
            self.visit_stmt(stmt.then_branch)
            if stmt.else_branch:
                self.visit_stmt(stmt.else_branch)
        elif isinstance(stmt, WhileStmt):
            self.type_of(stmt.cond)
            self.visit_stmt(stmt.body)
        elif isinstance(stmt, ForStmt):
            if stmt.init:
                self.type_of(stmt.init)
            if stmt.cond:
                self.type_of(stmt.cond)
            if stmt.step:
                self.type_of(stmt.step)
            self.visit_stmt(stmt.body)
        elif isinstance(stmt, ReturnStmt):
            got = "void" if stmt.expr is None else self.type_of(stmt.expr)
            exp = self.current_function.typ if self.current_function else "void"
            if exp != got and not (exp == "float" and got == "int"):
                raise SemanticError(f"Return type mismatch: expected {exp}, got {got}")
        elif isinstance(stmt, ExprStmt):
            if stmt.expr:
                self.type_of(stmt.expr)
        else:
            raise SemanticError(f"Unknown statement: {type(stmt).__name__}")

    def type_of(self, expr) -> str:
        if isinstance(expr, Literal):
            return expr.lit_type
        if isinstance(expr, VarRef):
            sym = self.scope.lookup(expr.name)
            if not sym:
                where = f" at line {expr.line}" if expr.line is not None else ""
                raise SemanticError(f"Undeclared variable '{expr.name}'{where}")
            return sym.typ
        if isinstance(expr, ArrayRef):
            sym = self.scope.lookup(expr.name)
            if not sym:
                where = f" at line {expr.line}" if expr.line is not None else ""
                raise SemanticError(f"Undeclared array '{expr.name}'{where}")
            if sym.size is None:
                where = f" at line {expr.line}" if expr.line is not None else ""
                raise SemanticError(f"'{expr.name}' is not an array{where}")
            idx_t = self.type_of(expr.index)
            if idx_t != "int":
                where = f" at line {expr.line}" if expr.line is not None else ""
                raise SemanticError(f"Array index must be int{where}")
            return sym.typ
        if isinstance(expr, Assign):
            lt = self.type_of(expr.target)
            rt = self.type_of(expr.value)
            if lt != rt and not (lt == "float" and rt == "int"):
                raise SemanticError(f"Type mismatch in assignment: {lt} = {rt}")
            return lt
        if isinstance(expr, UnaryOp):
            return self.type_of(expr.operand)
        if isinstance(expr, BinaryOp):
            lt = self.type_of(expr.left)
            rt = self.type_of(expr.right)
            if lt == "string" or rt == "string":
                raise SemanticError(
                    f"Operator {expr.op!r} is not defined for string literals"
                )
            if expr.op in ("+", "-", "*", "/", "%"):
                if lt == "float" or rt == "float":
                    return "float"
                return "int"
            return "int"
        if isinstance(expr, Call):
            fn = self.global_scope.lookup(expr.name)
            if not fn or fn.kind != "func":
                where = f" at line {expr.line}" if expr.line is not None else ""
                raise SemanticError(f"Undeclared function '{expr.name}'{where}")
            exp_count = len(fn.params or [])
            if len(expr.args) != exp_count:
                raise SemanticError(
                    f"Function '{expr.name}' expects {exp_count} args, got {len(expr.args)}"
                )
            for idx, arg in enumerate(expr.args):
                at = self.type_of(arg)
                et = fn.params[idx]
                if at != et and not (et == "float" and at == "int"):
                    raise SemanticError(
                        f"Function '{expr.name}' arg {idx + 1}: expected {et}, got {at}"
                    )
            return fn.typ
        raise SemanticError(f"Unknown expression: {type(expr).__name__}")
