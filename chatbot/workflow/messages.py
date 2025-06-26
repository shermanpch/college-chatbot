ASK_HYBRID_SEARCH_QUERY_HEADER = """🎯 **Refine Your College Search**

Tell me what matters most to you, and I'll help narrow down your options to find the perfect fit!

*You can combine ideas from any section below:*"""

# Question for hybrid search query prompt
_HYBRID_SEARCH_QUESTION = "💭 **What feature would you like to add?**"

ASK_MORE_CRITERIA_HEADER_BASE = """🔍 **Let's Narrow It Down Further**

Great! We found **{num_colleges} colleges** that match your criteria so far."""

ASK_MORE_CRITERIA_SUB_HEADER_NO_NO_OPTION = "Let's add one more preference to refine your list and get even more targeted results!"
ASK_MORE_CRITERIA_SUB_HEADER_WITH_NO_OPTION = 'Add one more preference to refine the list further, or say **"No"** if you\'re happy with these results!'

# Final question appended to every prompt
_FINAL_QUESTION = "\n🎯 **What would you like to filter by next?**"

_NO_OPTION_TEXT = """\n\n✨ *You can also say **"No"** to proceed with your current matches and see the results!*"""


def create_hybrid_search_query_prompt(
    dynamic_suggestions: list[str] | None = None,
) -> str:
    """
    Create the hybrid search query prompt with dynamic suggestions.

    Args:
        dynamic_suggestions: List of dynamic suggestions to include, or None for fallback

    Returns:
        Complete formatted prompt string
    """
    if dynamic_suggestions:
        # Format suggestions into a bulleted list
        formatted_suggestions = "\n".join([f'• **"{s}"**' for s in dynamic_suggestions])
        suggestions_section = (
            f"🎯 **Suggestions Based on Your Colleges**\n\n{formatted_suggestions}"
        )
    else:
        # Fallback suggestions
        suggestions_section = """🎯 **Example Suggestions**

• **"Acceptance rate less than 40%"**
• **"Tuition under $25,000"**
• **"Average SAT score above 1200"**
• **"Schools with on-campus housing"**"""

    return (
        f"{ASK_HYBRID_SEARCH_QUERY_HEADER}\n\n"
        f"{suggestions_section}\n\n"
        f"{_HYBRID_SEARCH_QUESTION}"
    )


def create_more_criteria_prompt(
    num_colleges: int,
    dynamic_suggestions: list[str] | None = None,
) -> str:
    """
    Create the more criteria prompt with dynamic suggestions.

    Args:
        num_colleges: Number of colleges currently in the list
        dynamic_suggestions: List of dynamic suggestions to include, or None for fallback

    Returns:
        Complete formatted prompt string
    """
    # Determine if "No" option should be available
    include_no_option = 10 <= num_colleges <= 12

    # Build prompt parts
    prompt_parts = []
    prompt_parts.append(ASK_MORE_CRITERIA_HEADER_BASE.format(num_colleges=num_colleges))

    if include_no_option:
        prompt_parts.append(ASK_MORE_CRITERIA_SUB_HEADER_WITH_NO_OPTION)
    else:
        prompt_parts.append(ASK_MORE_CRITERIA_SUB_HEADER_NO_NO_OPTION)

    # Add suggestions section
    if dynamic_suggestions:
        formatted_suggestions = "\n".join([f'• **"{s}"**' for s in dynamic_suggestions])
        prompt_parts.append("\n🎯 **Suggestions Based on Your Current Colleges**\n")
        prompt_parts.append(formatted_suggestions)
    else:
        # Fallback suggestions
        prompt_parts.append("\n🎯 **Example Suggestions**\n")
        prompt_parts.append('• **"Acceptance rate less than 40%"**')
        prompt_parts.append('• **"Tuition under $30,000"**')
        prompt_parts.append('• **"Average SAT score above 1200"**')
        prompt_parts.append('• **"Schools with strong campus life"**')

    if include_no_option:
        prompt_parts.append(_NO_OPTION_TEXT)

    prompt_parts.append(_FINAL_QUESTION)

    return "\n".join(prompt_parts)
