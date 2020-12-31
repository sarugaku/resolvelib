import pytest

from resolvelib.reporters import BaseReporter


@pytest.fixture(scope="session")
def base_reporter():
    return BaseReporter()


def constrained_first(resolution, candidates, information):
    return len(candidates)


def loose_first(resolution, candidates, information):
    return -len(candidates)


@pytest.fixture(scope="session", params=[constrained_first, loose_first])
def preference_strategy(request):
    return request.param
