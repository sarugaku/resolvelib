import collections

from .structs import DirectedGraph


RequirementInformation = collections.namedtuple('RequirementInformation', [
    'requirement', 'parent',
])


class NoVersionsAvailable(Exception):
    def __init__(self, requirement, parent):
        super(NoVersionsAvailable, self).__init__()
        self.requirement = requirement
        self.parent = parent


class RequirementsConflicted(Exception):
    def __init__(self, criterion):
        super(RequirementsConflicted, self).__init__()
        self.criterion = criterion


class Criterion(object):
    """Internal representation of a criterion.

    This holds two attributes:

    * `information` is a collection of `RequirementInformation` pairs. Each
      pair is a requirement contributing to this criterion, and the candidate
      that provides the requirement.
    * `candidates` is a collection containing all possible candidates deducted
      from the union of contributing requirements. It should never be empty.
    """
    def __init__(self, candidates, information):
        self.candidates = candidates
        self.information = information

    @classmethod
    def from_requirement(cls, provider, requirement, parent):
        """Build an instance from a requirement.
        """
        candidates = provider.find_matches(requirement)
        if not candidates:
            raise NoVersionsAvailable(requirement, parent)
        return cls(
            candidates=candidates,
            information=[RequirementInformation(requirement, parent)],
        )

    def iter_requirement(self):
        return (i.requirement for i in self.information)

    def iter_parent(self):
        return (i.parent for i in self.information)

    def merged_with(self, provider, requirement, parent):
        """Build a new instance from this and a new requirement.
        """
        infos = list(self.information)
        infos.append(RequirementInformation(requirement, parent))
        candidates = [
            c for c in self.candidates
            if provider.is_satisfied_by(requirement, c)
        ]
        if not candidates:
            raise RequirementsConflicted(self)
        return type(self)(candidates, infos)


class State(object):
    """Hold th resolution state in a round.
    """
    def __init__(self, other=None):
        if other is None:
            self.mapping = {}
            self.graph = DirectedGraph()
        else:
            self.mapping = dict(other.mapping)
            self.graph = DirectedGraph(other.graph)
        self.graph.add(None)    # Root requirement.

    def get_candidate(self, name):
        return self.mapping[name]

    def iter_children(self, name):
        return self.graph.iter_children(name)

    def iter_parents(self, name):
        return self.graph.iter_parents(name)

    def pin(self, candidate, name, parents):
        self.mapping[name] = candidate
        self.graph.add(name)
        for parent in parents:
            self.graph.connect(parent, name)


class ResolutionError(Exception):
    pass


class ResolutionImpossible(ResolutionError):
    def __init__(self, requirements):
        super(ResolutionImpossible, self).__init__()
        self.requirements = requirements


class ResolutionTooDeep(ResolutionError):
    def __init__(self, round_count):
        super(ResolutionTooDeep, self).__init__(round_count)
        self.round_count = round_count


class Resolution(object):
    """Stateful resolution object.

    This is designed as a one-off object that holds information to kick start
    the resolution process, and holds the results afterwards.
    """
    def __init__(self, provider, reporter):
        self._p = provider
        self._r = reporter
        self._criteria = {}
        self._states = []

    @property
    def state(self):
        try:
            return self._states[-1]
        except IndexError:
            raise AttributeError('state')

    def _contribute_to_criteria(self, requirement, parent):
        name = self._p.identify(requirement)
        try:
            crit = self._criteria[name]
        except KeyError:
            crit = Criterion.from_requirement(self._p, requirement, parent)
        else:
            crit = crit.merged_with(self._p, requirement, parent)
        self._criteria[name] = crit

    def _get_criterion_item_preference(self, item):
        name, criterion = item
        try:
            pinned = self._states[-1].mapping[name]
        except (IndexError, KeyError):
            pinned = None
        return self._p.get_preference(
            pinned, criterion.candidates, criterion.information,
        )

    def _check_pinnability(self, candidate):
        backup = self._criteria.copy()
        try:
            for subdep in self._p.get_dependencies(candidate):
                self._contribute_to_criteria(subdep, parent=candidate)
        except RequirementsConflicted:
            self._criteria = backup
            return False
        return True

    def _pin_criteria(self):
        state = self._states[-1]
        criterion_items = sorted(
            self._criteria.items(),
            key=self._get_criterion_item_preference,
        )
        for name, criterion in criterion_items:
            try:
                pin = state.mapping[name]
            except KeyError:
                satisfied = False
            else:
                satisfied = all(
                    self._p.is_satisfied_by(r, pin)
                    for r in criterion.iter_requirement()
                )
            if satisfied:   # If the current pin already works...
                continue
            candidates = list(criterion.candidates)
            while candidates:
                candidate = candidates.pop()
                if not self._check_pinnability(candidate):
                    continue
                parents = [
                    None if parent is None else self._p.identify(parent)
                    for parent in criterion.iter_parent()
                ]
                state.pin(candidate, name, parents)
                break
            else:   # All candidates tried, nothing works. Give up?
                raise ResolutionImpossible(list(criterion.iter_requirement()))

    def resolve(self, requirements, max_rounds):
        if self._states:
            raise RuntimeError('already resolved')

        for requirement in requirements:
            try:
                self._contribute_to_criteria(requirement, parent=None)
            except RequirementsConflicted as e:
                # If initial requirements conflict, nothing would ever work.
                raise ResolutionImpossible(e.requirements + [requirement])

        last = None
        self._r.starting()

        for round_index in range(max_rounds):
            self._r.starting_round(round_index)

            self._states.append(State(last))
            self._pin_criteria()

            curr = self._states[-1]
            if last is not None and len(curr.mapping) == len(last.mapping):
                # Nothing new added. Done! Remove the duplicated entry.
                self._states.pop()
                self._r.ending(last)
                return
            last = curr

            self._r.ending_round(round_index, curr)

        raise ResolutionTooDeep(max_rounds)


class Resolver(object):
    """The thing that performs the actual resolution work.
    """
    def __init__(self, provider, reporter):
        self.provider = provider
        self.reporter = reporter

    def resolve(self, requirements, max_rounds=20):
        """Take a collection of constraints, spit out the resolution result.

        May raise the following exceptions if a resolution cannot be found:

        * `NoVersionsAvailable`: A requirement has no available candidates.
        * `ResolutionImpossible`: A resolution cannot be found for the given
            combination of requirements.
        * `ResolutionTooDeep`: The dependency tree is too deeply nested and
            the resolver gave up. This is usually caused by a circular
            dependency, but you can try to resolve this by increasing the
            `max_rounds` argument.
        """
        resolution = Resolution(self.provider, self.reporter)
        resolution.resolve(requirements, max_rounds=max_rounds)
        return resolution
