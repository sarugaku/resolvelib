from collections import namedtuple

from packaging.specifiers import SpecifierSet
from packaging.version import Version

import resolvelib
import resolvelib.resolvers.resolution

index = """
first 1.0.0
    second == 1.0.0
first 2.0.0
    second == 2.0.0
    third == 1.0.0
first 3.0.0
    second == 3.0.0
    third == 2.0.0
second 1.0.0
    third == 1.0.0
second 2.0.0
    third == 2.0.0
second 3.0.0
    third == 3.0.0
third 1.0.0
third 2.0.0
third 3.0.0
"""


class Requirement(namedtuple("Requirement", "name specifier")):
    def __repr__(self):
        return f"<Requirement({self.name}{self.specifier})>"


class Candidate(namedtuple("Candidate", "name version")):
    def __repr__(self):
        return f"<{self.name}=={self.version}>"


def splitstrip(s, parts):
    return [item.strip() for item in s.strip().split(maxsplit=parts - 1)]


def read_spec(lines):
    candidates = {}
    latest = None
    for line in lines:
        if not line or line.startswith("#"):
            continue
        if not line.startswith(" "):
            name, version = splitstrip(line, 2)
            version = Version(version)
            latest = Candidate(name, version)
            candidates[latest] = set()
        else:
            if latest is None:
                raise RuntimeError("Spec has dependencies before first candidate")
            name, specifier = splitstrip(line, 2)
            specifier = SpecifierSet(specifier)
            candidates[latest].add(Requirement(name, specifier))
    return candidates


class Provider(resolvelib.AbstractProvider):
    def __init__(self, index):
        self.candidates = read_spec(index)

    def identify(self, requirement_or_candidate):
        return requirement_or_candidate.name

    def get_preference(
        self,
        identifier,
        resolutions,
        candidates,
        information,
        backtrack_causes,
    ):
        return sum(1 for _ in candidates[identifier])

    def find_matches(self, identifier, requirements, incompatibilities):
        name = identifier
        return sorted(
            c
            for c in self.candidates
            if all(self.is_satisfied_by(r, c) for r in requirements[name])
            and all(c.version != i.version for i in incompatibilities[name])
        )

    def is_satisfied_by(self, requirement, candidate):
        return (
            candidate.name == requirement.name
            and candidate.version in requirement.specifier
        )

    def get_dependencies(self, candidate):
        return self.candidates[candidate]


class Reporter(resolvelib.BaseReporter):
    def starting(self):
        print("starting()")

    def starting_round(self, index):
        print(f"starting_round({index})")

    def ending_round(self, index, state):
        print(f"ending_round({index}, ...)")

    def ending(self, state):
        print("ending(...)")

    def adding_requirement(self, requirement, parent):
        print(f"  adding_requirement({requirement}, {parent})")

    def backtracking(self, candidate):
        print(f"  backtracking({candidate})")

    def pinning(self, candidate):
        print(f"  pinning({candidate})")


if __name__ == "__main__":
    from pprint import pprint

    provider = Provider(index.splitlines())
    reporter = Reporter()
    resolver = resolvelib.resolvers.resolution.Resolver(provider, reporter)

    root_reqs = [Requirement("first", SpecifierSet())]
    result = resolver.resolve(root_reqs)

    pprint(result.mapping)
