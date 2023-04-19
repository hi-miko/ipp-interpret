# interpret.py (the 2nd project from the IPP class)

## Structure

1. Documentation<br>
    1.1 The goal<br>
    1.2 Design Patterns<br>
    1.3 Classes<br>
        1.3.1 Interpreter subsystem<br>
        1.3.2 Operations class<br>
        1.3.3 Stack class<br>
        1.3.4 Instructions class<br>
        1.3.5 FlowControl class<br>
        1.3.6 TemporaryFrame class
2. Usage
3. UML class diagram

## Documentation

### The goal

The explicit goal of this project was to create an interpreter for the XML representation of `ippcode23`. The representation was less strict
than in the previous IPP project and, so the interpreter had to have been made more strict, with extra checks for edge cases. 

The task was to create and interpreter in an object oriented way (with classes), with the optional, but encouraged bonus of implementing 
various design patterns.

### Design Patterns

This program has an attempt at a design pattern called the Facade. From specifications, this patterns goal is to create a class that would
represent a whole subsystem. Where it would use resources from other classes. This would create a high level interface for the whole subsystem
and the low level details could be ignored from the perspective of the end user.

### Classes

During implementation 6 classes have been made. 5 for different parts of the interpreter and 1 as the entire interpreter subsystem.

#### Interpreter subsystem

A Facade style class. This class combines together all the other classes and uses their resources to interpret the code.
This abstracts the end user from all the parts of an interpret. The only thing the have to know is how to use this class.
It creates resources out of the other classes and passes them on as needed.

#### Operations class

This class implements 2 important things. The first one is a dispatch table, so that the program knows what methods to call when presented 
with certain opcodes and the `run_instruction()` method, that actually calls the afformentioned method. All other methods in this class are
either helper methods, used for modularity or the process methods themselves. This Class also gets all the resources created and managed
by the Interpreter subsystem.

#### Stack class

A simple class that implements normalized stack operations. It is mainly used as a data stack and as a local frame stack.

#### Instruction class

This class creates objects that encompass individual instructions. When creating the object, this class also runs syntax checks and 
creates dependencies and argument list. All of these instance variables are available to the creator of this kind of object.

#### FlowControl class 

This is a class to control the order in which instructions are executed. It has the ability to move around it its own instruction list 
representation with the help of indexes. This allows this class to move to any instruction. This is important in jumps and would not have 
been able to do it implemented without this feature.

#### TemporaryFrame class

A very simple class that implements a temporary frame as a dictionary, with the added benefit of an instance variable specifying if the 
frame is initialized or not. This is useful because temporary frames (as the name suggests) do not exist for the entire run time of the 
interpreter, but instead they are created as needed.

## Usage

Help menu:

```
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

```

## UML class diagram

![image located in the root directory](./Class_diagram.png)
