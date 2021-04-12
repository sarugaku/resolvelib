import pytest

from resolvelib.structs import DirectedGraph, build_iter_view


@pytest.fixture()
def graph():
    return DirectedGraph()


def test_graph(graph):
    """Test integrity of a simple graph.

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


def _generate():
    yield 0
    yield 1


@pytest.mark.parametrize("source", [_generate, [0, 1], iter([0, 1])])
def test_iter_view_iterable(source):
    """Iterable protocol for the iterator view."""
    iterator = iter(build_iter_view(source))
    assert next(iterator) == 0
    assert next(iterator) == 1
    with pytest.raises(StopIteration):
        next(iterator)


@pytest.mark.parametrize("source", [_generate, [0, 1], iter([0, 1])])
def test_iter_view_multiple_iterable(source):
    """Iterator view can be independently iter-ed multiple times."""
    view = build_iter_view(source)
    iterator_a = iter(view)
    iterator_b = iter(view)

    next(iterator_a)
    assert next(iterator_b) == 0
    assert next(iterator_a) == 1
