__all__ = [
    '__version__',
    'AbstractProvider', 'BaseReporter',
    'Dependency', 'NoVersionsAvailable', 'RequirementsConflicted',
    'Resolver', 'ResolutionError', 'ResolutionImpossible', 'ResolutionTooDeep',
]

__version__ = '0.0.0.dev0'


from .providers import AbstractProvider
from .reporters import BaseReporter
from .resolvers import (
    Dependency, NoVersionsAvailable, RequirementsConflicted,
    Resolver, ResolutionError, ResolutionImpossible, ResolutionTooDeep,
)
