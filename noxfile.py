import argparse
import json
import pathlib

import nox


ROOT = pathlib.Path(__file__).resolve().parent

INIT_PY = ROOT.joinpath("src", "resolvelib", "__init__.py")

nox.options.sessions = ["lint", "tests"]
nox.options.reuse_existing_virtualenvs = True


@nox.session
def lint(session):
    session.install(".[lint]")

    session.run("black", "--check", ".")
    session.run("flake8", ".")
    session.run("mypy", "src")


@nox.session(python=["3.9", "3.8", "3.7", "3.6", "3.5", "2.7"])
def tests(session):
    session.install(".[test]")

    files = session.posargs or ["tests"]
    session.run("pytest", *files)


def _write_package_version(v):
    lines = []

    version_line = None
    with INIT_PY.open() as f:
        for line in f:
            if line.startswith("__version__ = "):
                line = version_line = f"__version__ = {json.dumps(str(v))}\n"
            lines.append(line)
    if not version_line:
        raise ValueError("__version__ not found in __init__.py")

    with INIT_PY.open("w", newline="\n") as f:
        f.write("".join(lines))


@nox.session
def release(session):
    session.install(".[release]")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        required=True,
        help="Version to release. Empty value uses the value in __init__.py.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository to upload to. Empty value disables publish.",
    )
    parser.add_argument(
        "--prebump",
        required=True,
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
            options.version,
            external=True,
        )
    else:
        session.log("Skipping preprocessing since --version is empty")

    if options.repo:
        session.log(f"Releasing distributions to {options.repo}...")
        session.run("setl", "publish", "--repository", options.repo)
    else:
        session.log("Building distributions locally since --repo is empty")
        session.run("setl", "publish", "--no-upload")

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
