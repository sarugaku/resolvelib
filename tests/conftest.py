import pytest

from resolvelib.reporters import BaseReporter


@pytest.fixture(scope="session")
def base_reporter():
    return BaseReporter()
