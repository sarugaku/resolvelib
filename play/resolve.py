"""Implementation to try out the resolver against RequirementsLib.

The `requirementslib.Requirement` interface is used for both requirements and
candidates. A candidate is simply a Requirement instance that guarentees to be
pinned with ``==``.

Recommended cases to test:

* "oslo.utils==1.4.0"
* "requests" "urllib3<1.21.1"
* "pylint==1.9" "pylint-quotes==0.1.9"
* "aiogremlin" "pyyaml"
* Pipfile from pypa/pipenv#1974 (need to modify a bit)
* Pipfile from pypa/pipenv#2529-410209718

"""

import argparse
import operator

from packaging.markers import InvalidMarker, Marker
from requirementslib import Pipfile, Requirement
from requirementslib.models.utils import make_install_requirement

from resolvelib import (
    AbstractProvider, BaseReporter, Resolver,
    NoVersionsAvailable, ResolutionImpossible,
)


parser = argparse.ArgumentParser()
parser.add_argument('packages', metavar='PACKAGE', nargs='*')
parser.add_argument('--project')
parser.add_argument('--dev', action='store_true', default=False)
options = parser.parse_args()


requirements = [Requirement.from_line(line) for line in options.packages]
if options.project:
    pipfile = Pipfile.load(options.project)
    requirements.extend(pipfile.packages.requirements)
    if options.dev:
        requirements.extend(pipfile.dev_packages.requirements)
elif options.dev:
    print('--dev is not useful without --project')


class RequirementsLibSpecificationProvider(AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self):
        self.sources = None
        self.invalid_candidates = set()

    def identify(self, dependency):
        return dependency.normalized_name

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

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

    def _filter_needed(self, requirement):
        if not requirement.markers:
            return True
        try:
            marker = Marker(requirement.markers)
        except InvalidMarker:   # Can't understand the marker, assume true...
            return True
        return marker.evaluate()

    def get_dependencies(self, candidate):
        return [
            r for r in (
                Requirement.from_line(d)
                for d in candidate.get_dependencies(sources=self.sources)
            ) if self._filter_needed(r)
        ]


class StdOutReporter(BaseReporter):
    """Simple reporter that prints things to stdout.
    """
    def starting(self, state):
        self._prev = None

    def _print_dependency(self, graph, key):
        print('{:>30}'.format(graph[key].as_line()))
        has = False
        for parent in graph.iter_parent(key):
            print('{:>31}'.format('(from {})'.format(graph[parent].as_line())))
            has = True
        if not has:
            print('{:>31}'.format('(root dependency)'))

    def ending_round(self, index, state):
        print('\n{:=^30}\n'.format(' Round {} '.format(index)))

        curr = state.graph
        if self._prev is None:
            difference = set(curr.keys())
            changed = set()
        else:
            difference = set(curr.keys()) - set(self._prev.keys())
            changed = set(
                k for k, v in curr.items()
                if k in self._prev and self._prev[k] != v
            )
        self._prev = curr

        if difference:
            print('New Packages: ')
            for k in difference:
                self._print_dependency(state.graph, k)
        else:
            print('No New Packages.')
        print()

        if changed:
            print('Changed Pins:')
            for k in changed:
                self._print_dependency(state.graph, k)
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
        print('{:>31}'.format('(from {})'.format(e.parent.as_line())))
    else:
        print('{:>31}'.format('(root dependency)'))
except ResolutionImpossible as e:
    print('\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:')
    for r in e.requirements:
        print('{:>30}'.format(r.as_line()))
        print()
