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
