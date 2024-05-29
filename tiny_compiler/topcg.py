from grammar import grammar
from lark import Lark, ParseTree, Token
from typing import Dict, List, Any
import json

# Visitor Pattern
# We only need 2 visitors (other types of nodes can be easily handled by these 2 visitors):
# 1. TopVisitor: visits the global definitions
# 2. StatementsVisitor: visits the statements in the function or block


class TopVisitor:
    _DEBUG: bool
    _symbol_table: Dict[str, Any]

    def __init__(self, DEBUG: bool = True, libpath: str = "lib"):
        self._DEBUG = DEBUG
        # load all lib functions in libpath
        # function_name.json
        import os
        self._symbol_table = {}
        for f in os.listdir(libpath):
            if f.endswith(".json"):
                with open(f"{libpath}/{f}", "r") as libf:
                    self._symbol_table[f.split(".")[0]] = json.load(libf)

    def visit(self, tree: ParseTree) -> List[Any]:
        if self._DEBUG:
            print(tree.pretty())
        # visit all the global declarations
        for gd in tree.children[0].children:
            d = gd.children[0]
            if d.data == "const_def":
                self.visit_const_def(d)
            elif d.data == "func_def":
                self.visit_func_def(d)
            else:
                raise ValueError(f"Unknown global definition {d.data}")
        if self._DEBUG:
            print(self._symbol_table.keys())
        # generate code for each function
        for fd in self._symbol_table.values():
            if fd["type"] == "func" and "instructions" not in fd:
                sv = StatementsVisitor(self._symbol_table, self._DEBUG)
                for ra, param in enumerate(fd["params"]):
                    sv._symbol_table[param] = {
                        "type": "var",
                        "relative_address": ra
                    }
                sv.visit_stmts(fd["stmts"])
                fd["instructions"] = sv._instructions
        # integrate all the instructions
        if "main" not in self._symbol_table:
            raise ValueError("Main function not defined")
        # generate a prelude for the main function
        result = [
            {
                "type": "save"
            },
            {
                "type": "call",
                "imm": None,
                "nargs": 0,    # no arguments
                "func_name": "main"
            },
            {
                "type": "syscall",
                "op": "terminate"
            }
        ]
        func_entries = {}
        for func_name, fd in self._symbol_table.items():
            if fd["type"] == "func":
                func_entries[func_name] = len(result)
                result.extend(fd["instructions"])
        # fill the call imm values
        for instr in result:
            if instr["type"] == "call":
                instr["imm"] = func_entries[instr["func_name"]]
        return result

    def visit_const_def(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        name, value = tree.children
        name, value = name.value, int(value.value)
        if name in self._symbol_table:
            raise ValueError(f"Symbol {name} already defined")
        self._symbol_table[name] = {
            "type": "const",
            "value": value
        }

    def visit_func_def(self, tree: ParseTree):
        # this visit function will not handle the stmts
        # just read the declaration and store it in the symbol table
        if self._DEBUG:
            print(tree.pretty())
        name, params, ret_size, stmts = tree.children
        name, params, ret_size = name.value, self.visit_params(params), int(ret_size.value)
        if name in self._symbol_table:
            raise ValueError(f"Symbol {name} already defined")
        self._symbol_table[name] = {
            "type": "func",
            "params": params,
            "ret_size": ret_size,
            "stmts": stmts
        }

    def visit_params(self, tree: ParseTree) -> List[str]:
        if self._DEBUG:
            print(tree.pretty())
        if len(tree.children) == 0:
            return []
        return [c.value for c in tree.children]


class StatementsVisitor:
    # this visitor will handle the stmts (block)
    _DEBUG: bool
    _symbol_table: Dict[str, Any]
    _global_symbol_table: Dict[str, Any]    # contains consts and functions
    _instructions: List[Any]

    def __init__(self, global_symbol_table: Dict[str, Any], _DEBUG: bool = True):
        self._global_symbol_table = global_symbol_table
        self._DEBUG = _DEBUG
        self._symbol_table = {}
        self._instructions = []

    # automatically calling the proper visit function based on the node type
    def visit(self, tree: ParseTree):
        getattr(self, f"visit_{tree.data}")(tree)

    ##############
    # stmt types #
    ##############
    # all stmt types will directly put their instructions to the self._instructions
    def visit_stmt(self, tree: ParseTree):
        self.visit(tree.children[0])

    def visit_stmts(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        for stmt in tree.children:
            self.visit(stmt)

    def visit_var_def(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        name, value = tree.children
        name, value = name.value, int(value.value)
        if name in self._symbol_table:
            raise ValueError(f"Symbol {name} already defined")
        ra = len(self._symbol_table)    # actual address = FP + relative address
        self._symbol_table[name] = {
            "type": "var",
            "relative_address": ra
        }
        self._instructions.append(
            {
                "type": "loadi",
                "imm": value
            }
        )

    def visit_while_stmt(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        cond, stmts = tree.children
        # prepare the instructions for the condition
        start_addr = len(self._instructions)
        self._instructions.extend(self.visit_expr(cond))
        # if the condition is false, jump to the end
        self._instructions.append(
            {
                "type": "rjmpz",
                "imm": None    # will be filled later
            }
        )
        rjmpz, rjmpz_addr = self._instructions[-1], len(self._instructions)
        # prepare the instructions for the while block
        self.visit_stmts(stmts)
        # jump back to the condition
        self._instructions.append(
            {
                "type": "rjmp",
                "imm": start_addr - len(self._instructions)
            }
        )
        rjmpz["imm"] = len(self._instructions) - rjmpz_addr + 1

    def visit_ifelse_stmt(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        cond, ifstmts, elsestmts = tree.children
        # prepare the instructions for the condition
        self._instructions.extend(self.visit_expr(cond))
        # if the condition is false, jump to the else block
        self._instructions.append(
            {
                "type": "rjmpz",
                "imm": None    # will be filled later
            }
        )
        rjmpz, rjmpz_addr = self._instructions[-1], len(self._instructions)
        # prepare the instructions for the if block
        self.visit_stmts(ifstmts)
        # if the if block is executed, jump to the end
        self._instructions.append(
            {
                "type": "rjmp",
                "imm": None    # will be filled later
            }
        )
        rjmp, rjmp_addr = self._instructions[-1], len(self._instructions)
        rjmpz["imm"] = len(self._instructions) - rjmpz_addr + 1
        # prepare the instructions for the else block
        self.visit_stmts(elsestmts)
        rjmp["imm"] = len(self._instructions) - rjmp_addr + 1

    def visit_assign_stmt(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        name, expr = tree.children
        name = name.value
        if name not in self._symbol_table:
            raise ValueError(f"Symbol {name} not defined")
        self._instructions.extend(self.visit_expr(expr))    # these instructions will push the temp result to the stack
        self._instructions.append(
            {
                "type": "store",
                "imm": self._symbol_table[name]["relative_address"]
            }
        )   # store the result to the variable

    def visit_return_stmt(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        args = tree.children[0]
        # prepare the instructions for the return value
        self._instructions.extend(self.visit_args(args))
        # put the return value to the stack
        for ra in range(len(args.children) - 1, -1, -1):
            self._instructions.append(
                {
                    "type": "store",
                    "imm": ra
                }
            )
        self._instructions.append(
            {
                "type": "ret",
                "ret_size": len(args.children)
            }
        )

    def visit_call_stmt(self, tree: ParseTree):
        if self._DEBUG:
            print(tree.pretty())
        params, name, args = tree.children
        name = name.value
        if name not in self._global_symbol_table:
            raise ValueError(f"Symbol {name} not defined")
        if self._global_symbol_table[name]["type"] != "func":
            raise ValueError(f"Symbol {name} is not a function")
        # save the current PC and FP
        self._instructions.append(
            {
                "type": "save"
            }
        )
        # prepare the instructions for the arguments
        self._instructions.extend(self.visit_args(args))
        # call the function
        self._instructions.append(
            {
                "type": "call",
                "imm": None,    # will be filled later
                "nargs": len(args.children),    # number of arguments
                "func_name": name
            }
        )
        # the callee will do the recovery of PC and FP
        # store return values to params
        for c in reversed(params.children):
            self._instructions.append(
                {
                    "type": "store",
                    "imm": self._symbol_table[c.value]["relative_address"]
                }
            )
        self._instructions.append(
            {
                "type": "pop",
                "imm": 2    # pop the saved PC and FP
            }
        )

    ########
    # args #
    ########
    def visit_args(self, tree: ParseTree) -> List[Any]:
        # this will put the arguments on the stack
        if self._DEBUG:
            print(tree.pretty())
        if len(tree.children) == 0:
            return []
        return sum([self.visit_expr(c) for c in tree.children], [])

    ########
    # expr #
    ########
    def visit_expr(self, tree: ParseTree) -> List[Any]:
        if self._DEBUG:
            print(tree.pretty())
        if tree.data == "expr":
            child = tree.children[0]
            if isinstance(child, Token):
                # local variable or global constant
                if child.type == "CNAME":
                    name = child.value
                    # local variable
                    if name in self._symbol_table:
                        return [
                            {
                                "type": "load",
                                "imm": self._symbol_table[name]["relative_address"]
                            }
                        ]
                    # global constant
                    elif name in self._global_symbol_table and self._global_symbol_table[name]["type"] == "const":
                        return [
                            {
                                "type": "load",
                                "imm": self._global_symbol_table[name]["value"]
                            }
                        ]
                    else:
                        raise ValueError(f"Symbol {name} not defined")
                # integer literal
                elif child.type == "INT":
                    return [
                        {
                            "type": "loadi",
                            "imm": int(child.value)
                        }
                    ]
                else:
                    raise ValueError(f"Unknown token {child.type}")
            # binary operation in parentheses
            else:   # child is a tree
                return self.visit_expr(child)
        # binary operation
        else:
            operand1, operand2 = tree.children
            return self.visit_expr(operand1) + self.visit_expr(operand2) + [
                {
                    "type": tree.data,
                }
            ]


class TopCodeGenerator:
    _grammar: str

    def __init__(self):
        self._grammar = grammar

    def compile(self, source: str) -> List[Any]:
        parser = Lark(self._grammar, parser = "lalr")
        tree = parser.parse(source)
        return TopVisitor().visit(tree)


if __name__ == "__main__":
    with open("examples/sum.txt", "r") as f:
        source = f.read()
    with open("examples/sum.json", "w") as f:
        f.write(json.dumps(TopCodeGenerator().compile(source), indent = 4))