import pathlib
import subprocess

import invoke
import parver


ROOT = pathlib.Path(__file__).resolve().parent.parent

INIT_PY = ROOT.joinpath("src", "resolvelib", "__init__.py")


def _read_version():
    out = subprocess.check_output(["git", "tag"], encoding="ascii")
    try:
        version = max(
            parver.Version.parse(v).normalize()
            for v in (line.strip() for line in out.split("\n"))
            if v
        )
    except ValueError:
        version = parver.Version.parse("0.0.0")
    return version


def _write_version(v):
    lines = []
    with INIT_PY.open() as f:
        for line in f:
            if line.startswith("__version__ = "):
                line = f"__version__ = {repr(str(v))}\n"
            lines.append(line)
    with INIT_PY.open("w", newline="\n") as f:
        f.write("".join(lines))


REL_TYPES = (
    "major",
    "minor",
    "patch",
)


def _bump_release(version, type_):
    if type_ not in REL_TYPES:
        raise ValueError(f"{type_} not in {REL_TYPES}")
    index = REL_TYPES.index(type_)
    next_version = version.base_version().bump_release(index)
    print(f"[bump] {version} -> {next_version}")
    return next_version


def _prebump(version, prebump):
    if prebump not in REL_TYPES:
        raise ValueError(f"{prebump} not in {REL_TYPES}")
    index = REL_TYPES.index(prebump)
    next_version = version.bump_release(index).bump_dev()
    print(f"[bump] {version} -> {next_version}")
    return next_version


@invoke.task()
def release(ctx, type_, repo, prebump="patch"):
    """Make a new release.
    """
    version = _read_version()

    if type_:
        version = _bump_release(version, type_)
        _write_version(version)

    ctx.run("towncrier")

    ctx.run(f'git commit -am "Release {version}"')

    ctx.run(f'git tag -a {version} -m "Version {version}"')

    if repo:
        print(f"[release] Releasing distributions to {repo}...")
        ctx.run(f"setl publish --repository={repo}")
    else:
        print(f"[release] Building distributions locally...")
        ctx.run(f"setl publish --no-upload")

    if prebump:
        version = _prebump(version, prebump)
        _write_version(version)
        ctx.run(f'git commit -am "Prebump to {version}"')
