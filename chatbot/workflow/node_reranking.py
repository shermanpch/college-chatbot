"""
Workflow node for re-ranking colleges based on user's clarifying answers.
"""

from typing import Any

from chatbot.components.college_reranker import (
    RankedDocuments,
    generate_reranked_colleges,
)
from projectutils.logger import setup_logger

from .state import GraphState
from .utils import get_api_key_error_message, is_api_key_error

# Set up logging
logger = setup_logger(__file__)


async def rerank_colleges_node(state: GraphState) -> dict[str, Any]:
    """
    Re-rank shortlisted colleges based on user's answers to clarifying questions
    using a Langchain LLM chain.
    """
    logger.info("Entering rerank_colleges_node")

    # Retrieve required data from state
    clarifying_questions = state.get("clarifying_questions", "")
    clarifying_responses = state.get("clarifying_responses", "")

    # If clarifying_responses is empty, extract from the last user message
    if not clarifying_responses:
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if last_message.get("role") == "user":
                clarifying_responses = last_message.get("content", "")
                logger.info(
                    f"Extracted clarifying responses from last message: {clarifying_responses}"
                )

    # Input final_docs is dict[str, Document]
    final_docs = state.get("final_docs", {})

    if not final_docs:
        logger.warning("No colleges found in final_docs for re-ranking")
        messages = state.get("messages", []).copy()
        messages.append(
            {
                "role": "assistant",
                "content": "I don't see any colleges to re-rank. Please try searching again.",
            }
        )
        return {
            "messages": messages,
            "clarifying_responses": clarifying_responses,
            "search_complete": True,
        }

    logger.info(f"Re-ranking {len(final_docs)} colleges")

    # Prepare student preferences for LLM
    student_preferences = f"Clarifying Questions:\n{clarifying_questions}\n\nStudent's Responses:\n{clarifying_responses}".strip()

    # Log the student preferences to see how they look
    logger.debug(f"Student preferences for LLM:\n{student_preferences}")

    try:
        # Prepare concatenated document contexts for LLM
        docs_context_for_llm_parts = []
        valid_document_ids = []
        doc_id_mapping = {}

        for doc_id, document_obj in final_docs.items():
            if hasattr(document_obj, "page_content") and hasattr(
                document_obj, "metadata"
            ):  # Ensure it's a Document object
                page_content = document_obj.page_content
                # Use the doc_id (key) as the document ID for the LLM, since that's how the mapping is structured
                docs_context_for_llm_parts.append(
                    f"--- DOCUMENT ID: {doc_id} ---\n{page_content}\n--- END DOCUMENT ID: {doc_id} ---\n\n"
                )
                valid_document_ids.append(doc_id)
                doc_id_mapping[doc_id] = doc_id  # In this case, they're the same
            else:
                logger.warning(
                    f"Item with key {doc_id} in final_docs is not a Document object. Skipping."
                )

        if not docs_context_for_llm_parts:
            logger.warning(
                "No valid documents found in final_docs to process for LLM ranking."
            )
            messages = state.get("messages", []).copy()
            messages.append(
                {
                    "role": "assistant",
                    "content": "I encountered an issue processing the college documents for ranking. Please try searching again.",
                }
            )
            return {
                "messages": messages,
                "clarifying_responses": clarifying_responses,
                "search_complete": True,
            }

        concatenated_document_contexts = "".join(docs_context_for_llm_parts)

        # Debug: Log the actual document IDs being sent to LLM
        logger.info(f"Valid document IDs being sent to LLM: {valid_document_ids}")
        logger.debug(
            f"First 500 chars of concatenated contexts: {concatenated_document_contexts[:500]}..."
        )

        # Generate reranked colleges using the new component
        llm_ranked_output: RankedDocuments = await generate_reranked_colleges(
            student_preferences=student_preferences,
            concatenated_document_contexts=concatenated_document_contexts,
        )

        # Process LLM rankings and append rank/reason to existing documents
        ranked_documents_found = []
        for item in llm_ranked_output.rankings:
            doc_id_from_llm = item.document_id
            # Ensure the doc_id from LLM is one of the valid ones that were sent
            if doc_id_from_llm in valid_document_ids and doc_id_from_llm in final_docs:
                # Get the original document and append rank/reason to its metadata
                original_doc_obj = final_docs[doc_id_from_llm]
                # Add rank and reason to the document's metadata
                original_doc_obj.metadata["llm_rank"] = item.rank
                original_doc_obj.metadata["llm_reason"] = item.reason
                ranked_documents_found.append(doc_id_from_llm)
            else:
                logger.warning(
                    f"LLM returned rank for an unexpected document_id: {doc_id_from_llm}. This item will be skipped."
                )

        # Check if LLM successfully ranked any documents
        if not ranked_documents_found and final_docs:
            logger.error(
                "LLM ranking failed to produce valid ranked items. Falling back."
            )
            raise Exception("LLM ranking yielded no valid items.")

        # Normalize rankings to be consecutive (1, 2, 3, 4, 5...)
        # Get all documents that have been ranked by the LLM
        ranked_docs = [
            doc
            for doc in final_docs.values()
            if doc.metadata.get("llm_rank") is not None
        ]

        # Sort by original LLM rank to maintain the LLM's intended order
        ranked_docs.sort(key=lambda doc: doc.metadata.get("llm_rank"))

        # Reassign consecutive ranks starting from 1
        for i, doc in enumerate(ranked_docs, 1):
            original_rank = doc.metadata.get("llm_rank")
            doc.metadata["llm_rank"] = i
            logger.info(
                f"Normalized rank for {doc.metadata.get('university_name', 'Unknown')}: {original_rank} -> {i}"
            )

        messages = state.get("messages", []).copy()
        messages.append(
            {
                "role": "assistant",
                "content": "I've re-ranked the colleges based on your responses using advanced analysis. The updated college recommendations reflect your preferences!",
            }
        )

        # Add SAT Profile to state messages
        current_sat_profile = state.get("current_sat_profile", {})
        sat_score = current_sat_profile.get("score", "N/A")
        sat_source = current_sat_profile.get("source_type", "N/A").title()
        sat_range = f"{current_sat_profile.get('lower_bound', 'N/A')}-{current_sat_profile.get('upper_bound', 'N/A')}"
        sat_profile_content = (
            f"## 📊 Your SAT Profile\n\n"
            f"- **Score:** {sat_score}\n"
            f"- **Estimated Range:** {sat_range}\n"
            f"- **Source:** {sat_source}"
        )
        messages.append(
            {
                "role": "assistant",
                "content": sat_profile_content,
            }
        )

        # Add Top 5 Ranked Colleges to state messages
        all_ranked_docs = [
            doc
            for doc in final_docs.values()
            if doc.metadata.get("llm_rank") is not None
        ]
        sorted_ranked_colleges = sorted(
            all_ranked_docs, key=lambda doc: doc.metadata.get("llm_rank")
        )

        messages.append(
            {
                "role": "assistant",
                "content": "## 🏆 Top College Recommendations",
            }
        )

        for _i, doc in enumerate(sorted_ranked_colleges[:5]):
            college_name = doc.metadata.get("university_name", "Unknown College")
            rank = doc.metadata.get("llm_rank", "N/A")
            reason = doc.metadata.get("llm_reason", "No reason provided.")
            source_path = doc.metadata.get("source")
            source_url = doc.metadata.get("source_url", doc.metadata.get("url", ""))

            # Add logging to track source_path and URL from metadata
            logger.debug(
                f"College: {college_name}, Source Path: '{source_path}', Source URL: '{source_url}'"
            )

            # Make college name clickable if URL is available, but keep markdown file functionality
            if source_url:
                clickable_college_name = f"[{college_name}]({source_url})"
                card_content = f"### Rank {rank}: {clickable_college_name}\n**Reasoning:** {reason}\n\n🌐 **Click college name above to view official page**\n📄 **Click to View:** {college_name} Report"
            else:
                card_content = f"### Rank {rank}: {college_name}\n**Reasoning:** {reason}\n\n📄 **Click to View:** {college_name} Report"

            messages.append(
                {
                    "role": "assistant",
                    "content": card_content,
                    "metadata": {
                        "college_name": college_name,
                        "source_path": source_path,
                        "message_type": "college_ranking",
                    },
                }
            )

        return {
            "messages": messages,
            "final_docs": final_docs,  # Return the updated documents
            "clarifying_responses": clarifying_responses,  # Keep this for record
        }

    except Exception as e:
        logger.error(f"Error during re-ranking: {e}")

        # Check for API key related errors
        if is_api_key_error(e):
            error_message = get_api_key_error_message()
        else:
            error_message = "I encountered an issue while re-ranking the colleges, but your original recommendations are still available above."

        # Fallback: return original mapping without re-ranking
        messages = state.get("messages", []).copy()
        messages.append(
            {
                "role": "assistant",
                "content": error_message,
            }
        )

        return {
            "messages": messages,
            "clarifying_responses": clarifying_responses,
            "search_complete": True,
        }
