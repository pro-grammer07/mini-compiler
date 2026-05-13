"""
Lexical analyzer - hand-coded DFA aligned with Lexical_Analyzer_detailed (C ref).

State numbers (diagram):
  S0 START | S1 EOF | S2 IDENT acc | S3 KEYWORD or IDENTIFIER | S4 INT acc |
  S5 FLOAT frac | S6 FLOAT exp | S7 FLOAT | S8 INT | S9-S11 '<', '<=' |
  S12-S14 '>', '>=' | S15-S17 '!', '!=' | S18-S20 '=', '==' | S21-S23 '+', '++' |
  S24-S26 '-', '--' | S27-S39 * / % ( ) { } [ ] ; : , . | S40-S41 string

Pipeline contract (downstream code must not break):
  Only these Token.kind values are emitted to the parser and later phases:
    KEYWORD, ID, NUMBER, SYMBOL, STR, EOF
  Column is the 1-based column of the first character of the lexeme (after
  comment stripping and whitespace skip), matching the historical lexer.

DFA accept label -> Token(kind, value)  (value is always the source lexeme
except EOF uses value 'EOF'.)
  KEYWORD / IDENTIFIER -> KEYWORD / ID  (ANSI reserved -> KEYWORD at S3)
  INT / FLOAT          -> NUMBER
  STR                  -> STR
  LEQ..PERIOD, OROR, ANDAND -> SYMBOL with value '<=', '<', ..., '.', '||', '&&'
  EOF                  -> EOF

S0 extension (not on original draw.io): '||' and '&&' so logical ops match
parser.py / GRAMMAR_SPEC. Default Lexer(source) is unchanged for the mini
subset: trace_dfa=False; comment stripping + token kinds stay compatible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from tokens import Token

# Kinds emitted after normalization; parser / IR expect only these.
_PIPELINE_TOKEN_KINDS = frozenset({"KEYWORD", "ID", "NUMBER", "SYMBOL", "STR", "EOF"})

__all__ = [
    "Lexer",
    "LexerError",
    "LexSymbol",
    "build_lex_symbol_table",
    "dfa_diagram_text",
    "dfa_states_reference",
]


class LexerError(Exception):
    pass


# All 32 ANSI C keywords (state 3 distinguishes KEYWORD vs IDENTIFIER by table)
ANSI_C_KEYWORDS = frozenset(
    {
        "auto",
        "break",
        "case",
        "char",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "enum",
        "extern",
        "float",
        "for",
        "goto",
        "if",
        "int",
        "long",
        "register",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "struct",
        "switch",
        "typedef",
        "union",
        "unsigned",
        "void",
        "volatile",
        "while",
    }
)

# Type-related keywords for lexical symbol table hints (subset of keywords)
TYPE_KEYWORDS = frozenset(
    {
        "int",
        "float",
        "double",
        "char",
        "void",
        "long",
        "short",
        "signed",
        "unsigned",
        "const",
        "volatile",
        "struct",
        "union",
        "enum",
        "extern",
        "static",
        "auto",
        "register",
        "typedef",
    }
)

# DFA state ids (same numbering as diagram)
S0, S1, S2, S3, S4, S5, S6, S7, S8, S9 = range(10)
S10, S11, S12, S13, S14, S15, S16, S17, S18, S19 = range(10, 20)
S20, S21, S22, S23, S24, S25, S26, S27, S28, S29 = range(20, 30)
S30, S31, S32, S33, S34, S35, S36, S37, S38, S39 = range(30, 40)
S40, S41 = 40, 41
S_DONE = 42


def dfa_states_reference() -> str:
    """One-line per state for console reference."""
    return """
DFA states (diagram numbering)
  S0   START (whitespace consumed before each token)
  S1   accept EOF
  S2   IDENT accumulator  [a-zA-Z0-9_] -> S2, else -> S3
  S3   accept KEYWORD or IDENTIFIER
  S4   INT accumulator    [0-9]->S4, '.'->S5, else->S8
  S5   FLOAT fraction      [0-9]->S5, [eE]->S6, else->S7
  S6   FLOAT exponent      [+\\-0-9]->S6, else->S7
  S7   accept FLOAT
  S8   accept INT
  S9   '<' pending         '='->S10, else->S11
  S10  accept LEQ (<=)
  S11  accept LESS (<)
  S12  '>' pending         '='->S13, else->S14
  S13  accept GREQ (>=)
  S14  accept GREATER (>)
  S15  '!' pending         '='->S16, else->S17
  S16  accept NEQ (!=)
  S17  accept NOT (!)
  S18  '=' pending         '='->S19, else->S20
  S19  accept EQUAL (==)
  S20  accept ASSIGN (=)
  S21  '+' pending         '+'->S22, else->S23
  S22  accept INC (++)
  S23  accept ADD (+)
  S24  '-' pending         '-'->S25, else->S26
  S25  accept DEC (--)
  S26  accept SUB (-)
  S27..S39  single-char accepts: * / % ( ) { } [ ] ; : , .
  S40  STRING accumulator  '"'->S41, else self-loop (incl. escapes)
  S41  accept STR

  Extension at S0 (grammar needs them):  "||" and "&&" as two-char operators.
""".strip()


def dfa_diagram_text() -> str:
    """ASCII overview of transitions for console display."""
    return r"""
================================================================================
                    LEXER DFA - CONSOLE REFERENCE
================================================================================

                         +----------------+
                         |  S0   START    |
                         | skip WS        |
                         +--------+-------+
                                  |
         +------------------------+------------------------+
         |            |           |           |            |
    [a-zA-Z_]      [0-9]         '"'        < > ! =      + -
         |            |           |           |            |
         v            v           v           v            v
      +-----+     +-----+     +-----+     +--+--+      +--+--+
      | S2  |     | S4  |     | S40 |     |S9 S12|      |S21  |
      | ID  |     | INT |     |STR  |     |S15 S18|     |S24  |
      +--+--+     +--+--+     +--+--+     +-------+     +-----+
         |            |           |            ...         ...
        S3           S8,S7       S41

  S0 immediate accepts (no intermediate states):  * / % ( ) { } [ ] ; : , .
  S0 also accepts  "||"  and  "&&"  (logical ops required by the parser).
  S0 on '\0'  ->  S1  EOF

  Identifier / number / string / compare / inc-dec paths follow the state list
  in dfa_states_reference().

================================================================================
""".strip()


def strip_comments(src: str) -> str:
    """Blank // and /* */ like the C lexer; copy string literals verbatim."""
    out: List[str] = []
    i, n = 0, len(src)
    while i < n:
        if i + 1 < n and src[i] == "/" and src[i + 1] == "/":
            i += 2
            while i < n and src[i] != "\n":
                out.append(" ")
                i += 1
        elif i + 1 < n and src[i] == "/" and src[i + 1] == "*":
            i += 2
            while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                out.append("\n" if src[i] == "\n" else " ")
                i += 1
            if i + 1 < n:
                i += 2
        elif src[i] == '"':
            out.append(src[i])
            i += 1
            while i < n and src[i] != '"':
                if src[i] == "\\" and i + 1 < n:
                    out.append(src[i])
                    i += 1
                out.append(src[i])
                i += 1
            if i < n:
                out.append(src[i])
                i += 1
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def _normalize_dfa_token(
    dfa_kind: str, lexeme: str, line: int, col: int
) -> Token:
    """Map diagram accept labels to kinds the rest of the compiler expects."""
    if dfa_kind == "IDENTIFIER":
        return Token("ID", lexeme, line, col)
    if dfa_kind == "KEYWORD":
        return Token("KEYWORD", lexeme, line, col)
    if dfa_kind in ("INT", "FLOAT"):
        return Token("NUMBER", lexeme, line, col)
    if dfa_kind == "STR":
        return Token("STR", lexeme, line, col)
    if dfa_kind == "EOF":
        return Token("EOF", "EOF", line, col)

    sym_map = {
        "LEQ": "<=",
        "LESS": "<",
        "GREQ": ">=",
        "GREATER": ">",
        "NEQ": "!=",
        "NOT": "!",
        "EQUAL": "==",
        "ASSIGN": "=",
        "INC": "++",
        "ADD": "+",
        "DEC": "--",
        "SUB": "-",
        "MUL": "*",
        "DIV": "/",
        "MOD": "%",
        "LPAREN": "(",
        "RPAREN": ")",
        "LBRACE": "{",
        "RBRACE": "}",
        "LSQBRAC": "[",
        "RSQBRAC": "]",
        "SEMICOLON": ";",
        "COLON": ":",
        "COMMA": ",",
        "PERIOD": ".",
        "OROR": "||",
        "ANDAND": "&&",
    }
    if dfa_kind in sym_map:
        return Token("SYMBOL", sym_map[dfa_kind], line, col)
    return Token(dfa_kind, lexeme, line, col)


class Lexer:
    def __init__(self, source: str, *, trace_dfa: bool = False):
        raw = strip_comments(source)
        self._src = raw
        self._pos = 0
        self.line = 1
        self.col = 1
        self.trace_dfa = trace_dfa
        self.dfa_traces: List[str] = []

    def _peek(self) -> str:
        if self._pos >= len(self._src):
            return "\0"
        return self._src[self._pos]

    def _adv(self) -> str:
        c = self._src[self._pos]
        self._pos += 1
        if c == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return c

    def _skip_ws(self) -> None:
        while self._pos < len(self._src) and self._src[self._pos].isspace():
            self._adv()

    def _next_dfa(self) -> Tuple[str, str, int, int, List[str]]:
        """
        Returns (dfa_kind, lexeme, token_line, token_col, state_path).
        """
        self._skip_ws()
        token_line = self.line
        token_col = self.col
        path: List[str] = ["S0"]
        chars: List[str] = []

        def append_ch(ch: str) -> None:
            chars.append(ch)

        st = S0
        dfa_kind = ""
        lexeme = ""

        while st != S_DONE:
            c = self._peek()
            if st == S0:
                if c == "\0":
                    path.append("S1")
                    return "EOF", "EOF", token_line, token_col, path
                if (
                    c == "|"
                    and self._pos + 1 < len(self._src)
                    and self._src[self._pos + 1] == "|"
                ):
                    path.append("S||")
                    append_ch(self._adv())
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "OROR", "".join(chars), S_DONE
                    path.append("accept(||)")
                    continue
                if (
                    c == "&"
                    and self._pos + 1 < len(self._src)
                    and self._src[self._pos + 1] == "&"
                ):
                    path.append("S&&")
                    append_ch(self._adv())
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "ANDAND", "".join(chars), S_DONE
                    path.append("accept(&&)")
                    continue
                elif c.isalpha() or c == "_":
                    path.append("S2")
                    append_ch(self._adv())
                    st = S2
                elif c.isdigit():
                    path.append("S4")
                    append_ch(self._adv())
                    st = S4
                elif c == '"':
                    path.append("S40")
                    append_ch(self._adv())
                    st = S40
                elif c == "<":
                    path.append("S9")
                    append_ch(self._adv())
                    st = S9
                elif c == ">":
                    path.append("S12")
                    append_ch(self._adv())
                    st = S12
                elif c == "!":
                    path.append("S15")
                    append_ch(self._adv())
                    st = S15
                elif c == "=":
                    path.append("S18")
                    append_ch(self._adv())
                    st = S18
                elif c == "+":
                    path.append("S21")
                    append_ch(self._adv())
                    st = S21
                elif c == "-":
                    path.append("S24")
                    append_ch(self._adv())
                    st = S24
                elif c == "*":
                    path.append("S27")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "MUL", "".join(chars), S_DONE
                elif c == "/":
                    path.append("S28")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "DIV", "".join(chars), S_DONE
                elif c == "%":
                    path.append("S29")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "MOD", "".join(chars), S_DONE
                elif c == "(":
                    path.append("S30")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "LPAREN", "".join(chars), S_DONE
                elif c == ")":
                    path.append("S31")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "RPAREN", "".join(chars), S_DONE
                elif c == "{":
                    path.append("S32")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "LBRACE", "".join(chars), S_DONE
                elif c == "}":
                    path.append("S33")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "RBRACE", "".join(chars), S_DONE
                elif c == "[":
                    path.append("S34")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "LSQBRAC", "".join(chars), S_DONE
                elif c == "]":
                    path.append("S35")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "RSQBRAC", "".join(chars), S_DONE
                elif c == ";":
                    path.append("S36")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "SEMICOLON", "".join(chars), S_DONE
                elif c == ":":
                    path.append("S37")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "COLON", "".join(chars), S_DONE
                elif c == ",":
                    path.append("S38")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "COMMA", "".join(chars), S_DONE
                elif c == ".":
                    path.append("S39")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "PERIOD", "".join(chars), S_DONE
                else:
                    path.append("UNKNOWN")
                    append_ch(self._adv())
                    dfa_kind, lexeme, st = "UNKNOWN", "".join(chars), S_DONE
            elif st == S2:
                if c.isalnum() or c == "_":
                    append_ch(self._adv())
                else:
                    path.append("S3")
                    st = S3
            elif st == S3:
                lexeme = "".join(chars)
                dfa_kind = "KEYWORD" if lexeme in ANSI_C_KEYWORDS else "IDENTIFIER"
                path.append(f"accept({dfa_kind})")
                st = S_DONE
            elif st == S4:
                if c.isdigit():
                    append_ch(self._adv())
                elif c == ".":
                    path.append("S5")
                    append_ch(self._adv())
                    st = S5
                else:
                    path.append("S8")
                    st = S8
            elif st == S5:
                if c.isdigit():
                    append_ch(self._adv())
                elif c in "eE":
                    path.append("S6")
                    append_ch(self._adv())
                    st = S6
                else:
                    path.append("S7")
                    st = S7
            elif st == S6:
                if c.isdigit() or c in "+-":
                    append_ch(self._adv())
                else:
                    path.append("S7")
                    st = S7
            elif st == S7:
                lexeme = "".join(chars)
                dfa_kind = "FLOAT"
                path.append("accept(FLOAT)")
                st = S_DONE
            elif st == S8:
                lexeme = "".join(chars)
                dfa_kind = "INT"
                path.append("accept(INT)")
                st = S_DONE
            elif st == S9:
                if c == "=":
                    path.append("S10")
                    append_ch(self._adv())
                    st = S10
                else:
                    path.append("S11")
                    st = S11
            elif st == S10:
                lexeme = "".join(chars)
                dfa_kind = "LEQ"
                path.append("accept(LEQ)")
                st = S_DONE
            elif st == S11:
                lexeme = "".join(chars)
                dfa_kind = "LESS"
                path.append("accept(LESS)")
                st = S_DONE
            elif st == S12:
                if c == "=":
                    path.append("S13")
                    append_ch(self._adv())
                    st = S13
                else:
                    path.append("S14")
                    st = S14
            elif st == S13:
                lexeme = "".join(chars)
                dfa_kind = "GREQ"
                path.append("accept(GREQ)")
                st = S_DONE
            elif st == S14:
                lexeme = "".join(chars)
                dfa_kind = "GREATER"
                path.append("accept(GREATER)")
                st = S_DONE
            elif st == S15:
                if c == "=":
                    path.append("S16")
                    append_ch(self._adv())
                    st = S16
                else:
                    path.append("S17")
                    st = S17
            elif st == S16:
                lexeme = "".join(chars)
                dfa_kind = "NEQ"
                path.append("accept(NEQ)")
                st = S_DONE
            elif st == S17:
                lexeme = "".join(chars)
                dfa_kind = "NOT"
                path.append("accept(NOT)")
                st = S_DONE
            elif st == S18:
                if c == "=":
                    path.append("S19")
                    append_ch(self._adv())
                    st = S19
                else:
                    path.append("S20")
                    st = S20
            elif st == S19:
                lexeme = "".join(chars)
                dfa_kind = "EQUAL"
                path.append("accept(EQUAL)")
                st = S_DONE
            elif st == S20:
                lexeme = "".join(chars)
                dfa_kind = "ASSIGN"
                path.append("accept(ASSIGN)")
                st = S_DONE
            elif st == S21:
                if c == "+":
                    path.append("S22")
                    append_ch(self._adv())
                    st = S22
                else:
                    path.append("S23")
                    st = S23
            elif st == S22:
                lexeme = "".join(chars)
                dfa_kind = "INC"
                path.append("accept(INC)")
                st = S_DONE
            elif st == S23:
                lexeme = "".join(chars)
                dfa_kind = "ADD"
                path.append("accept(ADD)")
                st = S_DONE
            elif st == S24:
                if c == "-":
                    path.append("S25")
                    append_ch(self._adv())
                    st = S25
                else:
                    path.append("S26")
                    st = S26
            elif st == S25:
                lexeme = "".join(chars)
                dfa_kind = "DEC"
                path.append("accept(DEC)")
                st = S_DONE
            elif st == S26:
                lexeme = "".join(chars)
                dfa_kind = "SUB"
                path.append("accept(SUB)")
                st = S_DONE
            elif st == S40:
                if c == "\0":
                    lexeme = "".join(chars)
                    dfa_kind = "UNKNOWN"
                    path.append("unterminated->UNKNOWN")
                    st = S_DONE
                elif c == '"':
                    path.append("S41")
                    append_ch(self._adv())
                    st = S41
                else:
                    if c == "\\" and self._pos + 1 < len(self._src):
                        append_ch(self._adv())
                    append_ch(self._adv())
            elif st == S41:
                lexeme = "".join(chars)
                dfa_kind = "STR"
                path.append("accept(STR)")
                st = S_DONE
            else:
                lexeme = "".join(chars) if chars else ""
                dfa_kind = "UNKNOWN"
                path.append("fallback")
                st = S_DONE

        return dfa_kind, lexeme, token_line, token_col, path

    def tokenize(self) -> List[Token]:
        tokens, errors = self.tokenize_with_errors()
        if errors:
            raise LexerError("\n".join(errors))
        return tokens

    def tokenize_with_errors(self) -> Tuple[List[Token], List[str]]:
        errors: List[str] = []
        self.dfa_traces = []
        out: List[Token] = []
        while True:
            dfa_kind, lexeme, tline, tcol, path = self._next_dfa()
            if self.trace_dfa:
                self.dfa_traces.append(
                    f"Line {tline} col {tcol}:  {' -> '.join(path)}  |  {dfa_kind!r} {lexeme!r}"
                )

            if dfa_kind == "UNKNOWN":
                errors.append(
                    f"Lexical error at line {tline}, col {tcol}: unexpected token {lexeme!r}"
                )
                continue

            tok = _normalize_dfa_token(dfa_kind, lexeme, tline, tcol)
            assert tok.kind in _PIPELINE_TOKEN_KINDS, (dfa_kind, tok.kind)
            out.append(tok)
            if dfa_kind == "EOF":
                break
        return out, errors


@dataclass
class LexSymbol:
    symbol: str
    token_type: str
    data_type: str
    line: int


def _number_dtype(lex: str) -> str:
    s = lex.lower()
    if "e" in s or "." in s:
        return "float"
    return "int"


def build_lex_symbol_table(tokens: List[Token]) -> List[LexSymbol]:
    entries: Dict[str, LexSymbol] = {}
    declared_types: Dict[str, str] = {}
    i = 0
    n = len(tokens)
    type_keywords = TYPE_KEYWORDS & ANSI_C_KEYWORDS

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
                                entries[p_name] = LexSymbol(
                                    p_name, "PARAMETER", p_type, tokens[j + 1].line
                                )
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
            dtype = _number_dtype(tok.value)
            key = f"literal:{tok.value}:{tok.line}:{tok.column}"
            entries[key] = LexSymbol(tok.value, "NUMBER", dtype, tok.line)
        elif tok.kind == "STR":
            key = f"literal:{tok.value}:{tok.line}:{tok.column}"
            entries[key] = LexSymbol(tok.value, "STR", "string", tok.line)
        i += 1

    return sorted(entries.values(), key=lambda e: (e.line, e.symbol))
