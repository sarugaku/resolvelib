from __future__ import annotations

import itertools
from abc import ABCMeta
from collections import namedtuple
from typing import (
    TYPE_CHECKING,
    Callable,
    Collection,
    Container,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Sequence,
    TypeVar,
    Union,
)

KT = TypeVar("KT")  # Identifier.
RT = TypeVar("RT")  # Requirement.
CT = TypeVar("CT")  # Candidate.

Matches = Union[Iterable[CT], Callable[[], Iterable[CT]]]

if TYPE_CHECKING:

    class RequirementInformation(NamedTuple, Generic[RT, CT]):
        requirement: RT
        parent: CT | None

    class State(NamedTuple, Generic[RT, CT, KT]):
        """Resolution state in a round."""

        mapping: dict[KT, CT]
        criteria: dict[KT, Criterion[RT, CT]]
        backtrack_causes: list[RequirementInformation[RT, CT]]

else:
    RequirementInformation = namedtuple(
        "RequirementInformation", ["requirement", "parent"]
    )
    State = namedtuple("State", ["mapping", "criteria", "backtrack_causes"])


class DirectedGraph(Generic[KT]):
    """A graph structure with directed edges."""

    def __init__(self) -> None:
        self._vertices: set[KT] = set()
        self._forwards: dict[KT, set[KT]] = {}  # <key> -> Set[<key>]
        self._backwards: dict[KT, set[KT]] = {}  # <key> -> Set[<key>]

    def __iter__(self) -> Iterator[KT]:
        return iter(self._vertices)

    def __len__(self) -> int:
        return len(self._vertices)

    def __contains__(self, key: KT) -> bool:
        return key in self._vertices

    def copy(self) -> DirectedGraph[KT]:
        """Return a shallow copy of this graph."""
        other = type(self)()
        other._vertices = set(self._vertices)
        other._forwards = {k: set(v) for k, v in self._forwards.items()}
        other._backwards = {k: set(v) for k, v in self._backwards.items()}
        return other

    def add(self, key: KT) -> None:
        """Add a new vertex to the graph."""
        if key in self._vertices:
            raise ValueError("vertex exists")
        self._vertices.add(key)
        self._forwards[key] = set()
        self._backwards[key] = set()

    def remove(self, key: KT) -> None:
        """Remove a vertex from the graph, disconnecting all edges from/to it."""
        self._vertices.remove(key)
        for f in self._forwards.pop(key):
            self._backwards[f].remove(key)
        for t in self._backwards.pop(key):
            self._forwards[t].remove(key)

    def connected(self, f: KT, t: KT) -> bool:
        return f in self._backwards[t] and t in self._forwards[f]

    def connect(self, f: KT, t: KT) -> None:
        """Connect two existing vertices.

        Nothing happens if the vertices are already connected.
        """
        if t not in self._vertices:
            raise KeyError(t)
        self._forwards[f].add(t)
        self._backwards[t].add(f)

    def iter_edges(self) -> Iterator[tuple[KT, KT]]:
        for f, children in self._forwards.items():
            for t in children:
                yield f, t

    def iter_children(self, key: KT) -> Iterator[KT]:
        return iter(self._forwards[key])

    def iter_parents(self, key: KT) -> Iterator[KT]:
        return iter(self._backwards[key])


class IteratorMapping(Mapping[KT, Iterator[CT]], Generic[RT, CT, KT]):
    def __init__(
        self,
        mapping: Mapping[KT, RT],
        accessor: Callable[[RT], Iterable[CT]],
        appends: Mapping[KT, Iterable[CT]] | None = None,
    ) -> None:
        self._mapping = mapping
        self._accessor = accessor
        self._appends: Mapping[KT, Iterable[CT]] = appends or {}

    def __repr__(self) -> str:
        return "IteratorMapping({!r}, {!r}, {!r})".format(
            self._mapping,
            self._accessor,
            self._appends,
        )

    def __bool__(self) -> bool:
        return bool(self._mapping or self._appends)

    def __contains__(self, key: object) -> bool:
        return key in self._mapping or key in self._appends

    def __getitem__(self, k: KT) -> Iterator[CT]:
        try:
            v = self._mapping[k]
        except KeyError:
            return iter(self._appends[k])
        return itertools.chain(self._accessor(v), self._appends.get(k, ()))

    def __iter__(self) -> Iterator[KT]:
        more = (k for k in self._appends if k not in self._mapping)
        return itertools.chain(self._mapping, more)

    def __len__(self) -> int:
        more = sum(1 for k in self._appends if k not in self._mapping)
        return len(self._mapping) + more


class _FactoryIterableView(Generic[RT]):
    """Wrap an iterator factory returned by `find_matches()`.

    Calling `iter()` on this class would invoke the underlying iterator
    factory, making it a "collection with ordering" that can be iterated
    through multiple times, but lacks random access methods presented in
    built-in Python sequence types.
    """

    def __init__(self, factory: Callable[[], Iterable[RT]]) -> None:
        self._factory = factory
        self._iterable: Iterable[RT] | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)})"

    def __bool__(self) -> bool:
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    def __iter__(self) -> Iterator[RT]:
        iterable = (
            self._factory() if self._iterable is None else self._iterable
        )
        self._iterable, current = itertools.tee(iterable)
        return current


class _SequenceIterableView(Generic[RT]):
    """Wrap an iterable returned by find_matches().

    This is essentially just a proxy to the underlying sequence that provides
    the same interface as `_FactoryIterableView`.
    """

    def __init__(self, sequence: Sequence[RT]):
        self._sequence = sequence

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._sequence})"

    def __bool__(self) -> bool:
        return bool(self._sequence)

    def __iter__(self) -> Iterator[RT]:
        return iter(self._sequence)


class IterableView(Container[CT], Iterator[CT], metaclass=ABCMeta):
    pass


def build_iter_view(
    matches: Iterable[CT] | Callable[[], Iterable[CT]]
) -> IterableView[CT]:
    """Build an iterable view from the value returned by `find_matches()`."""
    if callable(matches):
        return _FactoryIterableView(matches)  # type: ignore[return-value]
    if not isinstance(matches, Sequence):
        matches = list(matches)
    return _SequenceIterableView(matches)  # type: ignore[return-value]


class Criterion(Generic[RT, CT]):
    """Representation of possible resolution results of a package.

    This holds three attributes:

    * `information` is a collection of `RequirementInformation` pairs.
      Each pair is a requirement contributing to this criterion, and the
      candidate that provides the requirement.
    * `incompatibilities` is a collection of all known not-to-work candidates
      to exclude from consideration.
    * `candidates` is a collection containing all possible candidates deducted
      from the union of contributing requirements and known incompatibilities.
      It should never be empty, except when the criterion is an attribute of a
      raised `RequirementsConflicted` (in which case it is always empty).

    .. note::
        This class is intended to be externally immutable. **Do not** mutate
        any of its attribute containers.
    """

    def __init__(
        self,
        candidates: IterableView[CT],
        information: Collection[RequirementInformation[RT, CT]],
        incompatibilities: Collection[CT],
    ) -> None:
        self.candidates = candidates
        self.information = information
        self.incompatibilities = incompatibilities

    def __repr__(self) -> str:
        requirements = ", ".join(
            f"({req!r}, via={parent!r})" for req, parent in self.information
        )
        return f"Criterion({requirements})"

    def iter_requirement(self) -> Iterator[RT]:
        return (i.requirement for i in self.information)

    def iter_parent(self) -> Iterator[CT | None]:
        return (i.parent for i in self.information)
