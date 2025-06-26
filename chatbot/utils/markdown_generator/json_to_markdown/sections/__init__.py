"""
Section generators for Peterson data markdown conversion.

This module contains functions for generating different sections of university markdown documents.
"""

from .academics import generate_academics_section
from .admissions import generate_admissions_section
from .athletics import generate_athletics_section
from .campus_life import generate_campus_life_section
from .general_info import generate_general_info_section
from .tuition import generate_tuition_section

__all__ = [
    "generate_academics_section",
    "generate_admissions_section",
    "generate_athletics_section",
    "generate_campus_life_section",
    "generate_general_info_section",
    "generate_tuition_section",
]
