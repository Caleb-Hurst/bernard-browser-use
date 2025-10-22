"""
Context Loader Module

This module provides functionality to load contextual information from text files
based on issue labels. It's designed to supply background information to browser
automation agents by reading label-specific context files from the filesystem.

The primary use case is to enhance AI agent prompts with relevant domain-specific
information before executing automated QA tests or other browser tasks.
"""

import os
from pathlib import Path

"""
Given a list of labels, load and concatenate context from matching .txt files.
Each label will look for a file named <label>.txt in the context_dir (default: same dir as this file).
Returns a string with all context joined by two newlines.
"""
def load_context_from_labels(labels, context_dir=None):
    if context_dir is None:
        context_dir = Path(__file__).parent / "context"
    context_parts = []
    for label in labels:
        context_path = Path(context_dir) / f"{label}.txt"
        if os.path.exists(context_path):
            with open(context_path, 'r') as f:
                context_parts.append(f.read())
        # Attach air-employee context if label is '1094/1095'
        if label == '1094/1095':
            air_employee_path = Path(context_dir) / "air-employee.txt"
            if os.path.exists(air_employee_path):
                with open(air_employee_path, 'r') as f:
                    context_parts.append(f.read())
    return "\n\n".join(context_parts)
