from resolvelib import Resolver  # isort: skip
from visualization.generate import generate_html  # isort: skip
from visualization.reporter import GraphGeneratingReporter  # isort: skip
from pypi_wheel_provider import (  # isort: skip
    Requirement,
    PyPIProvider,
)

if __name__ == "__main__":
    provider = PyPIProvider()
    reporter = GraphGeneratingReporter()

    resolver = Resolver(provider, reporter)

    reqs = [Requirement("oslo.utils==1.4.0")]
    try:
        resolver.resolve(reqs)
    finally:
        with open("out2.html", "w") as f:
            generate_html(reporter.evolution, f)
