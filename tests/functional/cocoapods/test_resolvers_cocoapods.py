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
    m = re.match(r"^([<>=~]+)\s*(.+)$", s)
    op, ver = m.groups()
    if op == "=":
        return "== {}".format(ver)
    elif op == "~>":
        return "~= {0}, >= {0}".format(ver)
    return s


def _parse_specifier_set(inp):
    return packaging.specifiers.SpecifierSet(
        ", ".join(_convert_specifier(s.strip()) for s in inp.split(",") if s),
    )


def _iter_resolved(dependencies):
    for entry in dependencies:
        yield (entry["name"], entry["version"])
        for sub in _iter_resolved(entry["dependencies"]):
            yield sub


class CocoaPodsInputProvider(AbstractProvider):
    def __init__(self, filename):
        with open(filename) as f:
            case_data = json.load(f)

        index_name = os.path.join(
            INPUTS_DIR, "index", case_data.get("index", "awesome") + ".json",
        )
        with open(index_name) as f:
            self.index = json.load(f)

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
        except IndexError:
            return
        for entry in data:
            version = packaging.version.parse(entry["version"])
            if version not in requirement.spec:
                continue
            dependencies = [
                Requirement(k, _parse_specifier_set(v))
                for k, v in entry["dependencies"].items()
            ]
            yield Candidate(entry["name"], version, dependencies)

    def find_matches(self, requirement):
        return sorted(
            self._iter_matches(requirement),
            key=operator.attrgetter("ver"),
        )

    def is_satisfied_by(self, requirement, candidate):
        return candidate.ver in requirement.spec

    def get_dependencies(self, candidate):
        return candidate.deps


@pytest.fixture(
    params=[os.path.join(CASE_DIR, n) for n in CASE_NAMES],
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
