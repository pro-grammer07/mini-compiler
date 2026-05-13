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
    Param,
    Program,
    ReturnStmt,
    UnaryOp,
    VarDecl,
    VarRef,
    WhileStmt,
)
from tokens import Token


class ParserError(Exception):
    pass


def _number_literal_type(lex: str) -> str:
    s = lex.lower()
    if "e" in s or "." in s:
        return "float"
    return "int"


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0
        self.errors: List[str] = []

    def cur(self) -> Token:
        return self.tokens[self.i]

    def eat(self, kind: str, value: Optional[str] = None) -> Token:
        tok = self.cur()
        if tok.kind != kind or (value is not None and tok.value != value):
            expected = f"{kind} {value}" if value else kind
            self.errors.append(
                f"Syntax error at line {tok.line}, col {tok.column}: expected {expected}, got {tok.kind} {tok.value}"
            )
            if tok.kind != "EOF":
                self.i += 1
            return Token(kind, value or "", tok.line, tok.column)
        self.i += 1
        return tok

    def match(self, kind: str, value: Optional[str] = None) -> bool:
        tok = self.cur()
        return tok.kind == kind and (value is None or tok.value == value)

    def parse(self) -> Program:
        decls = []
        while not self.match("EOF"):
            start_i = self.i
            try:
                decls.append(self.parse_decl())
            except ParserError as e:
                tok = self.cur()
                self.errors.append(f"Syntax error at line {tok.line}, col {tok.column}: {e}")
                self.synchronize()
            if self.i == start_i:
                if self.cur().kind == "EOF":
                    break
                self.i += 1
        return Program(decls)

    def synchronize(self):
        while not self.match("EOF"):
            tok = self.cur()
            if tok.kind == "SYMBOL" and tok.value in (";", "}"):
                self.i += 1
                return
            self.i += 1

    def parse_type(self) -> str:
        tok = self.eat("KEYWORD")
        if tok.value not in ("int", "float", "void"):
            raise ParserError(f"Invalid type {tok.value}")
        return tok.value

    def parse_decl(self):
        t_tok = self.eat("KEYWORD")
        t = t_tok.value
        if t not in ("int", "float", "void"):
            raise ParserError(f"Invalid type {t}")
        name_tok = self.eat("ID")
        name = name_tok.value
        if self.match("SYMBOL", "("):
            self.eat("SYMBOL", "(")
            params = self.parse_params()
            self.eat("SYMBOL", ")")
            body = self.parse_block()
            return FuncDecl(t, name, params, body, line=name_tok.line)
        size = None
        if self.match("SYMBOL", "["):
            self.eat("SYMBOL", "[")
            size = int(self.eat("NUMBER").value)
            self.eat("SYMBOL", "]")
        self.eat("SYMBOL", ";")
        return VarDecl(t, name, size, line=name_tok.line)

    def parse_params(self) -> List[Param]:
        params = []
        if self.match("KEYWORD", "void"):
            self.eat("KEYWORD", "void")
            return params
        if self.match("SYMBOL", ")"):
            return params
        while True:
            pt = self.parse_type()
            name_tok = self.eat("ID")
            name = name_tok.value
            is_array = False
            if self.match("SYMBOL", "["):
                self.eat("SYMBOL", "[")
                self.eat("SYMBOL", "]")
                is_array = True
            params.append(Param(pt, name, is_array, line=name_tok.line))
            if not self.match("SYMBOL", ","):
                break
            self.eat("SYMBOL", ",")
        return params

    def parse_block(self) -> Block:
        self.eat("SYMBOL", "{")
        items = []
        while not self.match("SYMBOL", "}"):
            if self.match("KEYWORD") and self.cur().value in ("int", "float", "void"):
                items.append(self.parse_local_decl())
            else:
                items.append(self.parse_stmt())
        self.eat("SYMBOL", "}")
        return Block(items)

    def parse_local_decl(self) -> VarDecl:
        t_tok = self.eat("KEYWORD")
        t = t_tok.value
        if t not in ("int", "float", "void"):
            raise ParserError(f"Invalid type {t}")
        name_tok = self.eat("ID")
        name = name_tok.value
        size = None
        if self.match("SYMBOL", "["):
            self.eat("SYMBOL", "[")
            size = int(self.eat("NUMBER").value)
            self.eat("SYMBOL", "]")
        self.eat("SYMBOL", ";")
        return VarDecl(t, name, size, line=name_tok.line)

    def parse_stmt(self):
        if self.match("SYMBOL", "{"):
            return self.parse_block()
        if self.match("KEYWORD", "if"):
            return self.parse_if()
        if self.match("KEYWORD", "while"):
            return self.parse_while()
        if self.match("KEYWORD", "for"):
            return self.parse_for()
        if self.match("KEYWORD", "return"):
            return self.parse_return()
        return self.parse_expr_stmt()

    def parse_if(self) -> IfStmt:
        self.eat("KEYWORD", "if")
        self.eat("SYMBOL", "(")
        cond = self.parse_expr()
        self.eat("SYMBOL", ")")
        then_branch = self.parse_stmt()
        else_branch = None
        if self.match("KEYWORD", "else"):
            self.eat("KEYWORD", "else")
            else_branch = self.parse_stmt()
        return IfStmt(cond, then_branch, else_branch)

    def parse_while(self) -> WhileStmt:
        self.eat("KEYWORD", "while")
        self.eat("SYMBOL", "(")
        cond = self.parse_expr()
        self.eat("SYMBOL", ")")
        body = self.parse_stmt()
        return WhileStmt(cond, body)

    def parse_for(self) -> ForStmt:
        self.eat("KEYWORD", "for")
        self.eat("SYMBOL", "(")
        init = None if self.match("SYMBOL", ";") else self.parse_expr()
        self.eat("SYMBOL", ";")
        cond = None if self.match("SYMBOL", ";") else self.parse_expr()
        self.eat("SYMBOL", ";")
        step = None if self.match("SYMBOL", ")") else self.parse_expr()
        self.eat("SYMBOL", ")")
        body = self.parse_stmt()
        return ForStmt(init, cond, step, body)

    def parse_return(self) -> ReturnStmt:
        self.eat("KEYWORD", "return")
        expr = None if self.match("SYMBOL", ";") else self.parse_expr()
        self.eat("SYMBOL", ";")
        return ReturnStmt(expr)

    def parse_expr_stmt(self) -> ExprStmt:
        expr = None if self.match("SYMBOL", ";") else self.parse_expr()
        self.eat("SYMBOL", ";")
        return ExprStmt(expr)

    def parse_expr(self):
        return self.parse_assign()

    def parse_assign(self):
        left = self.parse_logical_or()
        if self.match("SYMBOL", "="):
            self.eat("SYMBOL", "=")
            value = self.parse_assign()
            return Assign(left, value)
        return left

    def parse_logical_or(self):
        node = self.parse_logical_and()
        while self.match("SYMBOL", "||"):
            op = self.eat("SYMBOL").value
            node = BinaryOp(op, node, self.parse_logical_and())
        return node

    def parse_logical_and(self):
        node = self.parse_equality()
        while self.match("SYMBOL", "&&"):
            op = self.eat("SYMBOL").value
            node = BinaryOp(op, node, self.parse_equality())
        return node

    def parse_equality(self):
        node = self.parse_rel()
        while self.match("SYMBOL") and self.cur().value in ("==", "!="):
            op = self.eat("SYMBOL").value
            node = BinaryOp(op, node, self.parse_rel())
        return node

    def parse_rel(self):
        node = self.parse_add()
        while self.match("SYMBOL") and self.cur().value in ("<", ">", "<=", ">="):
            op = self.eat("SYMBOL").value
            node = BinaryOp(op, node, self.parse_add())
        return node

    def parse_add(self):
        node = self.parse_mul()
        while self.match("SYMBOL") and self.cur().value in ("+", "-"):
            op = self.eat("SYMBOL").value
            node = BinaryOp(op, node, self.parse_mul())
        return node

    def parse_mul(self):
        node = self.parse_unary()
        while self.match("SYMBOL") and self.cur().value in ("*", "/", "%"):
            op = self.eat("SYMBOL").value
            node = BinaryOp(op, node, self.parse_unary())
        return node

    def parse_unary(self):
        if self.match("SYMBOL") and self.cur().value in ("!", "-"):
            op = self.eat("SYMBOL").value
            return UnaryOp(op, self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        tok = self.cur()
        if self.match("NUMBER"):
            self.eat("NUMBER")
            lit_type = _number_literal_type(tok.value)
            return Literal(tok.value, lit_type, line=tok.line)
        if self.match("STR"):
            self.eat("STR")
            return Literal(tok.value, "string", line=tok.line)
        if self.match("ID"):
            id_tok = self.eat("ID")
            name = id_tok.value
            if self.match("SYMBOL", "("):
                self.eat("SYMBOL", "(")
                args = []
                if not self.match("SYMBOL", ")"):
                    while True:
                        args.append(self.parse_expr())
                        if not self.match("SYMBOL", ","):
                            break
                        self.eat("SYMBOL", ",")
                self.eat("SYMBOL", ")")
                return Call(name, args, line=id_tok.line)
            if self.match("SYMBOL", "["):
                self.eat("SYMBOL", "[")
                idx = self.parse_expr()
                self.eat("SYMBOL", "]")
                return ArrayRef(name, idx, line=id_tok.line)
            return VarRef(name, line=id_tok.line)
        if self.match("SYMBOL", "("):
            self.eat("SYMBOL", "(")
            node = self.parse_expr()
            self.eat("SYMBOL", ")")
            return node
        raise ParserError(f"unexpected token {tok.kind} {tok.value} at line {tok.line}")
