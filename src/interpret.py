import getopt
import sys
from collections import OrderedDict
import xml.etree.ElementTree as et
from typing import NoReturn, Any

VERSION = 0.2

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
        self.ins_dict = OrderedDict()
        for instruction in self.root:
            try:
                order = int(instruction.attrib["order"])
                self.ins_dict[order] = instruction
            except KeyError:
                error(32)
            except ValueError:
                error(32)

    def print_instructions(self):
        if not self.init:
            error(99, addendum="flow control was not initialized before use")
        for key in sorted(self.ins_dict):
            print(f"key: {key}, value: {self.ins_dict[key]}")

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

def main():
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
    flow.print_instructions()

    sys.exit(0)

if __name__ == '__main__':
    main()
