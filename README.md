# Mini C Subset Compiler (Python)

This project implements a modular compiler for a well-defined subset of the C language and prints the output of each compiler phase:

1. Lexical analysis (token stream)
2. Syntax analysis (AST)
3. Semantic analysis (type checks and scope trace)
4. Intermediate representation (Three Address Code)
5. Optimization (constant folding + basic dead code elimination)
6. Target code generation (pseudo assembly)
7. LLVM IR generation (textual `.ll`)

## How to Run

### Prerequisites
- Python 3.10+ (works with standard library only)

### Run all phases
```powershell
python src/main.py examples/demo.c
```

### Emit LLVM IR in console
```powershell
python src/main.py examples/demo.c --emit-llvm
```

### Emit LLVM IR and write to file
```powershell
python src/main.py examples/demo.c --emit-llvm --llvm-out out.ll
```

### Build native executable from LLVM IR
```powershell
python src/main.py examples/demo.c --build-native --native-out out.exe
```

### Build and run native executable
```powershell
python src/main.py examples/demo.c --build-native --run-native --native-out out.exe
```

### Execute LLVM IR directly with `lli` (no `.exe` build)
```powershell
python src/main.py examples/demo.c --run-lli
```

### Stop at a specific phase
```powershell
python src/main.py examples/demo.c --phase lex
python src/main.py examples/demo.c --phase parse
python src/main.py examples/demo.c --phase semantic
python src/main.py examples/demo.c --phase ir
python src/main.py examples/demo.c --phase opt
```

## Supported C Subset

- Data types: `int`, `float`, `void`
- Declarations: global/local variables, arrays, functions
- Expressions:
  - Arithmetic: `+ - * / %`
  - Relational: `< > <= >= == !=`
  - Logical: `&& || !`
  - Assignment: `=`
- Statements:
  - Block `{ ... }`
  - `if`, `if-else`
  - `while`
  - `for`
  - `return`
  - Function calls
- Scope management:
  - Global scope
  - Function scope
  - Nested block scopes

## Project Structure

```text
src/
  ast_nodes.py
  ast_printer.py
  codegen.py
  ir.py
  lexer.py
  llvm_codegen.py
  main.py
  optimizer.py
  parser.py
  semantic.py
  tokens.py
examples/
  demo.c
tests/
  bad_semantic.c
PROJECT_REPORT.md
README.md
```

## Quick Test Cases

1. Full feature demo:
```powershell
python src/main.py examples/demo.c
```

2. Semantic error (undeclared variable `y`):
```powershell
python src/main.py tests/bad_semantic.c
```

## Notes

- Target output is pseudo assembly for instructional demonstration.
- LLVM backend now emits textual LLVM IR (`.ll`) from optimized TAC.
- Current LLVM backend models all values as `i32` for educational simplicity.
- Native build uses `clang` from LLVM toolchain and requires it on PATH.
- Direct LLVM execution uses `lli` from LLVM toolchain and requires it on PATH.
- Windows install example: `winget install LLVM.LLVM`
