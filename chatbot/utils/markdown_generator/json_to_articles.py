#!/usr/bin/env python3
"""
Main entry point for JSON to Articles Generator.

Usage:
  python chatbot/utils/markdown_generator/json_to_articles.py                    # Generate all articles
  python chatbot/utils/markdown_generator/json_to_articles.py --limit 3         # Generate 3 articles (for testing)
  python chatbot/utils/markdown_generator/json_to_articles.py --limit 5         # Generate 5 articles
  python chatbot/utils/markdown_generator/json_to_articles.py --model openai/gpt-4o  # Use specific model
  python chatbot/utils/markdown_generator/json_to_articles.py --skip-existing    # Skip universities with existing articles

Requires: pip install -e .
"""

import sys

if __name__ == "__main__":
    try:
        from chatbot.utils.markdown_generator.json_to_article.core import main
    except ImportError as e:
        print(
            f"ERROR: Import failed. Ensure 'pip install -e .' has been run and project structure is correct. Details: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Article generation failed: {e}", file=sys.stderr)
        sys.exit(1)
