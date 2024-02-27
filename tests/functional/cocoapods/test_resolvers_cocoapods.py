import collections
import json
import operator
import os
import re
import string

import pytest

from resolvelib import AbstractProvider, ResolutionImpossible, Resolver

Requirement = collections.namedtuple("Requirement", "name spec")
Candidate = collections.namedtuple("Candidate", "name ver deps")


INPUTS_DIR = os.path.abspath(os.path.join(__file__, "..", "inputs"))
CASE_DIR = os.path.join(INPUTS_DIR, "case")
CASE_NAMES = [name for name in os.listdir(CASE_DIR) if name.endswith(".json")]


def _parse_version(v):
    parts = []
    for part in re.split(r"[.-]", v):
        if part[:1] in "0123456789":
            parts.append(part.zfill(8))
        else:
            parts.append("*" + part)
    parts.append("*z")  # end mark
    return tuple(parts)


class Version:
    def __init__(self, v):
        self.v = v
        self._comp_key = _parse_version(v)

    def __repr__(self):
        return self.v

    @property
    def is_prerelease(self):
        return any(part[0] == "*" for part in self._comp_key[:-1])

    def __len__(self):
        return len(self._comp_key)

    def __eq__(self, o):
        if not isinstance(o, Version):
            return NotImplemented
        left = self
        if len(left) < len(o):
            left = left.pad(len(o) - len(left))
        elif len(left) > len(o):
            o = o.pad(len(left) - len(o))
        return left._comp_key == o._comp_key

    def __lt__(self, o):
        return self._comp_key < o._comp_key

    def __le__(self, o):
        return self._comp_key <= o._comp_key

    def __gt__(self, o):
        return self._comp_key > o._comp_key

    def __ge__(self, o):
        return self._comp_key >= o._comp_key

    def __hash__(self):
        return hash(self._comp_key)

    def pad(self, n):
        return Version(self.v + ".0" * n)


def _compatible_gt(a, b):
    """a ~> b"""
    if a < b:
        return False
    a_digits = [part for part in a._comp_key if part[0] != "*"]
    b_digits = [part for part in b._comp_key if part[0] != "*"]
    target_len = len(b_digits)
    return a_digits[: target_len - 1] == b_digits[: target_len - 1]


_compare_ops = {
    "=": operator.eq,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "~>": _compatible_gt,
    "!=": operator.ne,
}


def _version_in_spec(version, spec):
    if not spec:
        return not version.is_prerelease
    m = re.match(r"([><=~!]*)\s*(.*)", spec)
    op, ver = m.groups()
    if not op:
        op = "="
    spec_ver = Version(ver)
    allow_prereleases = spec_ver.is_prerelease
    if not allow_prereleases and version.is_prerelease:
        return False
    if len(spec_ver) > len(version):
        version = version.pad(len(spec_ver) - len(version))
    return _compare_ops[op](version, spec_ver)


def _iter_convert_specifiers(inp):
    for raw in inp.split(","):
        yield raw.strip()


def _version_in_specset(version, specset):
    for spec in _iter_convert_specifiers(specset):
        if not _version_in_spec(version, spec):
            return False
    return True


def _safe_json_load(filename):
    # Some fixtures have comments so they are not valid json.
    # We could use commentjson/json5 to load them,
    # but it's easier to strip the comments.
    # We only do it when json.load() fails to avoid unnecessary loading
    # all the json files to strings.
    with open(filename) as f:
        try:
            data = json.load(f)
        except ValueError:
            f.seek(0)
            strippedjson = re.sub(r"//.*$", "", f.read(), flags=re.MULTILINE)
            data = json.loads(strippedjson)
    return data


def _clean_identifier(s):
    # I'm not entirely sure how identifiers in the spec work. The only fixture
    # this matters (AFAICT) is swapping_changes_transitive_dependency, which
    # has a '\u0001' that seems to intend to be dropped?
    return "".join(c for c in s if c in string.printable)


def _iter_resolved(dependencies):
    for entry in dependencies:
        yield (entry["name"], Version(entry["version"]))
        for sub in _iter_resolved(entry["dependencies"]):
            yield sub


class CocoaPodsInputProvider(AbstractProvider):
    def __init__(self, filename):
        case_data = _safe_json_load(filename)

        index_name = os.path.join(
            INPUTS_DIR,
            "index",
            case_data.get("index", "awesome") + ".json",
        )
        self.index = _safe_json_load(index_name)

        self.root_requirements = [
            Requirement(_clean_identifier(key), spec)
            for key, spec in case_data["requested"].items()
        ]
        self.pinned_versions = {
            entry["name"]: Version(entry["version"])
            for entry in case_data["base"]
        }
        self.expected_resolution = dict(_iter_resolved(case_data["resolved"]))
        self.expected_conflicts = set(case_data["conflicts"])

    def identify(self, requirement_or_candidate):
        return requirement_or_candidate.name

    def get_preference(
        self,
        identifier,
        resolutions,
        candidates,
        information,
        backtrack_causes,
    ):
        return sum(1 for _ in candidates[identifier])

    def _iter_matches(self, name, requirements, incompatibilities):
        try:
            data = self.index[name]
        except KeyError:
            return
        bad_versions = {c.ver for c in incompatibilities[name]}
        for entry in data:
            version = Version(entry["version"])
            if any(
                not _version_in_specset(version, r.spec)
                for r in requirements[name]
            ):
                continue
            if version in bad_versions:
                continue
            # Some fixtures incorrectly set dependencies to an empty list.
            dependencies = entry["dependencies"] or {}
            dependencies = [Requirement(k, v) for k, v in dependencies.items()]
            yield Candidate(entry["name"], version, dependencies)

    def find_matches(self, identifier, requirements, incompatibilities):
        candidates = sorted(
            self._iter_matches(identifier, requirements, incompatibilities),
            key=operator.attrgetter("ver"),
            reverse=True,
        )
        pinned = self.pinned_versions.get(identifier)
        for c in candidates:
            if pinned is not None and c.ver != pinned:
                continue
            yield c

    def is_satisfied_by(self, requirement, candidate):
        return _version_in_specset(candidate.ver, requirement.spec)

    def get_dependencies(self, candidate):
        return candidate.deps


XFAIL_CASES = {
    # ResolveLib does not complain about cycles, so these will be different.
    # No right or wrong here, just a design decision.
    "circular.json": "circular dependencies works for us, no conflicts",
    "fixed_circular.json": "circular dependencies works for us, no backtracks",
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
    return {r.name for r, _ in exc.causes}


def _format_resolution(result):
    return {
        identifier: candidate.ver
        for identifier, candidate in result.mapping.items()
    }


def test_resolver(provider, reporter):
    resolver = Resolver(provider, reporter)

    if provider.expected_conflicts:
        with pytest.raises(ResolutionImpossible) as ctx:
            result = resolver.resolve(provider.root_requirements)
            print(_format_resolution(result))  # Provide some debugging hints.
        assert _format_conflicts(ctx.value) == provider.expected_conflicts
    else:
        result = resolver.resolve(provider.root_requirements)
        assert _format_resolution(result) == provider.expected_resolution
