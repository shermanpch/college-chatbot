"""
Terminal workflow node for displaying completion message and ending the workflow.
"""

from typing import Any

from projectutils.logger import setup_logger

from .state import GraphState

# Set up logging
logger = setup_logger(__file__)


async def workflow_completion_node(state: GraphState) -> dict[str, Any]:
    """
    Terminal node that displays the final completion message and ends the workflow.
    This should always be the last node in any workflow chain.
    """
    logger.info("Entering workflow_completion_node - ending workflow")

    messages = state.get("messages", []).copy()

    # Check if user declined clarification questions for a more personalized message
    wants_clarification = state.get("wants_clarification")
    if wants_clarification is False:
        # User declined clarification questions
        completion_content = "👍 **Perfect!** You're all set with your college analysis above.\n\n📄 Your personalized college report is being generated and will be available for download shortly. Feel free to review the information and reach out if you have any questions about specific schools or want to explore different options. Good luck with your college journey! 🎓\n\nType 'restart' to begin a new analysis or 'exit' to end."
    else:
        # Default completion message (for reranked results or other completion paths)
        completion_content = "✅ Analysis complete! Your personalized college report is being generated and will be available for download shortly. You can review your recommendations above. Type 'restart' to begin a new analysis or 'exit' to end."

    messages.append(
        {
            "role": "assistant",
            "content": completion_content,
        }
    )

    return {
        "messages": messages,
        "search_complete": True,  # This terminates the workflow
        "generate_pdf": True,  # Flag to generate PDF after messages are sent
    }
