#!/usr/bin/env python3
"""
Main entry point for JSON to Markdown Converter.

Run with: python chatbot/utils/markdown_generator/json_to_markdown.py
Requires: pip install -e .
"""

import sys

if __name__ == "__main__":
    try:
        from chatbot.utils.markdown_generator.json_to_markdown.core import main
    except ImportError as e:
        print(
            f"ERROR: Import failed. Ensure 'pip install -e .' has been run and project structure is correct. Details: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        main()
    except Exception as e:
        print(f"ERROR: Conversion failed: {e}", file=sys.stderr)
        sys.exit(1)
