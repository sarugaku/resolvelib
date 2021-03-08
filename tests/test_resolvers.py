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

        def find_matches(self, requirements):
            assert list(requirements) == [self.requirement]
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
