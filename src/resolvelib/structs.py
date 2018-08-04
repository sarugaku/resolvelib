class DirectedGraph(object):
    """A graph structure with directed edges.
    """
    def __init__(self, graph=None):
        if graph is None:
            self._vertices = set()
            self._forwards = {}      # <key> -> Set[<key>]
            self._backwards = {}    # <key> -> Set[<key>]
        elif isinstance(graph, type(self)):
            self._vertices = set(graph._vertices)
            self._forwards = {k: set(v) for k, v in graph._forwards.items()}
            self._backwards = {k: set(v) for k, v in graph._backwards.items()}
        else:
            raise TypeError('{} expected, not {}'.format(
                type(self).__name__, type(graph).__name__),
            )

    def __iter__(self):
        return iter(self._vertices)

    def __len__(self):
        return len(self._vertices)

    def __contains__(self, key):
        return key in self._vertices

    def add(self, key):
        self._vertices.add(key)
        self._forwards[key] = set()
        self._backwards[key] = set()

    def remove(self, key):
        if self._forwards[key]:
            raise ValueError('node has incoming edges')
        if self._backwards[key]:
            raise ValueError('node has outgoing edges')
        self._vertices.remove(key)
        del self._forwards[key]
        del self._backwards[key]

    def iter_edges(self):
        for f, children in self._forwards.items():
            for t in children:
                yield f, t

    def iter_children(self, key):
        return iter(self._forwards[key])

    def iter_parents(self, key):
        return iter(self._backwards[key])

    def connected(self, f, t):
        return f in self._forwards and t in self._forwards[f]

    # Extracted for subclassing.
    def _validate_for_connect(self, f, t):
        for v in (f, t):    # Make sure both ends are in the graph.
            if v not in self._vertices:
                raise KeyError(v)

    def connect(self, f, t):
        self._validate_for_connect(f, t)
        self._forwards[f].add(t)
        self._backwards[t].add(f)

    def disconnect(self, f, t):
        if f not in self._vertices:
            raise KeyError(f)
        if t not in self._vertices:
            raise KeyError(t)
        self._forwards[f].remove(t)
        self._backwards[t].remove(f)


def _recursive_check_cyclic(edges, key, visited):
    """Walk a graph to check if an edge set is cyclic.

    The method is fairly naive: If the key has been visited, this must be
    cyclic. Otherwise walk one step in each direction, and see if any of them
    are visited.
    """
    if key in visited:
        return True
    visited.add(key)
    try:
        targets = edges[key]
    except KeyError:
        return False
    return any(
        _recursive_check_cyclic(edges, target, visited)
        for target in targets
    )


class CyclicError(ValueError):
    pass


class DirectedAcyclicGraph(DirectedGraph):
    """A directed graph that ensures edges don't form loops.
    """
    def _validate_for_connect(self, f, t):
        super(DirectedAcyclicGraph, self)._validate_for_connect(f, t)
        # Make sure this new edge won't make the graph cyclic.
        if _recursive_check_cyclic(self._forwards, t, {f}):
            raise CyclicError(f, t)
