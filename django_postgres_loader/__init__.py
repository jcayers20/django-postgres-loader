"""Bulk CSV loading into PostgreSQL via Django model managers."""

from .managers import CopyManager

__all__ = ("CopyManager",)
