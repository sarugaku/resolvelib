import pytest

from resolvelib.graphs import DirectedAcyclicGraph, GraphAcyclicError


@pytest.fixture()
def graph():
    return DirectedAcyclicGraph()


def test_simple(graph):
    """
    a -> b -> c
    |         ^
    +---------+
    """
    graph.add_vertex('a', 'A')
    graph.add_vertex('b', 'B')
    graph.add_vertex('c', 'C')
    graph.add_edge('a', 'b')
    graph.add_edge('b', 'c')
    graph.add_edge('a', 'c')
    assert graph.vertices == {'a': 'A', 'b': 'B', 'c': 'C'}
    assert graph.edges == {'a': {'b', 'c'}, 'b': {'c'}}


def test_acyclic_simple(graph):
    """
    a -> b -> c
    ^         |
    +-- [X] --+
    """
    graph.add_vertex('a', 'A')
    graph.add_vertex('b', 'B')
    graph.add_vertex('c', 'C')
    graph.add_edge('a', 'b')
    graph.add_edge('b', 'c')
    with pytest.raises(GraphAcyclicError):
        graph.add_edge('c', 'a')
