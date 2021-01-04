from __future__ import print_function

import pytest

from resolvelib import BaseReporter


class TestReporter(BaseReporter):
    def __init__(self):
        self._indent = 0

    def backtracking(self, candidate):
        self._indent -= 1
        assert self._indent >= 0
        print(" " * self._indent, "Back ", candidate, sep="")

    def pinning(self, candidate):
        print(" " * self._indent, "Pin  ", candidate, sep="")
        self._indent += 1


@pytest.fixture(scope="session")
def reporter_cls():
    return TestReporter


@pytest.fixture()
def reporter(reporter_cls):
    return reporter_cls()
