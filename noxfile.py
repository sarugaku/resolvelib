import argparse
import pathlib

import nox


ROOT = pathlib.Path(__file__).resolve().parent.parent

INIT_PY = ROOT.joinpath("src", "resolvelib", "__init__.py")

nox.options.sessions = ["lint", "tests-3.8"]


@nox.session(python="3.8")
def lint(session):
    session.install(".[lint]")
    session.run("black", "--check", ".")
    session.run("flake8", "src", "tests", "noxfile.py")


@nox.session(python=["3.8", "2.7"])
def tests(session):
    session.install(".[test]")
    session.run("pytest", "tests")


def _write_package_version(v):
    lines = []

    version_line = None
    with INIT_PY.open() as f:
        for line in f:
            if line.startswith("__version__ = "):
                line = version_line = f"__version__ = {repr(str(v))}\n"
            lines.append(line)
    if not version_line:
        raise ValueError("__version__ not found in __init__.py")

    with INIT_PY.open("w", newline="\n") as f:
        f.write("".join(lines))


@nox.session(python="3.8")
def release(session):
    session.install(".[release]")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        help="Version to release. Empty value uses the value in __init__.py",
    )
    parser.add_argument(
        "--repo",
        help="Repository to upload to. Empty value disables publish.",
    )
    parser.add_argument(
        "--prebump",
        help="Version to bump to after release. Empty value disables bump.",
    )
    options = parser.parse_args(session.posargs)

    # Make sure the workspace is clean.
    session.run("git", "diff", "--no-patch", "--exit-code", external=True)

    if options.version:
        _write_package_version(options.version)
        session.run("towncrier", "--version", options.version)
        session.run(
            "git",
            "commit",
            "--all",
            "--message",
            f"Release {options.version}",
            external=True,
        )
        session.run(
            "git",
            "tag",
            "--annotate",
            "--message",
            f"Version {options.version}",
            external=True,
        )
    else:
        session.log("Skipping preprocessing since --version is empty")

    if options.repo:
        session.log(f"Releasing distributions to {options.repo}...")
        session.run("setl", "publish", "--repository", options.repo)
    else:
        session.log(f"Building distributions locally since --repo is empty")
        session.run(f"setl publish --no-upload")

    if options.prebump:
        _write_package_version(options.prebump)
        session.run(
            "git",
            "commit",
            "--all",
            "--message",
            f"Prebump to {options.prebump}",
            external=True,
        )
