import itertools

from .compat import collections_abc


class DirectedGraph(object):
    """A graph structure with directed edges."""

    def __init__(self):
        self._vertices = set()
        self._forwards = {}  # <key> -> Set[<key>]
        self._backwards = {}  # <key> -> Set[<key>]

    def __iter__(self):
        return iter(self._vertices)

    def __len__(self):
        return len(self._vertices)

    def __contains__(self, key):
        return key in self._vertices

    def copy(self):
        """Return a shallow copy of this graph."""
        other = DirectedGraph()
        other._vertices = set(self._vertices)
        other._forwards = {k: set(v) for k, v in self._forwards.items()}
        other._backwards = {k: set(v) for k, v in self._backwards.items()}
        return other

    def add(self, key):
        """Add a new vertex to the graph."""
        if key in self._vertices:
            raise ValueError("vertex exists")
        self._vertices.add(key)
        self._forwards[key] = set()
        self._backwards[key] = set()

    def remove(self, key):
        """Remove vertex from graph, disconnecting all edges from/to it."""
        self._vertices.remove(key)
        for f in self._forwards.pop(key):
            self._backwards[f].remove(key)
        for t in self._backwards.pop(key):
            self._forwards[t].remove(key)

    def connected(self, f, t):
        return f in self._backwards[t] and t in self._forwards[f]

    def connect(self, f, t):
        """Connect two existing vertices.

        Nothing happens if the vertices are already connected.
        """
        if t not in self._vertices:
            raise KeyError(t)
        self._forwards[f].add(t)
        self._backwards[t].add(f)

    def iter_edges(self):
        for f, children in self._forwards.items():
            for t in children:
                yield f, t

    def iter_children(self, key):
        return iter(self._forwards[key])

    def iter_parents(self, key):
        return iter(self._backwards[key])


class RequirementsView(collections_abc.Mapping):
    """A view to the current requirements state for the provider.

    :type criteria: Mapping[Identifier, Criterion]
    :type override: Mapping[Identifier, Collection[RequirementInformation]]
    """

    def __init__(self, criteria, override):
        self._criteria = criteria
        self._override = override

    def __getitem__(self, key):
        if key in self._override:
            infos = self._override[key]
        elif key in self._criteria:
            infos = self._criteria[key].information
        else:
            raise KeyError(key)
        return [r for r, _ in infos]

    def __iter__(self):
        return itertools.chain(
            self._override,
            (key for key in self._criteria if key not in self._override),
        )

    def __len__(self):
        count = itertools.count(
            key for key in self._override if key not in self._criteria
        )
        return count + len(self._criteria)
