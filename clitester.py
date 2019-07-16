import tempfile
import subprocess
import json
from collections import namedtuple
from pprint import pprint as pp
"""
FUNCTIONAL PROGRAMMING IN PYTHON
map/filter is not that useful, mostly because it is inflexible. E.g.
results = list(map(run_test_suite, list(tests)))
You have to wait for all the tests to finish before you can print any results!
map(func, [args]) doesn't even run by default, because you have to iterate over it first.
Also, map can only do multiple arguments if run_test_suite(iterable_arg, fixed_arg, fixed_arg).
Keyword arguments are another headache which might be solved by functools.partial.

It is enough to keep the spirit/behaviour of FP when using Python by using simple for loops.
"""
runners = {
    "go": "/home/shinichi/source/go/bin/aecli".split(" "),
    "py": "/home/shinichi/.virtualenvs/aeternity/bin/aecli".split(" "),
    "js": "node /home/shinichi/source/aeternity/aepp-cli-js/bin/aecli.js".split(" ")
}

with open("tests.json") as f:
    tests = json.load(f)

class Run:
    def __init__(self, language, test_description: dict):
        self.language = language
        self.cli_runner = runners[self.language]

        # Complex JSON parsing logic should be limited to this class, and this function
        self.subcommand = test_description["run"]["subcommand"]
        self.stdin = test_description["run"].get("stdin")
        self.pre = test_description["run"].get("pre")
        self.expect_success = test_description["expect"]["success"]
        self.expect_stdout_includes = test_description["expect"].get("stdout_includes")
        
        self.completed_process = None

    def __repr__(self):
        return " ".join([self.language, self.subcommand])

    def run(self):
        # Do not rely on CompletedProcess.args for this information.
        # Because if it fails very hard, a CompletedProcess might not be returned
        with tempfile.TemporaryDirectory() as tmpdirname:
            if self.pre:
                subprocess.run(self.pre, shell=True, cwd=tmpdirname)

            try:
                self.completed_process = subprocess.run(
                    self.cli_runner + self.subcommand.split(" "),
                    input=self.stdin,
                    encoding='utf-8',
                    capture_output=True,
                    cwd=tmpdirname,
                    timeout=10
                )
            except subprocess.TimeoutExpired:
                print(" ".join(self.cli_runner), self.subcommand, "timed out")

    def did_it_pass(self) -> (bool, list):
        # Before doing anything: if the process hung and was terminated, we won't have anything to do.
        if not self.completed_process:
            return False, ["process timed out"]

        # And if the return code was bad, do not test anything else because we cannot rely on
        # CompletedProcess.stdout being available.
        if self.completed_process.returncode != 0:
            return False, ["returned non-zero exit code\nstdout:{}\nstderr:{}".format(self.completed_process.stdout,self.completed_process.stderr)]

        criteria = []
        fail_reason = []
        # TODO: make this a function
        for s in self.expect_stdout_includes:
            if s not in self.completed_process.stdout:
                fail_reason.append("couldn't find \"{}\" in \"{}\"".format(s, self.completed_process.stdout.strip()))
                criteria.append(False)

        return all(criteria), fail_reason

class Test:
    def __init__(self, description):
        self.description = description
        self.go_result = None
        self.go_reason = []
        self.py_result = None
        self.py_reason = []
        self.js_result = None
        self.js_reason = []
    
    def run(self):
        r = Run("go", tests[self.description])
        r.run()
        self.go_result, self.go_reason = r.did_it_pass()

        r = Run("py", tests[self.description])
        r.run()
        self.py_result, self.py_reason = r.did_it_pass()

        r = Run("js", tests[self.description])
        r.run()
        self.js_result, self.js_reason = r.did_it_pass()

def TestPrinter(test: Test):
    def check_x(succeeded):
        if succeeded:
            return green("✔")
        return red("✖")
    def bold(text):
        return "\033[1m" + text + "\033[0m"
    def green(text):
        return "\033[32m" + text + "\033[0m"
    def red(text):
        return "\033[31m" + text + "\033[0m"

    print(green(test.description))
    print("Go:", check_x(test.go_result), "\n".join(test.go_reason))
    print("Py:", check_x(test.py_result), "\n".join(test.py_reason))
    print("JS:", check_x(test.js_result), "\n".join(test.js_reason))

for key in tests:
    t = Test(key)
    t.run()
    TestPrinter(t)
