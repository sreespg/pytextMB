"""The one exception the build raises for a problem it can explain."""


class BuildError(Exception):
    """A build step failed; the message says what to fix. The CLI prints it
    without a traceback, so it has to stand on its own."""
