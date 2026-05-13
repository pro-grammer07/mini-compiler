# C-Subset Compiler — Spring 2026
**Compiler Construction Project**

## Overview
A complete, end-to-end compiler for a well-defined subset of C, implemented in Python.
Writing the compiler in Python satisfies the **"source language other than C"** bonus criterion.

## Features
| Phase | Module | Status |
|-------|--------|--------|
| Lexical Analysis (Tokenizer) | `src/lexer.py` | ✅ Complete |
| Syntax Analysis (Parser) | `src/parser.py` | ✅ Complete |
| Semantic Analysis | `src/semantic.py` | ✅ Complete |
| TAC IR Generation | `src/tac_generator.py` | ✅ Complete |
| Optimization | `src/optimizer.py` | ✅ Complete |
| x86-64 Code Generation | `src/codegen.py` | ✅ Complete |
| Array Support | lexer/parser/semantic/tac | ✅ Complete |

## Supported C Subset
```
- Data types:       int, float, char, void
- Variables:        local, global, arrays (int arr[N])
- Operators:        arithmetic (+,-,*,/,%), relational (==,!=,<,<=,>,>=),
                    logical (&&,||,!), assignment (=,+=,-=,*=,/=), ++/--
- Control flow:     if/else (nested), while, for
- Functions:        definition, calls, recursion, parameters, return
- Scope:            global scope + local scope per function
- Comments:         // and /* */
```

## Optimizations
1. **Constant Folding** — `3 * 4 + 2` → `14` at compile time
2. **Algebraic Simplification** — `x * 1` → `x`, `x + 0` → `x`, `x * 0` → `0`
3. **Copy Propagation** — replaces copies with their source values
4. **Dead Code Elimination** — removes temporaries that are never used
5. **Unreachable Code Removal** — strips instructions after unconditional jumps

## Project Structure
```
compiler/
├── src/
│   ├── compiler.py        ← Main driver (entry point)
│   ├── lexer.py           ← Lexical analyzer (DFA tokenizer)
│   ├── parser.py          ← Recursive-descent parser
│   ├── ast_nodes.py       ← AST node definitions
│   ├── semantic.py        ← Semantic analyzer + symbol table
│   ├── tac_generator.py   ← TAC IR generator
│   ├── optimizer.py       ← Optimization passes
│   └── codegen.py         ← x86-64 assembly code generator
├── tests/
│   ├── test1_basic.c      ← Functions, recursion, arithmetic
│   ├── test2_arrays.c     ← Arrays, while, for loops
│   ├── test3_control.c    ← if/else, logical ops, nested control flow
│   ├── test4_errors.c     ← Semantic error detection
│   └── test5_optimize.c   ← Optimization showcase
├── run_tests.py           ← Automated test runner
└── README.md
```

## Requirements
- Python 3.8+ (no external dependencies)
- GCC (for assembling and linking the generated .s file)

## Usage

### Basic compilation
```bash
python3 src/compiler.py tests/test1_basic.c
# Output: tests/test1_basic.s  (x86-64 assembly)
```

### Show all compiler phases
```bash
python3 src/compiler.py tests/test5_optimize.c --all
```

### Show specific phases
```bash
python3 src/compiler.py myfile.c --tokens    # token stream
python3 src/compiler.py myfile.c --ast       # abstract syntax tree
python3 src/compiler.py myfile.c --symtab    # symbol table
python3 src/compiler.py myfile.c --tac       # raw TAC IR
python3 src/compiler.py myfile.c --opt-tac   # optimized TAC IR
python3 src/compiler.py myfile.c --asm       # x86-64 assembly
```

### Disable optimizations
```bash
python3 src/compiler.py myfile.c --no-opt
```

### Specify output file
```bash
python3 src/compiler.py myfile.c -o output.s
```

### Assemble and run (Linux x86-64)
```bash
python3 src/compiler.py myfile.c -o prog.s
gcc -o prog prog.s
./prog
```

### Run all tests
```bash
python3 run_tests.py
```

## Example — Constant Folding

Input:
```c
int main() {
    int f = (2 + 3) * (10 - 4);   // = 30
    int g = (5 > 3);               // = 1
    int i = f * 1;                 // simplify to f
    return f;
}
```

Raw TAC (before optimization):
```
  t1 = 2 + 3
  t2 = 10 - 4
  t3 = t1 * t2
  f = t3
  t4 = 5 > 3
  g = t4
  t5 = f * 1
  i = t5
  return f
```

Optimized TAC (after all passes):
```
  t3 = 30
  f = t3
  g = 1
  i = f
  return t3
```

## Grammar (BNF)
```
program    := (func_def | global_decl)*
func_def   := type IDENT '(' param_list ')' block
global_decl:= type IDENT ('[' INT ']')? ('=' expr)? ';'
param_list := (param (',' param)*)?
param      := type IDENT ('[' ']')?
block      := '{' stmt* '}'
stmt       := var_decl | if_stmt | while_stmt | for_stmt
            | return_stmt | block | expr_stmt
var_decl   := type IDENT ('[' INT ']')? ('=' expr)? ';'
if_stmt    := 'if' '(' expr ')' stmt ('else' stmt)?
while_stmt := 'while' '(' expr ')' stmt
for_stmt   := 'for' '(' for_init ';' expr? ';' expr? ')' stmt
return_stmt:= 'return' expr? ';'
expr       := assignment
assignment := or_expr (assign_op assignment)?
or_expr    := and_expr ('||' and_expr)*
and_expr   := eq_expr ('&&' eq_expr)*
eq_expr    := rel_expr (('=='|'!=') rel_expr)*
rel_expr   := add_expr (('<'|'<='|'>'|'>=') add_expr)*
add_expr   := mul_expr (('+' | '-') mul_expr)*
mul_expr   := unary (('*'|'/'|'%') unary)*
unary      := ('!'|'-'|'++'|'--') unary | postfix
postfix    := primary ('++'|'--')?
primary    := INT | FLOAT | CHAR | STRING | IDENT '(' args ')' 
            | IDENT '[' expr ']' | IDENT | '(' expr ')'
```

## Limitations & Future Work
- No struct/union support
- No pointer arithmetic
- No type casting
- No standard library linking (beyond extern declarations)
- Register allocator uses simple spill-everything strategy
- LLVM IR backend could be added for full optimization pipeline
