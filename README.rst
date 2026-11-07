==========
ResolveLib
==========

ResolveLib at the highest level provides a ``Resolver`` class that includes
dependency resolution logic. You give it some things, and a little information
on how it should interact with them, and it will spit out a resolution result.


Intended Usage
==============

::

    import resolvelib

    # Things I want to resolve.
    requirements = [...]

    # Implement logic so the resolver understands the requirement format.
    class MyProvider:
        ...

    provider = MyProvider()
    reporter = resolvelib.BaseReporter()

    # Create the (reusable) resolver.
    resolver = resolvelib.Resolver(provider, reporter)

    # Kick off the resolution process, and get the final result.
    result = resolver.resolve(requirements)

The provider interface is specified in ``resolvelib.providers``. You don't
need to inherit anything, however, only need to implement the right methods.


Terminology
===========

The intention of this section is to unify the terms we use when talking about
this code base, and packaging in general, to avoid confusion. Class and
variable names in the code base should try to stick to terms defined here.

Things passed into ``Resolver.resolve()`` and provided by the provider are all
considered opaque. They don't need to adhere to this set of terminologies.
Nothing can go wrong as long as the provider implementers can keep their heads
straight.

Package
-------

A thing that can be installed. A Package can have one or more versions
available for installation.

Version
-------

A string, usually in a number form, describing a snapshot of a Package. This
number should increase when a Package posts a new snapshot,
i.e a higher number means a more up-to-date snapshot.

Specifier
---------

A collection of one or more Versions. This could be a wildcard, indicating that
any Version is acceptable.

Candidate
---------

A combination of a Package and a Version, i.e. a "concrete requirement". Python
people sometimes call this a "locked" or "pinned" dependency. Both of
"requirement" and "dependency", however, SHOULD NOT be used when describing a
Candidate, to avoid confusion.

Some resolver architectures refer this as a "specification", but it is not
used here to avoid confusion with a *Specifier*.

Requirement
-----------

An intention to acquire a needed package, i.e. an "abstract requirement". A
"dependency", if not clarified otherwise, also refers to this concept.

A Requirement should specify two things: a Package, and a Specifier.

Implementing a provider
=======================

The resolver controls the search and backtracking; the provider defines what
requirements and candidates mean for your application. For example, two
requirements for different version ranges of the same package share an
identifier, while each available version is a separate candidate.

The methods on ``AbstractProvider`` divide this work as follows:

* ``identify(requirement_or_candidate)`` returns the same hashable identifier
  for requirements and candidates belonging to the same dependency.
* ``find_matches(identifier, requirements, incompatibilities)`` returns
  candidates for that identifier. Each candidate must satisfy **all** of
  ``requirements[identifier]`` and exclude the candidates in
  ``incompatibilities[identifier]``. Return your preferred candidate first
  (for example, the newest version first).
* ``is_satisfied_by(requirement, candidate)`` checks whether one candidate
  satisfies one requirement. Use the same rules here and in ``find_matches``.
* ``get_dependencies(candidate)`` returns the requirements introduced by that
  candidate, not the candidates that will satisfy them. The resolver will
  combine these with any existing constraints on the same identifiers.
* ``get_preference(...)`` orders **dependencies to resolve**, not candidate
  versions. The dependency with the lowest sort key is considered first.
* ``narrow_requirement_selection(...)`` can optionally reduce the dependencies
  considered by ``get_preference``. Subclassing ``AbstractProvider`` supplies
  a default that leaves the selection unchanged.

See `the provider interface <https://github.com/sarugaku/resolvelib/blob/main/src/resolvelib/providers.py>`_ for the complete
method signatures and argument contracts. The resolver can call these methods
again while backtracking; providers must not assume a candidate returned by
``find_matches`` will become part of the final solution.

For a runnable example using an in-memory package index, see
`reporter_demo.py <https://github.com/sarugaku/resolvelib/blob/main/examples/reporter_demo.py>`_. From a checkout, run::

    python -m pip install ".[test]"
    python examples/reporter_demo.py

This example supplies both a provider and a reporter. The reporter observes
resolution events; it does not choose candidates. The resolver finds a
compatible combination of ``first``, ``second``, and ``third`` and returns it
in ``result.mapping``, keyed by the identifiers returned by ``identify``.
The mapping describes the solution; resolving does not download or install it.

If no compatible combination exists, ``resolve`` raises
``ResolutionImpossible``; its ``causes`` attribute lists the requirements and
parent candidates involved in the conflict. ``ResolutionTooDeep`` instead
means the search reached its round limit, and does not prove that there is no
solution. A resolver instance can be reused for another call to ``resolve``.


Contributing
============

Please see `developer documentation <https://github.com/sarugaku/resolvelib/blob/main/DEVELOPMENT.rst>`__.
