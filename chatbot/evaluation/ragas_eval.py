import argparse
import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

from chatbot.components.retriever import create_self_query_retriever
from chatbot.components.vectorstore import get_vectorstore
from chatbot.evaluation.test_questions import test_questions
from projectutils.env import setup_project_environment
from projectutils.logger import setup_logger

# Setup environment (sets project root, ensures logs dir)
PROJECT_ROOT, LOGS_DIR = setup_project_environment()

load_dotenv()
logger = setup_logger(__file__)


def generate_datetime_output_path(base_path: str = "chatbot/evaluation/results") -> str:
    """
    Generate an output file path with datetime suffix in the filename.

    Args:
        base_path: Base directory path for results

    Returns:
        Full path with datetime suffix in the filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(base_path, f"ragas_evaluation_result_{timestamp}.json")
    return output_file


def extract_attribute_names(attributes_used: list[str]) -> set[str]:
    """
    Extract attribute names from the attributes_used list.

    Args:
        attributes_used: List of attribute expressions like "state == 'Massachusetts'"

    Returns:
        Set of attribute names like {'state', 'accept_rate', 'sat_math_75'}
    """
    attribute_names = set()

    for attr_expr in attributes_used:
        # Handle complex expressions with OR/AND
        if " OR " in attr_expr or " AND " in attr_expr:
            # Extract individual comparisons from complex expressions
            # Remove parentheses and split by OR/AND
            cleaned = attr_expr.replace("(", "").replace(")", "")
            parts = re.split(r"\s+(?:OR|AND)\s+", cleaned)
            for part in parts:
                attr_name = extract_single_attribute_name(part.strip())
                if attr_name:
                    attribute_names.add(attr_name)
        else:
            attr_name = extract_single_attribute_name(attr_expr)
            if attr_name:
                attribute_names.add(attr_name)

    return attribute_names


def extract_single_attribute_name(attr_expr: str) -> str:
    """
    Extract attribute name from a single attribute expression.

    Args:
        attr_expr: Single attribute expression like "state == 'Massachusetts'"

    Returns:
        Attribute name like 'state'
    """
    # Match patterns like: attribute_name operator value
    patterns = [
        r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*[<>=!]+",  # attribute_name >= value
        r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*==\s*null",  # attribute_name == null
        r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*!=",  # attribute_name != value
    ]

    for pattern in patterns:
        match = re.match(pattern, attr_expr.strip())
        if match:
            return match.group(1)

    return ""


def extract_metadata_filter_attributes(metadata_filter_str: str) -> set[str]:
    """
    Extract attribute names from the metadata filter string.

    Args:
        metadata_filter_str: String representation of the metadata filter

    Returns:
        Set of attribute names used in the filter
    """
    attribute_names = set()

    # Extract attribute names from patterns like "attribute='state', value='Minnesota'"
    attr_pattern = r"attribute='([^']+)'"
    matches = re.findall(attr_pattern, metadata_filter_str)

    for match in matches:
        attribute_names.add(match)

    return attribute_names


async def evaluate_document_retrieval(
    questions_to_test: list[int] = None,
    k: int = 12,
) -> dict[str, Any]:
    """
    Evaluate document retrieval performance using test questions.

    Args:
        questions_to_test: List of question indices to test (1-based). If None, tests all questions.
        k: Number of documents to retrieve per query

    Returns:
        Dictionary containing evaluation results and output file path
    """
    # Generate datetime-suffixed output path
    output_file = generate_datetime_output_path()

    logger.info("Starting document retrieval evaluation...")

    # Load vectorstore and create retriever
    logger.info("Loading vectorstore...")
    # Use the current get_vectorstore function with proper parameters
    vectorstore = await get_vectorstore(
        force_recreate=False,
        try_create_from_source_if_missing=True,
    )

    # Determine which questions to test
    if questions_to_test is None:
        questions_to_test = list(range(1, len(test_questions) + 1))

    logger.info(f"Testing {len(questions_to_test)} questions with k={k}")

    eval_results = []
    hit_count = 0
    total_questions = len(questions_to_test)

    for question_idx in questions_to_test:
        logger.info(f"Processing question {question_idx}...")

        # Get the test question (convert to 0-based index)
        test_question = test_questions.get_question_by_index(question_idx)
        if not test_question:
            logger.warning(f"Question {question_idx} not found, skipping...")
            continue

        try:
            # Create a fresh retriever for each question to avoid context bleeding
            retriever = create_self_query_retriever(vectorstore, k=k)

            # Retrieve documents using the self-query retriever
            retrieved_docs = retriever.invoke(test_question.question)

            # Extract university names from retrieved documents
            retrieved_targets = []
            for doc in retrieved_docs:
                university_name = doc.metadata.get("university_name", "")
                if university_name:
                    retrieved_targets.append(university_name)

            # Extract attributes from test question
            expected_attributes = extract_attribute_names(test_question.attributes_used)

            # Get the structured query that was generated
            structured_query = retriever.query_constructor.invoke(
                {"query": test_question.question}
            )

            # Extract attributes from the generated filter
            retrieved_attributes = set()
            search_query = ""
            metadata_filter_str = ""

            if hasattr(structured_query, "query") and structured_query.query:
                search_query = structured_query.query

            if hasattr(structured_query, "filter") and structured_query.filter:
                metadata_filter_str = str(structured_query.filter)
                retrieved_attributes = extract_metadata_filter_attributes(
                    metadata_filter_str
                )

            # Calculate attribute differences
            missing_attributes = list(expected_attributes - retrieved_attributes)
            extra_attributes = list(retrieved_attributes - expected_attributes)

            # Check if any expected targets were retrieved (hit)
            expected_targets_set = set(test_question.expected_targets)
            retrieved_targets_set = set(retrieved_targets)
            hit = bool(expected_targets_set.intersection(retrieved_targets_set))

            if hit:
                hit_count += 1

            # Create evaluation result
            eval_result = {
                "question_id": question_idx,
                "question": test_question.question,
                "targets": test_question.expected_targets,
                "attributes": list(expected_attributes),
                "retrieved_targets": retrieved_targets,
                "retrieved_attributes": list(retrieved_attributes),
                "missing_attributes": missing_attributes,
                "extra_attributes": extra_attributes,
                "search_query": search_query,
                "metadata_filter": metadata_filter_str,
                "hit": hit,
            }

            eval_results.append(eval_result)

            logger.info(
                f"Question {question_idx}: {'HIT' if hit else 'MISS'} - Retrieved {len(retrieved_targets)} universities"
            )

        except Exception as e:
            logger.error(f"Error processing question {question_idx}: {e}")
            # Add error result
            eval_result = {
                "question_id": question_idx,
                "question": test_question.question,
                "targets": test_question.expected_targets,
                "attributes": list(
                    extract_attribute_names(test_question.attributes_used)
                ),
                "retrieved_targets": [],
                "retrieved_attributes": [],
                "missing_attributes": [],
                "extra_attributes": [],
                "search_query": "",
                "metadata_filter": "",
                "hit": False,
            }
            eval_results.append(eval_result)

    # Calculate overall metrics
    hit_rate = hit_count / total_questions if total_questions > 0 else 0.0

    # Create final results structure
    results = {
        "metadata": {
            "Ragas model": os.getenv("OPENROUTER_RAGAS_MODEL", "openai/gpt-4o-mini"),
            "evaluation_timestamp": datetime.now().isoformat(),
            "output_file": output_file,
            "total_questions": total_questions,
            "questions_tested": questions_to_test,
            "k_documents_retrieved": k,
            "hit_rate": hit_rate,
        },
        "eval_results": eval_results,
    }

    # Save results to file
    logger.info(f"Saving results to {output_file}")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Evaluation complete! Hit rate: {hit_rate:.2%} ({hit_count}/{total_questions})"
    )

    return results


async def main():
    """Main function to run the evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate document retrieval performance"
    )
    parser.add_argument(
        "--questions",
        type=int,
        nargs="+",
        help="Specific question indices to test (1-based). If not provided, tests all questions.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=100,
        help="Number of documents to retrieve per query (default: 100)",
    )
    args = parser.parse_args()

    # Run evaluation
    results = await evaluate_document_retrieval(
        questions_to_test=args.questions, k=args.k
    )

    print("\nEvaluation Results:")
    print(f"Hit Rate: {results['metadata']['hit_rate']:.2%}")
    print(f"Results saved to: {results['metadata']['output_file']}")


if __name__ == "__main__":
    asyncio.run(main())
