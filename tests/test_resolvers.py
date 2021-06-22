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
        def __init__(self, requirement, candidate):
            self.requirement = requirement
            self.candidate = candidate

        def identify(self, requirement_or_candidate):
            assert requirement_or_candidate is self.requirement
            return requirement_or_candidate

        def get_preference(self, **_):
            return 0

        def get_dependencies(self, **_):
            return []

        def find_matches(self, identifier, requirements, incompatibilities):
            assert list(requirements[identifier]) == [self.requirement]
            assert next(incompatibilities[identifier], None) is None
            return [self.candidate]

        def is_satisfied_by(self, requirement, candidate):
            assert requirement is self.requirement
            assert candidate is self.candidate
            return False

    resolver = Resolver(Provider(requirement, candidate), BaseReporter())

    with pytest.raises(InconsistentCandidate) as ctx:
        resolver.resolve([requirement])

    assert str(ctx.value) == "Provided candidate 'bar' does not satisfy 'foo'"
    assert ctx.value.candidate is candidate
    assert list(ctx.value.criterion.iter_requirement()) == [requirement]


@pytest.mark.parametrize("specifiers", [["1", "12"], ["12", "1"]])
def test_candidate_depends_on_requirements_of_same_identifier(specifiers):
    # This test ensures if a candidate has multiple dependencies under the same
    # identifier, all dependencies of that identifier are correctly pulled in.
    # The parametrization ensures both requirement ordering work.

    # Parent depends on child twice, one allows v2, the other does not.
    # Each candidate is a 3-tuple (name, version, dependencies).
    # Each requirement is a 2-tuple (name, allowed_versions).
    # Candidate v2 is in from so it is preferred when both are allowed.
    all_candidates = {
        "parent": [("parent", "1", [("child", s) for s in specifiers])],
        "child": [("child", "2", []), ("child", "1", [])],
    }

    class Provider(AbstractProvider):
        def identify(self, requirement_or_candidate):
            return requirement_or_candidate[0]

        def get_preference(self, **_):
            return 0

        def get_dependencies(self, candidate):
            return candidate[2]

        def find_matches(self, identifier, requirements, incompatibilities):
            assert not list(incompatibilities[identifier])
            return (
                candidate
                for candidate in all_candidates[identifier]
                if all(candidate[1] in r[1] for r in requirements[identifier])
            )

        def is_satisfied_by(self, requirement, candidate):
            return candidate[1] in requirement[1]

    # Now when resolved, both requirements to child specified by parent should
    # be pulled, and the resolver should choose v1, not v2 (happens if the
    # v1-only requirement is dropped).
    resolver = Resolver(Provider(), BaseReporter())
    result = resolver.resolve([("parent", {"1"})])

    assert set(result.mapping) == {"parent", "child"}
    assert result.mapping["child"] == ("child", "1", [])
