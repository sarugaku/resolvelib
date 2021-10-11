"""Freeze metadata from Python index server to test locally.

Inspired by index_from_rubygems.rb from CocoaPods/Resolver-Integration-Specs.

This only reads metadata from wheels compatible with the given platform, and
does not cover sdists at all.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import email.parser
import itertools
import json
import logging
import os
import pathlib
import re
import sys
import urllib.parse
import zipfile
from typing import (
    IO,
    BinaryIO,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

import html5lib
import packaging.requirements
import packaging.tags
import packaging.utils
import packaging.version
import requests

logger = logging.getLogger()

PythonVersion = Union[Tuple[int], Tuple[int, int]]


def _parse_python_version(s: str) -> PythonVersion:
    match = re.match(r"^(\d+)(?:\.(\d+))?$", s)
    if not match:
        raise ValueError(s)
    major, *more = match.groups()
    if more:
        return (int(major), int(more[0]))
    return (int(major),)


def _parse_output_path(s: str) -> Optional[pathlib.Path]:
    if s == "-":
        return None
    if os.sep in s or (os.altsep and os.altsep in s):
        return pathlib.Path(s)
    return pathlib.Path(__file__).with_name("inputs").joinpath("index", s)


def parse_args(args: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "package_names",
        metavar="PACKAGE",
        nargs="+",
        type=packaging.utils.canonicalize_name,
    )
    parser.add_argument(
        "--python-version",
        dest="python_version",
        type=_parse_python_version,
        default=".".join(str(v) for v in sys.version_info[:2]),
    )
    parser.add_argument(
        "--interpreter",
        default=None,
    )
    parser.add_argument(
        "--platform",
        dest="platforms",
        action="append",
        default=None,
    )
    parser.add_argument(
        "--output",
        type=_parse_output_path,
        required=True,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
    )
    return parser.parse_args(args)


def get_output_path(path: pathlib.Path, overwrite: bool) -> pathlib.Path:
    if path.suffix != ".json":
        path = path.with_name(path.name + ".json")
    if path.is_file() and not overwrite:
        raise FileExistsError(os.fspath(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _parse_tag(s: str) -> FrozenSet[packaging.tags.Tag]:
    try:
        return packaging.tags.parse_tag(s)
    except ValueError:
        raise ValueError(f"invalid tag {s!r}")


@dataclasses.dataclass()
class WheelMatcher:
    required_python: packaging.version.Version
    tags: Dict[packaging.tags.Tag, int]

    @classmethod
    def compatible_with(
        cls,
        python_version: PythonVersion,
        impl: Optional[str],
        plats: Optional[List[str]],
    ) -> WheelMatcher:
        required_python = packaging.version.Version(
            ".".join(str(v) for v in python_version)
        )
        # TODO: Add ABI customization.
        tag_it = itertools.chain(
            packaging.tags.compatible_tags(python_version, impl, plats),
            packaging.tags.cpython_tags(python_version, None, plats),
        )
        tags = {t: i for i, t in enumerate(tag_it)}
        return cls(required_python, tags)

    def rank(self, tag: str, requires_python: Optional[str]) -> Optional[int]:
        if requires_python:
            spec = packaging.specifiers.SpecifierSet(requires_python)
            if self.required_python not in spec:
                return None
        ranks = [self.tags[t] for t in _parse_tag(tag) if t in self.tags]
        if not ranks:
            return None
        return min(ranks)


@dataclasses.dataclass()
class HttpFile:
    url: str
    session: requests.Session

    def __post_init__(self):
        self._offset = 0
        self._size = int(self.session.head(self.url).headers["Content-Length"])

    def read(self, n=None):
        if n is None:
            end = self._size
        else:
            end = self._offset + n
        headers = {"Range": f"bytes={self._offset}-{end - 1}"}
        res = self.session.get(self.url, headers=headers)
        data = res.content
        self._offset += len(data)
        return data

    def seek(self, offset, whence=0):
        if whence == 0:
            self._offset = offset
        elif whence == 1:
            self._offset += offset
        elif whence == 2:
            self._offset = self._size + offset
        else:
            err = f"ValueError: invalid whence ({whence}, should be 0, 1 or 2)"
            raise ValueError(err)

    def seekable(self):
        return True

    def tell(self):
        return self._offset


def _parse_wheel_name(rest: str) -> Tuple[str, str, str]:
    name, rest = rest.split("-", 1)
    version, x, y, z = rest.rsplit("-", 3)
    return name, version, f"{x}-{y}-{z}"


def _open_metadata(zf: zipfile.ZipFile, prefix: str) -> IO[bytes]:
    for fn in zf.namelist():
        if not fn.endswith(".dist-info/METADATA"):
            continue
        if packaging.utils.canonicalize_name(fn).startswith(prefix):
            return zf.open(fn)
    raise ValueError("Can't find metadata")


class PackageEntry(NamedTuple):
    version: str
    dependencies: List[str]


DistListMapping = Dict[str, List[Tuple[int, str]]]


@dataclasses.dataclass()
class Finder:
    index_urls: List[str]
    matcher: WheelMatcher
    session: requests.Session

    def collect_best_dist_urls(self, name: str) -> Dict[str, str]:
        all_dists: DistListMapping = collections.defaultdict(list)
        for index_url in self.index_urls:
            res = requests.get(f"{index_url}/{name}")
            res.raise_for_status()
            doc = html5lib.parse(res.content, namespaceHTMLElements=False)
            for el in doc.findall(".//a"):
                url = el.attrib["href"]
                filename = urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1]
                wheel_name, ext = filename.rsplit(".", 1)
                if ext != "whl":
                    continue
                requires_python = el.attrib.get("data-requires-python")
                name, version, tag = _parse_wheel_name(wheel_name)
                try:
                    rank = self.matcher.rank(tag, requires_python)
                except packaging.specifiers.InvalidSpecifier:
                    logger.critical(
                        "Dropping %s==%s; invalid Requires-Python %r",
                        name,
                        version,
                        requires_python,
                    )
                    continue
                if rank is None:
                    continue
                all_dists[version].append((rank, url))
        urls = {version: min(dists)[1] for version, dists in all_dists.items()}
        logger.info("%d URLs found for %s", len(urls), name)
        return urls

    def iter_package_entries(self, name: str) -> Iterator[PackageEntry]:
        for version, url in self.collect_best_dist_urls(name).items():
            http_file = cast(IO[bytes], HttpFile(url, self.session))
            with zipfile.ZipFile(http_file) as zf:
                with _open_metadata(zf, name) as f:
                    parser = email.parser.BytesParser()
                    data = parser.parse(cast(BinaryIO, f), headersonly=True)
            dependencies: List[str] = data.get_all("Requires-Dist", [])
            yield PackageEntry(version, dependencies)

    def process_package_entry(
        self, name: str, entry: PackageEntry
    ) -> Optional[Set[str]]:
        more = set()
        for dep in entry.dependencies:
            try:
                req = packaging.requirements.Requirement(dep)
            except packaging.requirements.InvalidRequirement:
                logger.critical(
                    "Dropping %s==%s; invalid dependency %r",
                    name,
                    entry.version,
                    dep,
                )
                return None
            more.add(str(packaging.utils.canonicalize_name(req.name)))
        return more

    def find(self, package_names: Iterable[str]) -> dict:
        data = {}
        while package_names:
            more: Set[str] = set()
            logger.info("Discovering %s", ", ".join(package_names))
            for name in package_names:
                entries: Dict[str, dict] = {}
                for e in self.iter_package_entries(name):
                    result = self.process_package_entry(name, e)
                    if result is None:
                        continue
                    more |= result
                    entries[e.version] = {"dependencies": e.dependencies}
                data[name] = entries
            package_names = {n for n in more if n not in data}
        return data


def main(args: Optional[List[str]]) -> int:
    options = parse_args(args)
    if not options.output:
        output_path: Optional[pathlib.Path] = None
    else:
        output_path = get_output_path(options.output, options.overwrite)
    matcher = WheelMatcher.compatible_with(
        options.python_version, options.interpreter, options.platforms
    )

    finder = Finder(["https://pypi.org/simple"], matcher, requests.Session())
    data = finder.find(options.package_names)

    if output_path is None:
        json.dump(data, sys.stdout, indent=2)
        print()
    else:
        with output_path.open("w") as f:
            json.dump(data, f, indent="\t")
        logger.info("Written: %s", os.fspath(output_path))

    return 0


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    sys.exit(main(None))
