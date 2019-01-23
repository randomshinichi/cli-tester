import subprocess
import json
from collections import namedtuple

"""
FUNCTIONAL PROGRAMMING IN PYTHON
map/filter is not that useful, mostly because it is inflexible. E.g.
results = list(map(run_test_suite, list(tests)))
You have to wait for all the tests to finish before you can print any results!
map(func, [args]) doesn't even run by default, because you have to iterate over it first.
Also, map can only do multiple arguments if run_test_suite(iterable_arg, fixed_arg, fixed_arg).
Keyword arguments are another headache which might be solved by functools.partial.

It is enough to keep the spirit/behaviour of FP when using Python by using simple for loops.

LIMITATIONS
You can't test the same subcommand twice (with a different environment), because the keys overwrite each other in the JSON
"""

aecli_go="/home/shinichi/source/go/bin/aecli --config ~/source/aeternity/aecli_config.yml".split(" ")
aecli_py="/home/shinichi/.virtualenvs/aeternity/bin/aecli".split(" ")
aecli_js="node /home/shinichi/source/aeternity/aepp-cli-js/bin/aecli.js".split(" ")

aecli = [aecli_go, aecli_py, aecli_js]

class RunResult:
    def __init__(self, cli: str, completed_process: subprocess.CompletedProcess, succeeded=None, fail_reason=''):
        self.cli = cli
        self.succeeded = succeeded
        self.completed_process = completed_process
        self.fail_reason = fail_reason
    def __repr__(self):
        return self.cli + " " + str(self.succeeded)

TestResult = namedtuple("TestResult", "subcommand go py js")

def TestResultPrinter(tr: TestResult):
    def check_x(succeeded):
        if succeeded:
            return "✔"
        return "✖"
    print(tr.subcommand)
    print("Go:", check_x(tr.go.succeeded), tr.go.fail_reason)
    print("Py:", check_x(tr.py.succeeded), tr.py.fail_reason)
    print("JS:", check_x(tr.js.succeeded), tr.js.fail_reason)

with open("tests.json") as f:
    tests = json.load(f)

def check_if_test_passed(run_result: RunResult, test_params) -> bool:
    criteria = []

    # If exit code is not 0, just consider it failed.
    try:
        run_result.completed_process.check_returncode()
    except subprocess.CalledProcessError as e:
        run_result.fail_reason = str(e)
        criteria.append(False)

    if not test_params.get("stdout_includes"):
        criteria.append(True)

    for s in test_params.get("stdout_includes"):
        if s not in run_result.completed_process.stdout:
            run_result.fail_reason = "check_if_test_passed(): couldn't find \"{}\" in \"{}\"".format(s, run_result.completed_process.stdout.strip())
            criteria.append(False)

    run_result.succeeded = all(criteria)
    return run_result.succeeded

def run_test_on_cli(cli: list, subcommand: str, input=None) -> RunResult:
    # Do not rely on CompletedProcess.args for this information.
    # Because if it fails very hard, a CompletedProcess might not be returned
    complete_command = " ".join(cli) + " " + subcommand

    try:
        completed_process = subprocess.run(cli + subcommand.split(" "), input=input, encoding='utf-8', capture_output=True, timeout=10)
        return RunResult(cli=complete_command, completed_process=completed_process)
    except subprocess.TimeoutExpired:
        print(cli, subcommand, "timed out")
        return RunResult(cli=complete_command, completed_process=None)

def run_test_suite(subcommand):
    test = tests[subcommand]

    run_results = []
    for cli in aecli:
        r = run_test_on_cli(cli, subcommand, input=test.get("stdin"))
        run_results.append(r)

    for r in run_results:
        check_if_test_passed(r, test)

    return TestResult(subcommand=subcommand, go=run_results[0], py=run_results[1], js=run_results[2])

for key in tests:
    r = run_test_suite(key)
    TestResultPrinter(r)