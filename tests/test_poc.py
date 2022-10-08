from pkg_resources import Requirement
from typing import List, Sequence, Set

from resolvelib import (
    AbstractProvider,
    BaseReporter,
)
from resolvelib.resolvers import (
    Criterion,
    Resolution,
    Resolver,
    RequirementInformation,
    RequirementsConflicted,
)


def test_poc(monkeypatch, reporter):
    all_candidates = {
        "parent": [("parent", "1", ["child<2"])],
        "child": [
            ("child", "2", ["grandchild>=2"]),
            ("child", "1", ["grandchild<2"]),
            ("child", "0.1", ["grandchild"]),
        ],
        "grandchild": [
            ("grandchild", "2", []),
            ("grandchild", "1", []),
        ],
    }

    class Provider(AbstractProvider):
        def identify(self, requirement_or_candidate):
            result: str = (
                Requirement.parse(requirement_or_candidate).key
                if isinstance(requirement_or_candidate, str)
                else requirement_or_candidate[0]
            )
            assert result in all_candidates
            return result

        def get_preference(self, *, identifier, **_):
            # prefer child over parent (alphabetically)
            return identifier

        def get_dependencies(self, candidate):
            return candidate[2]

        def find_matches(self, identifier, requirements, incompatibilities):
            return (
                candidate
                for candidate in all_candidates[identifier]
                if all(
                    candidate[1] in Requirement.parse(req)
                    for req in requirements[identifier]
                )
                if candidate not in incompatibilities[identifier]
            )

        def is_satisfied_by(self, requirement, candidate):
            return candidate[1] in Requirement.parse(requirement)

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

    resolver = Resolver(Provider(), reporter)
    result = resolver.resolve(["child", "parent"])

    def get_child_versions(information: Sequence[RequirementInformation]) -> Set[str]:
        return {
            inf[1][1]
            for inf in information
            if inf[1][0] == "child"
        }

    # verify that none of the rejected criteria are based on more than one candidate for
    # child
    assert not any(
        len(get_child_versions(criterion.information)) > 1
        for criterion in rejected_criteria
    )

    assert set(result.mapping) == {"parent", "child", "grandchild"}
    assert result.mapping["parent"][1] == "1"
    assert result.mapping["child"][1] == "1"
    assert result.mapping["grandchild"][1] == "1"

    # TODO: review test case
    # TODO: rename + move test
    # TODO: remove
    assert False
