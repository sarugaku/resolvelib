import collections

from .structs import DirectedAcyclicGraph


Save = collections.namedtuple('Save', 'candidates graph conflicts')


STATE_PROGRESS = 'progress'
STATE_REGRESS = 'regress'
STATE_END = '__end__'


class CandidateNotFound(Exception):
    pass


class ResolutionImpossible(Exception):
    pass


class ResolutionStateMachine(object):
    """State machine to handle the resolution progress.
    """
    def __init__(self, provider, requirements):
        # TODO: We also need a way to trace each entry in the resolution to
        # what resulted it being included, so we can add appropriate
        # environment markers to it for the installation process.
        self.p = provider

        self.saves = []
        self.graph = DirectedAcyclicGraph()
        self.conflicts = {}     # (name, version) -> List[(name, version)]

        self.requirements = [requirements]
        self.candidates = {
            self.p.identify(r): self.p.find_matches(r)
            for r in requirements
        }

    def _save(self):
        self.saves.append(Save(
            candidates={k: list(v) for k, v in self.candidates.items()},
            graph=DirectedAcyclicGraph(self.graph),
            conflicts={k: list(v) for k, v in self.conflicts.items()},
        ))

    def _load(self):
        try:
            self.candidates, self.graph, self.conflicts = self.saves.pop()
        except IndexError:
            raise ResolutionImpossible

    def _add_candidate(self, requirement):
        package = self.p.identify(requirement)
        try:
            candidate = self.graph[package]
        except KeyError:
            try:
                candidate = self.candidates[package].pop()
            except IndexError:
                raise CandidateNotFound(package)
            self.graph[package] = candidate
        else:
            if not self.p.filter_satisfied([candidate], requirement):
                self._add_conflict(candidate, )
                raise CandidateNotFound(package)
        return candidate

    def _update_candidates(self, requirement):
        package = self.p.identify(requirement)
        try:
            candidates = self.candidates[package]
        except KeyError:
            candidates = self.p.find_matches(requirement)
        else:
            candidates = self.p.filter_satisfied(candidates, requirement)
        if not candidates:

            raise CandidateNotFound(package)
        self.candidates[package] = candidates

    def _process_requirement(self, requirement):
        candidate = self._add_candidate(requirement)
        self._save()
        requirements = self.p.get_dependencies(candidate)
        for r in requirements:
            self._update_candidates(r)
        if requirements:
            self.requirements.append(requirements)

    def progress(self):
        step_count = len(self.requirements)
        for requirement in self.p.sorted_by_preference(self.requirements[-1]):
            try:
                self._process_requirement(requirement)
            except CandidateNotFound:
                return STATE_REGRESS
        # No new requirements added, we're done!
        if len(self.requirements) == step_count:
            return STATE_END
        return STATE_PROGRESS

    def regress(self):
        self._load()
        return STATE_PROGRESS

    def do(self):
        state = STATE_PROGRESS
        while state != STATE_END:
            state = getattr(self, state)()


class Resolver(object):
    """The thing that performs the actual resolution work.
    """
    def __init__(self, provider):
        # TODO: Take inspiration from Molinillo and provide a "UI" delegate
        # to report progress in alternative ways. This would be very
        # beneficial for Pipenv (i.e. report locking progress via TCP).
        self.provider = provider

    def resolve(self, requirements):
        """Take a collection of constraints, spit out the resolution result.

        Raises `ResolutionImpossible` if a resolution cannot be found.
        """
        state_machine = ResolutionStateMachine(self.provider, requirements)
        result = state_machine.do()
        return result
