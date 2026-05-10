import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from tokens import Token


class LexerError(Exception):
    pass


class Lexer:
    KEYWORDS = {
        "int",
        "float",
        "void",
        "if",
        "else",
        "while",
        "for",
        "return",
    }

    TOKEN_SPEC = [
        ("COMMENT", r"//[^\n]*"),
        ("MCOMMENT", r"/\*.*?\*/"),
        ("NUMBER", r"\d+\.\d+|\d+"),
        ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
        ("OP", r"\|\||&&|==|!=|<=|>=|[+\-*/%<>=!]|;|,|\(|\)|\{|\}|\[|\]"),
        ("NEWLINE", r"\n"),
        ("SKIP", r"[ \t\r]+"),
        ("MISMATCH", r"."),
    ]

    def __init__(self, source: str):
        self.source = source
        self.master = re.compile(
            "|".join(f"(?P<{name}>{pattern})" for name, pattern in self.TOKEN_SPEC),
            re.DOTALL,
        )

    def tokenize(self) -> List[Token]:
        tokens, errors = self.tokenize_with_errors()
        if errors:
            raise LexerError("\n".join(errors))
        return tokens

    def tokenize_with_errors(self) -> tuple[List[Token], List[str]]:
        line = 1
        col = 1
        tokens: List[Token] = []
        errors: List[str] = []

        for m in self.master.finditer(self.source):
            kind = m.lastgroup
            value = m.group()
            if kind == "NEWLINE":
                line += 1
                col = 1
                continue
            if kind in ("SKIP", "COMMENT", "MCOMMENT"):
                col += len(value)
                continue
            if kind == "ID" and value in self.KEYWORDS:
                kind = "KEYWORD"
            elif kind == "OP":
                kind = "SYMBOL"
            elif kind == "MISMATCH":
                errors.append(f"Lexical error at line {line}, col {col}: unexpected character {value!r}")
                col += len(value)
                continue

            tokens.append(Token(kind, value, line, col))
            col += len(value)

        tokens.append(Token("EOF", "EOF", line, col))
        return tokens, errors


@dataclass
class LexSymbol:
    symbol: str
    token_type: str
    data_type: str
    line: int


def build_lex_symbol_table(tokens: List[Token]) -> List[LexSymbol]:
    entries: Dict[str, LexSymbol] = {}
    declared_types: Dict[str, str] = {}
    i = 0
    n = len(tokens)
    type_keywords = {"int", "float", "void"}

    while i < n:
        tok = tokens[i]
        if tok.kind == "KEYWORD" and tok.value in type_keywords and i + 1 < n:
            nxt = tokens[i + 1]
            if nxt.kind == "ID":
                name = nxt.value
                if i + 2 < n and tokens[i + 2].kind == "SYMBOL" and tokens[i + 2].value == "(":
                    if name not in entries:
                        entries[name] = LexSymbol(name, "FUNCTION", tok.value, nxt.line)
                    declared_types[name] = tok.value
                    j = i + 3
                    while j < n and not (tokens[j].kind == "SYMBOL" and tokens[j].value == ")"):
                        if (
                            tokens[j].kind == "KEYWORD"
                            and tokens[j].value in type_keywords
                            and j + 1 < n
                            and tokens[j + 1].kind == "ID"
                        ):
                            p_type = tokens[j].value
                            p_name = tokens[j + 1].value
                            if p_name not in entries:
                                entries[p_name] = LexSymbol(p_name, "PARAMETER", p_type, tokens[j + 1].line)
                            declared_types[p_name] = p_type
                            j += 2
                            continue
                        j += 1
                    i = j + 1
                    continue
                if name not in entries:
                    entries[name] = LexSymbol(name, "IDENTIFIER", tok.value, nxt.line)
                declared_types[name] = tok.value
        elif tok.kind == "ID":
            dt = declared_types.get(tok.value, "unknown")
            if tok.value not in entries:
                entries[tok.value] = LexSymbol(tok.value, "IDENTIFIER", dt, tok.line)
        elif tok.kind == "NUMBER":
            dtype = "float" if "." in tok.value else "int"
            key = f"literal:{tok.value}:{tok.line}:{tok.column}"
            entries[key] = LexSymbol(tok.value, "NUMBER", dtype, tok.line)
        i += 1

    return sorted(entries.values(), key=lambda e: (e.line, e.symbol))
