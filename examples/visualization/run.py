import re
import sys

from reporter_demo import Candidate, Requirement
from visualization.generate import generate_html
from visualization.reporter import GraphGeneratingReporter


def process_arguments(function, args):
    function_arg_info = {
        "starting": [],
        "starting_round": [int],
        "ending_round": [int, ...],
        "ending": [...],
        "adding_requirement": ["requirement", "candidate"],
        "backtracking": ["candidate"],
        "pinning": ["candidate"],
    }
    assert function in function_arg_info

    retval = []
    argument_types = function_arg_info[function]
    for arg_type in argument_types:
        if arg_type is int:
            to_convert, _, args = args.partition(", ")
            value = int(to_convert)
        elif arg_type == "requirement":
            match = re.match(
                r"^<Requirement\('?([\w\-\._~]+)(.*?)'?\)>(.*)", args
            )
            assert match, repr(args)
            name, spec, args = match.groups()
            value = Requirement(name, spec)
        elif arg_type == "candidate":
            match = re.match(r"^(?:<(.+?)==(.+?)>|None)(.*)", args)
            assert match, repr(args)
            name, version, args = match.groups()
            if name and version:
                value = Candidate(name, version)
            else:
                assert not (name or version)
                value = None
        elif arg_type is ...:  # just consume it
            value, _, args = args.partition(", ")
        else:
            raise RuntimeError()

        retval.append(value)
        if args.startswith(","):
            args = args[1:].lstrip()

    return function, retval


def parse_line(line):
    one = line.strip()
    function, _, args = one.partition("(")

    assert args[-1] == ")"
    args = args[:-1]

    return process_arguments(function, args)


def run_reporter_from_logs(reporter, *, logs):
    for line in logs:
        function_name, args = parse_line(line)
        function = getattr(reporter, function_name)
        function(*args)


if __name__ == "__main__":
    usage = "usage: visualization.py reporter-demo-output.txt out.html"
    assert len(sys.argv) == 3, usage

    reporter = GraphGeneratingReporter()
    with open(sys.argv[1]) as f_one:
        run_reporter_from_logs(reporter, logs=f_one)

    with open(sys.argv[2], "w") as f_two:
        generate_html(reporter.evolution, outfile=f_two)
