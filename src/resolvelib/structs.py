class DirectedGraph(object):
    """A graph structure with directed edges.
    """
    def __init__(self, graph=None):
        if graph is None:
            self._vertices = {}     # <key> -> Any
            self._edges = {}        # <key> -> Set[<key>]
        elif isinstance(graph, type(self)):
            self._vertices = dict(graph._vertices)
            self._edges = {k: list(v) for k, v in graph._edges.items()}
        else:
            raise TypeError('DirectedAcyclicGraph expected, not {}'.format(
                type(graph).__name__),
            )

    def __iter__(self):
        return iter(self._vertices)

    def __len__(self):
        return len(self._vertices)

    def __contains__(self, key):
        return key in self._vertices

    def __getitem__(self, key):
        return self._vertices[key]

    def __setitem__(self, key, value):
        self._vertices[key] = value

    def keys(self):
        return self._vertices.keys()

    def values(self):
        return self._vertices.values()

    def items(self):
        return self._vertices.items()

    def iter_edge(self):
        for f, es in self._edges.items():
            for t in es:
                yield (f, t)

    def has_edge(self, from_key, to_key):
        return from_key in self._edges and to_key in self._edges[from_key]

    def _validate_edge_params(self, f, t):
        # Make sure both ends are in the graph.
        for v in (f, t):
            if v not in self._vertices:
                raise KeyError(v)

    def add_edge(self, from_key, to_key):
        # We're good if this edge already exists.
        if self.has_edge(from_key, to_key):
            return

        self._validate_edge_params(from_key, to_key)

        # Add the edge.
        if from_key not in self._edges:
            self._edges[from_key] = {to_key}
        else:
            self._edges[from_key].add(to_key)


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
    def _validate_edge_params(self, f, t):
        # Make sure this new edge won't make the graph cyclic.
        if _recursive_check_cyclic(self._edges, t, {f}):
            raise CyclicError(f, t)
