"""
LLM component for generating search suggestions to help users refine their college search.
"""

import os

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from chatbot.utils.prompt_loader import load_prompt
from projectutils.env import setup_project_environment
from projectutils.logger import setup_logger

# Call setup at the module level
PROJECT_ROOT, _ = setup_project_environment()

# Set up logging using the new utility
logger = setup_logger(__file__)


class SearchSuggestions(BaseModel):
    """Pydantic model for structured search suggestions output."""

    suggestions: list[str] = Field(description="List of example search criteria")


def create_suggestion_generator_chain():
    """
    Create a structured suggestion generation chain using LangChain and Pydantic.

    Returns:
        LCEL pipeline: prompt | llm | parser
    """
    # Initialize the LLM
    llm = ChatOpenAI(
        model=os.getenv("OPENROUTER_SELF_RETRIEVAL_MODEL"),
        temperature=0.7,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "College Chatbot",
        },
    )

    # Create the Pydantic output parser
    parser = PydanticOutputParser(pydantic_object=SearchSuggestions)

    # Load prompt template from markdown file and add format instructions
    base_prompt = load_prompt("search_suggestions.md")
    prompt_template = base_prompt + "\n\n{format_instructions}"

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "num_colleges",
            "num_suggestions",
            "distinguishing_features_summary",
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create LCEL pipeline following retriever.py pattern
    chain = prompt | llm | parser

    return chain


async def generate_search_suggestions(
    num_colleges: int,
    distinguishing_features_summary: str,
    num_suggestions: int = 5,
) -> list[str]:
    """
    Generate search suggestions using an LLM based on distinguishing college features.

    Args:
        num_colleges: Number of colleges in the current list
        distinguishing_features_summary: Summary of distinguishing features between colleges
        num_suggestions: Number of search suggestions to generate (default: 5)

    Returns:
        List of generated suggestions in the same order as provided by the LLM
    """
    try:
        logger.info(
            f"Generating {num_suggestions} search suggestions for {num_colleges} colleges"
        )

        # Create the structured chain
        suggestion_chain = create_suggestion_generator_chain()

        # Log LLM invocation
        logger.info(
            f"LLM CALL: Invoking search suggestion generator with model {os.getenv('OPENROUTER_SELF_RETRIEVAL_MODEL')} for {num_colleges} colleges"
        )

        # Invoke the chain with structured output
        result = await suggestion_chain.ainvoke(
            {
                "num_colleges": num_colleges,
                "num_suggestions": num_suggestions,
                "distinguishing_features_summary": distinguishing_features_summary,
            }
        )

        # Extract the suggestions list from the structured result
        suggestions_list = result.suggestions if hasattr(result, "suggestions") else []

        logger.info(
            f"Successfully generated {len(suggestions_list)} search suggestions"
        )
        return suggestions_list

    except Exception as e:
        logger.error(f"Error generating search suggestions: {e}")
        # Return a fallback list with generic suggestions
        fallback_suggestions = [
            "Acceptance rate less than 40%",
            "Tuition under $25,000",
            "Average SAT score above 1200",
            "Schools with on-campus housing",
        ]
        return fallback_suggestions[:num_suggestions]
