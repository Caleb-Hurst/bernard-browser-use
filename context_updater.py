"""
Context File Updater Module

This module provides functionality to parse task descriptions for "REMEMBER NEXT TIME FOR"
patterns and update context files using OpenAI API. It's designed to automatically
maintain and improve contextual information based on QA testing feedback.

The primary use case is to enhance the context files that help AI agents understand
features better by incorporating learnings from change requests and test feedback.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple

from openai import OpenAI


def parse_remember_next_time(task_description: str) -> Optional[Tuple[str, str]]:
	"""
	Parse task description for "REMEMBER NEXT TIME FOR" patterns.
	
	Looks for patterns like:
	"REMEMBER NEXT TIME FOR feature_name (information to remember)"
	
	Args:
		task_description (str): The full task description text
		
	Returns:
		Optional[Tuple[str, str]]: Tuple of (feature_name, information) or None if not found
	"""
	# Pattern to match "REMEMBER NEXT TIME FOR feature_name (information)"
	# Using non-greedy matching for the feature name and greedy for the parentheses content
	pattern = r'REMEMBER NEXT TIME FOR\s+([^(]+?)\s*\(\s*(.*?)\s*\)'
	
	match = re.search(pattern, task_description, re.IGNORECASE | re.DOTALL)
	if match:
		feature_name = match.group(1).strip()
		information = match.group(2).strip()
		return feature_name, information
	
	return None


def generate_context_content(feature_name: str, information: str, existing_content: Optional[str] = None) -> str:
	"""
	Generate context file content using OpenAI API.
	
	Args:
		feature_name (str): Name of the feature
		information (str): Information to remember for next time
		existing_content (Optional[str]): Existing file content to update, if any
		
	Returns:
		str: Generated markdown content for the context file
		
	Raises:
		Exception: If OpenAI API call fails
	"""
	api_key = os.environ.get("OPENAI_API_KEY")
	if not api_key:
		raise ValueError("OPENAI_API_KEY environment variable is not set")
	
	client = OpenAI(api_key=api_key)
	
	if existing_content:
		prompt = f"""You are helping to maintain context files that provide background information for QA testing of software features.

I have an existing context file for the "{feature_name}" feature:

---
{existing_content}
---

I need you to update this file to include the following new information:
{information}

Please provide the complete updated context file in markdown format. The file should:
1. Maintain all existing valuable information
2. Integrate the new information naturally
3. Be well-organized and easy to read
4. Focus on practical testing guidance and feature understanding
5. Use clear markdown formatting

Return only the updated markdown content, no explanations or extra text."""
	else:
		prompt = f"""You are helping to create a context file that provides background information for QA testing of a software feature.

I need you to create a new context file for the "{feature_name}" feature with the following information:
{information}

Please provide a well-structured context file in markdown format. The file should:
1. Be organized and easy to read
2. Focus on practical testing guidance and feature understanding  
3. Include relevant details that would help someone test this feature
4. Use clear markdown formatting (headers, bullet points, etc.)
5. Be comprehensive but concise

Return only the markdown content, no explanations or extra text."""

	try:
		response = client.chat.completions.create(
			model="gpt-4o",
			messages=[
				{"role": "user", "content": prompt}
			],
			temperature=0.3,
			max_tokens=2000
		)
		
		return response.choices[0].message.content.strip()
	except Exception as e:
		raise Exception(f"Failed to generate context content: {str(e)}")


def update_context_file(feature_name: str, information: str, context_dir: Optional[Path] = None) -> str:
	"""
	Update or create a context file for the given feature.
	
	Args:
		feature_name (str): Name of the feature (will be used as filename)
		information (str): Information to add to the context file
		context_dir (Optional[Path]): Directory containing context files (default: ./context)
		
	Returns:
		str: Path to the updated context file
		
	Raises:
		Exception: If file operations or OpenAI API call fails
	"""
	if context_dir is None:
		context_dir = Path(__file__).parent / "context"
	
	# Sanitize feature name for use as filename
	safe_feature_name = re.sub(r'[^\w\-]', '-', feature_name.lower())
	# Replace multiple consecutive dashes with single dash and strip dashes from ends
	safe_feature_name = re.sub(r'-+', '-', safe_feature_name).strip('-')
	context_file_path = context_dir / f"{safe_feature_name}.txt"
	
	# Read existing content if file exists
	existing_content = None
	if context_file_path.exists():
		try:
			with open(context_file_path, 'r', encoding='utf-8') as f:
				existing_content = f.read().strip()
		except Exception as e:
			raise Exception(f"Failed to read existing context file: {str(e)}")
	
	# Generate new content
	try:
		new_content = generate_context_content(feature_name, information, existing_content)
	except Exception as e:
		raise Exception(f"Failed to generate context content: {str(e)}")
	
	# Write the updated content
	try:
		# Ensure the context directory exists
		context_dir.mkdir(parents=True, exist_ok=True)
		
		with open(context_file_path, 'w', encoding='utf-8') as f:
			f.write(new_content)
		
		return str(context_file_path)
	except Exception as e:
		raise Exception(f"Failed to write context file: {str(e)}")


def process_task_for_context_updates(task_description: str, context_dir: Optional[Path] = None) -> Optional[str]:
	"""
	Process a task description and update context files if "REMEMBER NEXT TIME FOR" pattern is found.
	
	Args:
		task_description (str): Full task description text
		context_dir (Optional[Path]): Directory containing context files (default: ./context)
		
	Returns:
		Optional[str]: Path to updated context file, or None if no update needed
	"""
	remember_info = parse_remember_next_time(task_description)
	if not remember_info:
		return None
	
	feature_name, information = remember_info
	
	try:
		updated_file_path = update_context_file(feature_name, information, context_dir)
		print(f"Updated context file for '{feature_name}': {updated_file_path}")
		return updated_file_path
	except Exception as e:
		print(f"Error updating context file for '{feature_name}': {str(e)}")
		return None