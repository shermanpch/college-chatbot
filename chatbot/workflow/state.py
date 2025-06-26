from typing import Any, TypedDict

from langchain_chroma import Chroma
from langchain_core.documents import Document


# TypedDict for grouping SAT-related information
class SATAnalysisProfile(TypedDict):
    score: int | None
    upper_bound: int | None
    lower_bound: int | None
    source_type: str | None  # e.g., "latest", "previous", "predicted", "manual"


class GraphState(TypedDict):
    # Core interaction
    messages: list[dict[str, str]]

    # General workflow control
    expected_input: str | None

    # SAT data processing
    current_sat_profile: SATAnalysisProfile | None

    # State selection and college filtering
    selected_states: list[str] | None
    state_docs: list[Document] | None
    categorized_docs: list[Document] | None

    # Vectorstore and hybrid search
    db_vectorstore: Chroma | None
    hybrid_search_results: list[Document] | None
    final_docs: dict[str, Document] | None
    hybrid_query: str | None

    # Search state tracking
    last_query: str | None
    failed_query: str | None
    retry_search: bool | None
    last_input: str | None
    pending_query: str | None

    # Clarifying questions workflow
    wants_clarification: bool | None
    show_clarification_buttons: bool | None
    clarifying_questions: str | None
    clarifying_responses: str | None

    # Workflow completion
    search_complete: bool | None
    generate_pdf: bool | None


def create_initial_state(db_vectorstore: Chroma | None = None) -> GraphState:
    """Returns an initial clean state."""
    return {
        "messages": [],
        "expected_input": None,
        "current_sat_profile": None,
        "selected_states": None,
        "state_docs": None,
        "categorized_docs": None,
        "db_vectorstore": db_vectorstore,
        "hybrid_search_results": None,
        "final_docs": None,
        "hybrid_query": None,
        "last_query": None,
        "failed_query": None,
        "retry_search": None,
        "last_input": None,
        "pending_query": None,
        "wants_clarification": None,
        "show_clarification_buttons": None,
        "clarifying_questions": None,
        "clarifying_responses": None,
        "search_complete": None,
        "generate_pdf": None,
    }
