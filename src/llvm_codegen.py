import re
from typing import Dict, List, Set

from ir import Instr


class LLVMCodeGen:
    def __init__(self):
        self.lines: List[str] = []
        self.reg = 0
        self.pending_args: List[str] = []
        self.scalar_vars: Set[str] = set()
        self.array_vars: Set[str] = set()
        self.func_name = ""
        self.current_params: List[str] = []
        self.param_ptrs: Dict[str, str] = {}

    def new_reg(self) -> str:
        self.reg += 1
        return f"%r{self.reg}"

    @staticmethod
    def is_number(x: str) -> bool:
        if x is None:
            return False
        return bool(re.fullmatch(r"-?\d+(\.\d+)?", x))

    @staticmethod
    def is_temp_or_var(x: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x))

    def to_i32(self, operand: str) -> str:
        if self.is_number(operand):
            if "." in operand:
                return str(int(float(operand)))
            return operand
        reg = self.new_reg()
        self.lines.append(f"  {reg} = load i32, ptr {self.ptr_name(operand)}")
        return reg

    def ptr_name(self, name: str) -> str:
        return self.param_ptrs.get(name, f"%{name}")

    def collect_symbols(self, body: List[Instr]):
        self.scalar_vars.clear()
        self.array_vars.clear()
        for ins in body:
            if ins.op == "LABEL":
                continue
            if ins.op == "GOTO":
                continue
            if ins.op == "IFZ":
                if ins.a1 and self.is_temp_or_var(ins.a1):
                    self.scalar_vars.add(ins.a1)
                continue
            if ins.op == "CALL":
                if ins.res and self.is_temp_or_var(ins.res):
                    self.scalar_vars.add(ins.res)
                continue
            vars_to_check = (ins.a1, ins.a2, ins.res)
            for v in vars_to_check:
                if v and self.is_temp_or_var(v):
                    self.scalar_vars.add(v)
            if ins.op == "LOADARR" and ins.a1:
                self.array_vars.add(ins.a1)
            if ins.op == "STOREARR" and ins.res:
                self.array_vars.add(ins.res)
        self.scalar_vars -= self.array_vars

    def emit_allocas(self):
        self.param_ptrs = {}
        for p in self.current_params:
            ptr = f"%{p}.addr"
            self.param_ptrs[p] = ptr
            self.lines.append(f"  {ptr} = alloca i32")
            self.lines.append(f"  store i32 %{p}, ptr {ptr}")

        for v in sorted(self.scalar_vars):
            if v in self.current_params:
                continue
            self.lines.append(f"  %{v} = alloca i32")
            self.lines.append(f"  store i32 0, ptr %{v}")
        for a in sorted(self.array_vars):
            self.lines.append(f"  %{a} = alloca [256 x i32]")
            self.lines.append(f"  %_{a}_base = getelementptr inbounds [256 x i32], ptr %{a}, i32 0, i32 0")

    def emit_binary(self, ins: Instr):
        l = self.to_i32(ins.a1)
        r = self.to_i32(ins.a2)
        out = self.new_reg()
        if ins.op == "+":
            self.lines.append(f"  {out} = add nsw i32 {l}, {r}")
        elif ins.op == "-":
            self.lines.append(f"  {out} = sub nsw i32 {l}, {r}")
        elif ins.op == "*":
            self.lines.append(f"  {out} = mul nsw i32 {l}, {r}")
        elif ins.op == "/":
            self.lines.append(f"  {out} = sdiv i32 {l}, {r}")
        elif ins.op == "%":
            self.lines.append(f"  {out} = srem i32 {l}, {r}")
        elif ins.op in ("<", ">", "<=", ">=", "==", "!="):
            pred = {
                "<": "slt",
                ">": "sgt",
                "<=": "sle",
                ">=": "sge",
                "==": "eq",
                "!=": "ne",
            }[ins.op]
            b = self.new_reg()
            self.lines.append(f"  {b} = icmp {pred} i32 {l}, {r}")
            self.lines.append(f"  {out} = zext i1 {b} to i32")
        elif ins.op in ("&&", "||"):
            l1 = self.new_reg()
            r1 = self.new_reg()
            self.lines.append(f"  {l1} = icmp ne i32 {l}, 0")
            self.lines.append(f"  {r1} = icmp ne i32 {r}, 0")
            b = self.new_reg()
            bop = "and" if ins.op == "&&" else "or"
            self.lines.append(f"  {b} = {bop} i1 {l1}, {r1}")
            self.lines.append(f"  {out} = zext i1 {b} to i32")
        self.lines.append(f"  store i32 {out}, ptr {self.ptr_name(ins.res)}")

    def emit_instruction(self, ins: Instr):
        if ins.op == "LABEL":
            self.lines.append(f"{ins.a1}:")
            return

        if ins.op == "MOV":
            src = self.to_i32(ins.a1)
            self.lines.append(f"  store i32 {src}, ptr {self.ptr_name(ins.res)}")
            return

        if ins.op in {"+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!=", "&&", "||"}:
            self.emit_binary(ins)
            return

        if ins.op == "U-":
            v = self.to_i32(ins.a1)
            out = self.new_reg()
            self.lines.append(f"  {out} = sub nsw i32 0, {v}")
            self.lines.append(f"  store i32 {out}, ptr {self.ptr_name(ins.res)}")
            return

        if ins.op == "U!":
            v = self.to_i32(ins.a1)
            b = self.new_reg()
            out = self.new_reg()
            self.lines.append(f"  {b} = icmp eq i32 {v}, 0")
            self.lines.append(f"  {out} = zext i1 {b} to i32")
            self.lines.append(f"  store i32 {out}, ptr {self.ptr_name(ins.res)}")
            return

        if ins.op == "IFZ":
            c = self.to_i32(ins.a1)
            b = self.new_reg()
            cont = self.new_reg().replace("%", "bb")
            self.lines.append(f"  {b} = icmp eq i32 {c}, 0")
            self.lines.append(f"  br i1 {b}, label %{ins.res}, label %{cont}")
            self.lines.append(f"{cont}:")
            return

        if ins.op == "GOTO":
            self.lines.append(f"  br label %{ins.res}")
            return

        if ins.op == "ARG":
            self.pending_args.append(self.to_i32(ins.a1))
            return

        if ins.op == "CALL":
            args = ", ".join(f"i32 {a}" for a in self.pending_args)
            out = self.new_reg()
            self.lines.append(f"  {out} = call i32 @{ins.a1}({args})")
            self.lines.append(f"  store i32 {out}, ptr {self.ptr_name(ins.res)}")
            self.pending_args.clear()
            return

        if ins.op == "RET":
            if ins.a1 is None:
                self.lines.append("  ret i32 0")
            else:
                v = self.to_i32(ins.a1)
                self.lines.append(f"  ret i32 {v}")
            return

        if ins.op == "LOADARR":
            idx = self.to_i32(ins.a2)
            gep = self.new_reg()
            val = self.new_reg()
            self.lines.append(f"  {gep} = getelementptr inbounds i32, ptr %_{ins.a1}_base, i32 {idx}")
            self.lines.append(f"  {val} = load i32, ptr {gep}")
            self.lines.append(f"  store i32 {val}, ptr {self.ptr_name(ins.res)}")
            return

        if ins.op == "STOREARR":
            val = self.to_i32(ins.a1)
            idx = self.to_i32(ins.a2)
            gep = self.new_reg()
            self.lines.append(f"  {gep} = getelementptr inbounds i32, ptr %_{ins.res}_base, i32 {idx}")
            self.lines.append(f"  store i32 {val}, ptr {gep}")

    def emit_function(self, name: str, body: List[Instr], params: List[str]):
        self.current_params = params
        params_sig = ", ".join(f"i32 %{p}" for p in params)
        self.lines.append(f"define i32 @{name}({params_sig}) {{")
        self.lines.append("entry:")
        self.collect_symbols(body)
        self.emit_allocas()
        self.pending_args.clear()

        for ins in body:
            self.emit_instruction(ins)

        if not any(x.op == "RET" for x in body):
            self.lines.append("  ret i32 0")
        self.lines.append("}")
        self.lines.append("")

    def generate(self, code: List[Instr], function_params: Dict[str, List[str]]) -> List[str]:
        self.lines = [
            "; ModuleID = 'mini_c_subset'",
            "source_filename = \"mini_c_subset\"",
            "",
        ]
        i = 0
        while i < len(code):
            ins = code[i]
            if ins.op == "FUNC":
                name = ins.a1
                j = i + 1
                body: List[Instr] = []
                while j < len(code) and not (code[j].op == "END_FUNC" and code[j].a1 == name):
                    body.append(code[j])
                    j += 1
                self.emit_function(name, body, function_params.get(name, []))
                i = j + 1
            else:
                i += 1
        return self.lines
