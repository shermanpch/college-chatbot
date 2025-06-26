import asyncio
import os
import platform
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chatbot.components.data_loader import load_university_documents
from chatbot.config import CONFIG
from projectutils.env import setup_project_environment
from projectutils.logger import setup_logger

# Call setup at the module level
PROJECT_ROOT, _ = setup_project_environment()

# Set up logging using the new utility
logger = setup_logger(__file__)

# Add global lock for vectorstore operations
_vectorstore_creation_lock = asyncio.Lock()


def _set_path_permissions(path: Path, is_directory: bool = True) -> None:
    """
    Set permissions for a path in a cross-platform way.

    Args:
        path: Path to set permissions for
        is_directory: Whether the path is a directory
    """
    try:
        # Skip chmod on Windows
        if platform.system() == "Windows":
            return

        # Set Unix permissions
        if is_directory:
            path.chmod(0o755)
        else:
            path.chmod(0o644)
    except Exception as e:
        logger.warning(f"Could not set permissions for {path}: {e}")


def _fix_directory_permissions(directory_path: Path) -> None:
    """
    Fix permissions for ChromaDB directory and its contents.
    Cross-platform compatible - handles both Unix and Windows systems.

    Args:
        directory_path: Path to the directory to fix permissions for
    """
    try:
        # Check for Windows OS
        is_windows = platform.system() == "Windows"

        if is_windows:
            # On Windows, skip chmod operations as the directory is accessible by default
            # Windows handles permissions differently through ACLs
            logger.info(
                f"Windows detected - skipping chmod operations for {directory_path}"
            )
            return

        # Unix/Linux/macOS permission handling
        directory_path.chmod(0o755)

        # Fix permissions for all files and subdirectories
        for item in directory_path.rglob("*"):
            if item.is_dir():
                item.chmod(0o755)
            else:
                item.chmod(0o644)

        logger.info(f"Fixed permissions for {directory_path}")
    except Exception as e:
        logger.warning(f"Could not fix permissions for {directory_path}: {e}")
        # Don't raise the exception - permission issues shouldn't break the app


async def get_vectorstore(
    force_recreate: bool = False,
    try_create_from_source_if_missing: bool = False,
) -> Chroma:
    """
    Asynchronously initializes or loads a ChromaDB vector store.

    Args:
        force_recreate: If True, delete existing vectorstore and create new one from source
        try_create_from_source_if_missing: If True and DB doesn't exist, create from data_loader

    Returns:
        Chroma vectorstore instance

    Raises:
        ValueError: If vectorstore doesn't exist and creation from source not requested or fails
    """

    # Use lock to prevent concurrent vectorstore operations
    async with _vectorstore_creation_lock:
        # Initialize Sentence Transformers embeddings
        def _create_embeddings():
            return HuggingFaceEmbeddings(
                model_name=CONFIG.model.embedding_model,
                model_kwargs={"device": "cpu"},  # Use 'cuda' if you have GPU available
                encode_kwargs={"normalize_embeddings": True},
            )

        # Run embeddings creation in executor (it may download models)
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, _create_embeddings)

        # Ensure the persist directory exists with proper permissions
        persist_path = Path(CONFIG.chroma.persist_dir)
        if not persist_path.exists():
            try:
                persist_path.mkdir(parents=True, exist_ok=True)
                # Set proper permissions (cross-platform compatible)
                _set_path_permissions(persist_path, is_directory=True)
                logger.info(f"Created ChromaDB directory: {CONFIG.chroma.persist_dir}")
            except Exception as e:
                logger.error(f"Failed to create ChromaDB directory: {e}")
                raise

        # Check if DB needs to be recreated or if it exists
        # A ChromaDB exists if the directory exists AND contains actual database files
        # ChromaDB creates a chroma.sqlite3 file and UUID-named directories
        db_exists = False
        if os.path.exists(CONFIG.chroma.persist_dir):
            files = os.listdir(CONFIG.chroma.persist_dir)
            has_sqlite = "chroma.sqlite3" in files
            # Check for UUID directories (ChromaDB collection directories)
            has_collections = any(
                os.path.isdir(os.path.join(CONFIG.chroma.persist_dir, f))
                and len(f) == 36  # UUID length
                and f.count("-") == 4  # UUID format has 4 hyphens
                for f in files
            )
            db_exists = has_sqlite and has_collections

        # Fix permissions if directory exists but has permission issues
        if db_exists:
            try:
                # Try to fix permissions on the directory and its contents
                _fix_directory_permissions(persist_path)
            except Exception as e:
                logger.warning(
                    f"Could not fix permissions for {CONFIG.chroma.persist_dir}: {e}"
                )

        if force_recreate and db_exists:
            # Delete existing database directory to recreate
            logger.info(
                f"Force recreating DB: Removing existing directory {CONFIG.chroma.persist_dir}"
            )
            await loop.run_in_executor(None, shutil.rmtree, CONFIG.chroma.persist_dir)
            db_exists = False  # Update db_exists status

        if db_exists:
            # Load existing vectorstore
            logger.info(
                f"Loading existing ChromaDB vector store from {CONFIG.chroma.persist_dir}."
            )

            def _load_vectorstore():
                return Chroma(
                    persist_directory=CONFIG.chroma.persist_dir,
                    embedding_function=embeddings,
                    collection_name=CONFIG.chroma.collection_name,
                )

            vectorstore = await loop.run_in_executor(None, _load_vectorstore)
            return vectorstore
        else:  # DB does not exist
            if try_create_from_source_if_missing:
                logger.info(
                    f"Attempting to create new vectorstore from source as it's missing at {CONFIG.chroma.persist_dir}..."
                )
                try:
                    docs = await load_university_documents()
                    if not docs:
                        logger.warning(
                            "No documents loaded from source. Cannot create vectorstore."
                        )
                        raise ValueError(
                            "No documents loaded from data_loader, cannot create vectorstore."
                        )

                    logger.info(
                        f"Creating new ChromaDB vector store with {len(docs)} documents."
                    )

                    def _create_vectorstore():
                        return Chroma.from_documents(
                            documents=docs,
                            embedding=embeddings,
                            persist_directory=CONFIG.chroma.persist_dir,
                            collection_name=CONFIG.chroma.collection_name,
                        )

                    vectorstore = await loop.run_in_executor(None, _create_vectorstore)
                    logger.info("New vector store created and persisted from source.")
                    return vectorstore
                except ImportError as import_err:
                    logger.error(
                        "data_loader not found, cannot create vectorstore from source."
                    )
                    raise ValueError(
                        "data_loader not available for vectorstore creation."
                    ) from import_err
                except Exception as e:
                    logger.error(f"Failed to create new vectorstore from source: {e}")
                    raise ValueError(
                        f"Failed to create vectorstore from source: {str(e)}"
                    ) from e
            else:
                logger.error(
                    "Vectorstore does not exist and creation from source not requested."
                )
                raise ValueError(
                    "ChromaDB not found and creation from source not specified."
                )


def get_vectorstore_path() -> Path:
    """Return the absolute path where the Chroma store is persisted."""
    return PROJECT_ROOT / Path(CONFIG.chroma.persist_dir)


def get_vectorstore_stats(vectorstore: Chroma) -> dict:
    """
    Get basic statistics about the vector store.

    Args:
        vectorstore: The Chroma vector store instance.

    Returns:
        dict: Statistics about the vector store
    """
    try:
        # Get the collection
        collection = vectorstore._collection

        # Get count of documents
        count = collection.count()

        stats = {
            "document_count": count,
            "collection_name": CONFIG.chroma.collection_name,
            "persist_directory": CONFIG.chroma.persist_dir,
            "embedding_model": CONFIG.model.embedding_model,
        }

        return stats
    except Exception as e:
        return {"error": f"Failed to get stats: {e}"}
