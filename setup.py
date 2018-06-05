import os

from setuptools import find_packages, setup


def read_version():
    version_txt = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'src', 'resolvelib', 'version.txt',
    )
    with open(version_txt) as f:
        return f.read().strip()


# Put everything in setup.cfg, except those that don't actually work?
setup(
    # These really don't work.
    package_dir={'': 'src'},
    packages=find_packages('src'),

    # I don't know how to specify an empty key in setup.cfg.
    package_data={
        '': ['version.txt', 'LICENSE*', 'README*'],
    },

    # I need this to be dynamic.
    version=read_version(),
)
