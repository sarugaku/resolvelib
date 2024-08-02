from __future__ import annotations

from collections import namedtuple
from typing import TYPE_CHECKING, Any, Iterator, Sequence, Tuple

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

from resolvelib import (
    AbstractProvider,
    BaseReporter,
    InconsistentCandidate,
    ResolutionImpossible,
)
from resolvelib.resolvers import (
    RequirementsConflicted,
    Resolution,
    Resolver,
)

if TYPE_CHECKING:
    from typing import Iterable, Mapping

    from resolvelib.resolvers import (
        Criterion,
        RequirementInformation,
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


def test_resolving_conflicts():
    Candidate = namedtuple(
        "Candidate", ["name", "version", "requirements"]
    )  # name, version, requirements
    _Requirement = namedtuple("Requirement", ["name", "versions"])  # name, versions
    a1 = Candidate("a", 1, [_Requirement("q", {1})])
    a2 = Candidate("a", 2, [_Requirement("q", {2})])
    b = Candidate("b", 1, [_Requirement("q", {1})])
    q1 = Candidate("q", 1, [])
    q2 = Candidate("q", 2, [])
    all_candidates = {
        "a": [a1, a2],
        "b": [b],
        "q": [q1, q2],
    }

    class Reporter(BaseReporter):
        def __init__(self):
            self.backtracking_causes = None

        def resolving_conflicts(self, causes):
            self.backtracking_causes = causes

    class Provider(AbstractProvider):
        def identify(self, requirement_or_candidate):
            return requirement_or_candidate[0]

        def get_preference(self, **_):
            return 0

        def get_dependencies(self, candidate):
            return candidate.requirements

        def find_matches(self, identifier, requirements, incompatibilities):
            bad_versions = {c.version for c in incompatibilities[identifier]}
            candidates = [
                c
                for c in all_candidates[identifier]
                if all(c.version in r.versions for r in requirements[identifier])
                and c.version not in bad_versions
            ]
            return sorted(candidates, key=lambda c: c.version, reverse=True)

        def is_satisfied_by(self, requirement, candidate):
            return candidate.version in requirement.versions

    def run_resolver(*args):
        reporter = Reporter()
        resolver = Resolver(Provider(), reporter)
        try:
            resolver.resolve(*args)
            return reporter.backtracking_causes
        except ResolutionImpossible as e:
            return e.causes

    backtracking_causes = run_resolver(
        [_Requirement("a", {1, 2}), _Requirement("b", {1})]
    )
    exception_causes = run_resolver([_Requirement("a", {2}), _Requirement("b", {1})])
    assert exception_causes == backtracking_causes


def test_pin_conflict_with_self(monkeypatch, reporter):
    # type: (Any, BaseReporter) -> None
    """
    Verify correct behavior of attempting to pin a candidate version that conflicts
    with a previously pinned (now invalidated) version for that same candidate (#91).
    """
    Candidate = Tuple[str, Version, Sequence[str]]

    all_candidates: Mapping[str, Sequence[Candidate]] = {
        "parent": [("parent", Version("1"), ["child<2"])],
        "child": [
            ("child", Version("2"), ["grandchild>=2"]),
            ("child", Version("1"), ["grandchild<2"]),
            ("child", Version("0.1"), ["grandchild"]),
        ],
        "grandchild": [
            ("grandchild", Version("2"), []),
            ("grandchild", Version("1"), []),
        ],
    }

    class Provider(AbstractProvider[str, Candidate, str]):
        def identify(self, requirement_or_candidate: str | Candidate) -> str:
            result = (
                Requirement(requirement_or_candidate).name
                if isinstance(requirement_or_candidate, str)
                else requirement_or_candidate[0]
            )
            assert result in all_candidates, "unknown requirement_or_candidate"
            return result

        def get_preference(self, identifier: str, *args: Any, **kwargs: Any) -> str:
            # prefer child over parent (alphabetically)
            return identifier

        def get_dependencies(self, candidate: Candidate) -> Sequence[str]:
            return candidate[2]

        def find_matches(
            self,
            identifier: str,
            requirements: Mapping[str, Iterator[str]],
            incompatibilities: Mapping[str, Iterator[Candidate]],
        ) -> Iterator[Candidate]:
            return (
                candidate
                for candidate in all_candidates[identifier]
                if all(
                    self.is_satisfied_by(req, candidate)
                    for req in requirements[identifier]
                )
                if candidate not in incompatibilities[identifier]
            )

        def is_satisfied_by(self, requirement: str, candidate: Candidate) -> bool:
            return candidate[1] in Requirement(requirement).specifier

    # patch Resolution._get_updated_criteria to collect rejected states
    rejected_criteria: list[Criterion] = []
    get_updated_criteria_orig = Resolution._get_updated_criteria

    def get_updated_criteria_patch(self, candidate):
        try:
            return get_updated_criteria_orig(self, candidate)
        except RequirementsConflicted as e:
            rejected_criteria.append(e.criterion)
            raise

    monkeypatch.setattr(Resolution, "_get_updated_criteria", get_updated_criteria_patch)

    resolver: Resolver[str, Candidate, str] = Resolver(Provider(), reporter)
    result = resolver.resolve(["child", "parent"])

    def get_child_versions(
        information: Iterable[RequirementInformation[str, Candidate]],
    ) -> set[str]:
        return {
            str(inf.parent[1])
            for inf in information
            if inf.parent is not None and inf.parent[0] == "child"
        }

    # verify that none of the rejected criteria are based on more than one candidate for
    # child
    assert not any(
        len(get_child_versions(criterion.information)) > 1
        for criterion in rejected_criteria
    )

    assert set(result.mapping) == {"parent", "child", "grandchild"}
    assert result.mapping["parent"][1] == Version("1")
    assert result.mapping["child"][1] == Version("1")
    assert result.mapping["grandchild"][1] == Version("1")
