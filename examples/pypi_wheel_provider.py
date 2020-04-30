from email.message import EmailMessage
from email.parser import BytesParser
from io import BytesIO
from operator import attrgetter
from platform import python_version
from urllib.parse import urlparse
from zipfile import ZipFile

import requests
import html5lib
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from extras_provider import ExtrasProvider

PYTHON_VERSION = Version(python_version())


class Candidate:
    def __init__(self, name, version, url=None, extras=None):
        self.name = canonicalize_name(name)
        self.version = version
        self.url = url
        self.extras = extras

        self._metadata = None
        self._dependencies = None

    def __repr__(self):
        if not self.extras:
            return f"{self.name}=={self.version}"
        return f"{self.name}[{','.join(self.extras)}]=={self.version}"

    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = get_metadata_for_wheel(self.url)
        return self._metadata

    @property
    def requires_python(self):
        return self.metadata.get("Requires-Python")

    def _get_dependencies(self):
        deps = self.metadata.get_all("Requires-Dist", [])
        extras = self.extras if self.extras else [""]

        for d in deps:
            r = Requirement(d)
            if r.marker is None:
                yield r
            else:
                for e in extras:
                    if r.marker.evaluate({"extra": e}):
                        yield r

    @property
    def dependencies(self):
        if self._dependencies is None:
            self._dependencies = list(self._get_dependencies())
        return self._dependencies


def get_project_from_pypi(project, extras):
    url = "https://pypi.org/simple/{}".format(project)
    data = requests.get(url).content
    doc = html5lib.parse(data, namespaceHTMLElements=False)
    for i in doc.findall(".//a"):
        url = i.attrib["href"]
        py_req = i.attrib.get("data-requires-python")

        # Skip items that need a different Python version
        if py_req:
            spec = SpecifierSet(py_req)
            if PYTHON_VERSION not in spec:
                continue

        path = urlparse(url).path
        filename = path.rpartition("/")[-1]

        # We only handle wheels
        if not filename.endswith(".whl"):
            continue

        # TODO: Handle compatibility tags?

        # Very primitive wheel filename parsing
        name, version = filename[:-4].split("-")[:2]

        try:
            version = Version(version)
        except InvalidVersion:
            # Ignore files with invalid versions
            continue

        yield Candidate(name, version, url=url, extras=extras)


def get_metadata_for_wheel(url):
    data = requests.get(url).content
    with ZipFile(BytesIO(data)) as z:
        for n in z.namelist():
            if n.endswith(".dist-info/METADATA"):
                p = BytesParser()
                return p.parse(z.open(n), headersonly=True)

    # If we didn't find the metadata, return an empty dict
    return EmailMessage()


class PyPIProvider(ExtrasProvider):
    def identify(self, dependency):
        return canonicalize_name(dependency.name)

    def get_extras_for(self, dependency):
        # Extras is a set, which is not hashable
        return tuple(sorted(dependency.extras))

    def get_base_requirement(self, candidate):
        return Requirement("{}=={}".format(candidate.name, candidate.version))

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirements):
        assert requirements, "resolver promises at least one requirement"
        assert not any(
            r.extras for r in requirements[1:]
        ), "extras not supported in this example"

        name = canonicalize_name(requirements[0].name)

        # Need to pass the extras to the search, so they
        # are added to the candidate at creation - we
        # treat candidates as immutable once created.
        candidates = []
        for c in get_project_from_pypi(name, set()):
            version = c.version
            if all(version in r.specifier for r in requirements):
                candidates.append(c)
        return sorted(candidates, key=attrgetter("version"), reverse=True)

    def is_satisfied_by(self, requirement, candidate):
        if canonicalize_name(requirement.name) != candidate.name:
            return False
        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):
        return candidate.dependencies


if __name__ == "__main__":
    import sys
    from resolvelib import BaseReporter, Resolver

    def display_resolution(result):

        print("--- Pinned Candidates ---")
        for name, candidate in result.mapping.items():
            print(f"{name}: {candidate.name} {candidate.version}")

        print()
        print("--- Dependency Graph ---")
        for name in result.graph:
            targets = ", ".join(result.graph.iter_children(name))
            print(f"{name} -> {targets}")

    def main(reqs):
        # Things I want to resolve.
        requirements = [Requirement(r) for r in reqs]

        provider = PyPIProvider()
        reporter = BaseReporter()

        # Create the (reusable) resolver.
        resolver = Resolver(provider, reporter)

        # Kick off the resolution process, and get the final result.
        result = resolver.resolve(requirements)

        display_resolution(result)

    # Run the demo program
    main(sys.argv[1:])
