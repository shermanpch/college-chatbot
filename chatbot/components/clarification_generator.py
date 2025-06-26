"""
LLM component for generating clarifying questions to help users refine their college list.
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


class ClarifyingQuestions(BaseModel):
    """Pydantic model for structured clarifying questions output."""

    questions: list[str] = Field(
        description="List of clarifying questions to help narrow down college choices"
    )


def create_question_generator_chain():
    """
    Create a structured question generation chain using LangChain and Pydantic.

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
    parser = PydanticOutputParser(pydantic_object=ClarifyingQuestions)

    # Load prompt template from markdown file and add format instructions
    base_prompt = load_prompt("clarifying_questions.md")
    prompt_template = base_prompt + "\n\n{format_instructions}"

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "num_colleges",
            "num_questions",
            "distinguishing_features_summary",
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create LCEL pipeline following retriever.py pattern
    chain = prompt | llm | parser

    return chain


async def generate_clarification_questions(
    num_colleges: int,
    distinguishing_features_summary: str,
    num_questions: int = 5,
) -> list[str]:
    """
    Generate clarifying questions using an LLM based on distinguishing college features.

    Args:
        num_colleges: Number of colleges in the current list
        distinguishing_features_summary: Summary of distinguishing features between colleges
        num_questions: Number of clarifying questions to generate (default: 5)

    Returns:
        List of generated questions in the same order as provided by the LLM
    """
    try:
        logger.info(
            f"Generating {num_questions} clarifying questions for {num_colleges} colleges"
        )

        # Create the structured chain
        question_chain = create_question_generator_chain()

        # Log LLM invocation
        logger.info(
            f"LLM CALL: Invoking clarification question generator with model {os.getenv('OPENROUTER_SELF_RETRIEVAL_MODEL')} for {num_colleges} colleges"
        )

        # Invoke the chain with structured output
        result = await question_chain.ainvoke(
            {
                "num_colleges": num_colleges,
                "num_questions": num_questions,
                "distinguishing_features_summary": distinguishing_features_summary,
            }
        )

        # Extract the questions list from the structured result
        questions_list = result.questions if hasattr(result, "questions") else []

        logger.info(
            f"Successfully generated {len(questions_list)} clarifying questions"
        )
        return questions_list

    except Exception as e:
        logger.error(f"Error generating clarifying questions: {e}")
        # Return a fallback list with a single question
        fallback_question = f"To help refine your list of {num_colleges} colleges, could you share any additional preferences about cost, location, or campus features?"
        return [fallback_question]
