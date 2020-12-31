import collections
import json
import operator
import os

import pytest

from resolvelib.providers import AbstractProvider
from resolvelib.resolvers import Resolver


Requirement = collections.namedtuple("Requirement", "container constraint")
Candidate = collections.namedtuple("Candidate", "container version")


INPUTS_DIR = os.path.abspath(os.path.join(__file__, "..", "inputs"))

INPUT_NAMES = [n for n in os.listdir(INPUTS_DIR) if n.endswith(".json")]


def _parse_version(s):
    major, minor, rest = s.split(".", 2)
    if "-" in rest:
        patch, rest = rest.split("-", 1)
    else:
        patch, rest = rest, ""
    return (int(major), int(minor), int(patch), rest)


def _is_version_allowed(version, ranges):
    """Check version compatibility with Sematic Versioning."""
    for r in ranges:
        r = _parse_version(r)
        if r[0] != version[0]:
            continue
        if r[0] == 0:
            if version[:2] == r[:2] and version[2] >= r[2]:
                return True
        else:
            if version[1:] >= r[1:]:
                return True
    return False


def _calculate_preference(parsed_version):
    """Calculate preference of a version with Minimal Version Selection."""
    if parsed_version[0] == 0:
        return (
            0,
            -parsed_version[1],
            parsed_version[2],
            -len(parsed_version[3][:1]),
            parsed_version[3],
        )
    return (
        -parsed_version[0],
        parsed_version[1],
        parsed_version[2],
        -len(parsed_version[3][:1]),
        parsed_version[3],
    )


class SwiftInputProvider(AbstractProvider):
    def __init__(self, filename, preference_strategy):
        self.preference_strategy = preference_strategy

        with open(filename) as f:
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

    def identify(self, requirement_or_candidate):
        return requirement_or_candidate.container["identifier"]

    def get_preference(self, resolution, candidates, information):
        return self.preference_strategy(resolution, candidates, information)

    def _iter_matches(self, requirements):
        container = requirements[0].container
        for version in container["versions"]:
            ver = _parse_version(version)
            satisfied = all(
                _is_version_allowed(ver, r.constraint["requirement"])
                for r in requirements
            )
            if not satisfied:
                continue
            preference = _calculate_preference(ver)
            yield (preference, Candidate(container, version))

    def find_matches(self, requirements):
        matches = sorted(
            self._iter_matches(requirements),
            key=operator.itemgetter(0),
            reverse=True,
        )
        for _, candidate in matches:
            yield candidate

    def is_satisfied_by(self, requirement, candidate):
        return _is_version_allowed(
            _parse_version(candidate.version),
            requirement.constraint["requirement"],
        )

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


@pytest.fixture(
    params=[os.path.join(INPUTS_DIR, n) for n in INPUT_NAMES],
    ids=[n[:-5] for n in INPUT_NAMES],
)
def provider(request, preference_strategy):
    return SwiftInputProvider(request.param, preference_strategy)


def test_resolver(provider, base_reporter):
    resolver = Resolver(provider, base_reporter)
    result = resolver.resolve(provider.root_requirements)

    display = {
        identifier: candidate.version
        for identifier, candidate in result.mapping.items()
    }
    assert display == provider.expectation
