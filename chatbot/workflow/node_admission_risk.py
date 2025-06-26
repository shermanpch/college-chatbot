from typing import Any

from chatbot.components.college_utils import (
    add_admission_categories_to_documents,
    normalize_and_match_states,
)
from projectutils.logger import setup_logger

from .state import GraphState

# Set up logging
logger = setup_logger(__file__)


def categorize_colleges_node(state: GraphState) -> dict[str, Any]:
    """Add admission category metadata to the state-filtered college documents."""
    logger.info("Entering categorize_colleges_node")
    messages = state.get("messages", []).copy()

    # Get required data
    state_docs = state.get("state_docs", [])
    current_sat_profile = state.get("current_sat_profile", {})
    sat_upper = current_sat_profile.get("upper_bound")
    sat_lower = current_sat_profile.get("lower_bound")

    logger.info(
        f"Categorizing {len(state_docs)} colleges with SAT range {sat_lower}-{sat_upper}"
    )

    # Add admission category metadata using the updated function
    categorized_documents = add_admission_categories_to_documents(
        documents=state_docs, upper_sat=sat_upper, lower_sat=sat_lower
    )

    messages.append(
        {
            "role": "assistant",
            "content": "🔍 **Analyzing admission chances** based on your SAT profile...",
        }
    )

    logger.info("Exiting categorize_colleges_node successfully")
    return {
        "messages": messages,
        "categorized_docs": categorized_documents,
    }


def summarise_admission_node(state: GraphState) -> dict[str, Any]:
    """Calculate and present the admission category summary."""
    logger.info("Entering summarise_admission_node")
    messages = state.get("messages", []).copy()
    categorized_docs = state.get("categorized_docs", [])
    selected_states = state.get("selected_states", [])

    logger.info(
        f"Summarizing categories for {len(categorized_docs)} colleges in {len(selected_states)} states"
    )

    # Count colleges by category for each state
    state_summaries = {}
    for selected_state in selected_states:
        state_summaries[selected_state] = {
            "reach": 0,
            "target": 0,
            "safety": 0,
            "unknown": 0,
        }

    for doc in categorized_docs:
        metadata = doc.metadata
        doc_state = metadata.get("state", "").strip()
        admission_category = metadata.get("admission_category", "unknown")

        # Find which selected state this document belongs to
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

    # Format the summary with better markdown
    summary_lines = ["## 🎓 **College Admission Profile Analysis**", ""]

    for state_name, counts in state_summaries.items():
        total_colleges = (
            counts["reach"] + counts["target"] + counts["safety"] + counts["unknown"]
        )
        summary_lines.append(f"### 📍 **{state_name}** ({total_colleges} colleges)")
        summary_lines.append(f"- 🎯 **Target:** {counts['target']} colleges")
        summary_lines.append(f"- ✅ **Safety:** {counts['safety']} colleges")
        summary_lines.append(f"- 🚀 **Reach:** {counts['reach']} colleges")
        if counts["unknown"] > 0:
            summary_lines.append(f"- ❓ **Unknown:** {counts['unknown']} colleges")
        summary_lines.append("")

    # Add helpful explanation
    summary_lines.extend(
        [
            "---",
            "",
            "#### 📖 **Category Definitions:**",
            "- **🎯 Target:** Good match for your SAT profile",
            "- **✅ Safety:** Higher acceptance likelihood",
            "- **🚀 Reach:** More competitive, worth applying!",
            "",
        ]
    )

    summary_text = "\n".join(summary_lines)

    messages.append({"role": "assistant", "content": summary_text})

    # Ensure final_docs is populated if the workflow will skip hybrid search (i.e., fewer than 10 colleges)
    total_colleges = len(categorized_docs)
    final_docs_dict = None
    if total_colleges < 10 and total_colleges > 0:
        # Build a mapping doc_id -> Document, falling back to an enumerated key if document_id missing
        final_docs_dict = {
            doc.metadata.get("document_id", f"doc_{i}"): doc
            for i, doc in enumerate(categorized_docs)
        }

        # Log for debugging purposes
        logger.info(
            f"Populated final_docs with {len(final_docs_dict)} documents for visualization step."
        )

    logger.info("Exiting summarise_admission_node successfully")
    # Return messages and (optionally) final_docs
    result: dict[str, Any] = {"messages": messages}
    if final_docs_dict is not None:
        result["final_docs"] = final_docs_dict

    return result
