"""
Utility functions for metadata extraction.

This module contains helper functions used across different metadata extraction sections.
"""

from typing import Any

# Define field types for sentinel value assignment
FIELD_TYPES = {
    # String fields
    "university_name": str,
    "state": str,
    "city": str,
    "region": str,
    "zip_code": str,
    "application_deadline_regular": str,
    "application_deadline_early": str,
    # Integer fields
    "application_fee": int,
    "sat_verbal_25": int,
    "sat_verbal_75": int,
    "sat_verbal_avg": int,
    "sat_math_25": int,
    "sat_math_75": int,
    "sat_math_avg": int,
    "sat_total_avg": int,
    "act_composite_25": int,
    "act_composite_75": int,
    "act_composite_avg": int,
    "tuition_private": int,
    "tuition_in_state": int,
    "tuition_out_of_state": int,
    "room_and_board": int,
    "full_time_student_fees": int,
    "avg_financial_aid_package": int,
    "avg_freshman_financial_aid_package": int,
    "avg_international_financial_aid_package": int,
    "avg_loan_aid": int,
    "avg_grant_aid": int,
    "avg_scholarship_and_grant_aid_awarded": int,
    "total_faculty": int,
    # Float/number fields
    "accept_rate": float,
    "avg_high_school_gpa": float,
    "percentage_need_receive_financial_aid": float,
    "avg_percentage_of_financial_need_met": float,
    "percentage_students_need_fully_met": float,
    "student_faculty_ratio": float,
    "percent_students_on_campus": float,
    # Boolean fields (these shouldn't be None, but included for completeness)
    "college_owned_housing": bool,
    "housing_required_first_year": bool,
    "sport_basketball": bool,
    "sport_volleyball": bool,
    "sport_soccer": bool,
    "sport_softball": bool,
    "sport_cross_country": bool,
    "sport_baseball": bool,
    "sport_golf": bool,
    "sport_tennis": bool,
    "sport_track": bool,
    "sport_football": bool,
    "sport_lacrosse": bool,
    "sport_swimming": bool,
    "sport_ice_hockey": bool,
    "scholarship_sports_available": bool,
}


def convert_none_to_sentinel(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Convert None and 0 values to appropriate sentinel values based on field types.

    - String fields: None -> "not_reported"
    - Integer/Float fields: None or 0 -> -1
    - Boolean fields: None -> False (shouldn't happen, but safe default)

    Args:
        metadata: Dictionary with potentially None or 0 values

    Returns:
        Dictionary with sentinel values instead of None/0
    """
    converted = {}

    for key, value in metadata.items():
        field_type = FIELD_TYPES.get(key)

        if value is None:
            if field_type is str:
                converted[key] = "not_reported"
            elif field_type in (int, float):
                converted[key] = -1
            elif field_type is bool:
                converted[key] = False
            else:
                # Unknown field type, use string sentinel as default
                converted[key] = "not_reported"
        elif value == 0 and field_type in (int, float):
            # Convert 0 to -1 for numeric fields as 0 often indicates missing data
            converted[key] = -1
        else:
            converted[key] = value

    return converted


def get_sentinel_value(field_name: str, field_type: type = None) -> Any:
    """
    Get the appropriate sentinel value for a specific field.

    Args:
        field_name: Name of the field
        field_type: Optional explicit type override

    Returns:
        Appropriate sentinel value for the field
    """
    if field_type is None:
        field_type = FIELD_TYPES.get(field_name)

    if field_type is str:
        return "not_reported"
    elif field_type in (int, float):
        return -1
    elif field_type is bool:
        return False
    else:
        # Unknown field type, use string sentinel as default
        return "not_reported"


def is_sentinel_value(value: Any, field_name: str) -> bool:
    """
    Check if a value is a sentinel value for a given field.

    Args:
        value: The value to check
        field_name: Name of the field

    Returns:
        True if the value is a sentinel value, False otherwise
    """
    expected_sentinel = get_sentinel_value(field_name)
    return value == expected_sentinel


def derive_region_from_state(state: str) -> str:
    """Derive US region from state name."""
    region_mapping = {
        # Pacific
        "California": "Pacific",
        "Oregon": "Pacific",
        "Washington": "Pacific",
        "Alaska": "Pacific",
        "Hawaii": "Pacific",
        # Mountain
        "Arizona": "Mountain",
        "Colorado": "Mountain",
        "Idaho": "Mountain",
        "Montana": "Mountain",
        "Nevada": "Mountain",
        "New Mexico": "Mountain",
        "Utah": "Mountain",
        "Wyoming": "Mountain",
        # West North Central
        "Iowa": "West North Central",
        "Kansas": "West North Central",
        "Minnesota": "West North Central",
        "Missouri": "West North Central",
        "Nebraska": "West North Central",
        "North Dakota": "West North Central",
        "South Dakota": "West North Central",
        # West South Central
        "Arkansas": "West South Central",
        "Louisiana": "West South Central",
        "Oklahoma": "West South Central",
        "Texas": "West South Central",
        # East North Central
        "Illinois": "East North Central",
        "Indiana": "East North Central",
        "Michigan": "East North Central",
        "Ohio": "East North Central",
        "Wisconsin": "East North Central",
        # East South Central
        "Alabama": "East South Central",
        "Kentucky": "East South Central",
        "Mississippi": "East South Central",
        "Tennessee": "East South Central",
        # South Atlantic
        "Delaware": "South Atlantic",
        "Florida": "South Atlantic",
        "Georgia": "South Atlantic",
        "Maryland": "South Atlantic",
        "North Carolina": "South Atlantic",
        "South Carolina": "South Atlantic",
        "Virginia": "South Atlantic",
        "West Virginia": "South Atlantic",
        "Washington DC": "South Atlantic",
        # Mid-Atlantic
        "New Jersey": "Mid-Atlantic",
        "New York": "Mid-Atlantic",
        "Pennsylvania": "Mid-Atlantic",
        # New England
        "Connecticut": "New England",
        "Maine": "New England",
        "Massachusetts": "New England",
        "New Hampshire": "New England",
        "Rhode Island": "New England",
        "Vermont": "New England",
    }

    return region_mapping.get(state, "Other")


def get_sport_variations(sport: str) -> list[str]:
    """Get various name variations for a sport."""
    variations = {
        # Top tier sports (>80% coverage)
        "basketball": ["Basketball"],
        "volleyball": ["Volleyball"],
        "soccer": ["Soccer"],
        "softball": ["Softball"],
        "cross_country": ["Cross-country Running", "Cross Country"],
        # High coverage sports (70-80%)
        "baseball": ["Baseball"],
        "golf": ["Golf"],
        "tennis": ["Tennis"],
        "track": ["Track And Field", "Track and Field"],
        "football": ["Football"],
        # Medium coverage sports (45-70%)
        "indoor_track": ["Indoor Track"],
        "lacrosse": ["Lacrosse"],
        "cheerleading": ["Cheerleading"],
        "ultimate_frisbee": ["Ultimate Frisbee"],
        "swimming": ["Swimming And Diving", "Swimming"],
        # Lower but significant coverage sports (30-45%)
        "table_tennis": ["Table Tennis"],
        "rugby": ["Rugby"],
        "bowling": ["Bowling"],
        "ice_hockey": ["Ice Hockey"],
        "badminton": ["Badminton"],
    }

    return variations.get(sport, [sport.title()])
