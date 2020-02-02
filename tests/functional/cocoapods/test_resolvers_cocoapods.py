import collections
import json
import operator
import os
import re

import packaging.specifiers
import packaging.version
import pytest

from resolvelib.providers import AbstractProvider
from resolvelib.resolvers import Resolver


Requirement = collections.namedtuple("Requirement", "name spec")
Candidate = collections.namedtuple("Candidate", "name ver deps")


INPUTS_DIR = os.path.abspath(os.path.join(__file__, "..", "inputs"))

CASE_DIR = os.path.join(INPUTS_DIR, "case")

CASE_NAMES = [name for name in os.listdir(CASE_DIR) if name.endswith(".json")]


def _convert_specifier(s):
    if not s:
        return s
    m = re.match(r"^([<>=~!]*)\s*(.+)$", s)
    op, ver = m.groups()
    if not op or op == "=":
        return "== {}".format(ver)
    elif op == "~>":
        if ver == "0":  # packaging can't handle "~> 0".
            return ""
        return "~= {0}, >= {0}".format(ver)
    return s


def _iter_convert_specifiers(inp):
    for raw in inp.split(","):
        cov = _convert_specifier(raw.strip())
        if not cov:
            continue
        yield cov


def _parse_specifier_set(inp):
    return packaging.specifiers.SpecifierSet(
        ", ".join(_iter_convert_specifiers(inp)),
    )


def _safe_json_load(filename):
    try:
        with open(filename) as f:
            data = json.load(f)
    except ValueError:
        # Some fixtures has comments. Try to fix the file.
        with open(filename) as f:
            lines = [line for line in f if not line.lstrip().startswith("//")]
            data = json.loads("".join(lines))
    return data


def _iter_resolved(dependencies):
    for entry in dependencies:
        yield (entry["name"], entry["version"])
        for sub in _iter_resolved(entry["dependencies"]):
            yield sub


class CocoaPodsInputProvider(AbstractProvider):
    def __init__(self, filename):
        case_data = _safe_json_load(filename)

        index_name = os.path.join(
            INPUTS_DIR, "index", case_data.get("index", "awesome") + ".json",
        )
        self.index = _safe_json_load(index_name)

        self.root_requirements = [
            Requirement(key, _parse_specifier_set(spec))
            for key, spec in case_data["requested"].items()
        ]
        self.expected_resolution = dict(_iter_resolved(case_data["resolved"]))
        self.expected_conflicts = case_data["conflicts"]

    def identify(self, dependency):
        return dependency.name

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def _iter_matches(self, requirement):
        try:
            data = self.index[requirement.name]
        except KeyError:
            return
        for entry in data:
            version = packaging.version.parse(entry["version"])
            if version not in requirement.spec:
                continue
            # Some fixtures incorrectly set dependencies to an empty list.
            dependencies = entry["dependencies"] or {}
            dependencies = [
                Requirement(k, _parse_specifier_set(v))
                for k, v in dependencies.items()
            ]
            yield Candidate(entry["name"], version, dependencies)

    def find_matches(self, requirement):
        return sorted(
            self._iter_matches(requirement), key=operator.attrgetter("ver"),
        )

    def is_satisfied_by(self, requirement, candidate):
        return candidate.ver in requirement.spec

    def get_dependencies(self, candidate):
        return candidate.deps


XFAIL_CASES = {
    "complex_conflict.json",
    "complex_conflict_unwinding.json",
    "conflict_on_child.json",
    "deep_complex_conflict.json",
    "fixed_circular.json",
    "previous_conflict.json",
    "pruned_unresolved_orphan.json",
    "shared_parent_dependency_with_swapping.json",
    "simple_with_base.json",
    "spapping_and_rewinding.json",
    "swapping_children_with_successors.json",
}


@pytest.fixture(
    params=[
        pytest.param(
            os.path.join(CASE_DIR, n), marks=pytest.mark.xfail(strict=True)
        )
        if n in XFAIL_CASES
        else os.path.join(CASE_DIR, n)
        for n in CASE_NAMES
    ],
    ids=[n[:-5] for n in CASE_NAMES],
)
def provider(request):
    return CocoaPodsInputProvider(request.param)


def test_resolver(provider, base_reporter):
    resolver = Resolver(provider, base_reporter)
    result = resolver.resolve(provider.root_requirements)

    if provider.expected_conflicts:
        return

    display = {
        identifier: str(candidate.ver)
        for identifier, candidate in result.mapping.items()
    }
    assert display == provider.expected_resolution

    # TODO: Handle errors and assert conflicts.
