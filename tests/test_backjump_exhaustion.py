"""Regression test for backjump state exhaustion bug.

See: https://github.com/sarugaku/resolvelib/issues/194
"""

from __future__ import annotations

from collections import namedtuple
from typing import TYPE_CHECKING

import pytest

from resolvelib import AbstractProvider, BaseReporter, ResolutionImpossible, Resolver

if TYPE_CHECKING:
    from typing import Iterator, Mapping

# Test data structures
Candidate = namedtuple("Candidate", ["name", "version", "deps"])
Requirement = namedtuple("Requirement", ["name", "specifier"])


class BackjumpProvider(AbstractProvider):
    """Simple provider for testing state exhaustion during backjumping."""

    def __init__(self, all_candidates):
        self.all_candidates = all_candidates

    def identify(self, requirement_or_candidate):
        if isinstance(requirement_or_candidate, (Candidate, Requirement)):
            return requirement_or_candidate.name
        return requirement_or_candidate

    def get_preference(
        self, identifier, resolutions, candidates, information, backtrack_causes
    ):
        # Reproduce the same order as in the issue
        order = {"python": 0, "lz4": 1, "clickhouse-driver": 2}
        return order.get(identifier, 999)

    def get_dependencies(self, candidate):
        return candidate.deps

    def find_matches(
        self,
        identifier: str,
        requirements: Mapping[str, Iterator],
        incompatibilities: Mapping[str, Iterator],
    ):
        bad_versions = {c.version for c in incompatibilities[identifier]}
        candidates = []

        for candidate in self.all_candidates[identifier]:
            if candidate.version in bad_versions:
                continue

            # Check if candidate satisfies all requirements
            satisfies_all = True
            for req in requirements[identifier]:
                if not self.is_satisfied_by(req, candidate):
                    satisfies_all = False
                    break

            if satisfies_all:
                candidates.append(candidate)

        # Return candidates sorted by version (highest first)
        return sorted(candidates, key=lambda c: c.version, reverse=True)

    def is_satisfied_by(self, requirement, candidate):
        if requirement.name != candidate.name:
            return False

        spec = requirement.specifier
        if not spec:  # No version constraint
            return True

        version = candidate.version

        # Simple specifier parsing
        if spec.startswith("=="):
            return version == spec[2:]
        elif spec.startswith("<="):
            return version <= spec[2:]
        elif spec.startswith("<"):
            return version < spec[1:]
        elif spec.startswith(">="):
            return version >= spec[2:]
        elif spec.startswith(">"):
            return version > spec[1:]
        else:
            return True


def test_backjump_exhaustion():
    """Test that state exhaustion during backjumping raises ResolutionImpossible.

    Reproduces issue that caused IndexError to be raised from the line
    `self._states[-1]` in _push_new_state().
    """
    # Set up a dependency graph with conflicting requirements
    all_candidates = {
        "python": [Candidate("python", "3.12", [])],
        "lz4": [
            Candidate("lz4", "4.3.3", []),
            Candidate("lz4", "3.0.1", []),
            Candidate("lz4", "2.0.0", []),
        ],
        "clickhouse-driver": [
            Candidate(
                "clickhouse-driver",
                "0.2.9",
                [
                    # Conflicting requirements when lz4==4.3.3 is pinned
                    Requirement("lz4", ""),  # Any version
                    Requirement("lz4", "<=3.0.1"),  # But also <=3.0.1
                ],
            ),
        ],
    }

    provider = BackjumpProvider(all_candidates)
    resolver = Resolver(provider, BaseReporter())

    # Should raise ResolutionImpossible, not IndexError
    with pytest.raises(ResolutionImpossible) as exc_info:
        resolver.resolve(
            [
                Requirement("python", ">=3.12"),
                Requirement("lz4", "==4.3.3"),
                Requirement("clickhouse-driver", ">=0.2.9"),
            ]
        )

    assert len(exc_info.value.causes) > 0
