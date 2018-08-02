import collections

from .structs import DirectedGraph


RequirementInformation = collections.namedtuple('RequirementInformation', [
    'requirement', 'parent',
])


class RequirementsConflicted(Exception):
    pass


class Dependency(object):
    """Internal representation of a dependency.
    """
    def __init__(self, candidates, req_infos):
        self.candidates = candidates
        self._req_infos = req_infos

    @classmethod
    def from_requirment(cls, provider, requirement, parent):
        """Build an instance from a requirement.
        """
        candidates = provider.find_matches(requirement)
        return cls(
            candidates=candidates,
            req_infos=[RequirementInformation(requirement, parent)],
        )

    def iter_requirement(self):
        return (i.requirement for i in self._req_infos)

    def iter_parent(self):
        return (i.parent for i in self._req_infos)

    def merged_with(self, provider, requirement, parent):
        """Build a new instance from this and a new requirement.
        """
        infos = list(self._req_infos)
        infos.append(RequirementInformation(requirement, parent))
        candidates = [
            c for c in self.candidates
            if provider.is_satisfied_by(requirement, c)
        ]
        if not candidates:
            raise RequirementsConflicted
        return type(self)(candidates, infos)


class ResolutionError(Exception):
    pass


class ResolutionImpossible(ResolutionError):
    pass


class ResolutionTooDeep(ResolutionError):
    pass


class Resolution(object):
    """Stateful resolution object.

    This is designed as a one-off object that holds information to kick start
    the resolution process, and holds the results afterwards.
    """
    def __init__(self, provider, reporter):
        self._p = provider
        self._r = reporter
        self._dependencies = {}
        self._resolved = []     # Resolution state after each round.

    @property
    def dependencies(self):
        return list(self._dependencies.values())

    @property
    def graph(self):
        if not self._resolved:
            raise AttributeError('graph')
        return self._resolved[-1]

    def _add_constraint(self, requirement, parent):
        name = self._p.identify(requirement)
        if name in self._dependencies:
            dep = self._dependencies[name]
            dep = dep.merged_with(self._p, requirement, parent)
        else:
            dep = Dependency.from_requirment(self._p, requirement, parent)
        self._dependencies[name] = dep

    def _check_pinnability(self, candidate):
        subdeps = self._p.get_dependencies(candidate)
        backup = self._dependencies.copy()
        try:
            for subdep in subdeps:
                self._add_constraint(subdep, parent=candidate)
        except RequirementsConflicted:
            self._dependencies = backup
            return False
        return True

    def _pin_dependencies(self):
        graph = self._resolved[-1]
        for name, dependency in list(self._dependencies.items()):
            try:
                pin = graph[name]
            except KeyError:
                satisfied = False
            else:
                satisfied = all(
                    self._p.is_satisfied_by(r, pin)
                    for r in dependency.iter_requirement()
                )
            if satisfied:   # If the current pin already works...
                continue
            candidates = list(dependency.candidates)
            while candidates:
                candidate = candidates.pop()
                if not self._check_pinnability(candidate):
                    continue
                graph[name] = candidate
                for parent in dependency.iter_parent():
                    if parent:
                        graph.add_edge(self._p.identify(parent), name)
                break
            else:   # All candidates tried, nothing works. Give up?
                raise ResolutionImpossible

    def resolve(self, requirements, max_rounds=20):
        if self._resolved:
            raise RuntimeError('already resolved')

        try:    # If initial dependencies conflict, nothing would ever work.
            for requirement in requirements:
                self._add_constraint(requirement, parent=None)
        except RequirementsConflicted:
            raise ResolutionImpossible

        last_result = None
        self._r.starting(self)
        for round_index in range(max_rounds):
            self._r.starting_round(round_index, self)
            self._resolved.append(DirectedGraph(last_result))
            self._pin_dependencies()
            current_result = self._resolved[-1]
            if last_result and len(current_result) == len(last_result):
                # Nothing new added. Done! Remove the duplicated entry.
                self._resolved.pop()
                self._r.ending(self)
                return
            last_result = current_result
            self._r.ending_round(round_index, self)

        raise ResolutionTooDeep(max_rounds)


class Resolver(object):
    """The thing that performs the actual resolution work.
    """
    def __init__(self, provider, reporter):
        self.provider = provider
        self.reporter = reporter

    def resolve(self, requirements):
        """Take a collection of constraints, spit out the resolution result.

        Raises `ResolutionImpossible` if a resolution cannot be found.
        """
        resolution = Resolution(self.provider, self.reporter)
        resolution.resolve(requirements)
        return resolution
