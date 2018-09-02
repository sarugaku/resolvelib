0.2.1 (2018-08-21)
==================

Features
--------

- Add new reporting callbacks `adding_requirements`, `adding_candidate`, and `replacing_candidate` to report progress in requirement pinning.  `#2 <https://github.com/sarugaku/resolvelib/issues/2>`_


Bug Fixes
---------

- Fix missing edges in the resolved dependency graph caused by incorrectly copying stale constraint and parent-child information.  `#5 <https://github.com/sarugaku/resolvelib/issues/5>`_


0.2.0 (2018-08-07)
==================

* ``Resolver.resolve()`` now returns a `namedtuple` with public attributes,
  instead of an internal `Resolution` object.
* Update trove classifiers on PyPI to better reflect the project's intentions.
