==========
ResolveLib
==========

ResolveLib at the highest level provides a `Resolver` class that includes
dependency resolution logic. You give it some things, and a little information
on how it should interact with them, and it will spit out a resolution result.


Intended Usage
==============

::

    # Things I want to resolve.
    requirements = [...]

    # Implement logic so the resolver understands the requirement format.
    class MyProvider:
        ...

    provider = MyProvider()

    # Create the (reusable) resolver.
    from resolvelib import Resolver
    resolver = Resolver(provider)

    # Kick off the resolution process, and get the final result.
    result = resolver.resolve(requirements)

The provider interface is specified in ``resolvelib.providers``. You don't
need to inherit anything, however, only need to implement the right methods.


Terminology
===========

The intention of this section is to unify the terms we use when talking about
this code base, and packaging in general, to avoid confusion. Class and
variable names in the code base should try to stick to terms defined here.

Things passed into `Resolver.resolve()` and provided by the provider are all
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
number should increase when a Package post a new snapshot, i.e. a higher number
means a more up-to-date snapshot.

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

Some resolver architectures (e.g. Molinillo) refer this as a "specicifation",
but this is not chosen to avoid confusion with a *Specifier*.

Requirement
-----------

An intention to acquire a needed package, i.e. an "abstract requirement". A
"dependency", if not clarified otherwise, also refers to this concept.

A Requiremnt should specify two things: a Package, and a Specifier.


Dependency
----------

A dependency can be either a requirement, or a candidate. In implementations
you can treat it as the parent class and/or a protocol of the two.
