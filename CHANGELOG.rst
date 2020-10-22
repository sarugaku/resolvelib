0.5.1 (2020-10-22)
==================

Features
--------

- ``find_matches()`` now may return a ``Callable[[], Iterator[Candidate]]`` to
  avoid needing to provide all candidates eagerly for the resolver. This improves
  performance when fetching candidates is costly, but not always required.  `#57 <https://github.com/sarugaku/resolvelib/issues/57>`_


0.4.0 (2020-04-30)
==================

Features
--------

- Add ``parent`` argument to the ``add_requirement()`` reporter hook.  `#46 <https://github.com/sarugaku/resolvelib/issues/46>`_

- Redesign ``find_matches()`` to support a requirement "adding" candidates to
  the set, and nudge the provider away from implementing ``find_matches()`` and
  ``is_satisfied_by()`` with incorrect set properties.  `#49 <https://github.com/sarugaku/resolvelib/issues/49>`_


0.3.0 (2020-04-11)
==================

Features
--------

- Provide both the requirements and their parents as exceptiondata for the
  ``ResolutionImpossible`` exception, via a ``causes`` attribute that replaces
  the previous ``requirements`` attribute.  `#42 <https://github.com/sarugaku/resolvelib/issues/42>`_


Bug Fixes
---------

- Make resolver backtrack when none of the candidates requested for a package
  are able to resolve due to them requesting unworkable requirements, or a
  package has no candidates at all. Previously the resolver would give up on the
  spot.  `#18 <https://github.com/sarugaku/resolvelib/issues/18>`_

- Ensure the result returned by the resolver only contains candidates that are
  actually needed. This is done by tracing the graph after resolution completes,
  snipping nodes that don’t have a route to the root.  `#4 <https://github.com/sarugaku/resolvelib/issues/4>`_


0.2.2 (2018-09-03)
==================

Features
--------

- Remove reporting callbacks `adding_requirements`, `adding_candidate`, and `replacing_candidate` added in 0.2.1. These are not useful, and it’s better to remove them while we can.  `#6 <https://github.com/sarugaku/resolvelib/issues/6>`_


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
