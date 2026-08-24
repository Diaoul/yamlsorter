"""Errors this tool raises deliberately."""

from __future__ import annotations


class YAMLSorterError(Exception):
    """Base class for errors this tool raises deliberately."""


class ConfigError(YAMLSorterError):
    """A template is missing or unusable."""


class ParseError(YAMLSorterError):
    """A manifest could not be read or parsed."""
