grammar = """
start: global_defs
global_defs: global_def+
global_def: const_def
          | func_def
const_def: "const" CNAME "=" INT ";"
func_def: "func" CNAME "(" params ")" "->" INT "{" stmts "}"
var_def: "var" CNAME "=" INT ";"
params: "void"
      | CNAME ("," CNAME)*

stmts: stmt*
stmt: assign_stmt
    | ifelse_stmt
    | while_stmt
    | call_stmt
    | return_stmt
    | var_def

args: "void"
    | expr ("," expr)*
assign_stmt: CNAME "=" expr ";"
ifelse_stmt: "if" "(" expr ")" "{" stmts "}" "else" "{" stmts "}"
while_stmt: "while" "(" expr ")" "{" stmts "}"
call_stmt: "(" params ")" "<-" CNAME "(" args ")" ";"
return_stmt: "return" "(" args ")" ";"

expr: "(" expr ")"
    | expr "*" expr  -> mul
    | expr "/" expr  -> div
    | expr "%" expr  -> mod
    | expr "+" expr  -> add
    | expr "-" expr  -> sub
    | expr "==" expr  -> eq
    | expr "!=" expr  -> ne
    | expr "<" expr  -> lt
    | CNAME
    | INT

%import common.INT
%import common.CNAME
%import common.WS
%ignore WS
%import common.CPP_COMMENT
%ignore CPP_COMMENT
"""
