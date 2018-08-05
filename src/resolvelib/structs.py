class DirectedGraph(object):
    """A graph structure with directed edges.
    """
    def __init__(self, graph=None):
        if graph is None:
            self._vertices = set()
            self._forwards = {}     # <key> -> Set[<key>]
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
        """Add a new vertex to the graph.
        """
        if key in self._vertices:
            raise ValueError('vertex exists')
        self._vertices.add(key)
        self._forwards[key] = set()
        self._backwards[key] = set()

    def remove(self, key):
        """Remove a vertex from the graph, disconnecting all edges from/to it.
        """
        for f in self._forwards[key]:
            self._backwards[f].remove(key)
        for t in self._backwards[key]:
            self._forwards[t].remove(key)
        self._vertices.remove(key)
        del self._forwards[key]
        del self._backwards[key]

    def connected(self, f, t):
        return f in self._forwards and t in self._forwards[f]

    def connect(self, f, t):
        """Connect two existing vertices.

        Nothing happens if the vertices are already connected.
        """
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
