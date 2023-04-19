import getopt
import sys
import xml.etree.ElementTree as et
from collections import OrderedDict
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

def error(errcode: int, fname: str = "", addendum: str = "") -> NoReturn:
    '''
    Function to print out the error message given an error code.
    :param errcode: The given error code.
    :type errcode: int
    :param fname: Optional string that specifies in what function did the error occur at.
    :type fname: str
    :param addendum: Optional string that outputs an extra message in addition to the standard error message.
    :type addendum: str
    '''
    global errlist
    if fname != "":
        print(f"in function '{fname}'", file=sys.stderr)

    if addendum != "":
        print(f"{addendum}", file=sys.stderr)

    print(f"Error code {errcode}: {errlist[errcode]}", file=sys.stderr)

    sys.exit(errcode)

class Instruction:
    '''
    A class that wraps an instruction into an object and run various checks at initialization.
    :param instruction: A node from the xml reader class.
    :type instruction: et.Element
    '''
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
        for i, arg in enumerate(instruction):
            if (arg.tag != f"arg{arg_count}") and (arg.tag != f"arg{i+1}"):
                error(32)

            arg_count -= 1
            if "type" not in arg.attrib.keys():
                error(32)

            if arg.attrib["type"] not in self.valid_types:
                error(32)
    
    def stringify(self, string):
        start = 0
        while (x := string.find("\\", start)) != -1:
            o_str = string[x] + string[x+1] + string[x+2] + string[x+3]
            digit = string[x+1] + string[x+2] + string[x+3]
            if not digit.isdigit():
                start = x
            n_str = chr(int(digit))
            string = string.replace(o_str, n_str, 1)

        return string

    def create_dependencies(self, instruction: et.Element):
        self.arg_list = []
        self.dependencies = []
        
        rev = False
        for i, arg in enumerate(instruction):
            if i == 0:
                if (arg.tag == "arg2") or (arg.tag == "arg3"):
                    rev = True
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
                if attype == "string":
                    text = self.stringify(text)
                self.arg_list.append((text, attype))
            
        if rev:
            self.arg_list = self.arg_list[::-1]

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
    '''
    A class that implements a dispatch table that chooses how to parse individual opcodes.
    :param instruction: An Instruction class object.
    :type instruction: Instruction
    :param flow: A FlowControl class object that takes care of the program walkthrough.
    :type flow: FlowControl
    :param data_stack: A stack for holding data, used by stack opcodes.
    :type data_stack: Stack
    :param local_frame_stack: A stack for holding local frames.
    :type data_stack: Stack
    :param call_stack: A stack for holding instruction indexes.
    :type call_stack: Stack
    :param global_frame: A dictionary that is used to hold global variables.
    :type global_frame: dict
    :param temporary_frame: A frame that is from the TemporaryFrame class.
    :type temporary_frame: TemporaryFrame
    :param label_list: A list that hold all avaiable labels.
    :type label_list: list
    '''
    def frame_exists(self, frame: str) -> None:
        if frame == "GF":
            return
        if frame == "TF":
            if not self.temporary_frame.exists():
                error(55)
        elif frame == "LF":
            local_frame = self.local_frame_stack.get_top()
            if local_frame is None:
                error(55)
        else:
            error(31)

    def dependency_check(self, instruction: Instruction) -> None:
        for dp in instruction.dependencies:
            frame, name = dp.split("@")
            if frame == "GF":
                if name not in self.global_frame.keys():
                    error(54)
            elif frame == "TF":
                self.frame_exists("TF")
                if not self.temporary_frame.exists_var(name):
                    error(54)
            elif frame == "LF":
                self.frame_exists("LF")
                if name not in self.local_frame_stack.get_top().keys():
                    error(54)
            else:
                error(31)

    def check_arg_types(self, instruction: Instruction, types: str) -> None:
        for i, arg in enumerate(instruction.arg_list):
            if arg[1][0] != types[i]:
                error(53)

    def in_frame(self, name: str, frame: str) -> bool:
        if frame == "GF":
            if name in self.global_frame.keys():
                return True
        elif frame == "TF":
            return self.temporary_frame.exists_var(name)
        elif frame == "LF":
            if name in self.local_frame_stack.get_top().keys():
                return True
        else:
            error(31)

        return False

    def get_frame_value(self, instruction: str) -> (Any | tuple):
        frame, name = instruction.split("@")
        if frame == "GF":
            return self.global_frame[name]
        elif frame == "LF":
            return self.local_frame_stack.get_top()[name]
        elif frame == "TF":
            return self.temporary_frame.get_var(name)
        
    def set_frame_value(self, instruction: str, value: tuple) -> None:
        frame, name = instruction.split("@")
        if frame == "GF":
            self.global_frame[name] = value
        elif frame == "LF":
            self.local_frame_stack.get_top()[name] = value
        elif frame == "TF":
            self.temporary_frame.set_var(name, value)

    def move(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)

        arg1, _ = instruction.arg_list[0]
        arg2, arg_type2 = instruction.arg_list[1]

        if arg_type2 == "var":
            arg1_value = self.get_frame_value(arg1)
            arg2_value = self.get_frame_value(arg2)
            if arg2_value[1] is None:
                error(56)

            if (arg1_value[1] is None) or (arg1_value[1] == arg2_value[1]):
                self.set_frame_value(arg1, arg2_value)
            else:
                error(53)
        elif (arg_type2 == "int") or (arg_type2 == "string") or (arg_type2 == "bool") or (arg_type2 == "nil"):
            arg1_value = self.get_frame_value(arg1)

            if (arg1_value[1] is None) or (arg1_value[1] == arg_type2):
                self.set_frame_value(arg1, (arg2, arg_type2))
            else:
                error(53)
        else:
            error(53)

    def createframe(self) -> None:
        self.temporary_frame.set({})

    def pushframe(self) -> None:
        if self.temporary_frame.exists():
            self.local_frame_stack.append(self.temporary_frame.data)
            self.temporary_frame.remove()
        else:
            error(55)

    def popframe(self) -> None:
        if self.local_frame_stack.get_top() is not None:
            self.temporary_frame.set(self.local_frame_stack.get_top())
            self.local_frame_stack.pop()
        else:
            error(55)

    def defvar(self, instruction: Instruction) -> None:
        self.check_arg_types(instruction, "v")
        frame, name = instruction.arg_list[0][0].split("@")
        self.frame_exists(frame)

        if self.in_frame(name, frame):
            error(52)

        if frame == "GF":
            self.global_frame[name] = (None, None)
        elif frame == "TF":
            self.temporary_frame.set_var(name, (None, None))
        elif frame == "LF":
            self.local_frame_stack.get_top()[name] = (None, None)
        else:
            error(31)

    def call(self, instruction: Instruction) -> None:
        curr_index = self.flow.get_index()
        self.call_stack.append(curr_index)

        label = instruction.arg_list[0]
        
        if label[1] != "label":
            error(57)

        if label[0] not in self.label_list.keys():
            error(52)

        self.flow.set_index(self.label_list[label[0]])

    def return_(self) -> None:
        index = self.call_stack.get_top()
        if index is None:
            error(56)
        
        self.call_stack.pop()
        self.flow.set_index(index)

    def pushs(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)

        arg1, arg_type1 = instruction.arg_list[0]

        if arg_type1 == "var":
            arg1_value = self.get_frame_value(arg1)
            if arg1_value[1] is None:
                error(56)
        elif (arg_type1 == "type") or (arg_type1 == "label"):
            error(53)
        else:
            arg1_value = (arg1, arg_type1)
        
        self.data_stack.append(arg1_value)

    def pops(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        top_val = self.data_stack.get_top()

        if top_val is None:
            error(56)
        
        arg1, _ = instruction.arg_list[0]
        _, arg1_type = self.get_frame_value(arg1)
        if (top_val[1] != instruction.arg_list[0][1]) and (arg1_type is not None):
            error(53)

        self.set_frame_value(instruction.arg_list[0][0], top_val)

        self.data_stack.pop()
        
    def math_ops(self, instruction: Instruction, ops: str) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if (arg1[1] is not None) and (arg1[1] != "int"):
            error(53)
        
        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] != "int":
            error(53)

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])
        
        if arg3[1] != "int":
            error(53)
        
        op = ops[0]
        try:
            if op == "+":
                result = int(arg2[0]) + int(arg3[0])
            elif op == "-":
                result = int(arg2[0]) - int(arg3[0])
            elif op == "*":
                result = int(arg2[0]) * int(arg3[0])
            elif op == "/":
                result = int(arg2[0]) // int(arg3[0])
            else:
                error(99, addendum="Unknown operation type")
        except ValueError:
            error(32)
        except ZeroDivisionError:
            error(57)

        self.set_frame_value(instruction.arg_list[0][0], (result, "int"))

    def relation_ops(self, instruction: Instruction, ops: str) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if (arg1[1] is not None) and (arg1[1] != "bool"):
            error(53)

        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])
        
        op = ops[0]
        if op == "==":
            self.eq(instruction, arg2, arg3)
            return

        if arg2[1] != arg3[1]:
            error(53)
        
        args_type = arg2[1]

        if (args_type == "nil") or (args_type == "lable") or (arg2[1] == "type"):
            error(53)
        
        try:
            if args_type == "int":
                arg2 = int(arg2[0])
                arg3 = int(arg3[0])
            elif args_type == "bool":
                arg2 = eval(str(arg2[0]).lower().capitalize())
                arg3 = eval(str(arg3[0]).lower().capitalize())
            else:
                arg2 = arg2[0]
                arg3 = arg3[0]
        except ValueError:
            error(32)

        result = False
        if op == ">":
            result = arg2 > arg3
        elif op == "<":
            result = arg2 < arg3
        else:
            error(99, addendum="Unknown operation type")

        self.set_frame_value(instruction.arg_list[0][0], (result, "bool"))
    
    def eq(self, instruction, arg2, arg3) -> None:
        arg2_type = arg2[1]
        arg3_type = arg3[1]

        if (arg2[1] != arg3[1]) and ((arg2[1] != "nil") and (arg3[1] != "nil")):
            error(53)
        
        try:
            if arg2[1] == "string":
                arg2 = arg2[0]
            elif arg2[1] == "bool":
                arg2 = eval(str(arg2[0]).lower().capitalize())
            elif arg2[1] == "int":
                arg2 = int(arg2[0])

            if arg3[1] == "string":
                arg3 = arg3[0]
            elif arg3[1] == "bool":
                arg3 = eval(str(arg3[0]).lower().capitalize())
            elif arg3[1] == "int":
                arg3 = int(arg3[0])
        except ValueError:
            error(32)

        if (arg2_type == "nil") and (arg3_type == "nil"):
            result = True
        elif (arg2_type == "nil") or (arg3_type == "nil"):
            result = False
        else:
            result = arg2 == arg3

        self.set_frame_value(instruction.arg_list[0][0], (result, "bool"))

    def and_or(self, instruction: Instruction, ops) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if (arg1[1] is not None) and (arg1[1] != "bool"):
            error(53)

        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])

        if arg2[1] != "bool":
            error(53)

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])

        if arg3[1] != "bool":
            error(53)

        op = ops[0]
        try:
            if op == "and":
                result = eval(str(arg2[0]).lower().capitalize()) and eval(str(arg3[0]).lower().capitalize())
            elif op == "or":
                result = eval(str(arg2[0]).lower().capitalize()) or eval(str(arg3[0]).lower().capitalize())
            else:
                error(99, addendum="Unknown operation type")
        except ValueError:
            error(32)

        self.set_frame_value(instruction.arg_list[0][0], (result, "bool"))
 
    def not_(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]

        if (arg1[1] is not None) and (arg1[1] != "bool"):
            error(53)

        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])

        if arg2[1] != "bool":
            error(53)
       
        try:
            result = not bool(arg2[0].lower().capitalize())
        except ValueError:
            error(32)

        self.set_frame_value(instruction.arg_list[0][0], (result, "bool"))
        
    def int2char(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]

        if (arg1[1] is not None) and (arg1[1] != "string"):
            error(53)
        
        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] != "int":
            error(58)
        try:
            result = chr(int(arg2[0]))
        except ValueError:
            error(32)

        self.set_frame_value(instruction.arg_list[0][0], (result, "string"))

    def stri2int(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if (arg1[1] is not None) and (arg1[1] != "int"):
            error(53)
        
        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] != "string":
            error(53)

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])
        
        if arg3[1] != "int":
            error(53)
        try:
            result = ord(arg2[0][int(arg3[0])])
        except ValueError:
            error(32)
        except IndexError:
            error(58)

        self.set_frame_value(instruction.arg_list[0][0], (result, "int"))

    def read(self, instruction: Instruction) -> None:
        # TODO skip for now
        pass

    def write(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.instruction.arg_list[0]

        if arg1[1] == "var":
            arg1 = self.get_frame_value(arg1[0])

        if arg1[1] == "nil":
            print("", end="")
        elif arg1[1] == "bool":
            print(str(arg1[0].lower()), end="")
        else:
            print(arg1[0], end="")

    def concat(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if (arg1[1] is not None) and (arg1[1] != "string"):
            error(53)
        
        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] != "string":
            error(53)

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])
        
        if arg3[1] != "string":
            error(53)

        result = arg2[0] + arg3[0]
        self.set_frame_value(instruction.arg_list[0][0], (result, "string"))

    def strlen(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]

        if (arg1[1] is not None) and (arg1[1] != "int"):
            error(53)
        
        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] != "string":
            error(53)

        result = len(arg2[0])
        self.set_frame_value(instruction.arg_list[0][0], (result, "int"))

    def getchar(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if (arg1[1] is not None) and (arg1[1] != "string"):
            error(53)
        
        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] != "string":
            error(53)

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])
        
        if arg3[1] != "int":
            error(53)
        try:
            result = arg2[0][int(arg3[0])]
        except ValueError:
            error(32)
        except IndexError:
            error(58)

        self.set_frame_value(instruction.arg_list[0][0], (result, "string"))

    def setchar(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if arg1[1] != "string":
            error(53)
        
        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] != "int":
            error(53)

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])
        
        if arg3[1] != "string":
            error(53)

        try:
            index = int(arg2[0])
            r_as = arg3[0][0]
            
            result_1 = arg1[0][:index]
            result_2 = arg1[0][index+1:]

            result = result_1 + r_as + result_2
        except ValueError:
            error(32)
        except IndexError:
            error(58)

        self.set_frame_value(instruction.arg_list[0][0], (result, "string"))

    def type_(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.get_frame_value(instruction.arg_list[0][0])
        arg2 = self.instruction.arg_list[1]

        if (arg1[1] is not None) and (arg1[1] != "string"):
            error(53)

        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])
        
        if arg2[1] is None:
            self.set_frame_value(instruction.arg_list[0][0], ("", "string"))
        else:
            self.set_frame_value(instruction.arg_list[0][0], (arg2[1], "string"))
        
    def label(self, instruction: Instruction) -> None:
        pass

    def jump(self, instruction: Instruction) -> None:
        label = instruction.arg_list[0]
        
        if label[1] != "label":
            error(57)

        if label[0] not in self.label_list.keys():
            error(52)

        self.flow.set_index(self.label_list[label[0]])

    def j_eq(self, arg2, arg3):
        arg2_type = arg2[1]
        arg3_type = arg3[1]

        if (arg2[1] != arg3[1]) and ((arg2[1] != "nil") and (arg3[1] != "nil")):
            error(53)
        
        try:
            if arg2[1] == "string":
                arg2 = arg2[0]
            elif arg2[1] == "bool":
                arg2 = eval(str(arg2[0]).lower().capitalize())
            elif arg2[1] == "int":
                arg2 = int(arg2[0])

            if arg3[1] == "string":
                arg3 = arg3[0]
            elif arg3[1] == "bool":
                arg3 = eval(str(arg3[0]).lower().capitalize())
            elif arg3[1] == "int":
                arg3 = int(arg3[0])
        except ValueError:
            error(32)

        if (arg2_type == "nil") and (arg3_type == "nil"):
            result = True
        elif (arg2_type == "nil") or (arg3_type == "nil"):
            result = False
        else:
            result = arg2 == arg3
        
        return result

    def jumpifeq(self, instruction: Instruction) -> None:
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])

        result = self.j_eq(arg2, arg3)

        if result:
            self.jump(instruction)

    def jumpifneq(self, instruction: Instruction) -> None:
        arg2 = self.instruction.arg_list[1]
        arg3 = self.instruction.arg_list[2]

        if arg2[1] == "var":
            arg2 = self.get_frame_value(arg2[0])

        if arg3[1] == "var":
            arg3 = self.get_frame_value(arg3[0])

        result = not self.j_eq(arg2, arg3)

        if result:
            self.jump(instruction)

    def exit_(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.instruction.arg_list[0]

        if arg1[1] == "var":
            arg1 = self.get_frame_value(arg1[0])
        
        if arg1[1] != "int":
            error(53)
        
        try:
            errcode = int(arg1[0])
        except ValueError:
            error(32)

        if (errcode < 0) or (errcode > 49):
            error(57)

        exit(errcode)

    def dprint(self, instruction: Instruction) -> None:
        self.dependency_check(instruction)
        arg1 = self.instruction.arg_list[0]

        if arg1[1] == "var":
            arg1 = self.get_frame_value(arg1[0])
        
        print(arg1[0], file=sys.stderr, end="")
        
    def break_(self) -> None:
        index = self.flow.get_index()-1  # current position
        ins_list = self.flow.get_instructions()
        position = ins_list[index]
        
        print(f"\nPosition at order [{position[0]}] {position[1].attrib['opcode']}", file=sys.stderr)
        print(f"Global Frame: {self.global_frame}", file=sys.stderr)
        print("Temporary Frame: ", file=sys.stderr, end="")
        self.temporary_frame.print_frame(out="stderr")
        print("Local frame stack: ", file=sys.stderr, end="")
        self.local_frame_stack.print_stack(out="stderr")
        print(f"Performed instructions: {index+1}\n", file=sys.stderr)

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
        'ADD': (3, math_ops, '+'),
        'SUB': (3, math_ops, '-'),
        'MUL': (3, math_ops, '*'),
        'IDIV': (3, math_ops, '/'),
        'LT': (3, relation_ops, '<'),
        'GT': (3, relation_ops, '>'),
        'EQ': (3, relation_ops, '=='),
        'AND': (3, and_or, "and"),
        'OR': (3, and_or, "or"),
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
        'JUMP': (1, jump),
        'JUMPIFEQ': (3, jumpifeq),
        'JUMPIFNEQ': (3, jumpifneq),
        'EXIT': (1, exit_),
        'DPRINT': (1, dprint),
        'BREAK': (0, break_)
    }

    def __init__(self, instruction, flow, data_stack, local_frame_stack, global_frame, temporary_frame, label_list, call_stack):
        self.instruction = instruction
        self.flow = flow
        self.data_stack = data_stack
        self.local_frame_stack = local_frame_stack
        self.global_frame = global_frame
        self.temporary_frame = temporary_frame
        self.label_list = label_list
        self.call_stack = call_stack

    def run_instruction(self):
        if self.instruction.opcode == "LABEL":
            return

        try:
            arg, fce, *argv = self.dispatch_table[self.instruction.opcode]
        except KeyError:
            error(32)

        if arg != len(self.instruction.arg_list):
            error(32)
        
        if arg == 0:
            fce(self)
        elif arg == 3:
            if argv == []:
                fce(self, self.instruction)
            else:
                fce(self, self.instruction, argv)
        else:
            fce(self, self.instruction)


# Façade class for the whole interpret subsystem
class Interpret:
    '''
    A Façade style class from the Façade design pattern.
    This class combines together all the other classes and uses their resources to interpret the code.
    This abstracts the end user from all the parts of an interpret. The only thing the have to know is how to use this class.
    :param sfile: A file that holds the xml representation that needs to be interpreted.
    :type sfile: str
    :param ifile: A file that holds the user input values that can be used durring interpretation.
    :type ifile: str
    '''
    def get_all_labels(self) -> None:
        self.label_list = {}
        for i, instruction in enumerate(self.flow.get_instructions()):
            try:
                if instruction[1].attrib["opcode"] == "LABEL":
                    if instruction[1].find("arg1").text in self.label_list.keys():
                        error(52)

                    self.label_list[instruction[1].find("arg1").text] = i
            except KeyError:
                error(32)

    def __init__(self, sfile, ifile) -> None:
        self.ifile = ifile

        self.flow = FlowControl(sfile)
        self.flow.initialize()

        self.data_stack = Stack()
        self.local_frame_stack = Stack()
        self.call_stack = Stack()

        self.global_frame = {}
        self.temporary_frame = TemporaryFrame()
        
        self.get_all_labels()

    def interpret(self) -> None:
        while (ins := self.flow.next_instruction()) != -1:
            instruction_obj = Instruction(ins[1])
            operation = Operations(instruction_obj, self.flow, self.data_stack, self.local_frame_stack, self.global_frame, self.temporary_frame, self.label_list, self.call_stack)
            operation.run_instruction()

    def print_everything(self) -> None:
        print(f"Input file: {self.ifile}")

        print("Data stack: ", end="")
        self.data_stack.print_stack()

        print("Frame stack: ", end="")
        self.local_frame_stack.print_stack()

        print("global frame: ", end="")
        print(self.global_frame)

        print("Temporary frame: ", end="")
        self.temporary_frame.print_frame()

        print(f"Label list: {self.label_list}")

        print("Call stack: ", end="")
        self.call_stack.print_stack()

class Stack:
    '''
    A class that represents a stack.
    All normalized stack operations are present.
    '''
    def __init__(self) -> None:
        self.stack = []
        self._last_elem = None
        self._first_elem = None

    def append(self, item: Any) -> None:
        self.stack.append(item)
        if self._first_elem is None:
            self._first_elem = item
        self._last_elem = item

    def pop(self) -> None:
        try:
            self.stack.pop()
            self._last_elem = self.stack[-1]
        except IndexError:
            self._last_elem = self._first_elem = None

    def get_top(self) -> (Any | None):
        return self._last_elem

    def print_stack(self, out="cout") -> None:
        if out == "cout":
            fd = sys.stdout
        else:
            fd = sys.stderr

        print("[", end="", file=fd)

        last = len(self.stack)-1
        for i, item in enumerate(self.stack):
            if item is self._first_elem:
                print("first element -> ", end="", file=fd)
            print(item, end=" ")
            if item is self._last_elem:
                print("<- last element", end="", file=fd)

            if i != last:
                print(", ", end=" ", file=fd)

        print("] ", file=fd)

class TemporaryFrame():
    '''
    A class that implements a temporary frame.
    This is done with a class so that the program is able to specify that the temporary frame is uninitialized.
    '''
    def __init__(self) -> None:
        self._initialized = False
        self.data = {}

    def set(self, frame: dict) -> None:
        self._initialized = True
        self.data = frame
    
    def exists(self) -> bool:
        return self._initialized

    def remove(self) -> None:
        self._initialized = False

    def set_var(self, name: str, value: tuple) -> None:
        self.data[name] = value

    def exists_var(self, name: str) -> bool:
        return name in self.data.keys()

    def get_var(self, name: str) -> (Any | None):
        if self.exists_var(name):
            return self.data[name]
        else:
            return None

    def print_frame(self, out="cout") -> None:
        if out == "cout":
            fd = sys.stdout
        else:
            fd = sys.stderr

        print(self.data, end="", file=fd)
        if self._initialized:
            print(" <- initialized", file=fd)
        else:
            print(" <- uninitialized", file=fd)

class FlowControl:
    '''
    A class that implements the control of flow ie. instruction order durring interpretation.
    :param _xmlFile: The xml file that the program attempts to take the xml representation out of.
    :type _xmlFile: str
    '''
    def __init__(self, _xmlFile: str):
        self.xml_file = _xmlFile
        self.init = False

    def initialize(self):
        self.init = True
        if self.xml_file == "stdin":
            file = []
            while True:
                try:
                    line = input()
                    file.append(line)
                except EOFError:
                    break

            stdin = "".join(file)
            self.root = et.fromstring(stdin)
        else:
            try:
                self.tree = et.parse(self.xml_file)
                self.root = self.tree.getroot()
            except et.ParseError:
                error(31)

        try:
            if self.root.attrib["language"] != "IPPcode23":
                error(32)
        except KeyError:
            error(31)

        inst_dict = OrderedDict()
        for instruction in self.root:
            try:
                order = int(instruction.attrib["order"])
                if order in inst_dict.keys():
                    error(32)
                elif order <= 0:
                    error(32)
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

        for i, instruction in enumerate(self._sorted_ins):
            print(f"[{i}]", end=" ")
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
    interpret.interpret()

    sys.exit(0)

if __name__ == '__main__':
    main()
