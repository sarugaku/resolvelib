from ..structs import RequirementInformation
from .abstract import AbstractResolver, Result
from .criterion import (
    InconsistentCandidate,
    RequirementsConflicted,
    ResolutionError,
    ResolutionImpossible,
    ResolutionTooDeep,
    ResolverException,
)
