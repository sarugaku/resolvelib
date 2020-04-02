from packaging.specifiers import SpecifierSet
from packaging.version import Version

import resolvelib

spec = """\
A 1.0.0
    B >= 1.0.0
    C >= 2.0.0
B 1.0.0
C 1.0.0
C 2.0.0
C 3.0.0
"""

def splitstrip(s, parts):
    return [item.strip() for item in s.strip().split(maxsplit=parts-1)]

def read_spec(lines):
    candidates = {}
    latest = None
    for line in lines:
        if not line or line.startswith('#'):
            continue
        if not line.startswith(" "):
            name, version = splitstrip(line, 2)
            version = Version(version)
            latest = (name, version)
            candidates[latest] = set()
        else:
            if latest is None:
                raise RuntimeError("Spec has dependencies before first candidate")
            name, spec = splitstrip(line, 2)
            spec = SpecifierSet(spec)
            candidates[latest].add((name, spec))
    return candidates

class Provider(resolvelib.AbstractProvider):
    def __init__(self, spec):
        self.candidates = read_spec(spec)
    def identify(self, dependency):
        return dependency[0]
    def get_preference(self, resolution, candidates, information):
        return len(candidates)
    def find_matches(self, requirement):
        deps = [
            (n, v) for (n, v) in sorted(self.candidates, reverse=True)
            if n == requirement[0] and v in requirement[1]
        ]
        deps.sort()
        return deps
    def is_satisfied_by(self, requirement, candidate):
        return (
            candidate[0] == requirement[0] and
            candidate[1] in requirement[1]
        )
    def get_dependencies(self, candidate):
        return self.candidates[candidate]

class Reporter(resolvelib.BaseReporter):

    def adding_requirement(self, requirement):
        """Adding a new requirement into the resolve criteria.
        """
        print(f"Adding {requirement}")

    def backtracking(self, candidate):
        """Backtracking - removing a candidate after failing to pin.
        """
        print(f"Backtracking - removing {candidate}")

    def pinning(self, candidate):
        """Pinning - adding a candidate to the potential solution.
        """
        print(f"Pinned {candidate}")

def print_result(result):
    for k, v in result.mapping.items():
        print(f"{k}: {v}")

if __name__ == '__main__':
    provider = Provider(spec.splitlines())
    from pprint import pprint
    pprint(provider.candidates)
    resolver = resolvelib.Resolver(provider, Reporter())
    result = resolver.resolve([('A', SpecifierSet(">=1.0"))])
    print_result(result)
