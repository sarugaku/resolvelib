import collections
import operator

import pytest

from resolvelib import (
    AbstractProvider,
    BaseReporter,
    InconsistentCandidate,
    Resolver,
)


def test_candidate_inconsistent_error():
    requirement = "foo"
    candidate = "bar"

    class Provider(AbstractProvider):
        def identify(self, d):
            assert d is requirement or d is candidate
            return d

        def get_preference(self, *_):
            return 0

        def get_dependencies(self, _):
            return []

        def find_matches(self, rs):
            assert len(rs) == 1 and rs[0] is requirement
            return [candidate]

        def is_satisfied_by(self, r, c):
            assert r is requirement
            assert c is candidate
            return False

    resolver = Resolver(Provider(), BaseReporter())

    with pytest.raises(InconsistentCandidate) as ctx:
        resolver.resolve([requirement])

    assert str(ctx.value) == "Provided candidate 'bar' does not satisfy 'foo'"
    assert ctx.value.candidate is candidate
    assert list(ctx.value.criterion.iter_requirement()) == [requirement]


def test_criteria_pruning(reporter_cls, base_reporter):
    C = collections.namedtuple("C", "name version dependencies")
    R = collections.namedtuple("R", "name versions")

    # Both C versions have the same dependencies. The resolver should be start
    # enough to not pin C1 after C2 fails.
    candidate_definitions = [
        C("a", 1, []),
        C("a", 2, []),
        C("b", 1, [R("a", [2])]),
        C("c", 1, [R("b", [1]), R("a", [2])]),
        C("c", 2, [R("b", [1]), R("a", [1])]),
        C("c", 3, [R("b", [1]), R("a", [1])]),
    ]

    class Provider(AbstractProvider):
        def identify(self, d):
            return d.name

        def get_preference(self, resolution, candidates, information):
            # Order by name for reproducibility.
            return next(iter(candidates)).name

        def find_matches(self, requirements):
            if not requirements:
                return ()
            matches = (
                c
                for c in candidate_definitions
                if all(self.is_satisfied_by(r, c) for r in requirements)
            )
            return sorted(
                matches,
                key=operator.attrgetter("version"),
                reverse=True,
            )

        def is_satisfied_by(self, requirement, candidate):
            return (
                candidate.name == requirement.name
                and candidate.version in requirement.versions
            )

        def match_identically(self, reqs1, reqs2):
            vers1 = collections.defaultdict(set)
            vers2 = collections.defaultdict(set)
            for rs, vs in [(reqs1, vers1), (reqs2, vers2)]:
                for r in rs:
                    vs[r.name] = vs[r.name].union(r.versions)
            return vers1 == vers2

        def get_dependencies(self, candidate):
            return candidate.dependencies

    class Reporter(reporter_cls):
        def __init__(self):
            super(Reporter, self).__init__()
            self.pinned_c = []

        def pinning(self, candidate):
            super(Reporter, self).pinning(candidate)
            if candidate.name == "c":
                self.pinned_c.append(candidate.version)

    reporter = Reporter()
    result = Resolver(Provider(), reporter).resolve([R("c", [1, 2, 3])])

    pinned_versions = {c.name: c.version for c in result.mapping.values()}
    assert pinned_versions == {"a": 2, "b": 1, "c": 1}
    assert reporter.pinned_c == [3, 1], "should be smart enough to skip c==2"
