from __future__ import annotations


class CommandError(Exception):
    """An actionable, language-independent failure at the command boundary."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        exit_code: int = 1,
        retryable: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
            "details": self.details,
        }
