from __future__ import annotations

import sys
from types import TracebackType


class CustomException(Exception):
    """Application error with optional cause and call-site context."""

    def __init__(self, message: str, error_detail: BaseException | None = None) -> None:
        self.message = message
        self.error_detail = error_detail
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        _, _, exc_tb = sys.exc_info()
        location = self._format_location(exc_tb)

        parts = [self.message]
        if self.error_detail is not None:
            parts.append(f"Cause: {self.error_detail}")
        if location:
            parts.append(location)
        return " | ".join(parts)

    @staticmethod
    def _format_location(exc_tb: TracebackType | None) -> str:
        if exc_tb is None:
            return ""
        frame = exc_tb.tb_frame
        return f"File: {frame.f_code.co_filename} | Line: {exc_tb.tb_lineno}"

    def __str__(self) -> str:
        return self.args[0] if self.args else self.message
