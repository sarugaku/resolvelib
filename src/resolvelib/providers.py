class AbstractProvider(object):
    """Delegate class to provide requirment interface for the resolver.
    """
    def identify(self, dependency):
        """Given a dependency, return an identifier for it.

        This is used in many places to identify the dependency, e.g. whether
        two requirements should have their specifier parts merged, whether
        two specifications would conflict with each other (because they the
        same name but different versions).
        """
        raise NotImplementedError

    def find_matches(self, requirement):
        """Find all possible candidates that satisfy a requirement.

        This should try to get candidates based on the requirement's type.
        For VCS, local, and archive requirements, the one-and-only match is
        returned, and for a "named" requirement, the index(es) should be
        consulted to find concrete candidates for this requirement.

        The returned candidates should be sorted by reversed preference, e.g.
        the latest should be LAST. This is done so list-popping can be as
        efficient as possible.
        """
        raise NotImplementedError

    def filter_satisfied(self, candidates, requirement):
        """Filter given candidates, return those satisfying the requirement.

        The returned candidates should keep the preference ordering, i.e. best
        first, as returned by `get_candidates`.
        """
        raise NotImplementedError

    def get_dependencies(self, candidate):
        """Get dependencies of a candidate.

        This should return a collection of requirements that `candidate`
        specifies as its dependencies.
        """
        raise NotImplementedError
