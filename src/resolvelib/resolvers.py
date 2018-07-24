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
        raise NotImplementedError
