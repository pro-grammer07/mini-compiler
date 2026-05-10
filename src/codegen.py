from ir import Instr


class TargetCodeGen:
    def generate(self, code):
        asm = []
        for i in code:
            if i.op == "FUNC":
                asm.append(f"\nFUNC {i.a1}:")
            elif i.op == "END_FUNC":
                asm.append(f"END {i.a1}")
            elif i.op == "LABEL":
                asm.append(f"{i.a1}:")
            elif i.op == "GOTO":
                asm.append(f"  JMP {i.res}")
            elif i.op == "IFZ":
                asm.append(f"  JZ {i.a1}, {i.res}")
            elif i.op == "MOV":
                asm.append(f"  MOV {i.res}, {i.a1}")
            elif i.op in {"+", "-", "*", "/", "%"}:
                asm.append(f"  {self.map_op(i.op)} {i.res}, {i.a1}, {i.a2}")
            elif i.op in {"<", ">", "<=", ">=", "==", "!="}:
                asm.append(f"  CMP_{self.map_rel(i.op)} {i.res}, {i.a1}, {i.a2}")
            elif i.op in {"&&", "||"}:
                asm.append(f"  LOG_{'AND' if i.op == '&&' else 'OR'} {i.res}, {i.a1}, {i.a2}")
            elif i.op == "U-":
                asm.append(f"  NEG {i.res}, {i.a1}")
            elif i.op == "U!":
                asm.append(f"  NOT {i.res}, {i.a1}")
            elif i.op == "ARG":
                asm.append(f"  PUSH {i.a1}")
            elif i.op == "CALL":
                asm.append(f"  CALL {i.a1}, {i.a2} -> {i.res}")
            elif i.op == "RET":
                asm.append(f"  RET {i.a1 or ''}".rstrip())
            elif i.op == "LOADARR":
                asm.append(f"  LOAD {i.res}, {i.a1}[{i.a2}]")
            elif i.op == "STOREARR":
                asm.append(f"  STORE {i.res}[{i.a2}], {i.a1}")
            else:
                asm.append(f"  ; unsupported {i}")
        return asm

    @staticmethod
    def map_op(op: str) -> str:
        return {
            "+": "ADD",
            "-": "SUB",
            "*": "MUL",
            "/": "DIV",
            "%": "MOD",
        }[op]

    @staticmethod
    def map_rel(op: str) -> str:
        return {
            "<": "LT",
            ">": "GT",
            "<=": "LE",
            ">=": "GE",
            "==": "EQ",
            "!=": "NE",
        }[op]
