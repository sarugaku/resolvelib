class BaseReporter(object):
    """Delegate class to provider progress reporting for the resolver.
    """
    def starting(self):
        """Called before the resolution actually starts.
        """

    def starting_round(self, index):
        """Called before each round of resolution starts.

        The index is zero-based.
        """

    def adding_requirements(self, requirements):
        """Called before requirements are being added.

        The requirements are not necessarily new.
        """

    def adding_candidate(self, candidate):
        """Called before a candidate is being used to pin a requirement.
        """

    def replacing_candidate(self, current, replacement):
        """Called before a candidate is being replaced by another as the pin.
        """

    def ending_round(self, index, state):
        """Called before each round of resolution ends.

        This is NOT called if the resolution ends at this round. Use `ending`
        if you want to report finalization. The index is zero-based.
        """

    def ending(self, state):
        """Called before the resolution ends successfully.
        """
