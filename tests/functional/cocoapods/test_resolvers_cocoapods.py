import collections
import json
import os

import pytest

from resolvelib.providers import AbstractProvider
from resolvelib.resolvers import Resolver


Requirement = collections.namedtuple("Requirement", "name spec")
Candidate = collections.namedtuple("Candidate", "name ver deps")


INPUTS_DIR = os.path.abspath(os.path.join(__file__, "..", "inputs"))

CASE_DIR = os.path.join(INPUTS_DIR, "case")

CASE_NAMES = [name for name in os.listdir(CASE_DIR) if name.endswith(".json")]


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
            Requirement(key, spec)
            for key, spec in case_data["requested"].items()
        ]
        self.expected_resolution = {
            entry["name"]: entry["version"]
            for entry in case_data["resolved"]
        }
        self.expected_conflicts = case_data["conflicts"]

    def identify(self, dependency):
        return dependency.name

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        try:
            data = self.index[requirement.name]
        except IndexError:
            return []
        return [
            Candidate(entry["name"], entry["version"], entry["dependencies"])
            for entry in data
        ]

    def is_satisfied_by(self, requirement, candidate):
        raise NotImplementedError("God I need to implement Ruby version spec")

    def get_dependencies(self, candidate):
        return [Requirement(k, v) for k, v in candidate.deps.items()]


@pytest.fixture(
    params=[os.path.join(CASE_DIR, n) for n in CASE_NAMES],
    ids=[n[:-5] for n in CASE_NAMES],
)
def provider(request):
    return CocoaPodsInputProvider(request.param)


def test_resolver(provider, base_reporter):
    resolver = Resolver(provider, base_reporter)
    result = resolver.resolve(provider.root_requirements)

    display = {
        identifier: candidate.ver
        for identifier, candidate in result.mapping.items()
    }
    assert display == provider.expected_resolution

    # TODO: Handle errors and assert conflicts.
