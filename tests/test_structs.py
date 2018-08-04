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
    graph.add('a')
    graph.add('b')
    graph.add('c')
    graph.connect('a', 'b')
    graph.connect('b', 'c')
    graph.connect('a', 'c')
    assert set(graph) == {'a', 'b', 'c'}
    assert set(graph.iter_edges()) == {('a', 'b'), ('a', 'c'), ('b', 'c')}


def test_acyclic_simple(graph):
    """
    a -> b -> c
    ^         |
    +-- [X] --+
    """
    graph.add('a')
    graph.add('b')
    graph.add('c')
    graph.connect('a', 'b')
    graph.connect('b', 'c')
    with pytest.raises(CyclicError):
        graph.connect('c', 'a')
