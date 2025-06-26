import re
from typing import Any

from projectutils.logger import setup_logger

from .state import GraphState
from .utils import get_last_user_message_content

# Set up logging
logger = setup_logger(__file__)


def ask_manual_sat_node(state: GraphState) -> dict[str, Any]:
    """Ask user to manually enter SAT score - the starting point of the workflow."""
    logger.info("Entering ask_manual_sat_node")
    messages = state.get("messages", []).copy()

    # Direct welcome message asking for SAT score
    content = "Hello! To get started with your college recommendations, please enter your SAT score (400-1600)."

    messages.append(
        {
            "role": "assistant",
            "content": content,
        }
    )

    logger.info("Exiting ask_manual_sat_node successfully")
    return {"messages": messages, "expected_input": "sat_score"}


def process_manual_sat_input_node(state: GraphState) -> dict[str, Any]:
    """Process manually entered SAT score with validation."""
    logger.info("Entering process_manual_sat_input_node")
    messages = state.get("messages", []).copy()

    # Extract SAT score from last user message
    last_user_message = get_last_user_message_content(state)
    logger.info(f"Processing manual SAT input: '{last_user_message}'")

    # Validate SAT score (400-1600 range)
    score_match = re.search(
        r"(\b[4-9]\d{2}\b|\b1[0-5]\d{2}\b|\b1600\b)", last_user_message
    )

    if not score_match:
        logger.warning(
            f"Invalid SAT score '{last_user_message}' - must be between 400 and 1600"
        )
        messages.append(
            {
                "role": "assistant",
                "content": f"❌ **Invalid SAT Score**\n\nThe score '{last_user_message}' is not valid. Please provide a valid SAT score between **400 and 1600**.\n\n*Example: 1200*",
            }
        )
        return {"messages": messages, "expected_input": "sat_score"}

    # Valid score found
    sat_score = int(score_match.group())
    sat_upper = min(1600, sat_score + 50)
    sat_lower = max(400, sat_score - 50)

    logger.info(f"Valid manual SAT score: {sat_score} (Range: {sat_lower}-{sat_upper})")

    messages.append(
        {
            "role": "assistant",
            "content": f"Perfect! Using your SAT score: {sat_score} (Estimated Range: {sat_lower}-{sat_upper}).",
        }
    )

    logger.info("Exiting process_manual_sat_input_node successfully")
    return {
        "messages": messages,
        "current_sat_profile": {
            "score": sat_score,
            "upper_bound": sat_upper,
            "lower_bound": sat_lower,
            "source_type": "manual",
        },
        "expected_input": None,
    }
