import ast
import os

from setuptools import find_packages, setup


def read_version():
    version_txt = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'src', 'resolvelib', '__init__.py',
    )
    with open(version_txt) as f:
        for line in f:
            if not line.startswith('__version__'):
                continue
            return ast.literal_eval(line.split('=', 1)[-1].strip())
    raise RuntimeError('failed to read package version')


# Put everything in setup.cfg, except those that don't actually work?
setup(
    # These really don't work.
    package_dir={'': 'src'},
    packages=find_packages('src'),

    # I don't know how to specify an empty key in setup.cfg.
    package_data={
        '': ['LICENSE*', 'README*'],
    },

    # I need this to be dynamic.
    version=read_version(),
)
