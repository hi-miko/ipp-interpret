import getopt
import sys
from collections import OrderedDict
import xml.etree.ElementTree as et
from typing import NoReturn, Any

VERSION = 0.3

errlist = {
    10: "missing script parameter or use of a prohibited parameter combination",
    11: "error opening input files",
    12: "error opening output files for writing",
    31: "incorrect XML format in the input file",
    32: "unexpected XML structure",
    52: "error in semantic checks of input code in IPPcode23",
    53: "interpretation runtime error – incorrect operand types;",
    54: "interpretation runtime error – accessing a non-existing variable",
    55: "interpretation runtime error – non-existing frame",
    56: "interpretation runtime error – missing value",
    57: "interpretation runtime error – incorrect operand value",
    58: "interpretation runtime error – incorrect string manipulation.",
    99: "internal error"
}

usage_dialog = """
Usage:
    python interpret.py --source=file
    python interpret.py --input=file
    python interpret.py --source=file1 --input=file2
    python interpret.py --help
    python interpret.py --version

Flags:
    '--source' -> Input file with XML representation of the source code
    '--input' -> File with inputs for the interpretation of the given source code
    '--help' -> Displays this help dialog
    '--version' -> Displays the version of this source code

Specifications:
    - If either the 'source file' or the 'input file' is not specified then the not specified file will be read from stdin
"""

##< Function to print out the error message given an error code
# @param errcode the given error code
# @param fname optional argument to print where the error code happened
def error(errcode: int, fname: str = "", addendum: str = "") -> NoReturn:
    global errlist
    if fname != "":
        print(f"in function '{fname}'", file=sys.stderr)

    if addendum != "":
        print(f"{addendum}", file=sys.stderr)

    print(f"Error code {errcode}: {errlist[errcode]}", file=sys.stderr)

    sys.exit(errcode)

class Instruction:
    valid_types = ["var", "string", "type", "label", "int", "bool", "nil"]

    def syntax_checks(self, instruction: et.Element):
        if instruction.tag != "instruction":
            error(32)

        valid_keys = instruction.attrib.keys()
        if len(valid_keys) != 2:
            error(32)

        if ("order" not in valid_keys) or ("opcode" not in valid_keys):
            error(32)

        arg_count = len(instruction)
        for arg in instruction:
            if arg.tag != f"arg{arg_count}":
                error(32)

            arg_count -= 1
            if "type" not in arg.attrib.keys():
                error(32)

            if arg.attrib["type"] not in self.valid_types:
                error(32)

    def create_dependencies(self, instruction: et.Element):
        self.arg_list = []
        self.dependencies = []

        for arg in instruction:
            text = arg.text
            attype = arg.attrib["type"]
            if text == "":
                error(99, addendum="expected argument at instruction")
            
            if attype == "var":
                self.dependencies.append(text)
                self.arg_list.append((text, attype))
            elif attype == "type":
                self.arg_list.append((text, attype))
            elif attype == "label":
                self.dependencies.append(text)
                self.arg_list.append((text, attype))
            else:
                self.arg_list.append((text, attype))

    def __init__(self, instruction: et.Element):
        self.syntax_checks(instruction)
        self.create_dependencies(instruction)
        self.opcode = instruction.attrib["opcode"]

    def print_instruction_info(self) -> None:
        print(f"opcode: {self.opcode}")
        print("Dependencies: ", end="")
        for dependency in self.dependencies:
            print(dependency, end=", ")
        print()
        print("instruction list: ", end="")
        for literal in self.arg_list:
            print(literal, end=", ")
        print("\n")

# a class that implements a dispatch table
class Operations:
    def frame_exists(self, frame: str) -> None:
        if frame == "GF":
            return
        if frame == "TF":
            if self.temporary_frame is None:
                error(55)
        elif frame == "LF":
            local_frame = self.local_frame_stack.get_top()
            if local_frame is None:
                error(55)
        else:
            error(31, "frame_exists")

    def dependency_check(self, instruction: Instruction) -> None:
        for dp in instruction.dependencies:
            frame, name = dp.split("@")
            if frame == "GF":
                if name not in self.global_frame.keys():
                    error(54)
            elif frame == "TF":
                self.frame_exists("TF")
                if name not in self.temporary_frame.keys():
                    error(54)
            elif frame == "LF":
                self.frame_exists("LF")
                if name not in self.local_frame_stack.get_top().keys():
                    error(54)
            else:
                error(31, "dependency_check")

    def check_arg_types(self, instruction: Instruction, types: str) -> None:
        for i, arg in enumerate(instruction.arg_list):
            if arg[1][0] != types[i]:
                error(53)

    def in_frame(self, name: str, frame: str) -> bool:
        if frame == "GF":
            if name in self.global_frame.keys():
                return True
        elif frame == "TF":
            if name in self.temporary_frame.keys():
                return True
        elif frame == "LF":
            if name in self.local_frame_stack.get_top().keys():
                return True
        else:
            error(31, "in_frame")

        return False

    #TODO implement these lol
    def move(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        # TODO cont

    def createframe(self, instruction: Instruction) -> None:
        self.temporary_frame = {}

    def pushframe(self, instruction: Instruction) -> None:
        self.local_frame_stack.append(self.temporary_frame)
        self.temporary_frame = None

    def popframe(self, instruction: Instruction) -> None:
        top = self.local_frame_stack.get_top()
        if top is None:
            error(55)
        self.temporary_frame = top
        self.local_frame_stack.pop()

    def defvar(self, instruction: Instruction) -> None:
        self.check_arg_types(instruction, "v")
        frame, name = instruction.arg_list[0][0].split("@")
        self.frame_exists(frame)

        if self.in_frame(name, frame):
            error(52)

        if frame == "GF":
            self.global_frame[name] = (None, None)
        elif frame == "TF":
            self.temporary_frame[name] = (None, None)
        elif frame == "LF":
            self.local_frame_stack.get_top()[name] = (None, None)
        else:
            error(31, "local_frame")

    def call(self, instruction: Instruction) -> None:
        pass

    def return_(self, instruction: Instruction) -> None:
        pass

    def pushs(self, instruction: Instruction) -> None:
        pass

    def pops(self, instruction: Instruction) -> None:
        pass

    def add(self, instruction: Instruction) -> None:
        pass

    def sub(self, instruction: Instruction) -> None:
        pass

    def mul(self, instruction: Instruction) -> None:
        pass

    def idiv(self, instruction: Instruction) -> None:
        pass

    def lt(self, instruction: Instruction) -> None:
        pass

    def gt(self, instruction: Instruction) -> None:
        pass

    def eq(self, instruction: Instruction) -> None:
        pass

    def and_(self, instruction: Instruction) -> None:
        pass

    def or_(self, instruction: Instruction) -> None:
        pass

    def not_(self, instruction: Instruction) -> None:
        pass

    def int2char(self, instruction: Instruction) -> None:
        pass

    def stri2int(self, instruction: Instruction) -> None:
        pass

    def read(self, instruction: Instruction) -> None:
        pass

    def write(self, instruction: Instruction) -> None:
        pass

    def concat(self, instruction: Instruction) -> None:
        pass

    def strlen(self, instruction: Instruction) -> None:
        pass

    def getchar(self, instruction: Instruction) -> None:
        pass

    def setchar(self, instruction: Instruction) -> None:
        pass

    def type_(self, instruction: Instruction) -> None:
        pass

    def label(self, instruction: Instruction) -> None:
        pass

    def jump(self, instruction: Instruction) -> None:
        pass

    def jumpifeq(self, instruction: Instruction) -> None:
        pass

    def jumpifneq(self, instruction: Instruction) -> None:
        pass

    def exit_(self, instruction: Instruction) -> None:
        pass

    def dprint(self, instruction: Instruction) -> None:
        pass

    def break_(self, instruction: Instruction) -> None:
        pass

    dispatch_table = {
        'MOVE': (2, move),
        'CREATEFRAME': (0, createframe),
        'PUSHFRAME': (0, pushframe),
        'POPFRAME': (0, popframe),
        'DEFVAR': (1, defvar),
        'CALL': (1, call),
        'RETURN': (0, return_),
        'PUSHS': (1, pushs),
        'POPS': (1, pops),
        'ADD': (3, add),
        'SUB': (3, sub),
        'MUL': (3, mul),
        'IDIV': (3, idiv),
        'LT': (3, lt),
        'GT': (3, gt),
        'EQ': (3, eq),
        'AND': (3, and_),
        'OR': (3, or_),
        'NOT': (2, not_),
        'INT2CHAR': (2, int2char),
        'STRI2INT': (3, stri2int),
        'READ': (2, read),
        'WRITE': (1, write),
        'CONCAT': (3, concat),
        'STRLEN': (2, strlen),
        'GETCHAR': (3, getchar),
        'SETCHAR': (3, setchar),
        'TYPE': (2, type_),
        'LABEL': (1, label),
        'JUMP': (1, jump),
        'JUMPIFEQ': (3, jumpifeq),
        'JUMPIFNEQ': (3, jumpifneq),
        'EXIT': (1, exit_),
        'DPRINT': (1, dprint),
        'BREAK': (0, break_)
    }

    def __init__(self, instruction, flow, data_stack, local_frame_stack, global_frame, temporary_frame, label_list):
        self.instruction = instruction
        self.flow = flow
        self.data_stack = data_stack
        self.local_frame_stack = local_frame_stack
        self.global_frame = global_frame
        self.temporary_frame = temporary_frame
        self.label_list = label_list

    def run_instruction(self):
        arg, fce = self.dispatch_table[self.instruction.opcode]
        if arg != len(self.instruction.arg_list):
            error(52)

        fce(self, self.instruction)

#Façade class for the whole interpret subsystem
class Interpret:
    def get_all_labels(self) -> None:
        self.label_list = []
        for i, instruction in enumerate(self.flow.get_instructions()):
            if instruction[1].attrib["opcode"] == "LABEL":
                self.label_list.append((instruction[1].find("arg1").text, i))

    def __init__(self, sfile, ifile) -> None:
        self.ifile = ifile

        self.flow = FlowControl(sfile)
        self.flow.initialize()

        self.data_stack = Stack()
        self.local_frame_stack = Stack()

        self.global_frame = {}
        self.temporary_frame = None
        
        self.get_all_labels()

    def execute_instruction(self):
        print()

    def interpret(self) -> None:
        while (ins := self.flow.next_instruction()) != -1:
            instruction_obj = Instruction(ins[1])
            operation = Operations(instruction_obj, self.flow, self.data_stack, self.local_frame_stack, self.global_frame, self.temporary_frame, self.label_list)
            operation.run_instruction()

    def debug(self) -> None:
        # add numbers to data stack
        self.data_stack.append(0)
        self.data_stack.append(5)
        self.data_stack.append(10)
        self.data_stack.append(5)
        self.data_stack.append(20)
        
        # add local frames
        self.local_frame_stack.append({})
        self.local_frame_stack.append({})
        self.local_frame_stack.append({})
        self.local_frame_stack.append({})
        self.local_frame_stack.append({})

    def print_everything(self) -> None:
        print(f"Input file: {self.ifile}")
        print("Data stack: ", end="")
        self.data_stack.print_stack()
        print("Frame stack: ", end="")
        self.local_frame_stack.print_stack()
        print("global frame: ", end="")
        print(self.global_frame)
        print("Label list: ", end="")
        for item in self.label_list:
            print(f" [{item}]", end=" ->")
        print(" |")

class Stack:
    def __init__(self):
        self.stack = []
        self._last_elem = None
        self._first_elem = None

    def append(self, item: Any):
        self.stack.append(item)
        if self._first_elem is None:
            self._first_elem = item
        self._last_elem = item

    def pop(self):
        try:
            self.stack.pop()
            self._last_elem = self.stack[-1]
        except IndexError:
            self._last_elem = self._first_elem = None

    def get_top(self) -> (Any | None):
        return self._last_elem

    def print_stack(self) -> None:
        print("[ ", end="")
        for item in self.stack:
            if item is self._first_elem:
                print("first element -> ", end="")
            print(item, end=" ")
            if item is self._last_elem:
                print("<- last element", end="")
            print(", ", end=" ")
        print("] ")

class FlowControl:
    def __init__(self, _xmlFile: str):
        self.xml_file = _xmlFile
        self.init = False

    def initialize(self):
        self.init = True
        self.tree = et.parse(self.xml_file)
        self.root = self.tree.getroot()

        try:
            if self.root.attrib["language"] != "IPPcode23":
                error(31, "root.attrib")
        except KeyError:
            error(31, "keyerror")

        # TODO can change, normal dict should work, but I am not 100% sure
        inst_dict = OrderedDict()
        for instruction in self.root:
            try:
                order = int(instruction.attrib["order"])
                if order in inst_dict.keys():
                    error(31, "order1")
                elif order <= 0:
                    error(31, "order2")
                inst_dict[order] = instruction
            except KeyError:
                error(32)
            except ValueError:
                error(32)

        self._index = 0
        self._sorted_ins = []
        for key in sorted(inst_dict):
            self._sorted_ins.append((key, inst_dict[key]))

    # plural
    def get_instructions(self) -> list:
        if not self.init:
            error(99, addendum="flow control was not initialized before use")
        return self._sorted_ins

    def print_instructions(self):
        if not self.init:
            error(99, addendum="flow control was not initialized before use")

        for instruction in self._sorted_ins:
            print(instruction[0], end=" ")
            print(instruction[1].attrib["opcode"])

    def next_instruction(self):
        if not self.init:
            error(99, addendum="flow control was not initialized before use")
        try:
            ins = self._sorted_ins[self._index]
        except IndexError:
            ins = -1

        self._index += 1
        return ins

    def set_index(self, new_index):
        if (len(self._sorted_ins)-1) < new_index:
            error(99, addendum="instruction pointer index out of range")
        self._index = new_index

    def get_index(self):
        index = self._index
        if index < 0:
            error(99, addendum="instruction pointer index out of range")
        return index

def main() -> NoReturn:
    try:
        # written like this so we skip the first arg variable which is the name
        oplist, args = getopt.getopt(sys.argv[1:], '', ['help', 'version', 'source=', 'input='])
        if args != []:
            error(10)
    except getopt.GetoptError as err:
        error(10, addendum=err.msg)

    sfile = ifile = "stdin"
    for option, optarg in oplist:
        if option == "--source":
            sfile = optarg
        elif option == "--input":
            ifile = optarg
        elif option == "--version":
            print(f"{sys.argv[0]}: {VERSION}")
            sys.exit(0)
        elif option == "--help":
            print(usage_dialog)
            sys.exit(0)
        else:
            print(f"Unhandled option: '{option}'")
            error(10)

    if (sfile == "stdin") and (ifile == "stdin"):
        error(10)

    interpret = Interpret(sfile, ifile)
    interpret.print_everything()
    interpret.interpret()
    print()
    interpret.print_everything()

    sys.exit(0)

if __name__ == '__main__':
    main()
