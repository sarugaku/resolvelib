from packaging.version import Version
from pkg_resources import Requirement
from typing import Collection, Iterator, List, Mapping, Sequence, Set, Tuple, Union

from resolvelib import (
    AbstractProvider,
)
from resolvelib.resolvers import (
    Criterion,
    Resolution,
    Resolver,
    RequirementInformation,
    RequirementsConflicted,
)


def test_pin_conflict_with_self(monkeypatch, reporter) -> None:
    """
    Verify correct behavior of attempting to pin a candidate version that conflicts with a previously pinned (now invalidated)
    version for that same candidate (#91).
    """
    Candidate = Tuple[str, Version, Sequence[str]]  # name, version, requirements
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

    class Provider(AbstractProvider):  # AbstractProvider[str, Candidate, str]
        def identify(self, requirement_or_candidate: Union[str, Candidate]) -> str:
            result: str = (
                Requirement.parse(requirement_or_candidate).key
                if isinstance(requirement_or_candidate, str)
                else requirement_or_candidate[0]
            )
            assert result in all_candidates, "unknown requirement_or_candidate"
            return result

        def get_preference(self, identifier: str, *args: object, **kwargs: object) -> str:
            # prefer child over parent (alphabetically)
            return identifier

        def get_dependencies(self, candidate: Candidate) -> Sequence[str]:
            return candidate[2]

        def find_matches(
            self,
            identifier: str,
            requirements: Mapping[str, Iterator[str]],
            incompatibilities: Mapping[str, Iterator[Candidate]]
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
            return str(candidate[1]) in Requirement.parse(requirement)

    # patch Resolution._get_updated_criteria to collect rejected states
    rejected_criteria: List[Criterion] = []
    get_updated_criterion_orig = Resolution._get_updated_criteria

    def get_updated_criterion_patch(self, candidate) -> None:
        try:
            return get_updated_criterion_orig(self, candidate)
        except RequirementsConflicted as e:
            rejected_criteria.append(e.criterion)
            raise

    monkeypatch.setattr(
        Resolution, "_get_updated_criteria", get_updated_criterion_patch
    )

    resolver: Resolver = Resolver(Provider(), reporter)
    result = resolver.resolve(["child", "parent"])

    def get_child_versions(information: Collection[RequirementInformation[str, Candidate]]) -> Set[str]:
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

    # TODO: rename + move test
    # TODO: style check?
