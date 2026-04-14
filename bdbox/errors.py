"""Exceptions for bdbox."""


class Error(Exception):
    """Base class for all bdbox exceptions."""


class ParamsError(Error):
    """Raised for invalid parameters configuration."""


class ParamValidationError(Error, ValueError):
    """Raised when a parameter value fails validation."""
