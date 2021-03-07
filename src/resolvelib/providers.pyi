from typing import Any, Generic, Iterable, List, Protocol, Union

from .reporters import BaseReporter
from .structs import (
    KT,
    RT,
    CT,
    MatchesType,
    RequirementInformation,
)

class Comparable(Protocol):
    def __lt__(self, __other: Any) -> bool: ...

class AbstractProvider(Generic[RT, CT, KT]):
    def identify(self, requirement_or_candidate: Union[RT, CT]) -> KT: ...
    def get_preference(
        self,
        resolution: CT,
        candidates: Iterable[CT],
        information: RequirementInformation[RT, CT],
    ) -> Comparable: ...
    def find_matches(
        self,
        requirements: List[RT],
        incompatibilities: List[CT],
    ) -> MatchesType: ...
    def is_satisfied_by(self, requirement: RT, candidate: CT) -> bool: ...
    def get_dependencies(self, candidate: CT) -> Iterable[RT]: ...

class AbstractResolver(Generic[RT, CT, KT]):
    base_exception = Exception
    provider: AbstractProvider[RT, CT, KT]
    reporter: BaseReporter
    def __init__(
        self, provider: AbstractProvider[RT, CT, KT], reporter: BaseReporter
    ): ...
