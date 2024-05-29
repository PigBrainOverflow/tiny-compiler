# virtual machine
from typing import List, Any

class VirtualMachine:
    # there are only 4 states in the VM
    _stack: List[int]
    _pc: int
    _sp: int
    _fp: int
    def __init__(self, *, stack_size: int = 1024):
        self._stack = [0] * stack_size

    @staticmethod
    def is_halt(instr: Any) -> bool:
        if instr["type"] != "syscall":
            return False
        return instr["op"] == "terminate"

    @property
    def stack(self) -> List[int]:
        return self._stack[:self._sp + 1]

    ##############################
    # execute single instruction #
    ##############################

    ################
    # system call #
    ################
    def execute_syscall(self, instr: Any):
        if instr["op"] == "print":
            print(self._stack[self._sp])
            self._sp -= 1
        elif instr["op"] == "scan":
            self._sp += 1
            self._stack[self._sp] = int(input())
        elif instr["op"] == "terminate":
            pass
        self._pc += 1

    #####################
    # binary operations #
    #####################
    def execute_add(self, instr: Any):
        self._stack[self._sp - 1] += self._stack[self._sp]
        self._sp -= 1
        self._pc += 1

    def execute_sub(self, instr: Any):
        self._stack[self._sp - 1] -= self._stack[self._sp]
        self._sp -= 1
        self._pc += 1

    def execute_mul(self, instr: Any):
        self._stack[self._sp - 1] *= self._stack[self._sp]
        self._sp -= 1
        self._pc += 1

    def execute_div(self, instr: Any):
        self._stack[self._sp - 1] //= self._stack[self._sp]
        self._sp -= 1
        self._pc += 1

    def execute_mod(self, instr: Any):
        self._stack[self._sp - 1] %= self._stack[self._sp]
        self._sp -= 1
        self._pc += 1

    def execute_eq(self, instr: Any):
        self._stack[self._sp - 1] = int(self._stack[self._sp - 1] == self._stack[self._sp])
        self._sp -= 1
        self._pc += 1

    def execute_ne(self, instr: Any):
        self._stack[self._sp - 1] = int(self._stack[self._sp - 1] != self._stack[self._sp])
        self._sp -= 1
        self._pc += 1

    def execute_lt(self, instr: Any):
        self._stack[self._sp - 1] = int(self._stack[self._sp - 1] < self._stack[self._sp])
        self._sp -= 1
        self._pc += 1

    ##############
    # load/store #
    ##############
    def execute_loadi(self, instr: Any):
        self._sp += 1
        self._stack[self._sp] = instr["imm"]
        self._pc += 1

    def execute_load(self, instr: Any):
        self._sp += 1
        self._stack[self._sp] = self._stack[self._fp + instr["imm"]]
        self._pc += 1

    def execute_store(self, instr: Any):
        self._stack[self._fp + instr["imm"]] = self._stack[self._sp]
        self._sp -= 1
        self._pc += 1

    ########
    # jump #
    ########
    def execute_jmp(self, instr: Any):
        self._pc = instr["imm"]

    def execute_rjmpz(self, instr: Any):
        # relative jump if zero
        if self._stack[self._sp] == 0:
            self._pc += instr["imm"]
        else:
            self._pc += 1
        self._sp -= 1

    def execute_rjmp(self, instr: Any):
        # relative jump
        self._pc += instr["imm"]

    ###################
    # calling-related #
    ###################
    def execute_save(self, instr: Any):
        # push FP to the stack and reserve space for the return address
        self._stack[self._sp + 1] = self._fp
        self._sp += 2
        self._pc += 1

    def execute_call(self, instr: Any):
        # unlike jmp, call also saves the return address and sets FP
        self._fp = self._sp - instr["nargs"] + 1
        self._stack[self._fp - 1] = self._pc + 1
        self._pc = instr["imm"]

    def execute_ret(self, instr: Any):
        # return from a function
        self._pc = self._stack[self._fp - 1]
        self._sp = self._fp + instr["ret_size"] - 1
        self._fp = self._stack[self._fp - 2]

    def execute_push(self, instr: Any):
        self._sp += instr["imm"]
        self._pc += 1

    def execute_pop(self, instr: Any):
        self._sp -= instr["imm"]
        self._pc += 1

    def execute(self, code: List[Any]):
        self._pc, self._sp, self._fp = 0, 0, 0
        cur_instr = code[self._pc]
        while not VirtualMachine.is_halt(cur_instr):
            cur_type = cur_instr["type"]
            getattr(self, f"execute_{cur_type}")(cur_instr)
            cur_instr = code[self._pc]


if __name__ == "__main__":
    vm = VirtualMachine()
    import json
    with open("examples/sum_and_diff.json") as f:
        code = json.load(f)
    vm.execute(code)
