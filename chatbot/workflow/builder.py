from langgraph.graph import END, StateGraph

from .node_admission_risk import categorize_colleges_node, summarise_admission_node
from .node_clarifying_questions import ask_clarifying_questions_node
from .node_completion import workflow_completion_node
from .node_metadata_state import (
    ask_additional_states_node,
    ask_states_node,
    process_states_node,
)
from .node_reranking import rerank_colleges_node
from .node_sat import ask_manual_sat_node, process_manual_sat_input_node
from .node_search import (
    ask_hybrid_search_query_node,
    ask_more_criteria_node,
    intersect_and_final_count_node,
    perform_hybrid_search_node,
)
from .node_visualisation import generate_visualisations_node
from .routers import (
    main_dispatcher_node,
    route_after_admission_category_summary,
    route_after_clarifying_questions,
    route_after_intersection_count,
    route_after_manual_sat_processing,
    route_after_state_processing,
)
from .state import GraphState

# Create the workflow
main_workflow = StateGraph(GraphState)

# === WORKFLOW NODE DEFINITIONS ===
# Add all nodes organized by workflow phase

# Phase 1: SAT Setup (simplified)
main_workflow.add_node("ask_manual_sat", ask_manual_sat_node)
main_workflow.add_node("process_manual_sat", process_manual_sat_input_node)

# Phase 2: State Selection & College Filtering
main_workflow.add_node("ask_states_node", ask_states_node)
main_workflow.add_node("ask_additional_states_node", ask_additional_states_node)
main_workflow.add_node("process_states_node", process_states_node)
main_workflow.add_node("categorize_colleges_node", categorize_colleges_node)
main_workflow.add_node("summarise_admission_node", summarise_admission_node)

# Phase 3: Hybrid Search & Refinement
main_workflow.add_node("ask_hybrid_search_query", ask_hybrid_search_query_node)
main_workflow.add_node("ask_more_criteria_node", ask_more_criteria_node)
main_workflow.add_node("perform_hybrid_search", perform_hybrid_search_node)
main_workflow.add_node("intersect_and_final_count", intersect_and_final_count_node)

# Phase 4: Visualization & Completion
main_workflow.add_node("generate_visualisation", generate_visualisations_node)
main_workflow.add_node("ask_clarifying_questions", ask_clarifying_questions_node)
main_workflow.add_node("node_reranking", rerank_colleges_node)
main_workflow.add_node("workflow_completion", workflow_completion_node)

# === WORKFLOW ENTRY POINT ===
# Use main_dispatcher_node as the central routing hub
main_workflow.set_conditional_entry_point(main_dispatcher_node)

# === WORKFLOW EDGE DEFINITIONS ===
# Edges organized by workflow phase and routing logic

# SAT Setup Phase Routing

main_workflow.add_conditional_edges(
    "process_states_node",
    route_after_state_processing,
    {
        "ask_additional_states_node": "ask_additional_states_node",
        "categorize_colleges_node": "categorize_colleges_node",
        END: END,
    },
)

main_workflow.add_edge("ask_manual_sat", END)
main_workflow.add_conditional_edges(
    "process_manual_sat",
    route_after_manual_sat_processing,
    {
        "ask_states_node": "ask_states_node",
        "ask_manual_sat": "ask_manual_sat",
    },
)
main_workflow.add_edge("ask_states_node", END)
main_workflow.add_edge("ask_additional_states_node", END)

main_workflow.add_edge("categorize_colleges_node", "summarise_admission_node")

main_workflow.add_conditional_edges(
    "summarise_admission_node",
    route_after_admission_category_summary,
    {
        "ask_states_node": "ask_states_node",
        "ask_hybrid_search_query": "ask_hybrid_search_query",
        "generate_visualisation": "generate_visualisation",
        END: END,
    },
)

main_workflow.add_edge("ask_hybrid_search_query", END)
main_workflow.add_edge("perform_hybrid_search", "intersect_and_final_count")

main_workflow.add_conditional_edges(
    "intersect_and_final_count",
    route_after_intersection_count,
    {
        "ask_hybrid_search_query_node": "ask_hybrid_search_query",
        "ask_more_criteria_node": "ask_more_criteria_node",
        "generate_visualisation": "generate_visualisation",
        END: END,
    },
)

main_workflow.add_edge("ask_more_criteria_node", END)
main_workflow.add_edge("generate_visualisation", "ask_clarifying_questions")

main_workflow.add_conditional_edges(
    "ask_clarifying_questions",
    route_after_clarifying_questions,
    {
        "node_reranking": "node_reranking",
        "workflow_completion": "workflow_completion",
        END: END,
    },
)

main_workflow.add_edge("node_reranking", "workflow_completion")
main_workflow.add_edge("workflow_completion", END)

# Compile the graph
main_workflow_app = main_workflow.compile()
