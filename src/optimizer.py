from ir import Instr


def is_num(x: str) -> bool:
    if x is None:
        return False
    try:
        float(x)
        return True
    except ValueError:
        return False


def fold_constants(code):
    out = []
    for ins in code:
        if ins.op in {"+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!=", "&&", "||"}:
            if is_num(ins.a1) and is_num(ins.a2):
                a = float(ins.a1)
                b = float(ins.a2)
                if ins.op == "+":
                    v = a + b
                elif ins.op == "-":
                    v = a - b
                elif ins.op == "*":
                    v = a * b
                elif ins.op == "/":
                    v = a / b
                elif ins.op == "%":
                    v = int(a) % int(b)
                elif ins.op == "<":
                    v = 1 if a < b else 0
                elif ins.op == ">":
                    v = 1 if a > b else 0
                elif ins.op == "<=":
                    v = 1 if a <= b else 0
                elif ins.op == ">=":
                    v = 1 if a >= b else 0
                elif ins.op == "==":
                    v = 1 if a == b else 0
                elif ins.op == "!=":
                    v = 1 if a != b else 0
                elif ins.op == "&&":
                    v = 1 if (a != 0 and b != 0) else 0
                else:
                    v = 1 if (a != 0 or b != 0) else 0
                out.append(Instr("MOV", str(int(v) if float(v).is_integer() else v), None, ins.res))
                continue
        out.append(ins)
    return out


def dead_code_elim(code):
    out = []
    skip = False
    for ins in code:
        if ins.op == "GOTO":
            out.append(ins)
            skip = True
            continue
        if ins.op == "LABEL":
            skip = False
            out.append(ins)
            continue
        if not skip:
            out.append(ins)
    return out


def optimize(code):
    after_fold = fold_constants(code)
    after_dce = dead_code_elim(after_fold)
    return after_dce
