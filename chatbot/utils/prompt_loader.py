"""
Simple utility for loading prompt templates from markdown files.
"""

import os
from typing import Any

from jinja2 import Environment, FileSystemLoader

from projectutils.env import setup_project_environment

# Set up project environment
PROJECT_ROOT, _ = setup_project_environment()


def load_prompt(template_path: str, variables: dict[str, Any] | None = None) -> str:
    """
    Load a prompt template.

    Args:
        template_path: Path to template file. Can be:
                      - Just filename: 'template.md' (searches in chatbot/prompts/)
                      - Relative path: 'chatbot/prompts/template.md'
                      - Absolute path: '/full/path/template.md'
        variables: Optional variables for Jinja2 rendering

    Returns:
        Prompt content as string
    """
    # Resolve the full path
    if os.path.isabs(template_path):
        full_path = template_path
    elif os.sep in template_path or "/" in template_path:
        full_path = os.path.join(PROJECT_ROOT, template_path)
    else:
        full_path = os.path.join(PROJECT_ROOT, "chatbot", "prompts", template_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Template not found: {full_path}")

    # If no variables, return raw content
    if variables is None:
        with open(full_path, encoding="utf-8") as f:
            return f.read()

    # If variables provided, render as Jinja2 template
    template_dir = os.path.dirname(full_path)
    template_name = os.path.basename(full_path)

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    return template.render(**variables)
