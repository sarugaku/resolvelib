from resolvelib import BaseReporter

from collections import Counter, defaultdict
from itertools import count
from packaging.utils import canonicalize_name
from typing import NamedTuple

from pygraphviz import AGraph


class GraphGeneratingReporter(BaseReporter):
    def __init__(self):
        self.evolution = []  # List[str]
        self._evaluating = None

        # Dict[Candidate, Set[Requirement]]
        self._dependencies = defaultdict(set)
        # Dict[Candidate.name, Counter[Requirement]]
        self._active_requirements = defaultdict(Counter)

        self._node_names = {}
        self._counter = count()

        self.graph = AGraph(
            directed=True, rankdir="LR", labelloc="top", labeljust="center",
            nodesep="0", concentrate="true",
        )
        self.graph.add_node("root", label=":root:", shape="Mdiamond")
        self._node_names[self._key(None)] = "root"

        self.graph.edge_attr.update(
            {"arrowhead": "empty", "style": "dashed", "color": "#808080"}
        )

    #
    # Internal Graph-handling API
    #
    def _prepare_node(self, obj):
        cls = obj.__class__.__name__
        n = next(self._counter)
        node_name = f"{cls}_{n}"
        self._node_names[self._key(obj)] = node_name
        return node_name

    def _key(self, obj):
        if obj is None:
            return None
        return (
            obj.__class__.__name__,
            repr(obj),
        )

    def _get_subgraph(self, name, *, must_exist_already=True):
        name = canonicalize_name(name)

        c_name = f"cluster_{name}"
        subgraph = self.graph.get_subgraph(c_name)
        if subgraph is None:
            if must_exist_already:
                existing = [s.name for s in self.graph.subgraphs_iter()]
                raise RuntimeError(f"Graph for {name} not found. Existing: {existing}")
            else:
                subgraph = self.graph.add_subgraph(name=c_name, label=name)

        return subgraph

    def _add_candidate(self, candidate):
        if candidate is None:
            return
        if self._key(candidate) in self._node_names:
            return

        node_name = self._prepare_node(candidate)

        # A candidate is only seen after a requirement with the same name.
        subgraph = self._get_subgraph(candidate.name, must_exist_already=True)
        subgraph.add_node(node_name, label=candidate.version, shape="box")

    def _add_requirement(self, req):
        if self._key(req) in self._node_names:
            return

        name = self._prepare_node(req)

        subgraph = self._get_subgraph(req.name, must_exist_already=False)
        subgraph.add_node(name, label=str(req.specifier) or "*", shape="cds")

    def _ensure_edge(self, from_, *, to, **attrs):
        from_node = self._node_names[self._key(from_)]
        to_node = self._node_names[self._key(to)]

        try:
            existing = self.graph.get_edge(from_node, to_node)
        except KeyError:
            self.graph.add_edge(from_node, to_node, **attrs)
        else:
            existing.attr.update(attrs)

    def _get_node_for(self, obj):
        node_name = self._node_names[self._key(obj)]
        node = self.graph.get_node(node_name)
        assert node is not None
        return node_name, node

    def _track_evaluating(self, candidate):
        if self._evaluating != candidate:
            if self._evaluating is not None:
                self.backtracking(self._evaluating, internal=True)
                self.evolution.append(self.graph.to_string())
            self._evaluating = candidate

    #
    # Public reporter API
    #
    def starting(self):
        print(f"starting(self)")
        pass

    def starting_round(self, index):
        print(f"starting_round(self, {index})")
        # self.graph.graph_attr["label"] = f"Round {index}"
        self.evolution.append(self.graph.to_string())

    def ending_round(self, index, state):
        print(f"ending_round(self, {index}, state)")
        pass

    def ending(self, state):
        print(f"ending(self, state)")
        pass

    def adding_requirement(self, req, parent):
        print(f"adding_requirement(self, {req!r}, {parent!r})")
        self._track_evaluating(parent)

        self._add_candidate(parent)
        self._add_requirement(req)

        self._ensure_edge(parent, to=req)

        self._active_requirements[canonicalize_name(req.name)][req] += 1
        self._dependencies[parent].add(req)

        if parent is None:
            return

        # We're seeing the parent candidate (which is being "evaluated"), so
        # color all "active" requirements pointing to the it.
        # TODO: How does this interact with revisited candidates?
        for parent_req in self._active_requirements[canonicalize_name(parent.name)]:
            self._ensure_edge(parent_req, to=parent, color="#80CC80")

    def backtracking(self, candidate, internal=False):
        print(f"backtracking(self, {candidate!r}, internal={internal})")
        self._track_evaluating(candidate)
        self._evaluating = None

        # Update the graph!
        node_name, node = self._get_node_for(candidate)
        node.attr.update(shape="signature", color="red")

        for edge in self.graph.out_edges_iter([node_name]):
            edge.attr.update(style="dotted", arrowhead="vee", color="#FF9999")
            _, to = edge
            to.attr.update(color="black")

        for edge in self.graph.in_edges_iter([node_name]):
            edge.attr.update(style="dotted", color="#808080")

        # Trim "active" requirements, to remove anything that's not relevant now.
        for requirement in self._dependencies[candidate]:
            active = self._active_requirements[canonicalize_name(requirement.name)]
            active[requirement] -= 1
            if not active[requirement]:
                del active[requirement]

    def pinning(self, candidate):
        print(f"pinning(self, {candidate!r})")
        assert (
            self._evaluating == candidate or
            self._evaluating is None
        )
        self._evaluating = None

        self._add_candidate(candidate)

        # Update the graph!
        node_name, node = self._get_node_for(candidate)
        node.attr.update(color="#80CC80")

        # Requirement -> Candidate edges, from this candidate.
        for req in self._active_requirements[canonicalize_name(candidate.name)]:
            self._ensure_edge(req, to=candidate, arrowhead="vee", color="#80CC80")

        # Candidate -> Requirement edges, from this candidate.
        for edge in self.graph.out_edges_iter([node_name]):
            edge.attr.update(style="solid", arrowhead="vee", color="#80CC80")
            _, to = edge
            to.attr.update(color="#80C080")
