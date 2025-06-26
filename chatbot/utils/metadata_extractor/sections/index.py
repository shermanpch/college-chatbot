"""
Index metadata extraction for Peterson university data.
"""

from typing import Any

from ...markdown_generator.utils import generate_unique_id


def extract_index_metadata(
    json_record: dict[str, Any], index: int = 0
) -> dict[str, Any]:
    """
    Extract index-related metadata fields.

    Fields extracted:
    - document_id: A unique identifier generated using university data and index
    - record_index: The index position of this record in the dataset

    Args:
        json_record: A dictionary containing university data
        index: The index position in the original JSON array

    Returns:
        A dictionary with index metadata
    """
    metadata = {}

    # Generate unique document ID using the utility function
    metadata["document_id"] = generate_unique_id(json_record, index)

    # Store the record index
    metadata["record_index"] = index

    return metadata
