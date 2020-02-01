import collections
import json
import os

import pytest

from resolvelib.providers import AbstractProvider
from resolvelib.resolvers import Resolver


Requirement = collections.namedtuple("Requirement", "container, constraint")
Candidate = collections.namedtuple("Candidate", "container, version")


INPUTS_DIR = os.path.abspath(os.path.join(__file__, "..", "inputs"))


def _parse_version(s):
    major, minor, rest = s.split(".", 2)
    if "-" in rest:
        patch, rest = rest.split("-", 1)
    else:
        patch, rest = rest, ""
    return (int(major), int(minor), int(patch), rest)


class SwiftInputProvider(AbstractProvider):
    def __init__(self, filename):
        with open(os.path.join(INPUTS_DIR, filename + ".json")) as f:
            input_data = json.load(f)

        self.containers = {
            container["identifier"]: container
            for container in input_data["containers"]
        }
        self.root_requirements = [
            Requirement(self.containers[constraint["identifier"]], constraint)
            for constraint in input_data["constraints"]
        ]
        self.expectation = input_data["result"]

    def identify(self, dependency):
        return dependency.container["identifier"]

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        container = requirement.container
        return sorted(
            (
                Candidate(container, version)
                for version in container["versions"]
            ),
            key=lambda c: _parse_version(c.version),
            # Swift uses Minimal Version Selection, i.e. prefer earlier
            # versions to later.
            reverse=True,
        )

    def is_satisfied_by(self, requirement, candidate):
        return candidate.version in requirement.constraint["requirement"]

    def _iter_dependencies(self, candidate):
        for constraint in candidate.container["versions"][candidate.version]:
            identifier = constraint["identifier"]
            try:
                container = self.containers[identifier]
            except KeyError:
                # Package does not exist. Return a stub without candidates.
                container = {"identifier": identifier, "versions": {}}
            yield Requirement(container, constraint)

    def get_dependencies(self, candidate):
        return list(self._iter_dependencies(candidate))


@pytest.fixture()
def provider(request):
    return SwiftInputProvider(request.param)


@pytest.mark.parametrize(
    "provider",
    [name[:-5] for name in os.listdir(INPUTS_DIR) if name.endswith(".json")],
    indirect=True,
)
def test_resolver(provider, base_reporter):
    resolver = Resolver(provider, base_reporter)
    result = resolver.resolve(provider.root_requirements)

    display = {
        identifier: candidate.version
        for identifier, candidate in result.mapping.items()
    }

    assert display == provider.expectation
