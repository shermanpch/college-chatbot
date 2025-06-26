from typing import Any

from langchain_core.documents import Document

from chatbot.components import retriever as retriever_component
from chatbot.components.attributes import PETERSON_METADATA_FIELDS
from chatbot.components.college_utils import normalize_and_match_states
from chatbot.components.feature_analyzer import analyze_distinguishing_features
from chatbot.components.suggestion_generator import generate_search_suggestions
from projectutils.logger import setup_logger

from .messages import create_hybrid_search_query_prompt, create_more_criteria_prompt
from .state import GraphState
from .utils import get_last_user_message_content

# Set up logging
logger = setup_logger(__file__)


async def ask_hybrid_search_query_node(state: GraphState) -> dict[str, Any]:
    """Ask the user for their specific hybrid search query with dynamic suggestions."""
    logger.info("Entering ask_hybrid_search_query_node")
    messages = state.get("messages", []).copy()

    # If this is not a retry scenario, add the main prompt.
    # In a retry, the previous node ('intersect_and_final_count_node') has already
    # added a detailed message explaining the failure and asking for new criteria.
    if not state.get("retry_search", False):
        logger.info("First-time hybrid search query, generating dynamic prompt.")

        # Get categorized docs for feature analysis
        categorized_docs = state.get("categorized_docs", [])

        dynamic_suggestions = None
        if categorized_docs:
            try:
                # Create field type mappings from PETERSON_METADATA_FIELDS
                field_types = {}
                for attr_info in PETERSON_METADATA_FIELDS:
                    field_types[attr_info.name] = attr_info.type

                # Analyze distinguishing features
                distinguishing_features_summary = analyze_distinguishing_features(
                    categorized_docs,
                    field_types,
                    num_features_to_select=10,
                )

                # Generate dynamic suggestions
                dynamic_suggestions = await generate_search_suggestions(
                    len(categorized_docs),
                    distinguishing_features_summary,
                    num_suggestions=5,
                )

            except Exception as e:
                logger.error(f"Error generating dynamic suggestions: {e}")
                # dynamic_suggestions will remain None, triggering fallback in message function

        # Create the full prompt using centralized message function
        full_prompt = create_hybrid_search_query_prompt(dynamic_suggestions)

        messages.append(
            {
                "role": "assistant",
                "content": full_prompt,
            }
        )
    else:
        logger.info("In retry scenario after zero results. Skipping additional prompt.")

    logger.info("Exiting ask_hybrid_search_query_node successfully")
    return {
        "messages": messages,
        "expected_input": "hybrid_query",
    }


async def ask_more_criteria_node(state: GraphState) -> dict[str, Any]:
    """Ask the user for additional criteria to narrow down the search with dynamic suggestions."""
    logger.info("Entering ask_more_criteria_node")
    messages = state.get("messages", []).copy()
    final_docs = state.get("final_docs", {})
    num_colleges = len(final_docs)

    # Convert final_docs dict to list of Documents for analysis
    college_docs = list(final_docs.values()) if final_docs else []

    logger.info(
        f"Using {'prompt with' if 10 <= num_colleges <= 12 else 'standard prompt for'} {num_colleges} colleges"
    )

    dynamic_suggestions = None
    if college_docs:
        try:
            # Create field type mappings from PETERSON_METADATA_FIELDS
            field_types = {}
            for attr_info in PETERSON_METADATA_FIELDS:
                field_types[attr_info.name] = attr_info.type

            # Analyze distinguishing features
            distinguishing_features_summary = analyze_distinguishing_features(
                college_docs,
                field_types,
                num_features_to_select=10,
            )

            # Generate dynamic suggestions
            dynamic_suggestions = await generate_search_suggestions(
                num_colleges,
                distinguishing_features_summary,
                num_suggestions=5,
            )

        except Exception as e:
            logger.error(f"Error generating dynamic suggestions: {e}")

    # Create the full prompt using centralized message function
    full_prompt = create_more_criteria_prompt(num_colleges, dynamic_suggestions)

    messages.append(
        {
            "role": "assistant",
            "content": full_prompt,
        }
    )
    logger.info("Exiting ask_more_criteria_node successfully")
    return {"messages": messages, "expected_input": "additional_criteria"}


def perform_hybrid_search_node(state: GraphState) -> dict[str, Any]:
    """Execute hybrid search based on user query using fixed_filters from categorized documents."""
    logger.info("Entering perform_hybrid_search_node")
    messages = state.get("messages", []).copy()

    # Get the user's query from the last message
    user_query = get_last_user_message_content(state)
    logger.info(f"User query: '{user_query}'")

    # Handle query concatenation based on expected input type
    expected_input = state.get("expected_input")
    retry_after_zero_results = state.get("retry_search", False)

    accumulated_query = None

    if expected_input == "hybrid_query":
        if retry_after_zero_results:
            # This is a retry after zero results - user wants to replace the failed addition
            # The accumulated_query should already be restored to the last successful query
            current_accumulated = state.get("hybrid_query", "")

            if current_accumulated:
                # Add the new criteria to the restored successful query
                new_accumulated_query = f"{current_accumulated} {user_query}".strip()
                accumulated_query = new_accumulated_query
                search_query_for_retriever = new_accumulated_query
                logger.info(
                    f"Retry: Adding '{user_query}' to restored query '{current_accumulated}' → '{search_query_for_retriever}'"
                )
            else:
                # Fallback to treating as new query
                accumulated_query = user_query
                search_query_for_retriever = user_query
                logger.info(f"Retry fallback: '{search_query_for_retriever}'")
        else:
            # Initial query
            current_query_part = user_query
            accumulated_query = current_query_part
            search_query_for_retriever = current_query_part
            logger.info(f"Initial hybrid query: '{search_query_for_retriever}'")
    elif expected_input == "additional_criteria":
        # Additional criteria
        additional_criteria_part = user_query
        previous_accumulated_query = state.get("hybrid_query", "")
        new_accumulated_query = (
            f"{previous_accumulated_query} {additional_criteria_part}".strip()
        )
        accumulated_query = new_accumulated_query
        search_query_for_retriever = new_accumulated_query
        logger.info(f"Accumulated hybrid query: '{search_query_for_retriever}'")
    else:
        # Fallback to using user query directly
        search_query_for_retriever = user_query
        accumulated_query = state.get("hybrid_query")  # Preserve existing value
        logger.info(f"Fallback query: '{search_query_for_retriever}'")

    # Get the vectorstore from state
    db_vectorstore = state.get("db_vectorstore")

    if db_vectorstore is None:
        logger.warning("No vectorstore available for hybrid search")
        messages.append(
            {
                "role": "assistant",
                "content": "Sorry, the college database is not available for detailed searches.",
            }
        )
        return {
            "messages": messages,
            "search_complete": True,
            "hybrid_query": accumulated_query,
            "expected_input": None,
            "retry_search": False,  # Clear the retry flag
            "last_input": None,
            "pending_query": None,
        }

    # Determine the source for document_ids for the fixed_filter
    document_ids_for_filter = []
    # This is dict[str, Document] or None
    previous_final_docs_dict = state.get("final_docs")

    # last_query is set when a hybrid search + intersection is successful
    if state.get("last_query") and previous_final_docs_dict:
        # This means additional criteria are being applied to a previously successful search,
        # or retrying such an addition. Use document IDs from the last successful filter.
        document_ids_for_filter = list(previous_final_docs_dict.keys())
        logger.info(
            f"Using {len(document_ids_for_filter)} document IDs from current final_docs (last successful filter) for fixed_filters."
        )
    else:
        # This is the initial hybrid search for the selected states, or a retry of that initial search.
        # Use document IDs from all categorized documents for the selected states.
        categorized_docs_list = state.get(
            "categorized_docs", []
        )  # This is list[Document]
        document_ids_for_filter = [
            doc.metadata.get("document_id")
            for doc in categorized_docs_list
            if doc.metadata.get("document_id")
        ]
        logger.info(
            f"Using {len(document_ids_for_filter)} document IDs from categorized_docs for fixed_filters (initial search or retry of initial)."
        )

    if not document_ids_for_filter:
        logger.warning(
            "No document IDs available for fixed_filter. The search might be broader than expected or yield no results if it relies on these IDs."
        )
        # Handle case where no documents are available
        categorized_docs = state.get("categorized_docs", [])
        if not categorized_docs:
            logger.warning("No categorized state documents available for hybrid search")
            messages.append(
                {
                    "role": "assistant",
                    "content": "Sorry, no colleges are available for search. Please try selecting states first.",
                }
            )
            return {
                "messages": messages,
                "search_complete": True,
                "hybrid_query": accumulated_query,
                "expected_input": None,
                "retry_search": False,
                "last_input": None,
                "pending_query": None,
            }

    try:
        logger.info("Creating self-query retriever with fixed_filters...")

        # Create fixed filters using the determined document_ids
        fixed_filters = retriever_component.create_fixed_filters(
            document_id=document_ids_for_filter  # Use the new variable
        )

        # Create retriever and perform search
        retriever = retriever_component.create_self_query_retriever(
            vectorstore=db_vectorstore, k=1600, fixed_filters=fixed_filters
        )

        # Log the structured query details using our helper function
        logger.info("Analyzing structured query...")
        query_details = retriever_component.get_structured_query_details(
            retriever, search_query_for_retriever
        )

        logger.debug("Structured Query Analysis:")
        logger.debug(f"  Search Query: '{query_details['search_query']}'")
        logger.debug(f"  Fixed Filters: {query_details['fixed_filters']}")
        logger.debug(f"  LLM Metadata Filters: {query_details['metadata_filters']}")
        logger.debug(f"  Combined Metadata: {query_details['combined_metadata']}")
        logger.debug(f"  Limit: {query_details['limit']}")

        logger.info("Performing hybrid search...")
        retrieved_docs = retriever.invoke(search_query_for_retriever)
        logger.info(f"Retrieved {len(retrieved_docs)} documents from hybrid search")

        # Log some sample retrieved documents
        if retrieved_docs:
            logger.debug("Sample retrieved documents:")
            for i, doc in enumerate(retrieved_docs[:3]):  # Show first 3
                doc_id = doc.metadata.get("document_id", "unknown")
                institution_name = doc.metadata.get("institution_name", "unknown")
                state = doc.metadata.get("state", "unknown")
                logger.debug(f"  [{i + 1}] {institution_name} ({state}) - ID: {doc_id}")

        # Don't show the search results message - results will be shown in visualization

        logger.info("Exiting perform_hybrid_search_node successfully")
        return {
            "messages": messages,
            "hybrid_search_results": retrieved_docs,
            "hybrid_query": search_query_for_retriever,  # The query just tried
            "expected_input": None,
            "retry_search": False,  # Clear the retry flag
            "pending_query": search_query_for_retriever,
            "last_input": expected_input,
        }

    except Exception as e:
        logger.error(f"Error in perform_hybrid_search_node: {e}")
        messages.append(
            {
                "role": "assistant",
                "content": f"Sorry, there was an issue processing your query: {str(e)}",
            }
        )
        return {
            "messages": messages,
            "search_complete": True,
            "hybrid_query": search_query_for_retriever,
            "expected_input": None,
            "retry_search": False,  # Clear the retry flag
            "last_input": None,
            "pending_query": None,
        }


def intersect_and_final_count_node(state: GraphState) -> dict[str, Any]:
    """
    Intersect hybrid search results with categorized state documents,
    ensuring admission_category metadata is preserved in the final documents.
    """
    logger.info("Entering intersect_and_final_count_node")
    messages = state.get("messages", []).copy()

    # Get the current final_docs from state to preserve in case of failure
    current_final_docs_in_state = state.get("final_docs", {})

    categorized_docs = state.get("categorized_docs", [])
    hybrid_search_results = state.get("hybrid_search_results", [])
    selected_states = state.get("selected_states", [])

    logger.info(
        f"Intersecting {len(hybrid_search_results)} hybrid search results with {len(categorized_docs)} categorized documents"
    )

    # Create a dictionary mapping document IDs to categorized documents (which have admission_category)
    categorized_docs_map = {
        doc.metadata.get("document_id"): doc
        for doc in categorized_docs
        if doc.metadata.get("document_id")
    }

    # Create a dictionary mapping document IDs to hybrid search results
    hybrid_results_map = {
        doc.metadata.get("document_id"): doc
        for doc in hybrid_search_results
        if doc.metadata.get("document_id")
    }

    logger.info(
        f"Created maps: {len(categorized_docs_map)} categorized docs, {len(hybrid_results_map)} hybrid results"
    )

    # Find intersection of document IDs
    categorized_ids = set(categorized_docs_map.keys())
    hybrid_ids = set(hybrid_results_map.keys())
    final_doc_ids_intersect = categorized_ids.intersection(hybrid_ids)

    logger.info(
        f"Intersection resulted in {len(final_doc_ids_intersect)} matching colleges"
    )

    # Create final mapping, storing the full Document object with admission_category metadata
    final_docs = {}
    for doc_id in final_doc_ids_intersect:
        # Get the hybrid search result (has fresh content and metadata from vectorstore)
        hybrid_doc = hybrid_results_map[doc_id]

        # Get the categorized document (has admission_category in metadata)
        categorized_doc = categorized_docs_map[doc_id]

        # Create a new document with hybrid search content and merged metadata
        merged_metadata = hybrid_doc.metadata.copy()
        # Add the admission_category from the categorized document
        merged_metadata["admission_category"] = categorized_doc.metadata.get(
            "admission_category", "unknown"
        )

        # Create the final document
        final_doc = Document(
            page_content=hybrid_doc.page_content, metadata=merged_metadata
        )

        # Store the complete, updated Document object
        final_docs[doc_id] = final_doc

    # Count colleges by category for each state from the final documents' metadata
    state_summaries = {}
    for selected_state in selected_states:
        state_summaries[selected_state] = {
            "reach": 0,
            "target": 0,
            "safety": 0,
            "unknown": 0,
        }

    for _doc_id, doc in final_docs.items():
        metadata = doc.metadata  # Access metadata from the Document object
        doc_state = metadata.get("state", "").strip()
        admission_category = metadata.get("admission_category", "unknown")

        # Check if this document's state matches any of the selected states
        matched_state_name = None

        for selected_state in selected_states:
            if normalize_and_match_states(doc_state, selected_state):
                matched_state_name = selected_state
                break

        # If match is found, count it under that state
        if (
            matched_state_name
            and admission_category in state_summaries[matched_state_name]
        ):
            state_summaries[matched_state_name][admission_category] += 1

    # Format the final summary
    total_colleges = len(final_docs)

    if total_colleges > 0:
        # Don't add the filtering message when results are found
        # The visualization node will show the results directly
        pass

    # Track success/failure for query history
    pending_query = state.get("pending_query")
    last_input = state.get("last_input")

    # Add failure message if no colleges found
    if total_colleges == 0:
        # Prepare failure data
        last_user_query = get_last_user_message_content(state)

        # Determine what failed
        if last_input == "additional_criteria":
            failed_addition = last_user_query
            last_successful = state.get("last_query", "")
        else:  # initial "hybrid_query" failed
            failed_addition = pending_query
            last_successful = ""

        # Create failure message
        user_message_parts = ["## ❌ **No Results Found**", ""]
        if failed_addition and last_successful:
            user_message_parts.append(
                f'**What didn\'t work:** Your additional criteria **"{failed_addition}"** combined with your previous successful search for **"{last_successful}"** didn\'t yield any colleges.'
            )
            user_message_parts.append(
                f"**What's still active:** We'll keep the results from your search for **\"{last_successful}\"**."
            )
        elif failed_addition:  # Initial query failed
            user_message_parts.append(
                f"**What didn't work:** Your search criteria **\"{failed_addition}\"** didn't find any colleges matching your selected states and SAT profile."
            )
        else:  # Generic fallback
            user_message_parts.append(
                "Your latest search criteria didn't yield any colleges from the current selection."
            )

        user_message_parts.append("")
        user_message_parts.append(
            "**What to try next:** Please provide different criteria to refine your search. Consider:"
        )
        user_message_parts.append(
            '- Broadening the range (e.g., "under $40,000" instead of "under $30,000")'
        )
        user_message_parts.append(
            '- Different attributes (e.g., "acceptance rate below 50%")'
        )
        user_message_parts.append('- Alternative features (e.g., "strong campus life")')

        user_message_content = "\n".join(user_message_parts)
        messages.append({"role": "assistant", "content": user_message_content})

    result_updates = {
        "messages": messages,
        "pending_query": None,  # Clear the pending query
        "last_input": None,  # Clear the tracking field
    }

    if total_colleges > 0:
        # Successful intersection
        result_updates["final_docs"] = (
            final_docs  # final_docs here is the new intersection
        )
        result_updates["last_query"] = pending_query
        result_updates["failed_query"] = None
        result_updates["retry_search"] = False
        logger.info(
            f"Storing successful query: '{pending_query}' and updated final_docs with {len(final_docs)} colleges."
        )
    else:  # total_colleges == 0
        # Failed intersection, preserve previous final_docs
        result_updates["final_docs"] = (
            current_final_docs_in_state  # Restore previous state
        )
        result_updates["retry_search"] = True
        last_user_query = get_last_user_message_content(state)

        if last_input == "additional_criteria":
            result_updates["failed_query"] = last_user_query
            current_last_successful = state.get("last_query", "")
            result_updates["hybrid_query"] = current_last_successful
            logger.info(
                f"Storing failed addition: '{last_user_query}'. Restoring hybrid query to '{current_last_successful}'. final_docs preserved."
            )
        else:  # initial "hybrid_query" failed
            result_updates["failed_query"] = pending_query
            result_updates["last_query"] = ""
            result_updates["hybrid_query"] = ""
            logger.info(
                f"Storing failed initial query: '{pending_query}'. final_docs preserved (was likely None or empty)."
            )

    logger.info("Exiting intersect_and_final_count_node successfully")
    return result_updates
