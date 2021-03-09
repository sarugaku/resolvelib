from __future__ import print_function

import collections
import json
import operator
import os

import packaging.markers
import packaging.requirements
import packaging.specifiers
import packaging.utils
import packaging.version
import pytest

from resolvelib import AbstractProvider, ResolutionImpossible, Resolver


Candidate = collections.namedtuple("Candidate", "name version extras")


def _eval_marker(marker, extras=(None,)):
    if not marker:
        return True
    if not isinstance(marker, packaging.markers.Marker):
        marker = packaging.markers.Marker(marker)
    return any(marker.evaluate({"extra": extra}) for extra in extras)


def _iter_resolved(data):
    for k, v in data.items():
        if not isinstance(v, dict):
            v = {"version": v}
        yield k, v


class PythonInputProvider(AbstractProvider):
    def __init__(self, filename):
        with open(filename) as f:
            case_data = json.load(f)

        index_name = os.path.normpath(
            os.path.join(
                filename, "..", "..", "index", case_data["index"] + ".json"
            ),
        )
        with open(index_name) as f:
            self.index = json.load(f)

        self.root_requirements = [
            packaging.requirements.Requirement(r)
            for r in case_data["requested"]
        ]

        if "resolved" in case_data:
            self.expected_resolution = {
                k: packaging.version.parse(v["version"])
                for k, v in _iter_resolved(case_data["resolved"])
                if _eval_marker(v.get("marker"))
            }
        else:
            self.expected_resolution = None

        if "conflicted" in case_data:
            self.expected_confliction = set(case_data["conflicted"])
        else:
            self.expected_confliction = None

    def identify(self, requirement_or_candidate):
        name = packaging.utils.canonicalize_name(requirement_or_candidate.name)
        if requirement_or_candidate.extras:
            extras_str = ",".join(sorted(requirement_or_candidate.extras))
            return "{}[{}]".format(name, extras_str)
        return name

    def get_preference(self, resolution, candidates, information):
        transitive = all(parent is not None for _, parent in information)
        key = next(iter(candidates)).name if candidates else ""
        return (transitive, key)

    def _iter_matches(self, identifier, requirements, incompatibilities):
        name, _, _ = identifier.partition("[")
        bad_versions = {c.version for c in incompatibilities[identifier]}
        extras = {e for r in requirements[identifier] for e in r.extras}
        for key, value in self.index[name].items():
            v = packaging.version.parse(key)
            if any(v not in r.specifier for r in requirements[identifier]):
                continue
            if v in bad_versions:
                continue
            yield Candidate(name=name, version=v, extras=extras)

    def find_matches(self, identifier, requirements, incompatibilities):
        candidates = sorted(
            self._iter_matches(identifier, requirements, incompatibilities),
            key=operator.attrgetter("version"),
            reverse=True,
        )
        return candidates

    def is_satisfied_by(self, requirement, candidate):
        return candidate.version in requirement.specifier

    def _iter_dependencies(self, candidate):
        name = packaging.utils.canonicalize_name(candidate.name)
        if candidate.extras:
            r = "{}=={}".format(name, candidate.version)
            yield packaging.requirements.Requirement(r)
        for r in self.index[name][str(candidate.version)]["dependencies"]:
            requirement = packaging.requirements.Requirement(r)
            if not _eval_marker(requirement.marker, candidate.extras):
                continue
            yield requirement

    def get_dependencies(self, candidate):
        return list(self._iter_dependencies(candidate))


INPUTS_DIR = os.path.abspath(os.path.join(__file__, "..", "inputs"))

CASE_DIR = os.path.join(INPUTS_DIR, "case")

CASE_NAMES = [name for name in os.listdir(CASE_DIR) if name.endswith(".json")]


XFAIL_CASES = {
    "pyrex-1.9.8.json": "Too many rounds (>500)",
    "same-package-extras.json": "State not cleaned up correctly",
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
    return PythonInputProvider(request.param)


def _format_confliction(exception):
    return {
        packaging.utils.canonicalize_name(cause.requirement.name)
        for cause in exception.causes
    }


def _format_resolution(result):
    return {
        identifier: candidate.version
        for identifier, candidate in result.mapping.items()
        if not candidate.extras
    }


def test_resolver(provider, reporter):
    resolver = Resolver(provider, reporter)

    if provider.expected_confliction:
        with pytest.raises(ResolutionImpossible) as ctx:
            result = resolver.resolve(provider.root_requirements)
            print(_format_resolution(result))  # Provide some debugging hints.
        assert _format_confliction(ctx.value) == provider.expected_confliction
    else:
        resolution = resolver.resolve(provider.root_requirements)
        assert _format_resolution(resolution) == provider.expected_resolution
