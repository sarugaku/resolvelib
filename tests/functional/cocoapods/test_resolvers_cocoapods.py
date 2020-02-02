import collections
import json
import operator
import os
import re
import string

import commentjson
import packaging.specifiers
import packaging.version
import pytest

from resolvelib import AbstractProvider, ResolutionImpossible, Resolver


Requirement = collections.namedtuple("Requirement", "name spec")
Candidate = collections.namedtuple("Candidate", "name ver deps")


INPUTS_DIR = os.path.abspath(os.path.join(__file__, "..", "inputs"))

CASE_DIR = os.path.join(INPUTS_DIR, "case")

CASE_NAMES = [name for name in os.listdir(CASE_DIR) if name.endswith(".json")]


def _convert_specifier(s):
    if not s:
        return s
    m = re.match(r"^([<>=~!]*)\s*(.+)$", s)
    op, ver = m.groups()
    if not op or op == "=":
        return "== {}".format(ver)
    elif op == "~>":
        if len(ver) == 1:
            # PEP 440 can't handle "~= X" (no minor part). This translates to
            # a simple ">= X" because it means we accept major version changes.
            return ">= {}".format(ver)
        return "~= {0}, >= {0}".format(ver)
    return s


def _iter_convert_specifiers(inp):
    for raw in inp.split(","):
        cov = _convert_specifier(raw.strip())
        if not cov:
            continue
        yield cov


def _parse_specifier_set(inp):
    return packaging.specifiers.SpecifierSet(
        ", ".join(_iter_convert_specifiers(inp)),
    )


def _safe_json_load(filename):
    # Some fixtures has comments so the stdlib implementation doesn't work.
    # We only use commentjson if we absolutely need to because it's SLOW.
    try:
        with open(filename) as f:
            data = json.load(f)
    except ValueError:
        with open(filename) as f:
            data = commentjson.load(f)
    return data


def _clean_identifier(s):
    # I'm not entirely sure how identifiers in the spec work. The only fixture
    # this matters (AFAICT) is swapping_changes_transitive_dependency, which
    # has a '\u0001' that seems to intend to be dropped?
    return "".join(c for c in s if c in string.printable)


def _iter_resolved(dependencies):
    for entry in dependencies:
        yield (entry["name"], packaging.version.parse(entry["version"]))
        for sub in _iter_resolved(entry["dependencies"]):
            yield sub


class CocoaPodsInputProvider(AbstractProvider):
    def __init__(self, filename):
        case_data = _safe_json_load(filename)

        index_name = os.path.join(
            INPUTS_DIR, "index", case_data.get("index", "awesome") + ".json",
        )
        self.index = _safe_json_load(index_name)

        self.root_requirements = [
            Requirement(_clean_identifier(key), _parse_specifier_set(spec))
            for key, spec in case_data["requested"].items()
        ]
        self.pinned_versions = {
            entry["name"]: packaging.version.parse(entry["version"])
            for entry in case_data["base"]
        }
        self.expected_resolution = dict(_iter_resolved(case_data["resolved"]))
        self.expected_conflicts = set(case_data["conflicts"])

    def identify(self, dependency):
        return dependency.name

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def _iter_matches(self, requirement):
        try:
            data = self.index[requirement.name]
        except KeyError:
            return
        for entry in data:
            version = packaging.version.parse(entry["version"])
            if version not in requirement.spec:
                continue
            # Some fixtures incorrectly set dependencies to an empty list.
            dependencies = entry["dependencies"] or {}
            dependencies = [
                Requirement(k, _parse_specifier_set(v))
                for k, v in dependencies.items()
            ]
            yield Candidate(entry["name"], version, dependencies)

    def find_matches(self, requirement):
        mapping = {c.ver: c for c in self._iter_matches(requirement)}
        try:
            version = self.pinned_versions[requirement.name]
        except KeyError:
            return sorted(mapping.values(), key=operator.attrgetter("ver"))
        return [mapping.pop(version)]

    def is_satisfied_by(self, requirement, candidate):
        return candidate.ver in requirement.spec

    def get_dependencies(self, candidate):
        return candidate.deps


XFAIL_CASES = {
    "circular.json": "different resolution",
    "complex_conflict.json": "different resolution",
    "fixed_circular.json": "different resolution",
    "previous_conflict.json": "different resolution",
    "shared_parent_dependency_with_swapping.json": "KeyError: 'fog'",
    "spapping_and_rewinding.json": "different resolution",
}


@pytest.fixture(
    params=[
        pytest.param(
            os.path.join(CASE_DIR, n),
            marks=pytest.mark.xfail(strict=True, reason=XFAIL_CASES[n]),
        )
        if n in XFAIL_CASES
        else os.path.join(CASE_DIR, n)
        for n in CASE_NAMES
    ],
    ids=[n[:-5] for n in CASE_NAMES],
)
def provider(request):
    return CocoaPodsInputProvider(request.param)


def _format_conflicts(exc):
    return {r.name for r in exc.requirements}


def _format_resolution(result):
    return {
        identifier: candidate.ver
        for identifier, candidate in result.mapping.items()
    }


def test_resolver(provider, base_reporter):
    resolver = Resolver(provider, base_reporter)

    if provider.expected_conflicts:
        with pytest.raises(ResolutionImpossible) as ctx:
            result = resolver.resolve(provider.root_requirements)
            print(_format_resolution(result))  # Provide some debugging hints.
        assert _format_conflicts(ctx.value) == provider.expected_conflicts
    else:
        result = resolver.resolve(provider.root_requirements)
        assert _format_resolution(result) == provider.expected_resolution
