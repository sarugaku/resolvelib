import pathlib
import shlex
import shutil

import invoke


ROOT = pathlib.Path(__file__).resolve().parent


@invoke.task()
def build(ctx):
    """Build the package into distributables.

    This will create two distributables: source and wheel.
    """
    ctx.run(f'python setup.py sdist bdist_wheel')


@invoke.task()
def clean(ctx):
    """Clean previously built package artifacts.
    """
    ctx.run(f'python setup.py clean')
    dist = ROOT.joinpath('dist')
    print(f'removing {dist}')
    shutil.rmtree(str(dist))


@invoke.task(pre=[clean, build])
def upload(ctx, repo):
    """Upload the package to an index server.

    This implies cleaning and re-building the package.

    :param repo: Required. Name of the index server to upload to, as specifies
        in your .pypirc configuration file.
    """
    artifacts = ' '.join(
        shlex.quote(str(n))
        for n in ROOT.joinpath('dist').glob('resolvelib-*')
    )
    ctx.run(f'twine upload --repository="{repo}" {artifacts}')
