"""
Workflow node for analyzing shortlisted colleges and generating clarifying questions.
"""

from typing import Any

from chatbot.components.attributes import PETERSON_METADATA_FIELDS
from chatbot.components.clarification_generator import generate_clarification_questions
from chatbot.components.feature_analyzer import analyze_distinguishing_features
from projectutils.logger import setup_logger

from .state import GraphState
from .utils import is_api_key_error

# Set up logging
logger = setup_logger(__file__)


async def ask_clarifying_questions_node(state: GraphState) -> dict[str, Any]:
    """
    Analyze shortlisted colleges to identify distinguishing features and generate
    clarifying questions to help users refine their choices.
    Implements multi-phase logic for asking user preference first, then generating questions.
    """
    logger.info("Entering ask_clarifying_questions_node")

    user_wants_clarification = state.get("wants_clarification")
    expected_input = state.get("expected_input")

    # Check if the system is processing a yes/no response
    if expected_input == "yes_no" and user_wants_clarification is None:
        # This means the system is coming back from the router with a user response
        # We need to process the user's yes/no answer
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            user_response = last_message.get("content", "").lower().strip()

            if "yes" in user_response:
                # User wants clarification - set the flag and continue to generate questions
                user_wants_clarification = True
                logger.info("User confirmed they want clarification questions")
            elif "no" in user_response:
                # User declined clarification - set the flag and end workflow
                user_wants_clarification = False
                logger.info("User declined clarification questions")
            else:
                # Invalid response - retry with clearer instructions
                logger.info(
                    "Invalid response for clarifying choice - providing retry with enhanced guidance"
                )
                messages_copy = messages.copy()
                messages_copy.append(
                    {
                        "role": "assistant",
                        "content": "🤔 **I didn't quite catch that!**\n\nPlease respond with:\n- **'Yes'** if you'd like me to ask some questions to help refine your college list\n- **'No'** if you're all set with the current analysis\n\n💡 *You can also use the buttons above for easier selection!*",
                    }
                )
                return {
                    "messages": messages_copy,
                    "expected_input": "yes_no",
                    "show_clarification_buttons": True,  # Re-show buttons for clarity
                    "retry_clarification_prompt": True,  # Flag for better tracking
                }

    # Initial entry - ask user for preference
    if user_wants_clarification is None:
        logger.info("Asking user for clarification preference")

        content = "🎯 **Great! I've analyzed your college options above.**\n\nWould you like me to ask you a few quick questions to help you narrow down and prioritize these colleges based on what matters most to you?\n\n💡 *These questions will help identify your preferences around things like campus culture, academics, costs, and location to give you more personalized guidance.*"

        messages = state.get("messages", []).copy()
        messages.append(
            {
                "role": "assistant",
                "content": content,
            }
        )

        return {
            "messages": messages,
            "expected_input": "yes_no",
            "show_clarification_buttons": True,  # Flag for app.py to show custom buttons
        }

    # User chose "no" - route to completion node
    elif user_wants_clarification is False:
        logger.info("User declined clarification questions - routing to completion")

        return {
            "messages": state.get("messages", []).copy(),
            "wants_clarification": False,
            "search_complete": True,  # This will trigger routing to completion
            "expected_input": None,  # Clear expected input flag
            "show_clarification_buttons": False,  # Clear button flag
        }

    # User chose "yes" - generate clarifying questions
    elif user_wants_clarification is True:
        logger.info("User wants clarification questions - generating them")

        final_docs = state.get("final_docs", {})

        # Check if there are colleges to analyze
        if not final_docs:
            logger.warning("No colleges found in final_docs - routing to completion")
            messages = state.get("messages", []).copy()
            content = "🤷‍♂️ **Oops!** I don't see any colleges to analyze right now.\n\nPlease try searching for colleges again, and I'll be happy to help you narrow down your choices! 🔍"

            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )
            return {
                "messages": messages,
                "search_complete": True,  # This will trigger routing to completion
                "expected_input": None,  # Clear expected input flag
                "show_clarification_buttons": False,  # Clear button flag
            }

        num_colleges = len(final_docs)
        logger.info(f"Analyzing {num_colleges} colleges for distinguishing features")

        # Convert final_docs dict to list of Documents for analysis
        college_docs = list(final_docs.values())

        # Create field type mappings from PETERSON_METADATA_FIELDS
        field_types = {}
        for attr_info in PETERSON_METADATA_FIELDS:
            field_types[attr_info.name] = attr_info.type

        # Analyze distinguishing features using the new utility
        distinguishing_features_summary = analyze_distinguishing_features(
            college_docs,
            field_types,
            num_features_to_select=10,
        )

        # Generate questions using LLM
        try:
            questions_list = await generate_clarification_questions(
                num_colleges,
                distinguishing_features_summary,
                num_questions=5,
            )

            # Create enhanced headers and format questions
            header = "🎯 **Clarifying Questions to Rank Your College List**\n\n"
            sub_header = f"Based on my analysis of your **{num_colleges} colleges**, I've identified some key differences that could help you prioritize your choices. Here are some personalized questions:\n\n"

            divider = "---\n\n"

            # Convert list to formatted string with enhanced styling
            questions_formatted = ""
            for i, question in enumerate(questions_list, 1):
                questions_formatted += f"**{i}.** {question}\n\n"

            # Add enhanced format instructions
            format_instructions = "📝 **How to Answer:**\n\n"
            format_instructions += (
                "Please respond with your answers numbered like this:\n\n"
            )
            format_instructions += "```\n"
            format_instructions += "1. Your answer to question 1\n"
            format_instructions += "2. Your answer to question 2\n"
            format_instructions += "3. Your answer to question 3\n"
            format_instructions += "4. Your answer to question 4\n"
            format_instructions += "5. Your answer to question 5\n"
            format_instructions += "```\n\n"
            format_instructions += "💡 *Feel free to be as detailed or brief as you'd like - every bit helps me understand your preferences better!*"

            questions_text = (
                header
                + sub_header
                + divider
                + questions_formatted
                + divider
                + format_instructions
            )

        except Exception as e:
            logger.error(f"Error generating questions via LLM: {e}")

            # Check for API key related errors
            if is_api_key_error(e):
                fallback_header = "❌ **API Configuration Error**\n\n"
                fallback_content = "The OpenRouter API key is missing or invalid. Please check your API key configuration and try again.\n\n"
                fallback_content += (
                    "In the meantime, here are some general questions to consider:\n\n"
                )
            else:
                fallback_header = "🎯 **Help Me Understand Your Preferences**\n\n"
                fallback_content = f"I've found **{num_colleges} colleges** that match your criteria! To help you prioritize them, could you share:\n\n"

            fallback_content += "**1.** What's most important to you: cost, location, academic programs, or campus culture?\n\n"
            fallback_content += "**2.** Any specific preferences about campus size, setting (urban/rural), or special programs?\n\n"
            fallback_content += "**3.** What's your ideal balance between academic rigor and social life?\n\n"
            fallback_content += "📝 *Just share whatever comes to mind - this will help me give you more targeted advice!*"
            questions_text = fallback_header + fallback_content

        # Update state with questions
        messages = state.get("messages", []).copy()
        messages.append({"role": "assistant", "content": questions_text})

        result = {
            "messages": messages,
            "clarifying_questions": questions_text,
            "wants_clarification": True,
            "expected_input": "clarifying_answers",
        }

        logger.info("Clarifying questions generated and sent to user")
        return result
