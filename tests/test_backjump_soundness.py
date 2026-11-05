"""Backjumping must not report a solvable graph as impossible.

See https://github.com/sarugaku/resolvelib/issues/206.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from resolvelib import AbstractProvider, BaseReporter, ResolutionImpossible, Resolver
from resolvelib.resolvers import Resolution


@dataclass(frozen=True)
class Requirement:
    name: str
    allowed: frozenset[int]


@dataclass(frozen=True)
class Candidate:
    name: str
    version: int


PACKAGES = {
    "p0": {2: [Requirement("p2", frozenset({2}))]},
    "p1": {2: [Requirement("p0", frozenset({2}))], 1: []},
    "p2": {
        2: [Requirement("p1", frozenset({3}))],
        1: [Requirement("p1", frozenset({1, 2}))],
    },
}


class Provider(AbstractProvider):
    def identify(self, requirement_or_candidate):
        return requirement_or_candidate.name

    def get_preference(
        self, identifier, resolutions, candidates, information, backtrack_causes
    ):
        return identifier in resolutions

    def find_matches(self, identifier, requirements, incompatibilities):
        rejected = {candidate.version for candidate in incompatibilities[identifier]}
        wanted = list(requirements[identifier])
        return [
            Candidate(identifier, version)
            for version in sorted(PACKAGES[identifier], reverse=True)
            if version not in rejected and all(version in req.allowed for req in wanted)
        ]

    def is_satisfied_by(self, requirement, candidate):
        return (
            requirement.name == candidate.name
            and candidate.version in requirement.allowed
        )

    def get_dependencies(self, candidate):
        return list(PACKAGES[candidate.name][candidate.version])


def test_skipping_backjump_rejects_the_only_solution():
    """The heuristic skips p1, whose only dependency is outside the cause set."""
    resolution = Resolution(Provider(), BaseReporter())
    with pytest.raises(ResolutionImpossible):
        resolution.resolve(
            [Requirement("p2", frozenset({1, 2, 3}))],
            max_rounds=100,
        )


def test_resolve_finds_the_solution_after_the_skipping_pass():
    result = Resolver(Provider(), BaseReporter()).resolve(
        [Requirement("p2", frozenset({1, 2, 3}))],
        max_rounds=100,
    )
    assert {name: candidate.version for name, candidate in result.mapping.items()} == {
        "p2": 1,
        "p1": 1,
    }


def test_absent_candidate_is_still_impossible():
    with pytest.raises(ResolutionImpossible):
        Resolver(Provider(), BaseReporter()).resolve(
            [Requirement("p2", frozenset({2}))],
            max_rounds=100,
        )
