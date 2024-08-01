import pytest

from resolvelib import BaseReporter


class TestReporter(BaseReporter):
    def __init__(self):
        self._indent = 0
        self.visited = []

    def rejecting_candidate(self, criterion, candidate):
        self._indent -= 1
        self.visited.append(candidate)
        print(" " * self._indent, "Reject ", candidate, sep="")

    def pinning(self, candidate):
        print(" " * self._indent, "Pin  ", candidate, sep="")
        self.visited.append(candidate)
        self._indent += 1


@pytest.fixture(scope="session")
def reporter_cls():
    return TestReporter


@pytest.fixture()
def reporter(reporter_cls):
    return reporter_cls()
