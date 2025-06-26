"""
Athletics section generator for Peterson university markdown conversion.
"""

from ...formatters import get_value


def format_sport(sport_obj: dict) -> str:
    """Format a sport object into a markdown line."""
    sport_name = get_value(sport_obj, "sport")
    intercollegiate = get_value(sport_obj, "intercollegiate")
    scholarship = get_value(sport_obj, "scholarship")
    intramural = get_value(sport_obj, "intramural")

    # Handle special cases for intercollegiate field that might contain division info
    if intercollegiate not in ["Yes", "No", "Not Reported"]:
        # If it contains division info like "Division 3", keep it as is
        intercollegiate_display = intercollegiate
    else:
        intercollegiate_display = intercollegiate

    return f"- **{sport_name}:** Intercollegiate: {intercollegiate_display}, Scholarship: {scholarship}, Intramural: {intramural}"


def generate_athletics_section(uni_data: dict) -> list[str]:
    """Generate the Athletics section."""
    lines = ["## Athletics", ""]

    athletics = uni_data.get("athletics", {})

    # Men's Sports
    lines.append("### Men's Sports")
    lines.append("")

    mens_sports = athletics.get("Men's Sports", [])
    if mens_sports:
        for sport_obj in mens_sports:
            lines.append(format_sport(sport_obj))
    else:
        lines.append("- No men's sports data reported.")

    lines.append("")

    # Women's Sports
    lines.append("### Women's Sports")
    lines.append("")

    womens_sports = athletics.get("Women's Sports", [])
    if womens_sports:
        for sport_obj in womens_sports:
            lines.append(format_sport(sport_obj))
    else:
        lines.append("- No women's sports data reported.")

    lines.append("")
    return lines
