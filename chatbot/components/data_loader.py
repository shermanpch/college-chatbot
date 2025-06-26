import asyncio
import os
import re
from pathlib import Path

from langchain.schema import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    UnstructuredMarkdownLoader,
)

from chatbot.config import CONFIG
from chatbot.utils.markdown_generator.utils import lookup_university_by_id
from chatbot.utils.metadata_extractor.core import extract_metadata_from_json
from projectutils.env import setup_project_environment
from projectutils.logger import setup_logger

# Call setup at the module level
PROJECT_ROOT, _ = setup_project_environment()

# Set up logging using the new utility
logger = setup_logger(__file__)


def extract_document_id_from_content(content: str) -> str:
    """
    Extract the Document ID from markdown content.

    Handles two cases:
    1. Direct markdown: **Document ID:** `some_id_here`
    2. UnstructuredMarkdownLoader processed: Document ID: some_id_here

    Args:
        content (str): The markdown content

    Returns:
        str: The extracted document ID, or empty string if not found
    """
    # Case 1: Direct markdown format with markdown formatting
    # Look for "**Document ID:**" followed by whitespace and backticks containing the ID
    pattern_markdown = r"\*\*Document ID:\*\*\s*`([a-zA-Z0-9_]+)`"
    match = re.search(pattern_markdown, content)

    if match:
        return match.group(1).strip()

    # Case 2: UnstructuredMarkdownLoader processed format (plain text)
    # Look for "Document ID:" followed by whitespace and then capture the ID
    pattern_processed = r"Document ID:\s*([a-zA-Z0-9_]+)"
    match = re.search(pattern_processed, content)

    if match:
        return match.group(1).strip()

    return ""


async def load_university_documents() -> list[Document]:
    """
    Asynchronously loads markdown documents from the specified directory and enriches them
    with metadata using unique Document IDs for precise matching.
    Uses UnstructuredMarkdownLoader for better markdown-aware processing.
    """
    # Load markdown files using UnstructuredMarkdownLoader
    logger.info(f"Loading markdown files from: {CONFIG.paths.markdown_dir}")

    # Create the loader but run it in executor to avoid blocking
    def _load_documents():
        loader = DirectoryLoader(
            path=CONFIG.paths.markdown_dir,
            glob="*.md",
            loader_cls=UnstructuredMarkdownLoader,
            loader_kwargs={
                "mode": "single",  # Load each file as a single document
                "strategy": "fast",  # Use fast processing strategy
            },
            show_progress=True,
            use_multithreading=True,
        )
        return loader.load()

    # Run the document loading in a thread pool
    loop = asyncio.get_event_loop()
    markdown_docs = await loop.run_in_executor(None, _load_documents)

    logger.info(
        f"Loaded {len(markdown_docs)} markdown files using UnstructuredMarkdownLoader"
    )

    # Create metadata mapping for all documents asynchronously
    metadata_mapping = await create_document_metadata_mapping()

    processed_docs: list[Document] = []
    matched_count = 0
    unmatched_count = 0

    # Process documents with periodic yields to keep event loop responsive
    for i, md_doc in enumerate(markdown_docs):
        # Extract Document ID from the markdown content
        document_id = extract_document_id_from_content(md_doc.page_content)

        if document_id and document_id in metadata_mapping:
            # Use metadata from the mapping
            metadata = metadata_mapping[document_id].copy()

            # Remove internal mapping fields that aren't needed for documents
            metadata.pop("source_file", None)
            metadata.pop("source_path", None)
            metadata.pop("status", None)

            # Merge with existing metadata (like 'source') from the loader
            md_doc.metadata.update(metadata)

            # Add the document ID to metadata for easy reference
            md_doc.metadata["document_id"] = document_id

            processed_docs.append(md_doc)
            matched_count += 1
        else:
            # No Document ID found or no metadata mapping available
            if document_id:
                logger.warning(
                    f"No metadata mapping found for Document ID: {document_id}"
                )
                md_doc.metadata["document_id"] = document_id
            else:
                filename = os.path.basename(md_doc.metadata.get("source", "unknown"))
                logger.warning(f"No Document ID found in file: {filename}")

            processed_docs.append(md_doc)
            unmatched_count += 1

        # Yield control every 50 documents to keep event loop responsive
        if i % 50 == 0:
            await asyncio.sleep(0)

    logger.info(
        f"Successfully loaded and processed {len(processed_docs)} university documents."
    )
    logger.info(f"  - Matched with metadata: {matched_count}")
    logger.info(f"  - Unmatched: {unmatched_count}")
    return processed_docs


async def create_document_metadata_mapping(output_path: str = None) -> dict:
    """
    Asynchronously create a mapping that maps document IDs to their extracted metadata.

    This function:
    1. Reads all markdown files from CONFIG.paths.markdown_dir
    2. Extracts document IDs from each file
    3. Looks up corresponding JSON records using the document ID
    4. Extracts metadata from the JSON records
    5. Creates a mapping {document_id: metadata, ...}

    Returns:
        dict: Mapping of document_id to metadata
    """
    logger.info("Creating document ID to metadata mapping...")

    markdown_dir = Path(CONFIG.paths.markdown_dir)
    if not markdown_dir.exists():
        logger.error(f"Markdown directory does not exist: {markdown_dir}")
        return {}

    mapping = {}
    processed_count = 0
    found_count = 0
    error_count = 0

    # Get all markdown files
    md_files = list(markdown_dir.glob("*.md"))

    # Process files in batches asynchronously
    batch_size = 50
    for i in range(0, len(md_files), batch_size):
        batch = md_files[i : i + batch_size]

        # Process batch of files concurrently
        tasks = []
        for md_file in batch:
            tasks.append(_process_markdown_file_async(md_file))

        # Wait for batch to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for md_file, result in zip(batch, batch_results, strict=False):
            processed_count += 1

            if isinstance(result, Exception):
                logger.error(f"Error processing {md_file}: {result}")
                error_count += 1
                # Add error entry
                error_key = f"error_{md_file.stem}"
                mapping[error_key] = {
                    "source_file": md_file.name,
                    "source_path": str(md_file),
                    "status": "processing_error",
                    "error": str(result),
                }
            else:
                document_id, extracted_meta = result
                if extracted_meta:
                    mapping[document_id] = extracted_meta
                    found_count += 1

        # Yield control after each batch
        await asyncio.sleep(0)

    # Log summary
    logger.info("Document metadata mapping created:")
    logger.info(f"  - Total files processed: {processed_count}")
    logger.info(f"  - Successfully mapped with metadata: {found_count}")
    logger.info(f"  - Files with errors: {error_count}")
    logger.info(f"  - Total entries in mapping: {len(mapping)}")

    return mapping


async def _process_markdown_file_async(md_file: Path) -> tuple[str, dict]:
    """
    Asynchronously process a single markdown file to extract metadata.

    Returns:
        tuple: (document_id, metadata_dict)
    """
    try:
        # Read file asynchronously
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None, lambda: md_file.read_text(encoding="utf-8")
        )

        # Extract document ID from content
        document_id = extract_document_id_from_content(content)

        if document_id:
            # Look up the university data using the unique ID
            # Run this in executor since it involves file I/O
            json_record = await loop.run_in_executor(
                None, lookup_university_by_id, document_id
            )

            if json_record:
                # Extract metadata from the JSON record
                extracted_meta = await loop.run_in_executor(
                    None, extract_metadata_from_json, json_record
                )

                # Add source file information
                extracted_meta["source_file"] = md_file.name
                extracted_meta["source_path"] = str(md_file)

                logger.debug(f"Processed {document_id} from {md_file.name}")
                return document_id, extracted_meta
            else:
                logger.warning(
                    f"No JSON record found for Document ID: {document_id} in {md_file.name}"
                )
                # Still add basic info even if no JSON record found
                return document_id, {
                    "source_file": md_file.name,
                    "source_path": str(md_file),
                    "status": "no_json_record_found",
                }
        else:
            logger.warning(f"No Document ID found in file: {md_file.name}")
            # Use filename as fallback key for files without document IDs
            fallback_key = f"no_id_{md_file.stem}"
            return fallback_key, {
                "source_file": md_file.name,
                "source_path": str(md_file),
                "status": "no_document_id_found",
            }

    except Exception as e:
        # Re-raise exception to be handled by the caller
        raise e
