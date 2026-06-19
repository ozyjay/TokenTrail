"""Shared adapter types."""

from __future__ import annotations


class AdapterError(Exception):
    """Raised when a backend adapter cannot complete a local operation."""
