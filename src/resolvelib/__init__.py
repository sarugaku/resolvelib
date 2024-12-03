__all__ = [
    "AbstractProvider",
    "AbstractResolver",
    "BaseReporter",
    "InconsistentCandidate",
    "RequirementsConflicted",
    "ResolutionError",
    "ResolutionImpossible",
    "ResolutionTooDeep",
    "Resolver",
    "__version__",
]

__version__ = "1.1.1dev0"


from .providers import AbstractProvider
from .reporters import BaseReporter
from .resolvers import (
    AbstractResolver,
    InconsistentCandidate,
    RequirementsConflicted,
    ResolutionError,
    ResolutionImpossible,
    ResolutionTooDeep,
    Resolver,
)
