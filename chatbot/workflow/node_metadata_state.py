from typing import Any

from chatbot.components import retriever as retriever_component
from chatbot.components.college_utils import (
    convert_abbreviations_to_full_names,
    validate_states,
)
from projectutils.logger import setup_logger

from .state import GraphState
from .utils import get_api_key_error_message, is_api_key_error

# Set up logging
logger = setup_logger(__file__)


def ask_states_node(state: GraphState) -> dict[str, Any]:
    """Ask the user for a list of states they are interested in."""
    logger.info("Entering ask_states_node")
    messages = state.get("messages", []).copy()

    messages.append(
        {
            "role": "assistant",
            "content": "Which states are you interested in for colleges? Please provide a comma-separated list (e.g., California, NY, Texas). Maximum 3 states allowed.",
        }
    )

    logger.info("Exiting ask_states_node successfully")
    return {"messages": messages, "expected_input": "states_list"}


def ask_additional_states_node(state: GraphState) -> dict[str, Any]:
    """Ask the user for additional states to expand their search."""
    logger.info("Entering ask_additional_states_node")
    messages = state.get("messages", []).copy()

    selected_states = state.get("selected_states", [])
    if selected_states:
        current_states_text = ", ".join(selected_states)
        remaining_slots = 3 - len(selected_states)
        messages.append(
            {
                "role": "assistant",
                "content": f"You currently selected: {current_states_text}. Please add up to {remaining_slots} more state{'s' if remaining_slots > 1 else ''} to expand your search (e.g., California, NY, Texas):",
            }
        )
    else:
        messages.append(
            {
                "role": "assistant",
                "content": "Please provide additional states to expand your search (e.g., California, NY, Texas). Maximum 3 states total:",
            }
        )

    logger.info("Exiting ask_additional_states_node successfully")
    return {"messages": messages, "expected_input": "additional_states_list"}


def process_states_node(state: GraphState) -> dict[str, Any]:
    """Process the user's state input and retrieve documents using the retriever's fixed_filters."""
    logger.info("Entering process_states_node")
    messages = state.get("messages", []).copy()

    # Extract the state list from the last user message
    last_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break

    logger.info(f"Processing user input: '{last_user_message}'")

    # Check if this is additional states or initial states
    expected_input = state.get("expected_input")
    is_additional_states = expected_input == "additional_states_list"
    existing_states = state.get("selected_states", []) if is_additional_states else []

    # Parse the comma-separated state string
    try:
        parsed_states_list = [
            state.strip() for state in last_user_message.split(",") if state.strip()
        ]

        if not parsed_states_list:
            logger.warning("No states provided by user")
            if is_additional_states:
                messages.append(
                    {
                        "role": "assistant",
                        "content": "Please provide at least one additional state. Try again with a comma-separated list (e.g., California, NY, Texas). Maximum 3 states total.",
                    }
                )
                return {
                    "messages": messages,
                    "expected_input": "additional_states_list",
                }
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": "Please provide at least one state. Try again with a comma-separated list (e.g., California, NY, Texas). Maximum 3 states allowed.",
                    }
                )
                return {"messages": messages, "expected_input": "states_list"}

        # Check if adding these states would exceed the 3-state limit
        current_state_count = len(existing_states) if is_additional_states else 0
        total_states_count = current_state_count + len(parsed_states_list)

        if total_states_count > 3:
            max_additional = 3 - current_state_count
            logger.warning(
                f"Too many states provided. Current: {current_state_count}, trying to add: {len(parsed_states_list)}, max allowed: 3"
            )

            if is_additional_states:
                if max_additional <= 0:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"You already have 3 states selected ({', '.join(existing_states)}). Cannot add more states.",
                        }
                    )
                    return {
                        "messages": messages,
                        "expected_input": None,
                        "selected_states": existing_states,
                    }
                else:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"You can only add {max_additional} more state{'s' if max_additional > 1 else ''} (you currently have {current_state_count}/3). Please provide fewer states:",
                        }
                    )
                    return {
                        "messages": messages,
                        "expected_input": "additional_states_list",
                    }
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Please provide at most 3 states. You provided {len(parsed_states_list)} states. Try again with a comma-separated list (e.g., California, NY, Texas):",
                    }
                )
                return {"messages": messages, "expected_input": "states_list"}

        logger.info(f"Parsed states: {parsed_states_list}")

        # Validate states before processing
        valid_states, invalid_states = validate_states(parsed_states_list)

        # If ALL states are invalid, ask for re-input
        if invalid_states and not valid_states:
            logger.warning(f"All states are invalid: {invalid_states}")
            invalid_states_text = ", ".join(invalid_states)

            if is_additional_states:
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"{invalid_states_text} {'do not exist' if len(invalid_states) > 1 else 'does not exist'}. Please provide valid state names or abbreviations (e.g., California, NY, Texas):",
                    }
                )
                return {
                    "messages": messages,
                    "expected_input": "additional_states_list",
                }
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"{invalid_states_text} {'do not exist' if len(invalid_states) > 1 else 'does not exist'}. Please provide valid state names or abbreviations (e.g., California, NY, Texas):",
                    }
                )
                return {"messages": messages, "expected_input": "states_list"}

        # If some states are invalid but valid ones exist, process valid states first
        # then ask for replacements for the invalid ones
        has_invalid_states_to_replace = bool(invalid_states)
        if invalid_states:
            logger.warning(f"Some invalid states need replacement: {invalid_states}")

        # Convert abbreviations to full state names for consistent display
        full_state_names = convert_abbreviations_to_full_names(valid_states)
        logger.info(f"Converted to full names: {full_state_names}")

        # Combine with existing states if this is additional states
        if is_additional_states:
            all_states = existing_states + full_state_names
            # Remove duplicates while preserving order
            combined_states = []
            for s in all_states:
                if s not in combined_states:
                    combined_states.append(s)
            full_state_names = combined_states
            logger.info(f"Combined with existing states: {full_state_names}")

        # Use the retriever's fixed_filters to get documents for selected states
        db_vectorstore = state.get("db_vectorstore")
        if not db_vectorstore:
            logger.error("db_vectorstore not found in state for state filtering.")
            messages.append(
                {
                    "role": "assistant",
                    "content": "Error: College database not available.",
                }
            )
            return {
                "messages": messages,
                "expected_input": None,
                "search_complete": True,
            }

        # Create fixed filters for the states
        filters_for_states = retriever_component.create_fixed_filters(
            state=full_state_names
        )

        # Create a retriever instance specifically for this state filtering task
        # k should be large enough to get all colleges in those states.
        state_filter_retriever = retriever_component.create_self_query_retriever(
            vectorstore=db_vectorstore,
            k=1600,
            fixed_filters=filters_for_states,
        )

        # A generic query to satisfy the retriever, actual filtering is by fixed_filters
        retrieved_documents_for_states = state_filter_retriever.invoke("universities")

        logger.info(
            f"Retrieved {len(retrieved_documents_for_states)} documents for states: {full_state_names}"
        )

        # Create the main success message
        success_message = (
            f"Okay, I'll focus on colleges in: {', '.join(full_state_names)}."
        )

        messages.append(
            {
                "role": "assistant",
                "content": success_message,
            }
        )

        # If there were invalid states, ask for replacements
        if has_invalid_states_to_replace:
            invalid_states_text = ", ".join(invalid_states)
            messages.append(
                {
                    "role": "assistant",
                    "content": f"{invalid_states_text} {'do not exist' if len(invalid_states) > 1 else 'does not exist'}. Please provide additional valid states to replace {'them' if len(invalid_states) > 1 else 'it'} (e.g., California, NY, Texas):",
                }
            )

            logger.info("Exiting process_states_node - asking for replacement states")
            return {
                "messages": messages,
                "selected_states": full_state_names,  # Store valid states processed so far
                "state_docs": retrieved_documents_for_states,
                "expected_input": "additional_states_list",
            }

        logger.info("Exiting process_states_node successfully")
        return {
            "messages": messages,
            "selected_states": full_state_names,  # Store full names for consistent display
            "state_docs": retrieved_documents_for_states,
            "expected_input": None,
        }

    except Exception as e:
        logger.error(f"Error in process_states_node: {e}")
        error_input_type = (
            "additional_states_list" if is_additional_states else "states_list"
        )

        # Check for API key related errors
        if is_api_key_error(e):
            messages.append(
                {
                    "role": "assistant",
                    "content": get_api_key_error_message(),
                }
            )
        else:
            # Generic parsing error for other issues
            messages.append(
                {
                    "role": "assistant",
                    "content": "I had trouble parsing that. Please provide states as a comma-separated list (e.g., California, NY, Texas).",
                }
            )
        return {"messages": messages, "expected_input": error_input_type}
