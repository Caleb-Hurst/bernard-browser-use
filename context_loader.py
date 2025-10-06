import os
from pathlib import Path

def load_context_from_labels(labels, context_dir=None):
    """
    Given a list of labels, load and concatenate context from matching .txt files.
    Each label will look for a file named <label>.txt in the context_dir (default: same dir as this file).
    Returns a string with all context joined by two newlines.
    """
    if context_dir is None:
        context_dir = Path(__file__).parent
    context_parts = []
    for label in labels:
        context_path = Path(context_dir) / f"{label}.txt"
        if os.path.exists(context_path):
            with open(context_path, 'r') as f:
                context_parts.append(f.read())
    return "\n\n".join(context_parts)
