import argparse
import shutil
import subprocess
from pathlib import Path

from ast_printer import dump
from codegen import TargetCodeGen
from ir import IRGenerator
from lexer import Lexer, LexerError, build_lex_symbol_table
from llvm_codegen import LLVMCodeGen
from optimizer import optimize
from parser import Parser, ParserError
from semantic import SemanticAnalyzer, SemanticError


GRAMMAR_SPEC = """program      := { decl } EOF ;
decl         := type ID ( func_decl | var_decl ) ;
func_decl    := "(" [ params ] ")" block ;
var_decl     := [ "[" NUMBER "]" ] ";" ;
params       := "void" | param { "," param } ;
param        := type ID [ "[" "]" ] ;
type         := "int" | "float" | "void" ;

block        := "{" { local_decl | stmt } "}" ;
local_decl   := type ID [ "[" NUMBER "]" ] ";" ;

stmt         := block
              | "if" "(" expr ")" stmt [ "else" stmt ]
              | "while" "(" expr ")" stmt
              | "for" "(" [expr] ";" [expr] ";" [expr] ")" stmt
              | "return" [expr] ";"
              | [expr] ";" ;

expr         := assign ;
assign       := logical_or [ "=" assign ] ;
logical_or   := logical_and { "||" logical_and } ;
logical_and  := equality { "&&" equality } ;
equality     := rel { ("==" | "!=") rel } ;
rel          := add { ("<" | ">" | "<=" | ">=") add } ;
add          := mul { ("+" | "-") mul } ;
mul          := unary { ("*" | "/" | "%") unary } ;
unary        := ("!" | "-") unary | primary ;
primary      := NUMBER
              | ID
              | ID "(" [ args ] ")"
              | ID "[" expr "]"
              | "(" expr ")" ;
args         := expr { "," expr } ;"""


def build_native_from_llvm(llvm_file: str, native_out: str, run_native: bool):
    clang = shutil.which("clang")
    if not clang:
        raise RuntimeError(
            "clang not found on PATH. Install LLVM/Clang and re-run.\n"
            "Windows (winget): winget install LLVM.LLVM"
        )

    print(f"\n=== NATIVE BUILD (CLANG) ===")
    cmd = [clang, llvm_file, "-o", native_out]
    print("Command:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Native build failed.\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    print(f"Native executable generated: {native_out}")

    if run_native:
        print("\n=== RUN NATIVE EXECUTABLE ===")
        run_cmd = [native_out]
        print("Command:", " ".join(run_cmd))
        run_proc = subprocess.run(run_cmd, capture_output=True, text=True)
        print(f"Exit code: {run_proc.returncode}")
        if run_proc.stdout:
            print("stdout:")
            print(run_proc.stdout)
        if run_proc.stderr:
            print("stderr:")
            print(run_proc.stderr)


def run_lli(llvm_file: str):
    lli = shutil.which("lli")
    if not lli:
        raise RuntimeError(
            "lli not found on PATH. Install LLVM tools and re-run.\n"
            "Windows (winget): winget install LLVM.LLVM"
        )

    print("\n=== RUN LLVM IR (LLI) ===")
    cmd = [lli, llvm_file]
    print("Command:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Exit code: {proc.returncode}")
    if proc.stdout:
        print("stdout:")
        print(proc.stdout)
    if proc.stderr:
        print("stderr:")
        print(proc.stderr)


def compile_source(source: str, phase: str, emit_llvm: bool = False, llvm_out: str = "") -> bool:
    has_errors = False
    print("=== SOURCE CODE ===")
    print(source)

    lexer = Lexer(source)
    tokens, lex_errors = lexer.tokenize_with_errors()
    print("\n=== LEXICAL ANALYSIS (TOKENS) ===")
    print(f"{'LINE':<6} {'TYPE':<12} {'LEXEME':<18}")
    print("-" * 38)
    for t in tokens:
        print(f"{t.line:<6} {t.kind:<12} {t.value:<18}")

    lex_symbols = build_lex_symbol_table(tokens)
    print("\n=== LEXICAL SYMBOL TABLE ===")
    print(f"{'SYMBOL':<16} {'TOKEN TYPE':<12} {'DATA TYPE':<10} {'LINE':<6}")
    print("-" * 52)
    for s in lex_symbols:
        print(f"{s.symbol:<16} {s.token_type:<12} {s.data_type:<10} {s.line:<6}")
    if lex_errors:
        has_errors = True
        print("\n=== LEXICAL ERRORS ===")
        for e in lex_errors:
            print(e)
    if phase == "lex":
        return has_errors

    parser = Parser(tokens)
    ast = parser.parse()
    print("\n=== PARSER GRAMMAR SPECIFICATION (EBNF) ===")
    print(GRAMMAR_SPEC)
    print("\n=== SYNTAX ANALYSIS (AST) ===")
    print(dump(ast))
    if parser.errors:
        has_errors = True
        print("\n=== SYNTAX ERRORS ===")
        for e in parser.errors:
            print(e)
    if phase == "parse":
        return has_errors

    sema = SemanticAnalyzer()
    scope_trace = sema.analyze(ast)
    print("\n=== SEMANTIC ANALYSIS (TYPE/SCOPE TRACE) ===")
    for line in scope_trace:
        print(line)
    if sema.errors:
        has_errors = True
        print("\n=== SEMANTIC ERRORS ===")
        for e in sema.errors:
            print(e)
    if phase == "semantic":
        return has_errors

    if lex_errors or parser.errors or sema.errors:
        print("\nSkipping IR/code generation due to previous errors.")
        return True

    irgen = IRGenerator()
    ir = irgen.generate(ast)
    print("\n=== INTERMEDIATE REPRESENTATION (3AC) ===")
    for i, ins in enumerate(ir):
        print(f"{i:03d}: {ins}")
    if phase == "ir":
        return

    opt = optimize(ir)
    print("\n=== OPTIMIZED IR ===")
    for i, ins in enumerate(opt):
        print(f"{i:03d}: {ins}")
    if phase == "opt":
        return

    target = TargetCodeGen().generate(opt)
    print("\n=== TARGET CODE (PSEUDO ASSEMBLY) ===")
    for line in target:
        print(line)

    if emit_llvm:
        function_params = {}
        for d in ast.decls:
            if hasattr(d, "params") and hasattr(d, "name"):
                function_params[d.name] = [p.name for p in d.params]
        llvm = LLVMCodeGen().generate(opt, function_params)
        print("\n=== LLVM IR (TEXT) ===")
        for line in llvm:
            print(line)
        if llvm_out:
            Path(llvm_out).write_text("\n".join(llvm), encoding="utf-8")
            print(f"\nLLVM IR written to: {llvm_out}")
    return has_errors


def main():
    argp = argparse.ArgumentParser(description="Mini C Subset Compiler")
    argp.add_argument("file", help="Input C-like source file")
    argp.add_argument(
        "--phase",
        default="all",
        choices=["all", "lex", "parse", "semantic", "ir", "opt"],
        help="Stop after selected phase",
    )
    argp.add_argument(
        "--emit-llvm",
        action="store_true",
        help="Emit textual LLVM IR after target code",
    )
    argp.add_argument(
        "--llvm-out",
        default="",
        help="Optional output path for emitted .ll file",
    )
    argp.add_argument(
        "--build-native",
        action="store_true",
        help="Compile emitted LLVM IR to native executable using clang",
    )
    argp.add_argument(
        "--run-native",
        action="store_true",
        help="Run native executable after successful build (requires --build-native)",
    )
    argp.add_argument(
        "--native-out",
        default="out.exe",
        help="Output path for native executable (default: out.exe)",
    )
    argp.add_argument(
        "--run-lli",
        action="store_true",
        help="Execute emitted LLVM IR directly with lli",
    )
    args = argp.parse_args()

    source = Path(args.file).read_text(encoding="utf-8")
    try:
        if args.run_native and not args.build_native:
            raise RuntimeError("--run-native requires --build-native")

        ll_path = args.llvm_out or "out.ll"
        should_emit_llvm = args.emit_llvm or args.build_native or args.run_lli
        has_errors = compile_source(source, args.phase, emit_llvm=should_emit_llvm, llvm_out=ll_path)

        if has_errors:
            print("\nCompilation finished with errors.")
            raise SystemExit(1)

        if args.build_native:
            build_native_from_llvm(ll_path, args.native_out, args.run_native)
        if args.run_lli:
            run_lli(ll_path)

        print("\nCompilation pipeline finished successfully.")
    except (LexerError, ParserError, SemanticError, RuntimeError) as e:
        print(f"\nCompiler error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
