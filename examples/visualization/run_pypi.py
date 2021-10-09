from pypi_wheel_provider import PyPIProvider, Requirement
from visualization.generate import generate_html
from visualization.reporter import GraphGeneratingReporter

from resolvelib import Resolver

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
