from langgraph.graph import END

from projectutils.logger import setup_logger

from .state import GraphState
from .utils import get_last_user_message_content

# Set up logging
logger = setup_logger(__file__)


def route_after_manual_sat_processing(state: GraphState) -> str:
    """Route after manual SAT processing - check if SAT was successfully set or needs retry."""
    logger.info("Entering route_after_manual_sat_processing")

    # Check if a valid SAT profile was created
    current_sat_profile = state.get("current_sat_profile")
    expected_input = state.get("expected_input")

    if current_sat_profile is not None and expected_input is None:
        # SAT was successfully processed, continue to next step
        logger.info("Valid SAT score processed, routing to ask_states_node")
        return "ask_states_node"
    elif expected_input == "sat_score":
        # SAT input failed validation, ask for SAT again
        logger.info("Invalid SAT score, routing back to ask_manual_sat")
        return "ask_manual_sat"
    else:
        # Unexpected state
        logger.error(
            f"Unexpected state in SAT processing - current_sat_profile: {current_sat_profile}, expected_input: {expected_input}"
        )
        return "ask_manual_sat"


def route_after_state_processing(state: GraphState) -> str:
    """Route after state processing based on whether colleges were found."""
    logger.info("Entering route_after_state_processing")

    # Check if expecting user input (e.g., for replacement states)
    expected_input = state.get("expected_input")
    if expected_input:
        logger.info(
            f"Expecting user input ({expected_input}). Routing to END to wait for user response."
        )
        return END

    state_docs = state.get("state_docs", [])
    messages = state.get("messages", []).copy()

    if not state_docs:
        logger.info(
            "No colleges found after state filtering. Routing to ask_additional_states_node."
        )
        messages.append(
            {
                "role": "assistant",
                "content": "No colleges found for the states you selected. Let's try adding some more states to your search.",
            }
        )
        state["messages"] = messages
        state["expected_input"] = (
            "additional_states_list"  # To guide ask_additional_states_node
        )
        return "ask_additional_states_node"
    else:
        logger.info(
            f"Found {len(state_docs)} colleges. Routing to categorize_colleges_node."
        )
        return "categorize_colleges_node"


def main_dispatcher_node(state: GraphState) -> str:
    """
    Main dispatcher to route based on expected input state and workflow conditions.

    This is the central routing hub that handles:
    1. User input routing based on expected_input field
    2. Workflow state progression logic
    3. Special cases like search completion and clarification workflows
    4. Error recovery and fallback scenarios

    Key routing decisions:
    - student_id: Route to profile fetch
    - sat_score: Route to SAT processing
    - yes_no: Route to clarification or SAT choice handlers
    - hybrid_query/additional_criteria: Route to search operations
    - State-based routing for workflow progression
    """
    logger.info("Entering main_dispatcher_node")

    # Check if hybrid search workflow is complete
    if state.get("search_complete") is True:
        logger.info("Workflow complete - routing to END")
        return END

    # Route based on what type of input is expected
    expected_input = state.get("expected_input")
    logger.info(f"Expected input: {expected_input}")

    if expected_input == "sat_score":
        logger.info("Routing to process_manual_sat")
        return "process_manual_sat"
    elif expected_input == "yes_no":
        # Check if this is for clarifying recommendation choice
        if (
            state.get("wants_clarification") is None
            and state.get("final_docs") is not None
        ):
            # This is for clarifying recommendation choice - let the node handle the logic
            logger.info(
                "Routing to ask_clarifying_questions to process yes/no response"
            )
            return "ask_clarifying_questions"
    elif expected_input == "clarifying_answers":
        # Extract user's answers and route to re-ranking
        logger.info("User provided clarifying answers - routing to node_reranking")
        user_answers = get_last_user_message_content(state)
        state["clarifying_responses"] = user_answers
        state["expected_input"] = None
        return "node_reranking"
    elif expected_input == "states_list":
        logger.info("Routing to process_states_node")
        return "process_states_node"
    elif expected_input == "additional_states_list":
        logger.info("Routing to process_states_node for additional states")
        return "process_states_node"
    elif expected_input == "hybrid_query":
        logger.info("Routing to perform_hybrid_search")
        return "perform_hybrid_search"
    elif expected_input == "additional_criteria":
        # Complex logic for handling "No" responses in hybrid search refinement
        # Different behavior based on college count: 10-12 allows "No", >12 requires criteria
        user_response = get_last_user_message_content(state).lower().strip()
        final_docs = state.get("final_docs", {})
        num_colleges = len(final_docs)

        # If user said "No" and there are 10-12 colleges, finalize the workflow
        if user_response == "no" and 10 <= num_colleges <= 12:
            logger.info(
                f"WORKFLOW DECISION: User said 'No' with {num_colleges} colleges (10-12 range). "
                f"This is acceptable - finalizing workflow and proceeding to visualization."
            )
            messages_copy = state.get("messages", []).copy()
            messages_copy.append(
                {
                    "role": "assistant",
                    "content": f"Perfect! Since you're satisfied with the current {num_colleges} colleges, I'll conclude the search here. You can review the college analysis above.",
                }
            )
            state["messages"] = messages_copy
            return "generate_visualisation"
        elif user_response == "no" and num_colleges > 12:
            # User said "No" but has too many colleges - this is not allowed
            logger.info(
                f"WORKFLOW VIOLATION: User said 'No' with {num_colleges} colleges (>12). "
                f"Must provide criteria when >12 colleges. Rejecting and requesting proper criteria."
            )
            messages_copy = state.get("messages", []).copy()
            messages_copy.append(
                {
                    "role": "assistant",
                    "content": f"I still have {num_colleges} colleges, which is quite a lot! Please provide specific criteria to help narrow down the list (like cost, location, or academic focus) rather than saying 'No'.",
                }
            )
            state["messages"] = messages_copy
            state["expected_input"] = "additional_criteria"  # Keep expecting criteria
            return "ask_more_criteria_node"
        else:
            logger.info("Routing to perform_hybrid_search for additional criteria")
            return "perform_hybrid_search"

    # Check various state conditions to determine next step
    current_sat_profile = state.get("current_sat_profile")
    state_docs = state.get("state_docs")
    categorized_docs = state.get("categorized_docs")
    db_vectorstore = state.get("db_vectorstore")

    # If SAT profile is set but states not processed yet, ask for states
    if (
        current_sat_profile is not None
        and state_docs is None
        and not state.get("selected_states")
        and not expected_input
    ):
        logger.info(
            "SAT profile set, states not processed yet. Routing to ask_states_node."
        )
        return "ask_states_node"

    # If states are processed but colleges not categorized yet
    if (
        state_docs is not None
        and len(state_docs) > 0
        and categorized_docs is None
        and not expected_input
    ):
        logger.info("Routing to categorize_colleges_node")
        return "categorize_colleges_node"

    # If colleges are categorized but risk summary not done yet
    if (
        categorized_docs is not None
        and not expected_input
        and db_vectorstore is not None  # We have vectorstore for hybrid search
        and not state.get(
            "search_complete"
        )  # Haven't started hybrid search workflow yet
    ):
        logger.info("Routing to summarise_admission_node")
        return "summarise_admission_node"

    # If states are processed but no colleges found, skip categorization and go to risk summary
    if (
        state_docs is not None
        and len(state_docs) == 0  # No colleges found
        and categorized_docs is None
        and not expected_input
    ):
        logger.info(
            "No colleges found after filtering - skipping categorization and going to risk summary"
        )
        return "summarise_admission_node"

    # If SAT profile is set but no other processing has started, this indicates an unexpected state.
    if current_sat_profile is not None:
        logger.error(
            "Unexpected state condition - SAT profile exists but no processing path identified"
        )
        return END

    # Default case - start workflow by asking for SAT score
    logger.info("Default routing to ask_manual_sat")
    return "ask_manual_sat"


def route_after_admission_category_summary(state: GraphState) -> str:
    """
    Route after admission category summary based on college count.

    Implements college count-based routing logic:
    - 0 colleges: Restart state selection to find more options
    - < 10 colleges: Skip hybrid search and proceed to visualizations
    - ≥ 10 colleges: Start hybrid search to narrow down results

    This is a critical decision point that determines whether the workflow
    proceeds to hybrid search or jumps directly to visualization/completion.
    """
    logger.info("Entering route_after_admission_category_summary")
    categorized_docs = state.get("categorized_docs", [])
    num_colleges = len(categorized_docs)
    messages = state.get("messages", []).copy()

    logger.info(f"Evaluating {num_colleges} colleges for hybrid search decision")

    if num_colleges == 0:
        logger.info(
            "No colleges found after categorization. Automatically restarting workflow to ask for states."
        )

        # Clear search-related state to restart from state selection
        state["state_docs"] = None
        state["categorized_docs"] = None
        state["selected_states"] = None
        state["expected_input"] = None

        # Add a message explaining the restart
        messages.append(
            {
                "role": "assistant",
                "content": "I didn't find any colleges that match your criteria in the selected states. Let's try a fresh start with different state selections to find colleges that might be a better fit for you.",
            }
        )
        state["messages"] = messages

        return "ask_states_node"
    elif num_colleges < 10:
        logger.info(
            f"Number of colleges ({num_colleges}) is less than 10. Proceeding to visualizations and clarifying questions."
        )
        messages.append(
            {
                "role": "assistant",
                "content": f"I found {num_colleges} colleges that fit your profile and selected states. Since this is a focused list, I'll generate visualizations and then ask some clarifying questions to help refine your recommendations.",
            }
        )
        state["messages"] = messages
        # Set final_docs to the categorized_docs so visualizations can work
        state["final_docs"] = {
            doc.metadata.get("document_id", f"doc_{i}"): doc
            for i, doc in enumerate(categorized_docs)
            if doc.metadata.get("document_id")
        }
        return "generate_visualisation"
    else:
        logger.info(
            f"Number of colleges ({num_colleges}) is 10 or more. Proceeding to hybrid search."
        )
        return "ask_hybrid_search_query"


def route_after_intersection_count(state: GraphState) -> str:
    """
    Route after intersection count based on whether more criteria are needed.

    Implements search result evaluation logic:
    - No results (0 colleges): Return to search query to try different criteria
    - < 10 colleges: Proceed to visualizations (good focused result)
    - 10-12 colleges: Ask for additional criteria with option to decline
    - > 12 colleges: Ask for additional criteria (required to narrow down)

    This function handles the core hybrid search result evaluation and determines
    whether to continue refining search criteria or proceed to visualization.
    """
    logger.info("Entering route_after_intersection_count")
    final_docs = state.get("final_docs", {})
    num_colleges = len(final_docs)

    logger.info(f"Number of colleges after intersection: {num_colleges}")

    if num_colleges == 0:
        logger.info(
            "No colleges found after intersection. Routing to ask_hybrid_search_query_node."
        )
        return "ask_hybrid_search_query_node"
    elif num_colleges < 10:
        logger.info(
            f"Number of colleges ({num_colleges}) is less than 10. Finalizing hybrid search."
        )
        return "generate_visualisation"
    else:
        logger.info(
            f"Number of colleges ({num_colleges}) is 10 or more. Asking for more criteria."
        )
        return "ask_more_criteria_node"


def route_after_clarifying_questions(state: GraphState) -> str:
    """Route after asking clarifying questions - either to reranking if user wants questions, or to completion if user declines."""
    logger.info("Entering route_after_clarifying_questions")

    wants_clarification = state.get("wants_clarification")
    search_complete = state.get("search_complete")
    clarifying_responses = state.get("clarifying_responses")
    expected_input = state.get("expected_input")

    if wants_clarification is True:
        # User wants clarification questions - check if they've provided answers yet
        if clarifying_responses:
            # User has provided answers - route to reranking
            logger.info(
                "User wants clarification and has provided responses - routing to node_reranking"
            )
            return "node_reranking"
        elif expected_input == "clarifying_answers":
            # Questions are shown but user hasn't answered yet - wait for answers
            logger.info(
                "Clarifying questions shown, waiting for user answers - routing to END"
            )
            return END
        else:
            # User wants clarification but questions haven't been shown yet - go back to ask_clarifying_questions
            logger.info(
                "User wants clarification but questions not shown yet - routing back to ask_clarifying_questions"
            )
            return "ask_clarifying_questions"
    elif wants_clarification is False or search_complete is True:
        # User declined clarification or workflow is complete - route to completion
        logger.info(
            "User declined clarification or workflow complete - routing to workflow_completion"
        )
        return "workflow_completion"
    else:
        # Still waiting for user input - route to END to wait for user response
        logger.info("Still waiting for user input on clarification - routing to END")
        return END
