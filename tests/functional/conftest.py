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


@pytest.fixture()
def reporter():
    return TestReporter()
