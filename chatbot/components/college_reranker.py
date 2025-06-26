"""
LLM component for re-ranking colleges based on user preferences.
"""

import os

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from chatbot.utils.prompt_loader import load_prompt
from projectutils.logger import setup_logger

# Set up logging
logger = setup_logger(__file__)


class RankedDocumentItem(BaseModel):
    rank: int = Field(description="The numerical rank of the document, e.g., 1, 2, 3.")
    document_id: str = Field(description="The unique identifier of the document.")
    reason: str = Field(description="A detailed reason for the assigned rank.")


class RankedDocuments(BaseModel):
    rankings: list[RankedDocumentItem] = Field(
        description="A list of ranked documents with reasons."
    )


def create_reranking_chain():
    """
    Create a structured college reranking chain using LangChain and Pydantic.

    Returns:
        LCEL pipeline: prompt | llm | parser
    """
    # Initialize the LLM
    llm = ChatOpenAI(
        model=os.getenv("OPENROUTER_SELF_RETRIEVAL_MODEL", "openai/gpt-4o-mini"),
        temperature=0.3,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "College Chatbot",
        },
    )

    # Create the Pydantic output parser
    parser = PydanticOutputParser(pydantic_object=RankedDocuments)

    # Load prompt template from markdown file
    prompt_template_str = load_prompt("reranking.md")

    prompt = PromptTemplate(
        template=prompt_template_str,
        input_variables=["student_preferences", "concatenated_document_contexts"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create LCEL pipeline
    chain = prompt | llm | parser

    return chain


async def generate_reranked_colleges(
    student_preferences: str, concatenated_document_contexts: str
) -> RankedDocuments:
    """
    Generate reranked colleges using an LLM based on student preferences and college documents.

    Args:
        student_preferences: String containing clarifying questions and student responses
        concatenated_document_contexts: String containing all college document contexts

    Returns:
        RankedDocuments object containing the ranked college list with reasons
    """
    try:
        logger.info("Generating reranked colleges via LLM.")

        # Create the structured chain
        reranking_chain = create_reranking_chain()

        # Log LLM invocation
        logger.info(
            f"LLM CALL: Invoking college reranker with model {os.getenv('OPENROUTER_SELF_RETRIEVAL_MODEL', 'openai/gpt-4o-mini')} for college reranking"
        )

        # Invoke the chain with structured output
        result: RankedDocuments = await reranking_chain.ainvoke(
            {
                "student_preferences": student_preferences,
                "concatenated_document_contexts": concatenated_document_contexts,
            }
        )

        logger.info(f"Successfully generated {len(result.rankings)} reranked items.")
        return result

    except Exception as e:
        logger.error(f"Error generating reranked colleges: {e}")
        raise  # Re-raise the exception to let the calling code handle it
