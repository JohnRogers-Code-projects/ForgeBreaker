"""
Failure Explanation Envelope — Unified Response Classification.

This module defines the response envelope that ALL API endpoints must use
to communicate outcomes to the frontend. Every user-visible failure must
be classified and explained.

INVARIANT: No raw 500 errors may reach the frontend.

Response types:
- Success: Operation completed successfully
- Refusal: System chose not to proceed (expected, explainable)
- KnownFailure: System knows why it failed
- UnknownFailure: System does not know why it failed

This is enforced by code, not convention.
"""

from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class FailureKind(str, Enum):
    """Classification of failure types."""

    # Input validation failures
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED = "missing_required"

    # Resource failures
    NOT_FOUND = "not_found"
    EMPTY_RESULT = "empty_result"

    # Constraint violations
    CARD_NAME_LEAKAGE = "card_name_leakage"
    VALIDATION_FAILED = "validation_failed"
    FORMAT_ILLEGAL = "format_illegal"

    # Service failures
    SERVICE_UNAVAILABLE = "service_unavailable"
    EXTERNAL_API_ERROR = "external_api_error"

    # Unknown
    UNKNOWN = "unknown"


class OutcomeType(str, Enum):
    """High-level outcome classification."""

    SUCCESS = "success"
    REFUSAL = "refusal"
    KNOWN_FAILURE = "known_failure"
    UNKNOWN_FAILURE = "unknown_failure"


T = TypeVar("T")


class FailureDetail(BaseModel):
    """Detailed information about a failure."""

    kind: FailureKind = Field(
        ...,
        description="Classification of the failure",
    )
    message: str = Field(
        ...,
        description="User-appropriate explanation of what went wrong",
    )
    detail: str | None = Field(
        default=None,
        description="Additional technical detail (optional)",
    )
    suggestion: str | None = Field(
        default=None,
        description="Suggested action for the user",
    )


class ApiResponse(BaseModel, Generic[T]):
    """
    Universal response envelope for all API endpoints.

    Every response is classified into one of four outcome types,
    ensuring no failure reaches the user unexplained.
    """

    outcome: OutcomeType = Field(
        ...,
        description="High-level classification of the result",
    )
    data: T | None = Field(
        default=None,
        description="Response data (present on success)",
    )
    failure: FailureDetail | None = Field(
        default=None,
        description="Failure details (present on non-success)",
    )

    @classmethod
    def success(cls, data: T) -> "ApiResponse[T]":
        """Create a success response."""
        return cls(outcome=OutcomeType.SUCCESS, data=data)

    @classmethod
    def refusal(
        cls,
        kind: FailureKind,
        message: str,
        detail: str | None = None,
        suggestion: str | None = None,
    ) -> "ApiResponse[Any]":
        """
        Create a refusal response.

        Use when the system chose not to proceed due to a constraint.
        Example: Card name invariant violation.
        """
        return cls(
            outcome=OutcomeType.REFUSAL,
            failure=FailureDetail(
                kind=kind,
                message=message,
                detail=detail,
                suggestion=suggestion,
            ),
        )

    @classmethod
    def known_failure(
        cls,
        kind: FailureKind,
        message: str,
        detail: str | None = None,
        suggestion: str | None = None,
    ) -> "ApiResponse[Any]":
        """
        Create a known failure response.

        Use when the system knows exactly why the operation failed.
        Example: Resource not found, invalid input format.
        """
        return cls(
            outcome=OutcomeType.KNOWN_FAILURE,
            failure=FailureDetail(
                kind=kind,
                message=message,
                detail=detail,
                suggestion=suggestion,
            ),
        )

    @classmethod
    def unknown_failure(
        cls,
        detail: str | None = None,
    ) -> "ApiResponse[Any]":
        """
        Create an unknown failure response.

        Use when the system does not know why it failed.
        This is the catch-all for unexpected exceptions.
        """
        return cls(
            outcome=OutcomeType.UNKNOWN_FAILURE,
            failure=FailureDetail(
                kind=FailureKind.UNKNOWN,
                message=("An unexpected error occurred. Try simplifying your request or retrying."),
                detail=detail,
                suggestion="If this persists, please report the issue.",
            ),
        )


# Standard exception types that map to known failures


class KnownError(Exception):
    """
    Base class for exceptions that represent known, explainable failures.

    Subclass this for errors where the system knows exactly what went wrong.
    """

    def __init__(
        self,
        kind: FailureKind,
        message: str,
        detail: str | None = None,
        suggestion: str | None = None,
        status_code: int = 400,
    ):
        self.kind = kind
        self.message = message
        self.detail = detail
        self.suggestion = suggestion
        self.status_code = status_code
        super().__init__(message)

    def to_response(self) -> ApiResponse[Any]:
        """Convert to an ApiResponse."""
        return ApiResponse.known_failure(
            kind=self.kind,
            message=self.message,
            detail=self.detail,
            suggestion=self.suggestion,
        )


class RefusalError(Exception):
    """
    Exception for constraint-based refusals.

    Use when the system refuses to proceed due to an integrity constraint.
    Example: Card name invariant violation.
    """

    def __init__(
        self,
        kind: FailureKind,
        message: str,
        detail: str | None = None,
        suggestion: str | None = None,
    ):
        self.kind = kind
        self.message = message
        self.detail = detail
        self.suggestion = suggestion
        super().__init__(message)

    def to_response(self) -> ApiResponse[Any]:
        """Convert to an ApiResponse."""
        return ApiResponse.refusal(
            kind=self.kind,
            message=self.message,
            detail=self.detail,
            suggestion=self.suggestion,
        )
