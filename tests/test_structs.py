import pytest

from resolvelib.structs import DirectedAcyclicGraph, CyclicError


@pytest.fixture()
def graph():
    return DirectedAcyclicGraph()


def test_simple(graph):
    """
    a -> b -> c
    |         ^
    +---------+
    """
    graph['a'] = 'A'
    graph['b'] = 'B'
    graph['c'] = 'C'
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
    graph['a'] = 'A'
    graph['b'] = 'B'
    graph['c'] = 'C'
    graph.add_edge('a', 'b')
    graph.add_edge('b', 'c')
    with pytest.raises(CyclicError):
        graph.add_edge('c', 'a')
