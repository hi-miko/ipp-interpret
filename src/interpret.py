import getopt
import sys
from typing import NoReturn

VERSION = 0.1

errlist = {
    31: "incorrect XML format in the input file",
    32: "unexpected XML structure",
    10: "missing script parameter or use of a prohibited parameter combination",
    11: "error opening input files",
    12: "error opening output files for writing",
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
def error(errcode: int, fname: str = "") -> NoReturn:
    global errlist
    if fname == "":
        print(f"Error code {errcode}: {errlist[errcode]}")
    else:
        print(f"Error code {errcode} (in function: {fname}): {errlist[errcode]}")

    sys.exit(errcode)

# written like this so we skip the first arg variable which is the name
try:
    oplist, args = getopt.getopt(sys.argv[1:], '', ['help', 'version', 'source=', 'input='])
except getopt.GetoptError as err:
    print(err)
    error(10)

sfile = ifile = ""
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

if (sfile == "") and (ifile == ""):
    error(10)
