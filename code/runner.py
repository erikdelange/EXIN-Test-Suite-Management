"""" Run scripts and execute tests.

Developed for testing the EXIN interpreter. This interpreter is a
separate executable. This module contains functions to call this
interpreter and have it execute one or more scripts. The output
(stdout, stderr and returncode) of every script is captured. For
testing this output is compared to previously saved expected results.

EXIN can be found here:
https://github.com/erikdelange/EXIN-AST-The-Experimental-Interpreter
"""
import ctypes
import json
import os
import subprocess
from typing import Tuple

import jsonschema

import config
from config import ProcessResult, SourceCodeFileList, TestResult, TestResultList, TestStatus


def run_single_script(files: SourceCodeFileList, stdin: str = "") -> Tuple[bool, ProcessResult]:
    """ Run the code in SourceCodeFileList, using stdin as replacement for keyboard input.

    Create the files in list SourceCodeFileList then call the interpreter for the mainfile. The
    name of this mainfile is a global constant, so fixed. After the interpreter has finished (or
    failed) collect the results and remove the files which previously have been created.

    :param files: list of SourceCodeFile tuples (name + code) for each source code file to create
    :param stdin: the interpreters stdin is redirected to this string
    :return: tuple with bool which is true if execution was successful, and ProcessResults
    """
    result = ProcessResult(exception="unknown")

    try:
        for file in files:
            if file.name:
                with open(file.name, "w") as f:
                    f.write(file.code)

        info = subprocess.run([config.interpreter, config.mainfile],
                              input=stdin,
                              capture_output=True,
                              encoding="utf-8",
                              timeout=config.timeout)
    except subprocess.TimeoutExpired:
        result = ProcessResult(exception=f"command timed out after {config.timeout} seconds")
    except FileNotFoundError:
        result = ProcessResult(exception=f"interpreter {config.interpreter} not found")
    except OSError as e:
        result = ProcessResult(exception=f"{os.strerror(e.errno)} ({e.errno})")
    except Exception as e:  # for debugging only
        result = ProcessResult(exception=f"unexpected exception {e}")
    else:
        result = ProcessResult(stdout=info.stdout,
                               stderr=info.stderr,
                               returncode=str(ctypes.c_int32(info.returncode).value))
    finally:
        for file in files:  # cleanup the files which were created
            if file.name:
                try:
                    os.remove(file.name)
                except OSError:
                    pass

    return True if result.exception == "" else False, result


def run_single_test(script: str) -> TestResult:
    """ Run a single test and return the test results.

    :param script: fully qualified path name of test script
    :return: a single TestResult tuple
    """
    try:
        with open(script, "r") as file:
            scriptdata = json.load(file)
            jsonschema.validate(scriptdata, config.testschema)
            sourcecodelist = [config.SourceCodeFile(item["name"], item["code"]) for item in scriptdata["code"]]
            ok, processresult = run_single_script(sourcecodelist, scriptdata["stdin"])
            if ok:
                if processresult.stdout == scriptdata["expected"]["stdout"] \
                        and processresult.stderr == scriptdata["expected"]["stderr"] \
                        and processresult.returncode == scriptdata["expected"]["returncode"]:
                    status = TestStatus.PASS
                else:  # successful run but result not as expected
                    status = TestStatus.FAIL
            else:  # ok == False, run failed
                status = TestStatus.EXCEPTION
    except (jsonschema.ValidationError, jsonschema.SchemaError) as e:
        processresult = ProcessResult(exception=f"JSON Schema {type(e).__name__}", exceptiondetail=e)
        status = TestStatus.EXCEPTION
    except (OSError, ValueError) as e:
        processresult = ProcessResult(
            exception=f"{type(e).__name__} while loading {os.path.relpath(script, config.scriptroot)}: {e}")
        status = TestStatus.EXCEPTION
    except Exception as e:  # for debugging only
        processresult = ProcessResult(exception=f"unexpected exception {e}")
        status = TestStatus.EXCEPTION

    return TestResult(script=script, status=status, processresult=processresult)


def run_test(script: str) -> TestResultList:
    """ Run test(s) and return the test results, traversing sub-directories.

    :param script: fully qualified path name of test script or directory with scripts to run
    :return: list with zero or more TestResult tuples
    """
    results = list()

    if os.path.isdir(script):
        for filename in os.listdir(script):
            results += run_test(os.path.join(script, filename))
    elif os.path.isfile(script) and script.endswith(config.extension):
        results.append(run_single_test(script))

    return results
