import argparse
import operator

from requirementslib import Requirement
from requirementslib.models.utils import make_install_requirement

from resolvelib import AbstractProvider, BaseReporter, Resolver


parser = argparse.ArgumentParser()
parser.add_argument('packages', metavar='PACKAGE', nargs='+')
options = parser.parse_args()

requirements = [Requirement.from_line(line) for line in options.packages]


class RequirementsLibSpecificationProvider(AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self):
        self.sources = None

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

    def filter_satisfied(self, candidates, requirement):
        if requirement.specifiers:
            specifier = requirement.ireq.specifier
            candidates = (
                c for c in candidates
                if next(specifier.filter([c.get_specifier().version]), None)
            )
        return list(candidates)

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
        print('\nStable Pins:')
        for node in state.graph.values():
            print('{:>30}'.format(node.as_line()))
        print()


r = Resolver(RequirementsLibSpecificationProvider(), StdOutReporter())
r.resolve(requirements)
