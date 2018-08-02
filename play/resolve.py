"""Implementation to try out the resolver against RequirementsLib.

The `requirementslib.Requirement` interface is used for both requirements and
candidates. A candidate is simply a Requirement instance that guarentees to be
pinned with ``==``.

Recommended cases to test:

* "oslo.utils==1.4.0"
* "requests" "urllib3<1.21.1"
* "pylint==1.9" "pylint-quotes==0.1.9"
* "aiogremlin" "pyyaml"

"""

import argparse
import operator

from requirementslib import Requirement
from requirementslib.models.utils import make_install_requirement

from resolvelib import (
    AbstractProvider, BaseReporter, Resolver,
    NoVersionsAvailable, ResolutionImpossible,
)


parser = argparse.ArgumentParser()
parser.add_argument('packages', metavar='PACKAGE', nargs='+')
options = parser.parse_args()

requirements = [Requirement.from_line(line) for line in options.packages]


class RequirementsLibSpecificationProvider(AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self):
        self.sources = None
        self.invalid_candidates = set()

    def identify(self, dependency):
        return dependency.normalized_name

    def find_matches(self, requirement):
        name = requirement.normalized_name
        markers = requirement.ireq.markers
        extras = requirement.ireq.extras
        icans = sorted(
            requirement.find_all_matches(sources=self.sources),
            key=operator.attrgetter('version'),
        )
        return [Requirement.from_line(str(make_install_requirement(
            name, ican.version, extras=extras, markers=markers,
        ))) for ican in icans]

    def is_satisfied_by(self, requirement, candidate):
        if not requirement.specifiers:  # Short circuit for speed.
            return True
        candidate_line = candidate.as_line()
        if candidate_line in self.invalid_candidates:
            return False
        try:
            version = candidate.get_specifier().version
        except ValueError:
            print('ignoring invalid version {}'.format(candidate_line))
            self.invalid_candidates.add(candidate_line)
            return False
        specifier = requirement.ireq.specifier
        for _ in specifier.filter([version]):
            return True
        return False

    def get_dependencies(self, candidate):
        return [
            Requirement.from_line(d)
            for d in candidate.get_dependencies(sources=self.sources)
        ]


class StdOutReporter(BaseReporter):
    """Simple reporter that prints things to stdout.
    """
    def starting(self, state):
        self._prev = None

    def ending_round(self, index, state):
        print('\n{:=^30}\n'.format(' Round {} '.format(index)))

        curr = state.graph
        if self._prev is None:
            difference = set(curr.keys())
        else:
            difference = set(curr.keys()) - set(self._prev.keys())
        self._prev = curr

        if difference:
            print('New Packages: ')
            for k in difference:
                print('{:>30}'.format(state.graph[k].as_line()))
        else:
            print('No New Packages.')
        print()

    def ending(self, state):
        print('=' * 30)
        print('\nSTABLE PINS:')
        for node in state.graph.values():
            print('{:>30}'.format(node.as_line()))
        print()


r = Resolver(RequirementsLibSpecificationProvider(), StdOutReporter())
try:
    r.resolve(requirements)
except NoVersionsAvailable as e:
    print('\nCANNOT RESOLVE. NO CANDIDATES FOUND FOR:')
    print('{:>30}'.format(e.requirement.as_line()))
    if e.parent:
        print('{:>30}'.format('(from {})'.format(e.parent.as_line())))
    else:
        print('{:>30}'.format('(root dependency)'))
except ResolutionImpossible as e:
    print('\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:')
    for r in e.requirements:
        print('{:>30}'.format(r.as_line()))
        print()
