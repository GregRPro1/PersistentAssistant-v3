# prompt_formatter.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Provides formatting logic to convert raw user input into structured prompts.

def format_prompt(input_text: str) -> str:
    """
    Formats raw input into a structured prompt.

    Args:
        input_text (str): The raw user input.

    Returns:
        str: A formatted version suitable for AI prompt submission.
    """
    if not input_text.strip():
        return ""

    header = "=== Structured Prompt ==="
    footer = "=== End of Prompt ==="
    body = input_text.strip()

    return f"{header}\n\n{body}\n\n{footer}"
