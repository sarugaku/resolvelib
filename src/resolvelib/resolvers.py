class Resolver(object):
    """The thing that performs the actual resolution work.
    """
    def __init__(self, provider):
        # TODO: Take inspiration from Molinillo and provide a "UI" delegate
        # to report progress in alternative ways. This would be very
        # beneficial for Pipenv (i.e. report locking progress via TCP).
        self._p = provider

    def resolve(self, requirements):
        """Take a collection of constraints, spit out the resolution result.
        """
        # TODO: I want to implement this to resolve into a graph structure,
        # not a flat dict like pip-tools, but Python doesn't have a built-in
        # graph type, so this would require additional work. We also need a way
        # to trace each entry in the resolution to what resulted it being
        # included, so we can add appropriate environment markers to it for
        # the installation process.
        raise NotImplementedError
