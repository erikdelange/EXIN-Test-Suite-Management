""" Configuration constants. """

from typing import List, NamedTuple

# Directory from where to search for ui*.ui files if this python script
# is frozen. See also ui.loadUi()
appdir = ""

# Root directory for test scripts
scriptroot = ""

# Path to the EXIN interpreter executable
interpreter = ""

# Name of file to feed to the interpreter, interpretation starts here
mainfile = "main.x"

# Timeout in seconds before the interpreter process is killed
timeout = 5

# Mandatory extension of test script filename
extension = ".json"


class SourceCodeFile(NamedTuple):
    """ Single sourcecode file with name and code content. """
    name: str
    code: str


# Typedef for list()
SourceCodeFileList = List[SourceCodeFile]


class ProcessResult(NamedTuple):
    """" Script execution result. """
    stdout: str = ""
    stderr: str = ""
    returncode: str = ""
    exception: str = ""
    exceptiondetail: str = ""


class TestStatus:
    """ All possible test statuses. """
    PASS = "pass"
    FAIL = "fail"
    EXCEPTION = "exception"


class TestResult(NamedTuple):
    """" Test results for a script. """
    script: str
    status: TestStatus
    processresult: ProcessResult


# Typedef for list()
TestResultList = List[TestResult]

# Definition of JSON file containing a test, follows JSON Schema
# standards from https://json-schema.org/. Everywhere where a test
# is loaded use this definition to check the file contents.
testschema = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "code": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "code": {"type": "string"}
                },
                "required": ["name", "code"]
            }
        },
        "stdin": {"type": "string"},
        "expected": {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "returncode": {"type": "string"}
            },
            "required": ["stdout", "stderr", "returncode"]
        }
    },
    "required": ["description", "code", "stdin", "expected"]
}
