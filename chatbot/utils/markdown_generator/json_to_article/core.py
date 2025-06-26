"""
Core article generation logic for Peterson university data.

This module contains the main functions that orchestrate the
generation of AI articles from Peterson university data.
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

from chatbot.config import CONFIG
from chatbot.utils.prompt_loader import load_prompt
from projectutils.env import setup_project_environment
from projectutils.logger import setup_logger

from ..formatters import slugify
from ..utils import generate_unique_id, load_peterson_data

load_dotenv()

# Call setup at the module level
PROJECT_ROOT, _ = setup_project_environment()

# Set up logging using the new utility
logger = setup_logger(__file__)

# Global lock for thread-safe file operations
mapping_lock = asyncio.Lock()


class AsyncArticleGenerator:
    def __init__(self, api_key=None, max_concurrent=10, max_requests_per_minute=50):
        """Initialize the AsyncArticleGenerator with OpenRouter API key and rate limiting."""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable or pass it directly."
            )

        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "College Chatbot",
        }

        # Rate limiting
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = []

    async def _wait_for_rate_limit(self):
        """Wait if approaching the rate limit."""
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]

        # If at the limit, wait until another request can be made
        if len(self.request_times) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0]) + 1  # Add 1 second buffer
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.1f} seconds...")
                await asyncio.sleep(sleep_time)
                # Clean up old requests after waiting
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < 60]

    async def generate_article(self, json_input, model=None, session=None):
        """
        Generate an article using the prompt template and JSON input.

        Args:
            json_input (dict): The JSON data about the university
            model (str): The model to use for generation (defaults to OPENROUTER_MODEL env var)
            session (aiohttp.ClientSession): Optional session to reuse

        Returns:
            str: The generated article content
        """
        # Use environment variable if model not specified
        if model is None:
            model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

        # Generate the prompt using centralized prompt loader
        template_path = (
            "chatbot/utils/markdown_generator/json_to_article/prompt_template.md"
        )
        formatted_prompt = load_prompt(template_path, {"json_input": json_input})

        # Prepare the API request
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "temperature": 0.7,
        }

        async with self.semaphore:
            await self._wait_for_rate_limit()
            self.request_times.append(time.time())

            # Use provided session or create a new one
            if session:
                return await self._make_request(session, payload, model)
            else:
                async with aiohttp.ClientSession() as new_session:
                    return await self._make_request(new_session, payload, model)

    async def _make_request(self, session, payload, model):
        """Make the actual API request with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Sending request to OpenRouter API with model: {model} (attempt {attempt + 1})"
                )
                async with session.post(
                    self.base_url, headers=self.headers, json=payload
                ) as response:
                    if response.status == 429:  # Rate limit exceeded
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"Rate limit exceeded, waiting {wait_time} seconds before retry..."
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    result = await response.json()
                    article_content = result["choices"][0]["message"]["content"]
                    logger.debug("Article generated successfully")
                    return article_content

            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"API request failed after {max_retries} attempts: {e}"
                    )
                    raise Exception(f"API request failed: {e}") from e
                else:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
            except KeyError as e:
                logger.error(f"Unexpected API response format: {e}")
                raise Exception(f"Unexpected API response format: {e}") from e

        raise Exception("Max retries exceeded")


async def update_mapping_file(mapping_file, unique_id, mapping_entry):
    """Thread-safe update of the id_mapping.json file."""
    async with mapping_lock:
        try:
            # Read existing mapping
            if mapping_file.exists():
                with open(mapping_file, encoding="utf-8") as f:
                    id_mapping = json.load(f)
            else:
                id_mapping = {}

            # Add new entry
            id_mapping[unique_id] = mapping_entry

            # Write back to file
            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump(id_mapping, f, indent=2, ensure_ascii=False)

            logger.debug(
                f"Updated mapping file with entry for {mapping_entry.get('university_name', unique_id)}"
            )

        except Exception as e:
            logger.error(f"Failed to update mapping file for {unique_id}: {e}")


async def process_university_async(
    generator,
    session,
    uni_data,
    index,
    output_dir,
    existing_mapping,
    skip_existing,
    mapping_file,
):
    """Process a single university asynchronously."""
    try:
        university_name = uni_data.get("university_name", "N/A")

        # Generate unique identifier (same as json_to_markdown)
        unique_id = generate_unique_id(uni_data, index=index)

        # Check if this university already has an article
        if skip_existing and unique_id in existing_mapping:
            # Verify the file still exists
            existing_filename = existing_mapping[unique_id]["filename"]
            existing_filepath = output_dir / existing_filename

            if existing_filepath.exists():
                logger.info(
                    f"Skipping {university_name} - article already exists ({existing_filename})"
                )

                # Ensure skipped university is in mapping file
                existing_entry = existing_mapping.get(unique_id, {})
                mapping_entry = {
                    "university_name": university_name,
                    "filename": existing_entry.get("filename", existing_filename),
                    "json_index": index,
                    "slug": slugify(university_name),
                }
                await update_mapping_file(mapping_file, unique_id, mapping_entry)

                return {
                    "status": "skipped",
                    "unique_id": unique_id,
                    "university_name": university_name,
                    "index": index,
                }
            else:
                logger.info(
                    f"Article file missing for {university_name}, regenerating..."
                )

        logger.info(f"Generating article for {university_name} ({index + 1})")

        # Generate filename with document ID appended
        filename = slugify(university_name) + f"_{unique_id}.md"
        filepath = output_dir / filename

        # Generate article content using AI
        article_content = await generator.generate_article(uni_data, session=session)

        # Create markdown content with document ID header
        markdown_content = []
        markdown_content.append(f"# {university_name} Article")
        markdown_content.append("")
        markdown_content.append(f"**Document ID:** `{unique_id}`")
        markdown_content.append("")
        markdown_content.append(article_content)

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(markdown_content))

        logger.info(f"Successfully generated article for {university_name}")

        # Update mapping file immediately
        mapping_entry = {
            "university_name": university_name,
            "filename": filename,
            "json_index": index,
            "slug": slugify(university_name),
        }
        await update_mapping_file(mapping_file, unique_id, mapping_entry)

        return {
            "status": "success",
            "unique_id": unique_id,
            "university_name": university_name,
            "filename": filename,
            "index": index,
            "slug": slugify(university_name),
        }

    except Exception as e:
        logger.error(f"Failed to generate article for {university_name}: {e}")
        try:
            unique_id = generate_unique_id(uni_data, index=index)
        except Exception:
            unique_id = f"failed_{index}"

        return {
            "status": "failed",
            "unique_id": unique_id,
            "university_name": university_name,
            "index": index,
            "error": str(e),
        }


async def convert_to_articles_async(
    limit=None,
    refresh=False,
    max_concurrent=30,
    max_requests_per_minute=200,
):
    """Convert Peterson university data to individual articles using async processing.

    Args:
        limit (int, optional): Maximum number of articles to generate. If None, generates all.
        refresh (bool): If True, regenerate all articles including existing ones. If False, skip existing articles.
        max_concurrent (int): Maximum number of concurrent requests.
        max_requests_per_minute (int): Maximum requests per minute to respect rate limits.
    """
    start_time = time.time()
    logger.info("Starting Peterson data to articles conversion (ASYNC)...")

    if limit:
        logger.info(f"Limited mode: Generating only {limit} articles")

    if refresh:
        logger.info(
            "Refresh mode: Will regenerate all articles including existing ones"
        )
    else:
        logger.info("Skip existing mode: Will skip universities with existing articles")

    # Define file paths using config constants
    input_file = PROJECT_ROOT / Path(CONFIG.paths.input_json)
    output_dir = PROJECT_ROOT / Path(CONFIG.paths.json_articles_dir)
    mapping_file = output_dir / "id_mapping.json"

    # Validate input file exists
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    # Handle output directory based on refresh flag
    existing_mapping = {}
    if not refresh and output_dir.exists() and mapping_file.exists():
        # Load existing mapping to check which articles already exist
        try:
            with open(mapping_file, encoding="utf-8") as f:
                existing_mapping = json.load(f)
            logger.info(f"Loaded existing mapping with {len(existing_mapping)} entries")
        except Exception as e:
            logger.warning(f"Could not load existing mapping file: {e}")
            existing_mapping = {}
    elif refresh:
        # Clear and recreate output directory (original behavior)
        if output_dir.exists():
            logger.info(f"Clearing existing output directory: {output_dir}")
            shutil.rmtree(output_dir)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    if refresh:
        logger.info(f"Created fresh output directory: {output_dir}")
    else:
        logger.info(f"Using existing output directory: {output_dir}")

    # Load university data
    universities = load_peterson_data(input_file)

    # Limit the number of universities if specified
    if limit and limit < len(universities):
        universities = universities[:limit]
        logger.info(f"Limited to first {limit} universities")

    # Initialize article generator
    try:
        generator = AsyncArticleGenerator(
            max_concurrent=max_concurrent,
            max_requests_per_minute=max_requests_per_minute,
        )
    except ValueError as e:
        logger.error(f"Error: {e}")
        logger.error("Please set your OpenRouter API key as an environment variable:")
        logger.error("export OPENROUTER_API_KEY='your-api-key-here'")
        sys.exit(1)

    # Process universities concurrently
    logger.info(
        f"Processing {len(universities)} universities with max {max_concurrent} concurrent requests..."
    )

    async with aiohttp.ClientSession() as session:
        # Create tasks for all universities
        tasks = [
            process_university_async(
                generator,
                session,
                uni_data,
                i,
                output_dir,
                existing_mapping,
                not refresh,  # skip_existing = not refresh
                mapping_file,
            )
            for i, uni_data in enumerate(universities)
        ]

        # Process tasks in batches to avoid overwhelming the system
        batch_size = max_concurrent * 2  # Process in batches
        results = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            logger.info(
                f"Processing batch {i // batch_size + 1}/{(len(tasks) + batch_size - 1) // batch_size} ({len(batch)} universities)"
            )
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)

            # Progress update
            completed = min(i + batch_size, len(tasks))
            elapsed = time.time() - start_time
            logger.info(
                f"Completed {completed}/{len(tasks)} universities in {elapsed:.1f}s"
            )

    # Process results for statistics (mapping is updated in real-time)
    successful_conversions = 0
    failed_conversions = 0
    skipped_conversions = 0

    logger.info(f"Processing {len(results)} results for statistics...")

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task failed with exception: {result}")
            failed_conversions += 1
        elif result["status"] == "success":
            successful_conversions += 1
        elif result["status"] == "skipped":
            skipped_conversions += 1
        elif result["status"] == "failed":
            failed_conversions += 1

    # Read final mapping file to get accurate count
    try:
        if mapping_file.exists():
            with open(mapping_file, encoding="utf-8") as f:
                final_mapping = json.load(f)
            logger.info(
                f"Final mapping file contains {len(final_mapping)} entries: {mapping_file}"
            )
        else:
            logger.warning(f"Mapping file not found: {mapping_file}")
    except Exception as e:
        logger.error(f"Failed to read final mapping file: {e}")
        logger.error(f"Mapping file path: {mapping_file}")
        logger.error(f"Output directory exists: {output_dir.exists()}")
        logger.error(
            f"Output directory permissions: {oct(output_dir.stat().st_mode)[-3:] if output_dir.exists() else 'N/A'}"
        )

    # Log summary
    total_time = time.time() - start_time
    logger.info("Article generation complete!")
    logger.info("Summary:")
    logger.info(f"  Total universities processed: {len(universities)}")
    logger.info(f"  Successfully generated: {successful_conversions}")
    logger.info(f"  Failed generations: {failed_conversions}")
    if not refresh:
        logger.info(f"  Skipped (already exist): {skipped_conversions}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Article mapping file: {mapping_file}")
    logger.info(
        f"  Total time: {total_time:.1f} seconds ({total_time / 60:.1f} minutes)"
    )
    if successful_conversions > 0:
        logger.info(
            f"  Average time per article: {total_time / successful_conversions:.1f} seconds"
        )

    if limit:
        logger.info(f"  Limited mode: Generated {limit} articles")


def convert_to_articles(limit=None, refresh=False):
    """Synchronous wrapper for async article conversion."""
    return asyncio.run(convert_to_articles_async(limit, refresh))


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate AI articles from Peterson university data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        python -m chatbot.utils.markdown_generator.json_to_articles                    # Generate all articles
        python -m chatbot.utils.markdown_generator.json_to_articles --limit 5         # Generate 5 articles
        python -m chatbot.utils.markdown_generator.json_to_articles --model openai/gpt-4o  # Use specific model
        python -m chatbot.utils.markdown_generator.json_to_articles --refresh         # Regenerate all articles (default: skip existing)
        python -m chatbot.utils.markdown_generator.json_to_articles --max-concurrent 20 --max-requests-per-minute 100  # High throughput
        """,
    )

    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Maximum number of articles to generate",
    )

    parser.add_argument(
        "--model",
        type=str,
        metavar="MODEL",
        help="OpenRouter model to use (e.g., 'openai/gpt-4o-mini', 'anthropic/claude-3-haiku')",
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Regenerate all articles, including existing ones (default: skip existing)",
    )

    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=30,
        metavar="N",
        help="Maximum number of concurrent requests (default: 30)",
    )

    parser.add_argument(
        "--max-requests-per-minute",
        type=int,
        default=200,
        metavar="N",
        help="Maximum requests per minute to respect rate limits (default: 200)",
    )

    return parser.parse_args()


def main():
    """Main function to orchestrate the Peterson data to articles conversion"""
    args = parse_args()

    # Set model if specified, otherwise use environment variable
    if args.model:
        os.environ["OPENROUTER_MODEL"] = args.model
        logger.info(f"Using model from CLI argument: {args.model}")
    else:
        # Show which model will be used from environment or default
        model_to_use = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        if "OPENROUTER_MODEL" in os.environ:
            logger.info(
                f"Using model from OPENROUTER_MODEL environment variable: {model_to_use}"
            )
        else:
            logger.info(
                f"Using default model (OPENROUTER_MODEL not set): {model_to_use}"
            )

    logger.info("Peterson Data to Articles Converter - Starting...")

    if args.limit:
        logger.info(f"Running in limited mode: generating {args.limit} articles")
    else:
        logger.info("Running in full mode: generating all articles")

    asyncio.run(
        convert_to_articles_async(
            limit=args.limit,
            refresh=args.refresh,
            max_concurrent=args.max_concurrent,
            max_requests_per_minute=args.max_requests_per_minute,
        )
    )

    logger.info("Peterson Data to Articles Converter - Complete!")


if __name__ == "__main__":
    main()
