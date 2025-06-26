import argparse
import re
import shutil
from pathlib import Path

from chatbot.config import CONFIG
from projectutils.env import setup_project_environment
from projectutils.logger import setup_logger

# Setup project environment and logger
PROJECT_ROOT, _ = setup_project_environment()
logger = setup_logger(__file__)

# Define directory paths using config constants
ARTICLES_DIR = PROJECT_ROOT / Path(CONFIG.paths.json_articles_dir)
STRUCTURED_DOCS_DIR = PROJECT_ROOT / Path(CONFIG.paths.json_docs_dir)
RAG_DOCS_DIR = PROJECT_ROOT / Path(CONFIG.paths.markdown_dir)


def process_article_content(content: str) -> str:
    """
    Process article content to:
    1. Remove the word "Article" from the header
    2. Wrap the Document ID with triple dashes
    """
    lines = content.splitlines()
    processed_lines = []

    for _i, line in enumerate(lines):
        # Process header line to remove "Article"
        if line.startswith("# ") and " Article" in line:
            processed_line = line.replace(" Article", "")
            processed_lines.append(processed_line)
        # Process Document ID line to wrap with ---
        elif line.strip().startswith("**Document ID:**"):
            processed_lines.append(line)
            processed_lines.append("---")
        else:
            processed_lines.append(line)

    return "\n".join(processed_lines)


def combine_documents(limit: int | None = None):
    """
    Combines AI-generated articles with structured markdown documents.
    The AI-generated article content comes first, followed by a separator,
    then the content from the structured document (starting from its first H2 heading).
    """
    if RAG_DOCS_DIR.exists():
        logger.info(f"Removing existing RAG documents directory: {RAG_DOCS_DIR}")
        shutil.rmtree(RAG_DOCS_DIR)
    RAG_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created RAG documents directory: {RAG_DOCS_DIR}")

    processed_count = 0
    error_count = 0
    skipped_count = 0

    if not ARTICLES_DIR.exists():
        logger.error(f"Articles directory not found: {ARTICLES_DIR}")
        return

    if not STRUCTURED_DOCS_DIR.exists():
        logger.error(f"Structured documents directory not found: {STRUCTURED_DOCS_DIR}")
        return

    article_files = sorted(
        ARTICLES_DIR.glob("*.md")
    )  # Sort for consistent processing order
    logger.info(f"Found {len(article_files)} article files to process.")

    files_to_process = article_files
    if limit is not None:
        files_to_process = article_files[:limit]
        logger.info(f"Processing a limit of {limit} files.")

    for i, article_file_path in enumerate(files_to_process):
        base_filename = article_file_path.name
        structured_doc_file_path = STRUCTURED_DOCS_DIR / base_filename
        output_file_path = RAG_DOCS_DIR / base_filename

        logger.info(f"Processing file {i + 1}/{len(files_to_process)}: {base_filename}")

        if not structured_doc_file_path.exists():
            logger.warning(
                f"Structured document not found for {base_filename}. Skipping."
            )
            skipped_count += 1
            continue

        try:
            article_content = article_file_path.read_text(encoding="utf-8")
            structured_content = structured_doc_file_path.read_text(encoding="utf-8")

            # Process article content to remove "Article" from header and wrap Document ID
            processed_article_content = process_article_content(article_content)

            # Extract the relevant part of the structured content (from the first H2 heading)
            # This regex looks for a line starting with '## '
            match = re.search(r"^(## .*?)$", structured_content, re.MULTILINE)
            if match:
                # Get content from the start of the H2 heading line
                structured_part_to_append = structured_content[match.start() :].strip()
            else:
                logger.warning(
                    f"No H2 heading found in structured doc {base_filename}. "
                    "Attempting to strip common header."
                )
                # Fallback: try to remove known H1 and Document ID lines
                lines = structured_content.splitlines()
                content_start_index = 0
                if lines:
                    if lines[0].startswith("# "):  # Remove H1 title
                        content_start_index += 1
                    if (
                        len(lines) > content_start_index
                        and "**Document ID:**" in lines[content_start_index]
                    ):  # Remove Doc ID line
                        content_start_index += 1
                    # Remove potential blank line after ID
                    if (
                        len(lines) > content_start_index
                        and not lines[content_start_index].strip()
                    ):
                        content_start_index += 1
                structured_part_to_append = "\n".join(
                    lines[content_start_index:]
                ).strip()
                if (
                    not structured_part_to_append
                ):  # if it became empty, use original as last resort
                    logger.warning(
                        f"Fallback stripping resulted in empty content for {base_filename}, using full structured_content after separator."
                    )
                    structured_part_to_append = structured_content.strip()

            # Combine contents
            combined_content = f"{processed_article_content.strip()}\n\n---\n\n{structured_part_to_append}"

            output_file_path.write_text(combined_content, encoding="utf-8")
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing {base_filename}: {e}")
            error_count += 1

    logger.info("RAG document combination summary:")
    logger.info(f"  Successfully processed: {processed_count}")
    logger.info(f"  Skipped (missing counterpart): {skipped_count}")
    logger.info(f"  Errors: {error_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Combine AI articles and structured markdown documents into RAG-ready files."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of files to process (for testing).",
    )
    args = parser.parse_args()

    logger.info("Starting RAG document generation process...")
    combine_documents(limit=args.limit)
    logger.info("RAG document generation process finished.")


if __name__ == "__main__":
    main()
