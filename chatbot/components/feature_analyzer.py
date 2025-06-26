"""
Utility module for analyzing distinguishing features among college metadata.

This module provides functions to analyze numeric and boolean fields in college metadata
to identify distinguishing characteristics for generating suggestions and questions.
"""

import statistics

from langchain_core.documents import Document

from chatbot.utils.metadata_extractor.utils import get_sentinel_value
from projectutils.logger import setup_logger

# Set up logging
logger = setup_logger(__file__)


def _analyze_numeric_field(
    college_metadata_list: list[dict], field_name: str, num_colleges: int
) -> dict | None:
    """Analyze a numeric field to determine if it has good variance."""
    values = []

    # Get the appropriate sentinel value for this field
    sentinel_value = get_sentinel_value(field_name, int)

    for metadata in college_metadata_list:
        value = metadata.get(field_name)
        if value is not None and value != sentinel_value:
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                # Skip values that can't be converted to float
                continue

    # Need at least 2 values to calculate variance
    if len(values) < 2:
        return None

    # Calculate statistics
    min_val = min(values)
    max_val = max(values)
    mean_val = statistics.mean(values)

    # Calculate standard deviation if there are enough values
    if len(values) >= 2:
        stdev = statistics.stdev(values)
    else:
        stdev = 0

    # Calculate coefficient of variation and cap it for fair comparison
    cv = stdev / mean_val if mean_val > 0 else 0
    capped_variance = min(cv, 2.0)  # Cap at 2.0 to prevent extreme outliers

    return {
        "name": field_name,
        "type": "numeric",
        "min": min_val,
        "max": max_val,
        "avg": mean_val,
        "stdev": stdev,
        "count": len(values),
        "variance_score": capped_variance,
    }


def _analyze_boolean_field(
    college_metadata_list: list[dict], field_name: str, num_colleges: int
) -> dict | None:
    """Analyze a boolean field to determine if it has good distribution."""
    true_count = 0
    false_count = 0

    for metadata in college_metadata_list:
        value = metadata.get(field_name)
        # For boolean fields, only exclude None values (missing data)
        # Both True and False are valid values
        if value is not None:
            if value is True or value == "true" or value == 1:
                true_count += 1
            elif value is False or value == "false" or value == 0:
                false_count += 1

    total_count = true_count + false_count

    # Need at least some data to be meaningful
    if total_count < 2:
        return None

    # Calculate normalized variance score for boolean fields
    # Range: 0.0 (no variance) to 1.0 (perfect 50/50 split)
    balance_ratio = min(true_count, false_count) / total_count
    normalized_variance = balance_ratio * 2  # Scale 0-0.5 range to 0-1.0

    return {
        "name": field_name,
        "type": "boolean",
        "true_count": true_count,
        "false_count": false_count,
        "total_count": total_count,
        "variance_score": normalized_variance,
    }


def _select_top_distinguishing_fields(
    identified_fields: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """Select the top most distinguishing fields based on variance scores."""
    if not identified_fields:
        return []

    # Sort by variance score in descending order
    sorted_fields = sorted(
        identified_fields, key=lambda x: x.get("variance_score", 0), reverse=True
    )

    # Return top N fields
    return sorted_fields[:top_n]


def _create_features_summary(top_fields: list[dict]) -> str:
    """Create a human-readable summary of distinguishing features for the LLM."""
    logger.info(
        f"Creating features summary for {len(top_fields)} distinguishing fields"
    )

    summary_lines = []

    for field in top_fields:
        field_name = field["name"]
        field_type = field["type"]
        variance_score = field.get("variance_score", 0)

        logger.debug(
            f"Processing field '{field_name}' (type: {field_type}, variance_score: {variance_score:.3f})"
        )

        if field_type == "numeric":
            min_val = field["min"]
            max_val = field["max"]
            avg_val = field["avg"]

            # Format numbers appropriately
            if "tuition" in field_name or "aid" in field_name or "room" in field_name:
                # Currency formatting
                summary_line = f"- Field: '{field_name}' (Numeric), Range: ${min_val:,.0f} - ${max_val:,.0f}, Average: ${avg_val:,.0f}"
            elif "percent" in field_name or "rate" in field_name:
                # Percentage formatting
                summary_line = f"- Field: '{field_name}' (Numeric), Range: {min_val:.1%} - {max_val:.1%}, Average: {avg_val:.1%}"
            else:
                # General numeric formatting
                summary_line = f"- Field: '{field_name}' (Numeric), Range: {min_val:.1f} - {max_val:.1f}, Average: {avg_val:.1f}"

            summary_lines.append(summary_line)

        elif field_type == "boolean":
            true_count = field["true_count"]
            false_count = field["false_count"]
            summary_line = f"- Field: '{field_name}' (Boolean), Availability: {true_count} schools offer it, {false_count} schools do not."
            summary_lines.append(summary_line)

    final_summary = "\n".join(summary_lines)
    logger.info(f"Features summary content:\n{final_summary}")

    return final_summary


def analyze_distinguishing_features(
    college_docs: list[Document],
    field_types: dict[str, str],
    num_features_to_select: int = 5,
) -> str:
    """
    Analyze distinguishing features among a list of colleges.

    Args:
        college_docs: List of Document objects containing college metadata
        field_types: Dictionary mapping field names to their types ('number', 'integer', 'boolean')
        num_features_to_select: Number of top distinguishing features to select

    Returns:
        Human-readable summary string of distinguishing features
    """
    logger.info(f"Analyzing distinguishing features for {len(college_docs)} colleges")

    # Extract metadata from each document
    college_metadata_list = []
    for doc in college_docs:
        college_metadata_list.append(doc.metadata)

    num_colleges = len(college_docs)

    # Analyze fields to find distinguishing characteristics
    identified_fields = []

    # Analyze each field based on its type
    for field_name, field_type in field_types.items():
        if field_type in ["number", "integer"]:
            field_analysis = _analyze_numeric_field(
                college_metadata_list, field_name, num_colleges
            )
            if field_analysis:
                identified_fields.append(field_analysis)
        elif field_type == "boolean":
            field_analysis = _analyze_boolean_field(
                college_metadata_list, field_name, num_colleges
            )
            if field_analysis:
                identified_fields.append(field_analysis)

    # Select the top most distinguishing fields
    top_fields = _select_top_distinguishing_fields(
        identified_fields, top_n=num_features_to_select
    )

    # Create summary for LLM
    distinguishing_features_summary = _create_features_summary(top_fields)

    logger.info(f"Successfully analyzed {len(top_fields)} distinguishing features")
    return distinguishing_features_summary
