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
import os

from requirementslib import Pipfile, Requirement
from requirementslib.models.utils import make_install_requirement

from resolvelib import (
    AbstractProvider, BaseReporter, Resolver,
    NoVersionsAvailable, ResolutionImpossible,
)


parser = argparse.ArgumentParser()
parser.add_argument('packages', metavar='PACKAGE', nargs='*')
parser.add_argument('--project')
options = parser.parse_args()


requirements = [Requirement.from_line(line) for line in options.packages]
if options.project:
    os.chdir(options.project)
    pipfile = Pipfile.load(options.project)
    requirements.extend(pipfile.packages.requirements)
    requirements.extend(pipfile.dev_packages.requirements)


def _filter_needed(requirement):
    if not requirement.markers:
        return True
    return requirement.ireq.match_markers()


class RequirementsLibProvider(AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self, root_requirements):
        self.sources = None
        self.invalid_candidates = set()
        self.non_named_requirements = {
            requirement.name: requirement
            for requirement in root_requirements
            if not requirement.is_named
        }

    def identify(self, dependency):
        return dependency.normalized_name

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        name = requirement.normalized_name
        if name in self.non_named_requirements:
            return [self.non_named_requirements[name]]
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
        name = requirement.normalized_name
        if name in self.non_named_requirements:
            return self.non_named_requirements[name] == requirement
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
        return requirement.ireq.specifier.contains(version)

    def get_dependencies(self, candidate):
        try:
            dependencies = candidate.get_dependencies(sources=self.sources)
        except Exception as e:
            print('failed to get dependencies for {0!r}: {1}'.format(
                candidate.as_line(), e,
            ))
            return []
        return [
            r for r in (Requirement.from_line(d) for d in dependencies)
            if _filter_needed(r)
        ]


def _print_title(text):
    print('\n{:=^84}\n'.format(text))


def _print_requirement(r, end='\n'):
    print('{:>40}'.format(r.as_line()), end=end)


def _key_sort(name):
    if name is None:
        return (-1, '')
    return (ord(name[0].lower()), name)


def _print_dependency(state, key):
    _print_requirement(state.mapping[key], end='')
    parents = sorted(state.graph.iter_parents(key), key=_key_sort)
    for i, p in enumerate(parents):
        if p is None:
            line = '(user)'
        else:
            line = state.mapping[p].as_line()
        if i == 0:
            padding = ' <= '
        else:
            padding = ' ' * 44
        print('{pad}{line}'.format(pad=padding, line=line))


class StdOutReporter(BaseReporter):
    """Simple reporter that prints things to stdout.
    """
    def starting(self):
        self._prev = None

    def ending_round(self, index, state):
        _print_title(' Round {} '.format(index))
        mapping = state.mapping
        if self._prev is None:
            difference = set(mapping.keys())
            changed = set()
        else:
            difference = set(mapping.keys()) - set(self._prev.keys())
            changed = set(
                k for k, v in mapping.items()
                if k in self._prev and self._prev[k] != v
            )
        self._prev = mapping

        if difference:
            print('New pins: ')
            for k in difference:
                _print_dependency(state, k)
        print()

        if changed:
            print('Changed pins:')
            for k in changed:
                _print_dependency(state, k)
        print()


_print_title(' User requirements ')
for r in requirements:
    _print_requirement(r)


r = Resolver(RequirementsLibProvider(requirements), StdOutReporter())
try:
    state = r.resolve(requirements)
except NoVersionsAvailable as e:
    print('\nCANNOT RESOLVE. NO CANDIDATES FOUND FOR:')
    print('{:>40}'.format(e.requirement.as_line()))
    if e.parent:
        print('{:>41}'.format('(from {})'.format(e.parent.as_line())))
    else:
        print('{:>41}'.format('(root dependency)'))
except ResolutionImpossible as e:
    print('\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:')
    for r in e.requirements:
        _print_requirement(r)
else:
    _print_title(' STABLE PINS ')
    for k in sorted(state.mapping):
        _print_dependency(state, k)

print()
