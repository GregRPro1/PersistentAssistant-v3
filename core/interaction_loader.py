# interaction_loader.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Loads previously logged interactions (YAML format) from disk.
#   Returns the input, prompt, and response text as strings.

import yaml
import os

def load_interaction(file_path: str) -> tuple[str, str, str]:
    """
    Loads an interaction from a YAML file.

    Args:
        file_path (str): Full path to the interaction YAML file.

    Returns:
        tuple[str, str, str]: (input_text, prompt_text, response_text)

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If any required field is missing in the file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Interaction file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    try:
        return (
            data["input_text"],
            data["prompt_text"],
            data["response_text"]
        )
    except KeyError as e:
        raise ValueError(f"Missing required field in interaction file: {e}")
