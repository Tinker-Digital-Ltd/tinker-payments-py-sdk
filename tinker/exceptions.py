"""SDK exception types."""


class TinkerError(Exception):
    """Base SDK exception."""


class ApiError(TinkerError):
    """Raised when API returns an error response."""


class NetworkError(TinkerError):
    """Raised when request transport fails."""


class InvalidPayloadError(TinkerError):
    """Raised when payload parsing or shape validation fails."""
