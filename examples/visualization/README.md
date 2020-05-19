# Visualization Reporter

This directory contains a reporter, that can be used to visualize how the
resolution algorithm is exploring the dependency graph, by exposing the
information about the process that is being provided by the reporter.

## Usage

There's 2 ways to try out the reporter defined in this directory:

1. With `run.py`, based on an output from `reporter_demo.py`. This demonstrates
   how to "record" a resolution run, and "play it back" later to generate the
   visualization.

   ```sh-session
   $ # In the examples/ directory
   $ python reporter_demo.py > foo.txt
   $ python visualization/run.py foo.txt out.html
   ...
   ```

2. With `run_pypi.py`, that uses the `pypi_wheel_provider.py` example code. This
   demonstrates how a visualization can be generated while running the resolver.

   ```sh-session
   $ # In the examples/ directory
   $ python visualization/run_pypi.py out.html
   ...
   ```

> NOTE: This code mainly serves to demonstrate what can be done with
> resolvelib's Reporter API. It likely contains bugs and there's definitely a
> lot of scope for improvement here (more interactive visualization, making it
> easier to look at and work with larger dependency graphs and more).
