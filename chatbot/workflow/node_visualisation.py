import re
from typing import Any

import chainlit as cl
import plotly.graph_objects as go

from projectutils.logger import setup_logger

from .state import GraphState

# Set up logging
logger = setup_logger(__file__)


async def generate_visualisations_node(state: GraphState) -> dict[str, Any]:
    """Generate and display college recommendation visualizations using Chainlit."""
    logger.info("Entering generate_visualisations_node")

    final_docs = state.get("final_docs", {})
    num_colleges = len(final_docs)

    logger.info(f"Generating visualizations for {num_colleges} colleges")

    # Check if college data exists - if not, let ask_clarifying_questions_node handle this
    if not final_docs:
        logger.info("No final_docs found, skipping visualisation generation.")
        return {"messages": state.get("messages", []).copy()}

    # Prepare college data for visualization
    colleges_data = []
    for doc_id, doc_object in final_docs.items():
        colleges_data.append(
            {
                "doc_id": doc_id,
                "metadata": doc_object.metadata,
                "page_content": doc_object.page_content,
            }
        )

    # Initialize list to collect messages
    messages_to_add_to_state = []

    # Generate visualizations and collect messages
    comparison_message = await _generate_comparison_table(colleges_data)
    if comparison_message:
        messages_to_add_to_state.append(comparison_message)

    cost_message = await _generate_cost_breakdown_chart(colleges_data)
    if cost_message:
        messages_to_add_to_state.append(cost_message)

    acceptance_message = await _generate_acceptance_rate_chart(colleges_data)
    if acceptance_message:
        messages_to_add_to_state.append(acceptance_message)

    college_card_messages = await _generate_individual_college_cards(colleges_data)
    messages_to_add_to_state.extend(college_card_messages)

    # Get current state messages and extend with new messages
    current_state_messages = state.get("messages", []).copy()
    current_state_messages.extend(messages_to_add_to_state)

    logger.info("Visualizations generated. Proceeding to ask clarifying questions.")
    return {"messages": current_state_messages}


async def _generate_comparison_table(colleges_data: list[dict]) -> dict | None:
    """Generate and return a markdown comparison table as a message dictionary."""
    logger.info("Generating comparison table")

    # Determine which tuition columns are active across all colleges
    has_in_state = False
    has_out_of_state = False
    has_private = False

    for college in colleges_data:
        metadata = college["metadata"]
        tuition_in_state = metadata.get("tuition_in_state", 0)
        tuition_out_of_state = metadata.get("tuition_out_of_state", 0)
        tuition_private = metadata.get("tuition_private", 0)

        if tuition_in_state > 0:
            has_in_state = True
        if tuition_out_of_state > 0:
            has_out_of_state = True
        if tuition_private > 0:
            has_private = True

    # Build dynamic header
    markdown_table = "## 🎓 Your Shortlisted Colleges: At a Glance\n\n"
    markdown_table += "| College | Location |"

    # Add tuition columns based on what's available
    if has_in_state:
        markdown_table += " Tuition (In-State) |"
    if has_out_of_state:
        markdown_table += " Tuition (Out-of-State) |"
    if has_private:
        markdown_table += " Tuition (Private) |"

    markdown_table += (
        " Acceptance Rate | Avg Aid | Student-Faculty Ratio | Admission Category |\n"
    )

    # Build dynamic separator row
    separator = "|---------|----------|"
    if has_in_state:
        separator += "------------------|"
    if has_out_of_state:
        separator += "--------------------|"
    if has_private:
        separator += "------------------|"
    separator += (
        "-----------------|---------|---------------------|------------------|\n"
    )
    markdown_table += separator

    for college in colleges_data:
        metadata = college["metadata"]

        # Extract and format data
        university_name = metadata.get("university_name", "N/A")
        url = metadata.get("url", "")
        city = metadata.get("city", "N/A")
        state = metadata.get("state", "N/A")

        # Format acceptance rate
        accept_rate = metadata.get("accept_rate", -1)
        accept_rate_str = f"{int(accept_rate * 100)}%" if accept_rate > 0 else "N/A"

        # Format financial aid
        avg_financial_aid_package = metadata.get("avg_financial_aid_package", -1)
        aid_str = (
            _format_currency(avg_financial_aid_package)
            if avg_financial_aid_package > 0
            else "N/A"
        )

        # Format student-faculty ratio
        student_faculty_ratio = metadata.get("student_faculty_ratio", -1)
        ratio_str = (
            f"{int(student_faculty_ratio)}:1" if student_faculty_ratio > 0 else "N/A"
        )

        # Get admission category
        admission_category = metadata.get("admission_category", "N/A").title()

        # Format college name with link if URL available, using truncated name
        short_name = _truncate_college_name(university_name, max_length=35)
        college_name_cell = f"[{short_name}]({url})" if url else short_name
        location_cell = f"{city}, {state}"

        # Start building the row
        row = f"| {college_name_cell} | {location_cell} |"

        # Add tuition columns dynamically
        if has_in_state:
            tuition_in_state = metadata.get("tuition_in_state", -1)
            tuition_in_state_str = (
                _format_currency(tuition_in_state) if tuition_in_state > 0 else "N/A"
            )
            row += f" {tuition_in_state_str} |"

        if has_out_of_state:
            tuition_out_of_state = metadata.get("tuition_out_of_state", -1)
            tuition_out_of_state_str = (
                _format_currency(tuition_out_of_state)
                if tuition_out_of_state > 0
                else "N/A"
            )
            row += f" {tuition_out_of_state_str} |"

        if has_private:
            tuition_private = metadata.get("tuition_private", -1)
            tuition_private_str = (
                _format_currency(tuition_private) if tuition_private > 0 else "N/A"
            )
            row += f" {tuition_private_str} |"

        # Add remaining columns
        row += (
            f" {accept_rate_str} | {aid_str} | {ratio_str} | {admission_category} |\n"
        )
        markdown_table += row

    return {"role": "assistant", "content": markdown_table}


async def _generate_cost_breakdown_chart(colleges_data: list[dict]) -> dict | None:
    """Generate and return a Plotly cost breakdown chart as a message dictionary."""
    logger.info("Generating cost breakdown chart")

    # Data preparation for plotting all tuition costs
    college_names_for_plot = []
    full_college_names_for_hover = []
    all_in_state_tuitions = []
    all_out_of_state_tuitions = []
    all_private_tuitions = []
    all_financial_aid = []

    for college in colleges_data:
        metadata = college["metadata"]
        university_name = metadata.get("university_name", "Unknown")

        # Get all tuition types
        tuition_in_state = metadata.get("tuition_in_state", 0)
        tuition_out_of_state = metadata.get("tuition_out_of_state", 0)
        tuition_private = metadata.get("tuition_private", 0)

        # Only include colleges that have at least one valid tuition type
        if tuition_in_state > 0 or tuition_out_of_state > 0 or tuition_private > 0:
            # Truncate long college names for better display
            display_name = _truncate_college_name(university_name, max_length=30)
            college_names_for_plot.append(display_name)
            full_college_names_for_hover.append(university_name)

            # Add tuition values (None if not available for proper alignment)
            all_in_state_tuitions.append(
                tuition_in_state if tuition_in_state > 0 else None
            )
            all_out_of_state_tuitions.append(
                tuition_out_of_state if tuition_out_of_state > 0 else None
            )
            all_private_tuitions.append(
                tuition_private if tuition_private > 0 else None
            )

            # Add financial aid data
            avg_financial_aid_package = metadata.get("avg_financial_aid_package", 0)
            all_financial_aid.append(
                avg_financial_aid_package if avg_financial_aid_package > 0 else 0
            )

    if not college_names_for_plot:
        return {
            "role": "assistant",
            "content": "⚠️ **Cost Breakdown**\n\nNo cost data available for the recommended colleges.",
        }

    # Ensure display names are unique to avoid confusion
    college_names_for_plot = _ensure_unique_display_names(
        college_names_for_plot, full_college_names_for_hover
    )

    # Sort by average financial aid (descending), then by college name (ascending) for stable sorting
    data_to_sort = list(
        zip(
            college_names_for_plot,
            full_college_names_for_hover,
            all_in_state_tuitions,
            all_out_of_state_tuitions,
            all_private_tuitions,
            all_financial_aid,
            strict=False,
        )
    )

    sorted_combined_data = sorted(
        data_to_sort,
        key=lambda x: (-x[5], x[0]),  # Sort by aid descending, then name ascending
    )

    # Unzip data back into their respective lists
    (
        college_names_for_plot,
        full_college_names_for_hover,
        all_in_state_tuitions,
        all_out_of_state_tuitions,
        all_private_tuitions,
        all_financial_aid,
    ) = zip(*sorted_combined_data, strict=False)

    # Convert back to lists
    college_names_for_plot = list(college_names_for_plot)
    full_college_names_for_hover = list(full_college_names_for_hover)
    all_in_state_tuitions = list(all_in_state_tuitions)
    all_out_of_state_tuitions = list(all_out_of_state_tuitions)
    all_private_tuitions = list(all_private_tuitions)
    all_financial_aid = list(all_financial_aid)

    # Create Plotly figure
    fig = go.Figure()

    # Add tuition traces for each type if data exists
    if any(t is not None for t in all_in_state_tuitions):
        fig.add_trace(
            go.Bar(
                name="In-State Tuition",
                x=college_names_for_plot,
                y=all_in_state_tuitions,
                marker_color="lightgreen",
                hovertemplate="<b>%{text}</b><br>In-State Tuition: $%{y:,.0f}<extra></extra>",
                text=full_college_names_for_hover,
            )
        )

    if any(t is not None for t in all_out_of_state_tuitions):
        fig.add_trace(
            go.Bar(
                name="Out-of-State Tuition",
                x=college_names_for_plot,
                y=all_out_of_state_tuitions,
                marker_color="lightsalmon",
                hovertemplate="<b>%{text}</b><br>Out-of-State Tuition: $%{y:,.0f}<extra></extra>",
                text=full_college_names_for_hover,
            )
        )

    if any(t is not None for t in all_private_tuitions):
        fig.add_trace(
            go.Bar(
                name="Private Tuition",
                x=college_names_for_plot,
                y=all_private_tuitions,
                marker_color="lightcoral",
                hovertemplate="<b>%{text}</b><br>Private Tuition: $%{y:,.0f}<extra></extra>",
                text=full_college_names_for_hover,
            )
        )

    # Add financial aid bars
    fig.add_trace(
        go.Bar(
            name="Avg. Financial Aid",
            x=college_names_for_plot,
            y=all_financial_aid,
            marker_color="lightblue",
            hovertemplate="<b>%{text}</b><br>Avg. Aid: $%{y:,.0f}<extra></extra>",
            text=full_college_names_for_hover,
        )
    )

    # Calculate dynamic width based on number of colleges
    # Base width + additional width per college
    base_width = 600
    width_per_college = 120
    dynamic_width = max(
        base_width, base_width + (len(college_names_for_plot) - 3) * width_per_college
    )

    # Update layout with grouped bars and higher legend position
    fig.update_layout(
        xaxis_title="College",
        yaxis_title="Amount ($)",
        barmode="group",
        hovermode="x unified",
        template="plotly_white",
        height=1500,
        width=dynamic_width,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.2,  # Move legend closer to top edge
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(255,255,255,0.8)",
            "bordercolor": "rgba(0,0,0,0.1)",
            "borderwidth": 1,
        },
        xaxis={
            "tickangle": 45,  # Rotate x-axis labels
            "tickmode": "linear",
        },
        margin={
            "b": 50,  # Increase bottom margin for rotated labels
            "l": 80,
            "r": 80,
            "t": 50,  # Increase top margin to accommodate higher legend
        },
    )

    elements = [cl.Plotly(figure=fig, display="inline")]
    return {
        "role": "assistant",
        "content": "## 💰 Show Me the Money!\n\nHere's a comparison of college costs and potential financial aid. The chart shows sticker prices by tuition type and average financial aid available:",
        "elements": elements,
    }


async def _generate_acceptance_rate_chart(colleges_data: list[dict]) -> dict | None:
    """Generate and return a Plotly acceptance rate chart as a message dictionary."""
    logger.info("Generating acceptance rate chart")

    college_names = []
    full_college_names = []  # Store original names for hover
    acceptance_rates = []

    for college in colleges_data:
        metadata = college["metadata"]

        university_name = metadata.get("university_name", "Unknown")
        accept_rate = metadata.get("accept_rate", -1)

        # Skip colleges with no acceptance rate data
        if accept_rate <= 0:
            continue

        # Truncate long college names for better display
        display_name = _truncate_college_name(university_name, max_length=30)

        college_names.append(display_name)
        full_college_names.append(university_name)  # Store original for hover
        acceptance_rates.append(accept_rate * 100)  # Convert to percentage

    if not college_names:
        return {
            "role": "assistant",
            "content": "⚠️ **Acceptance Rates**\n\nNo acceptance rate data available for the recommended colleges.",
        }

    # Ensure display names are unique to avoid confusion
    college_names = _ensure_unique_display_names(college_names, full_college_names)

    # Sort by acceptance rate (descending - highest chance first)
    sorted_data = sorted(
        zip(college_names, full_college_names, acceptance_rates, strict=False),
        key=lambda x: x[2],
        reverse=True,
    )
    college_names, full_college_names, acceptance_rates = zip(
        *sorted_data, strict=False
    )

    # Color-code bars
    colors = []
    for rate in acceptance_rates:
        if rate > 75:
            colors.append("green")
        elif rate >= 50:
            colors.append("orange")
        else:
            colors.append("red")

    # Create Plotly figure
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(college_names),
                y=list(acceptance_rates),
                marker_color=colors,
                hovertemplate="<b>%{text}</b><br>Acceptance Rate: %{y:.1f}%<extra></extra>",
                text=list(full_college_names),  # Store full names for hover
            )
        ]
    )

    # Calculate dynamic width based on number of colleges
    base_width = 600
    width_per_college = 120
    dynamic_width = max(
        base_width, base_width + (len(college_names) - 3) * width_per_college
    )

    fig.update_layout(
        xaxis_title="College",
        yaxis_title="Acceptance Rate (%)",
        template="plotly_white",
        height=700,
        width=dynamic_width,
        showlegend=False,
        xaxis={
            "tickangle": 45,  # Rotate x-axis labels
            "tickmode": "linear",
        },
        margin={
            "b": 50,  # Increase bottom margin for rotated labels
            "l": 80,
            "r": 80,
            "t": 50,
        },
    )

    elements = [cl.Plotly(figure=fig, display="inline")]
    return {
        "role": "assistant",
        "content": "## 🎯 What Are My Odds?\n\nHere's how selective your shortlisted colleges are:",
        "elements": elements,
    }


async def _generate_individual_college_cards(colleges_data: list[dict]) -> list[dict]:
    """Generate and return individual college markdown cards as message dictionaries."""
    logger.info("Generating individual college cards")

    new_messages = []
    for college in colleges_data:
        metadata = college["metadata"]
        page_content = college["page_content"]

        university_name = metadata.get("university_name", "Unknown College")

        # Generate markdown card for this college
        card_md = _generate_college_card_markdown(metadata, page_content)

        # Add title to the card content
        titled_card_md = f"## {university_name}\n\n{card_md}"

        new_messages.append({"role": "assistant", "content": titled_card_md})

    return new_messages


def _format_currency(amount: float) -> str:
    """Format a number as currency."""
    if amount <= 0:
        return "N/A"
    return f"${amount:,.0f}"


def _truncate_college_name(name: str, max_length: int = 25) -> str:
    """Truncate college name if too long, preserving readability."""
    if len(name) <= max_length:
        return name

    # Try to truncate at word boundary
    words = name.split()
    truncated = ""
    for word in words:
        if len(truncated + " " + word) <= max_length - 3:  # Leave space for "..."
            truncated += (" " if truncated else "") + word
        else:
            break

    return truncated + "..." if truncated else name[: max_length - 3] + "..."


def _ensure_unique_display_names(
    college_names: list[str], full_names: list[str]
) -> list[str]:
    """Ensure truncated display names are unique by adding distinguishing suffixes."""
    display_names = []
    name_counts = {}

    # First pass: count occurrences and create basic display names
    for display_name in college_names:
        name_counts[display_name] = name_counts.get(display_name, 0) + 1

    # Second pass: make duplicates unique
    name_counters = {}
    for _i, (display_name, full_name) in enumerate(
        zip(college_names, full_names, strict=False)
    ):
        if name_counts[display_name] == 1:
            # Unique name, use as is
            display_names.append(display_name)
        else:
            # Duplicate name, need to make unique
            name_counters[display_name] = name_counters.get(display_name, 0) + 1

            # Try to find a distinguishing part
            if " at " in full_name:
                location_part = full_name.split(" at ")[1].split(",")[0].strip()
                unique_name = f"{display_name.replace('...', '')} at {location_part}"
            elif "," in full_name and len(full_name.split(",")) > 1:
                # Use state or city after comma
                location_part = full_name.split(",")[1].strip()
                unique_name = f"{display_name.replace('...', '')} ({location_part})"
            else:
                # Fall back to numbering
                unique_name = (
                    f"{display_name.replace('...', '')} ({name_counters[display_name]})"
                )

            # Ensure it fits within reasonable length
            if len(unique_name) > 35:
                unique_name = unique_name[:32] + "..."

            display_names.append(unique_name)

    return display_names


def _extract_size_setting(page_content: str) -> str:
    """Extract size and setting information from Fast Facts."""
    # Look for "Setting & Size:" followed by content until the next field name
    # Since markdown loader strips **, the code looks for the next field by name
    fast_facts_match = re.search(
        r"Setting & Size[:\s]*([^:\n]+?)(?=\s*(?:Acceptance Rate|Price Tag|Aid Generosity|Stand-out Strength|Founded)|\n|$)",
        page_content,
        re.IGNORECASE,
    )
    if fast_facts_match:
        raw_text = fast_facts_match.group(1).strip()
        # Parse "Suburban • 1,900 undergrads" to "Suburban - 1,900 undergrads"
        parsed_text = raw_text.replace("•", "-").strip()
        return parsed_text

    # Alternative pattern - look for size info without the formal structure
    setting_match = re.search(r"Setting[:\s]*([^•\n]+)", page_content, re.IGNORECASE)
    if setting_match:
        return setting_match.group(1).strip()

    return ""


def _extract_standout_strength(page_content: str) -> str:
    """Extract standout strength or similar information."""
    # Look for "Stand-out Strength" specifically
    standout_match = re.search(
        r"Stand-out Strength[:\s]*([^\n]+)", page_content, re.IGNORECASE
    )
    if standout_match:
        return standout_match.group(1).strip()

    # Look for other strength indicators
    strength_patterns = [
        r"known for[:\s]*([^\.]+)",
        r"renowned for[:\s]*([^\.]+)",
        r"specialized in[:\s]*([^\.]+)",
        r"focus on[:\s]*([^\.]+)",
    ]

    for pattern in strength_patterns:
        match = re.search(pattern, page_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return "Strong academic programs and student support"


def _extract_descriptive_paragraph(page_content: str) -> str:
    """Extract the descriptive paragraph that comes after the Fast Facts section."""

    # Pattern: Fast Facts line, then descriptive paragraph, then General Information
    # Structure: Fast Facts\n\n[facts line]\n\n[descriptive paragraph]\n\nGeneral Information
    pattern = r"Fast Facts\s*\n\n[^\n]+\n\n(.+?)\n\nGeneral Information"
    match = re.search(pattern, page_content, re.DOTALL | re.IGNORECASE)

    if match:
        descriptive_paragraph = match.group(1).strip()
        return descriptive_paragraph

    return ""


def _generate_college_card_markdown(metadata: dict, page_content: str) -> str:
    """Generate a detailed markdown card for a single college."""
    city = metadata.get("city", "N/A")
    state = metadata.get("state", "N/A")

    # Start without header since it's already in the title
    card_md = ""

    # Location & basic info
    card_md += f"📍 **Location:** {city}, {state}\n\n"

    # Extract size and setting from Fast Facts
    size_setting = _extract_size_setting(page_content)
    if size_setting:
        card_md += f"🏫 **Setting & Size:** {size_setting}\n\n"

    # Financial info
    tuition_private = metadata.get("tuition_private", -1)
    avg_financial_aid_package = metadata.get("avg_financial_aid_package", -1)
    accept_rate = metadata.get("accept_rate", -1)

    card_md += "💰 **Financials:**\n"
    if tuition_private > 0:
        card_md += f"- Tuition: {_format_currency(tuition_private)}\n"
    if avg_financial_aid_package > 0:
        card_md += (
            f"- Avg. Financial Aid: {_format_currency(avg_financial_aid_package)}\n"
        )
    if accept_rate > 0:
        card_md += f"- Acceptance Rate: {int(accept_rate * 100)}%\n"
    card_md += "\n"

    # What makes it stand out
    standout_strength = _extract_standout_strength(page_content)
    if standout_strength:
        card_md += f"✨ **What makes it stand out?**\n{standout_strength}\n\n"

    # Good to know section
    card_md += "📝 **Good to Know:**\n"

    student_faculty_ratio = metadata.get("student_faculty_ratio", -1)
    if student_faculty_ratio > 0:
        card_md += f"- Student-Faculty Ratio: {int(student_faculty_ratio)}:1\n"

    housing_required_first_year = metadata.get("housing_required_first_year", None)
    if housing_required_first_year is not None:
        housing_text = "Required" if housing_required_first_year else "Not required"
        card_md += f"- First-year housing: {housing_text}\n"

    percent_students_on_campus = metadata.get("percent_students_on_campus", -1)
    if percent_students_on_campus > 0:
        card_md += (
            f"- Students living on campus: {int(percent_students_on_campus * 100)}%\n"
        )

    scholarship_sports_available = metadata.get("scholarship_sports_available", None)
    if scholarship_sports_available is not None:
        sports_text = "Available" if scholarship_sports_available else "Not available"
        card_md += f"- Sports scholarships: {sports_text}\n"

    # Add descriptive paragraph from Fast Facts section
    descriptive_paragraph = _extract_descriptive_paragraph(page_content)
    if descriptive_paragraph:
        card_md += f"\n🎯 **Why This Might Be Right for You**\n{descriptive_paragraph}"

    return card_md
