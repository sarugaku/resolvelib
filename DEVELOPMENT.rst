===========
Development
===========

ResolveLib is a volunteer maintained open source project and we welcome contributions of all forms.
The sections below will help you get started with development, testing, and documentation.


Getting Started
===============

The first thing to do is to fork this repository, install with test dependencies and run tests.


.. code-block:: shell

    python -m pip install .[test]

    python -m pytest


Submitting Pull Requests
========================

Please make sure any changes are covered by existing tests or that new tests are added.
ResolveLib is used on many different python versions and operating systems and environments so every effort must be made in order to keep code portable.
Pull requests should be small to facilitate easier review.


Release Process for Maintainers
===============================

Replace ``X.Y.Z`` with the release you would like to make.

(The following assumes the remote you forked is called ``origin``, and the canonical sarugaku/resolvelib is under ``upstream``.)

* Make sure the news fragments are in place.
* ``git checkout -b release/X.Y.Z``
* ``nox -s release -- --repo https://upload.pypi.org/legacy/ --prebump X.Y.Z+1.dev0 --version X.Y.Z``
* ``git push upstream --tags``
* ``git push origin release/X.Y.Z``
* Open a pull request on GitHub and merge the ``release/X.Y.Z`` branch into main.

Breakdown of the ``release`` nox task:

* Writes ``X.Y.Z`` to ``src/resolvelib/__init__.py``.
* Runs ``towncrier`` to update the changelog and delete news fragments.
* Commit the changelog and version change.
* Tag the commit as release ``X.Y.Z``.
* Build, check, and upload distributions to the index specified by ``repo``.
* Writes ``X.Y.Z+1.dev0`` to ``src/resolvelib/__init__.py``.
* Commit the "prebump" change.
