__all__ = [
    "__version__",
    "AbstractProvider",
    "AbstractResolver",
    "BaseReporter",
    "InconsistentCandidate",
    "Resolver",
    "RequirementsConflicted",
    "ResolutionError",
    "ResolutionImpossible",
    "ResolutionTooDeep",
]

__version__ = "1.0.2.dev0"


from .providers import AbstractProvider
from .reporters import BaseReporter
from .resolvers.abstract import AbstractResolver
from .resolvers.criterion import (
    InconsistentCandidate,
    RequirementsConflicted,
    ResolutionError,
    ResolutionImpossible,
    ResolutionTooDeep,
    Resolver,
)
