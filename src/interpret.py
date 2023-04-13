import getopt
import sys
from collections import OrderedDict
import xml.etree.ElementTree as et
from typing import NoReturn, Any

VERSION = 0.2

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
        self.literals = []
        self.dependencies = []

        arg_count = len(instruction)
        for arg in instruction:
            text = arg.text
            attype = arg.attrib["type"]
            if text == "":
                error(99, addendum="expected argument at instruction")

            if attype == "var":
                self.dependencies.append(text)
            elif attype == "type":
                self.literals.append(text)
            elif attype == "label":
                self.dependencies.append(text)
            else:
                self.literals.append(text)

            arg_count -= 1

    def __init__(self, instruction: et.Element):
        self.syntax_checks(instruction)
        self.create_dependencies(instruction)
        self.opcode = instruction.attrib["opcode"]

    def print_instruction_info(self):
        print(f"opcode: {self.opcode}")
        print("Dependencies: ", end="")
        for dependency in self.dependencies:
            print(dependency, end=", ")
        print()
        print("literals: ", end="")
        for literal in self.literals:
            print(literal, end=", ")
        print("\n")

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

    def get_top(self):
        return self._last_elem

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
                error(31)
        except KeyError:
            error(31)

        # TODO can change, normal dict should work, but I am not 100% sure
        inst_dict = OrderedDict()
        for instruction in self.root:
            try:
                order = int(instruction.attrib["order"])
                inst_dict[order] = instruction
            except KeyError:
                error(32)
            except ValueError:
                error(32)

        self._index = 0
        self._sorted_ins = list()
        for key in sorted(inst_dict):
            self._sorted_ins.append((key, inst_dict[key]))

    def print_instructions(self):
        if not self.init:
            error(99, addendum="flow control was not initialized before use")

        for instruction in self._sorted_ins:
            print(instruction[0], end=" ")
            print(instruction[1].attrib["opcode"])

    def next_instruction(self):
        try:
            ins = self._sorted_ins[self._index]
        except IndexError:
            error(99, addendum="no more instructions")

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

    flow = FlowControl(sfile)
    flow.initialize()
    for instruction in flow._sorted_ins:
        obj_ins = Instruction(instruction[1])
        obj_ins.print_instruction_info()

    sys.exit(0)

if __name__ == '__main__':
    main()
