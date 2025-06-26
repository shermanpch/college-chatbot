"""College and university data processing utilities."""

from typing import Any

from langchain_core.documents import Document

# State abbreviation mapping - maps lowercase abbreviations to lowercase full state names
STATE_ABBREVIATIONS = {
    "al": "alabama",
    "ak": "alaska",
    "az": "arizona",
    "ar": "arkansas",
    "ca": "california",
    "co": "colorado",
    "ct": "connecticut",
    "de": "delaware",
    "fl": "florida",
    "ga": "georgia",
    "hi": "hawaii",
    "id": "idaho",
    "il": "illinois",
    "in": "indiana",
    "ia": "iowa",
    "ks": "kansas",
    "ky": "kentucky",
    "la": "louisiana",
    "me": "maine",
    "md": "maryland",
    "ma": "massachusetts",
    "mi": "michigan",
    "mn": "minnesota",
    "ms": "mississippi",
    "mo": "missouri",
    "mt": "montana",
    "ne": "nebraska",
    "nv": "nevada",
    "nh": "new hampshire",
    "nj": "new jersey",
    "nm": "new mexico",
    "ny": "new york",
    "nc": "north carolina",
    "nd": "north dakota",
    "oh": "ohio",
    "ok": "oklahoma",
    "or": "oregon",
    "pa": "pennsylvania",
    "ri": "rhode island",
    "sc": "south carolina",
    "sd": "south dakota",
    "tn": "tennessee",
    "tx": "texas",
    "ut": "utah",
    "vt": "vermont",
    "va": "virginia",
    "wa": "washington",
    "wv": "west virginia",
    "wi": "wisconsin",
    "wy": "wyoming",
    "dc": "district of columbia",
}


def validate_states(states: list[str]) -> tuple[list[str], list[str]]:
    """
    Validate a list of state names/abbreviations and separate valid from invalid ones.

    Args:
        states (List[str]): List of state names or abbreviations to validate

    Returns:
        Tuple[List[str], List[str]]: A tuple containing (valid_states, invalid_states)

    Examples:
        >>> validate_states(["CA", "Texas", "InvalidState", "NY"])
        (["CA", "Texas", "NY"], ["InvalidState"])
    """
    valid_states = []
    invalid_states = []

    # Get all valid state names (both full names and abbreviations)
    valid_abbreviations = set(STATE_ABBREVIATIONS.keys())
    valid_full_names = set(STATE_ABBREVIATIONS.values())

    for state in states:
        state_normalized = state.lower().strip()

        # Check if it's a valid abbreviation or full name
        if (
            state_normalized in valid_abbreviations
            or state_normalized in valid_full_names
        ):
            valid_states.append(state.strip())
        else:
            invalid_states.append(state.strip())

    return valid_states, invalid_states


def normalize_and_match_states(state1: str, state2: str) -> bool:
    """
    Check if two state names/abbreviations refer to the same state.

    Args:
        state1 (str): First state name or abbreviation
        state2 (str): Second state name or abbreviation

    Returns:
        bool: True if they refer to the same state, False otherwise

    Examples:
        >>> normalize_and_match_states("CA", "California")
        True
        >>> normalize_and_match_states("New York", "ny")
        True
        >>> normalize_and_match_states("California", "Texas")
        False
    """
    # Normalize both states
    state1_norm = state1.lower().strip()
    state2_norm = state2.lower().strip()

    # Direct match
    if state1_norm == state2_norm:
        return True

    # Check if one is an abbreviation of the other
    if (
        state1_norm in STATE_ABBREVIATIONS
        and STATE_ABBREVIATIONS[state1_norm] == state2_norm
    ):
        return True
    if (
        state2_norm in STATE_ABBREVIATIONS
        and STATE_ABBREVIATIONS[state2_norm] == state1_norm
    ):
        return True

    return False


def convert_abbreviations_to_full_names(states: list[str]) -> list[str]:
    """
    Convert state abbreviations to full state names for display purposes.

    Args:
        states (List[str]): List of state names or abbreviations

    Returns:
        List[str]: List with abbreviations converted to full names
    """
    converted_states = []
    for state in states:
        state_normalized = state.lower().strip()

        # If it's an abbreviation, convert to full name (title case)
        if state_normalized in STATE_ABBREVIATIONS:
            full_name = STATE_ABBREVIATIONS[state_normalized]
            # Convert to title case for display
            converted_states.append(full_name.title())
        else:
            # Keep original (might already be full name)
            # Ensure consistent title case
            converted_states.append(state.strip().title())

    return converted_states


def filter_documents_by_states(
    metadata_mapping: dict[str, Any], states: list[str] = None
) -> dict[str, Any]:
    """
    Filter document metadata mapping for documents in specified states.

    Args:
        metadata_mapping (Dict[str, Any]): Document metadata mapping.

        states (List[str], optional): List of state names to filter by.
                                    Can be full state names (e.g., "California") or abbreviations (e.g., "CA").
                                    If None or empty, returns all documents.

    Returns:
        Dict[str, Any]: Filtered metadata mapping containing only documents from specified states.

    Examples:
        # Filter for documents from California and Texas
        mapping = await create_document_metadata_mapping()
        filtered = filter_documents_by_states(mapping, states=["California", "Texas"])

        # Filter using state abbreviations
        mapping = await create_document_metadata_mapping()
        filtered = filter_documents_by_states(mapping, states=["CA", "TX", "NY"])

        # Use custom metadata mapping
        custom_mapping = await create_document_metadata_mapping()
        filtered = filter_documents_by_states(custom_mapping, states=["Florida"])
    """

    # If no states specified, return all documents
    if not states:
        return metadata_mapping.copy()

    # Filter documents using the normalize_and_match_states function
    filtered_mapping = {}

    for doc_id, metadata in metadata_mapping.items():
        doc_state = metadata.get("state", "").strip()

        # Check if document state matches any of the requested states
        for requested_state in states:
            if normalize_and_match_states(doc_state, requested_state):
                filtered_mapping[doc_id] = metadata
                break  # Found a match, no need to check other states

    return filtered_mapping


def add_admission_categories_to_documents(
    documents: list[Document], upper_sat: int, lower_sat: int
) -> list[Document]:
    """
    Add admission category metadata to each document based on SAT score ranges.

    Args:
        documents (list[Document]): List of Document objects to process
        upper_sat (int): Upper bound SAT score for the student
        lower_sat (int): Lower bound SAT score for the student

    Returns:
        list[Document]: New list of Document objects with admission_category added to their metadata

    Admission Category Logic:
        - Reach: upper_sat <= sat_total_25 (student's best score is at/below 25th percentile)
        - Target: lower_sat < sat_total_75 AND upper_sat > sat_total_25 (student overlaps with middle range)
        - Safety: lower_sat >= sat_total_75 (student's worst score is at/above 75th percentile)
        - Unknown: Missing SAT data for the university

    Examples:
        # Student with SAT range 1100-1200
        docs_with_categories = add_admission_categories_to_documents(documents, upper_sat=1200, lower_sat=1100)
    """
    updated_documents = []
    for doc in documents:
        # Copy metadata to avoid modifying the original document's metadata directly if it's referenced elsewhere
        updated_metadata = doc.metadata.copy()

        sat_total_25 = updated_metadata.get("sat_total_25")
        sat_total_75 = updated_metadata.get("sat_total_75")

        admission_category = "unknown"
        if sat_total_25 is not None and sat_total_75 is not None:
            if upper_sat <= sat_total_25:
                admission_category = "reach"
            elif lower_sat >= sat_total_75:
                admission_category = "safety"
            elif lower_sat < sat_total_75 and upper_sat > sat_total_25:
                admission_category = "target"
            else:
                admission_category = "unknown"

        updated_metadata["admission_category"] = admission_category
        new_doc = Document(page_content=doc.page_content, metadata=updated_metadata)
        updated_documents.append(new_doc)
    return updated_documents
