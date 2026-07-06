class DataDetectiveError(Exception):
    """Base exception for data-detective errors."""


class DataLoadError(DataDetectiveError):
    """Raised when CSV loading fails."""


class EmptyDataError(DataLoadError):
    """Raised when the loaded dataset is empty."""
