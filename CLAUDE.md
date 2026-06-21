# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered college admissions chatbot built with **Chainlit** (conversational UI) and **LangGraph** (state machine workflow). Users enter SAT scores and state preferences, then the system filters 1,500+ colleges from a ChromaDB vector store through a multi-phase workflow: SAT input → geographic filtering → admission risk categorization → hybrid semantic search → visualization → optional clarification/reranking → PDF report generation.

## Commands

```bash
# Install (editable with dev tools)
pip install -e ".[dev]"

# Run the app
chainlit run chatbot/app.py

# Lint & format
ruff check .
ruff format .

# Pre-commit hooks
pre-commit install
pre-commit run --all-files

# Docker Compose (production with Cloudflare Tunnel)
docker compose up -d --build

# Docker Compose (local dev, app only)
docker compose up -d --build app
```

## Architecture

### Core Packages

- `chatbot/` — Main application package
- `projectutils/` — Environment setup (`env.py`) and logging config (`logger.py`)

### Entry Point

`chatbot/app.py` — Chainlit app. Initializes the global ChromaDB vectorstore (with async locks), manages user sessions, and invokes the LangGraph workflow on each message.

### LangGraph Workflow (`chatbot/workflow/`)

The workflow is a compiled `StateGraph` defined in `builder.py` with state in `state.py` (`GraphState` TypedDict). Nodes are individual async functions; routing between nodes is handled by conditional edge functions in `routers.py`.

**Workflow phases (in order):**

1. **SAT Input** (`node_sat.py`) — Collect and validate SAT score (400–1600)
2. **State Selection** (`node_metadata_state.py`) — Filter colleges by US states
3. **Admission Risk** (`node_admission_risk.py`) — Categorize into Safety/Target/Reach
4. **Hybrid Search** (`node_search.py`) — Semantic + keyword search with iterative refinement
5. **Visualization** (`node_visualisation.py`) — Generate charts via Plotly
6. **Clarification & Reranking** (`node_clarifying_questions.py`, `node_reranking.py`) — Optional personalization
7. **Completion** (`node_completion.py`) — PDF report generation

The entry point is `main_dispatcher_node` (conditional entry point) which routes to the correct node based on `expected_input` in the state.

### Components (`chatbot/components/`)

Reusable modules: `vectorstore.py` (ChromaDB init), `retriever.py` (hybrid search), `college_utils.py` (data helpers), `college_reranker.py`, `pdf_generator.py` (ReportLab PDF creation), `feature_analyzer.py`, `suggestion_generator.py`, `clarification_generator.py`, `attributes.py` (SelfQueryRetriever metadata field definitions), `data_loader.py` (university document loading).

### Prompts (`chatbot/prompts/`)

LLM prompt templates as markdown files. Component modules (`retriever.py`, `college_reranker.py`, `suggestion_generator.py`, `clarification_generator.py`) load them via `load_prompt` in `chatbot/utils/prompt_loader.py`. Workflow nodes call these components rather than loading prompts directly.

### Data (`data/`)

- `data/chatbot/peterson_data.json` — 31MB raw college dataset (1,500+ colleges)
- `data/chatbot/peterson_rag_documents/` — 1,526 markdown files used for vectorization
- `data/chroma-peterson/` — Persistent ChromaDB vector store (embedding model: `all-MiniLM-L6-v2`)
- `data/scripts/` — Data collection/processing scripts

## Key Technical Details

- **LLM access**: OpenRouter API (`OPENROUTER_API_KEY`) — supports swapping models via env vars
- **Vector DB**: ChromaDB with `all-MiniLM-L6-v2` sentence-transformer embeddings
- **Python**: 3.10+ required; async/await throughout
- **Linting**: Ruff (line-length 88, double quotes, isort, bugbear, comprehensions, pyupgrade)
- **Environment**: Copy `.env.example` to `.env`; minimum required: `OPENROUTER_API_KEY` and `OPENROUTER_SELF_RETRIEVAL_MODEL`
