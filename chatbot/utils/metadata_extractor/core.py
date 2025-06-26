"""
Core metadata extraction logic for Peterson university data.

This module contains the main extraction function that orchestrates the
generation of metadata from Peterson university data for ChromaDB.
"""

from typing import Any

from .sections import (
    extract_academic_metadata,
    extract_admissions_metadata,
    extract_athletics_metadata,
    extract_cost_aid_metadata,
    extract_housing_metadata,
    extract_identity_location_metadata,
)
from .utils import convert_none_to_sentinel


def extract_metadata_from_json(json_record: dict[str, Any]) -> dict[str, Any]:
    """
    Extracts comprehensive shortlist metadata from a university's JSON object.

    Extracts ~46 scalar fields with ≥60% coverage for ChromaDB metadata filtering:
    - Location & Identity (url, university_name, state, city, zip_code, country, region★)
    - Admissions & selectivity (accept_rate, avg_high_school_gpa, application_fee, deadlines, test_optional)
    - Standardized test bands (SAT verbal/math 25/75/avg, ACT composite 25/75/avg)
    - Cost & aid (tuition variants, room_and_board, avg_financial_aid_package, etc.)
    - Academic environment (student_faculty_ratio, total_faculty)
    - Campus living (college_owned_housing, housing_required_first_year, percent_students_on_campus)
    - Athletics (sport booleans, scholarship_sports_available)

    Args:
        json_record: A dictionary containing university data

    Returns:
        A dictionary with flattened metadata suitable for ChromaDB
    """
    metadata = {}

    # Extract metadata from each section
    metadata.update(extract_identity_location_metadata(json_record))
    metadata.update(extract_admissions_metadata(json_record))
    metadata.update(extract_cost_aid_metadata(json_record))
    metadata.update(extract_academic_metadata(json_record))
    metadata.update(extract_housing_metadata(json_record))
    metadata.update(extract_athletics_metadata(json_record))

    # Convert None values to appropriate sentinel values instead of removing them
    return convert_none_to_sentinel(metadata)
