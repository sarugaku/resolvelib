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

    def sorted_by_preference(self, requirements, resolution, conflicts):
        """Sort requirements based on preference.

        The preference is defined as "I think this requirement should be
        resolved first". The most preferred item should be pu FIRST. This
        preference could depend on a various of issues, including (not
        necessarily in this order):

        * Is this package specified in the current resolution result?
        * How relaxed is the requirement? Stricter ones should probably be
          worked on first? (I don't know, actually.)
        * How many possibilities are there to satisfy this requirement? Those
          with few left should likely be worked on first, I guess?
        * Are there any known conflicts for this requirement? We should
          probably work on those with the most known conflicts.

        A new list should be returned. It should contain all the same entries
        of `requirements`, but with proper ordering.
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


class RequirementsLibSpecificationProvider(AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self):
        # TODO: Provide additional context for this provider, e.g. index URLs,
        # whether to allow prereleases, etc.
        pass

    def identify(self, dependency):
        # Treat a package with extra(s) as distinct from the package without
        # extras. `requests` is distinct from `requests[soc]`, and
        # `requests[soc]` is also distinct from both `requests[security]`
        # and `requests[security,soc]`.
        # TODO: Do we need to normalize package and extra names?
        if not dependency.extras:
            return dependency.name
        return '{}[{}]'.format(dependency.name, ','.join(dependency.extras))

    # TODO: ...

    def get_dependencies(self, candidate):
        # This should ask opinions of:
        # * Cached resolution results (unless explicitly disabled).
        # * Cached wheel (both the Simple or JSON API know what wheel to use).
        # * The JSON API.
        # * Downloaded wheel specified by the Simple API.
        # * Built source distribution, either specified by the Simple API, or
        #   the requirement directly (in VCS or archive requirements).
        raise NotImplementedError('TODO')
