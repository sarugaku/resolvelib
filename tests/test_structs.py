import pytest

from resolvelib.structs import DirectedGraph


@pytest.fixture()
def graph():
    return DirectedGraph()


def test_simple(graph):
    """
    a -> b -> c
    |         ^
    +---------+
    """
    graph.add("a")
    graph.add("b")
    graph.add("c")
    graph.connect("a", "b")
    graph.connect("b", "c")
    graph.connect("a", "c")
    assert set(graph) == {"a", "b", "c"}
    assert set(graph.iter_edges()) == {("a", "b"), ("a", "c"), ("b", "c")}
