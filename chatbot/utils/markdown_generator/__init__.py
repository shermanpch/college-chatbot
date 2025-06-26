"""
Markdown Generator Package

This package contains utilities for converting JSON data to markdown format
and generating articles from JSON data using AI.

Shared utilities:
- utils: Data loading, ID generation, and university lookup
- formatters: Text formatting and value processing utilities
"""

from .formatters import get_value, slugify
from .utils import (
    generate_unique_id,
    load_peterson_data,
    lookup_university_by_id,
    search_universities,
)

__all__ = [
    "generate_unique_id",
    "load_peterson_data",
    "lookup_university_by_id",
    "search_universities",
    "slugify",
    "get_value",
]
