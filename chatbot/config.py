import os
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Environment                                                                  #
# --------------------------------------------------------------------------- #

# Disable ChromaDB telemetry globally
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Disable HuggingFace tokenizers parallelism to avoid fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "False"

# --------------------------------------------------------------------------- #
# Configuration                                                                #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Paths:
    """Filesystem locations used throughout the project."""

    input_json: str = "data/chatbot/peterson_data.json"
    markdown_dir: str = "data/chatbot/peterson_rag_documents"
    json_articles_dir: str = "data/chatbot/peterson_json_articles"
    json_docs_dir: str = "data/chatbot/peterson_json_docs"


@dataclass(frozen=True)
class ChromaSettings:
    """Persistent‑vector‑store configuration."""

    persist_dir: str = "data/chroma-peterson"
    collection_name: str = "peterson"


@dataclass(frozen=True)
class ModelSettings:
    """Embedding model configuration."""

    embedding_model: str = "all-MiniLM-L6-v2"


# --------------------------------------------------------------------------- #
# Aggregated config access                                                     #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AppConfig:
    paths: Paths = Paths()
    chroma: ChromaSettings = ChromaSettings()
    model: ModelSettings = ModelSettings()


CONFIG = AppConfig()
