#!/usr/bin/env python3
"""
Demonstration script for the context file updating feature.

This script shows how the context updater works with various task descriptions.
Run with: python demo_context_updater.py

To test with real OpenAI API, set OPENAI_API_KEY environment variable.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from context_updater import (
	parse_remember_next_time, 
	process_task_for_context_updates,
	update_context_file
)


def demo_parsing():
	"""Demonstrate parsing of different task formats."""
	print("=" * 60)
	print("DEMO: Parsing 'REMEMBER NEXT TIME FOR' patterns")
	print("=" * 60)
	
	test_tasks = [
		"Please test the login feature. REMEMBER NEXT TIME FOR recruiting (To post a job you need to first ensure you possess the feature)",
		"Test user management. REMEMBER NEXT TIME FOR user-permissions (Admin users must verify their identity before accessing sensitive data)",
		"Check billing system. REMEMBER NEXT TIME FOR payments (Credit card processing requires PCI compliance verification)",
		"Regular test task without any special instructions",
		"Multiple instructions here. REMEMBER NEXT TIME FOR onboarding (The wizard has 3 steps: email verification, profile setup, and tutorial completion)",
	]
	
	for i, task in enumerate(test_tasks, 1):
		print(f"\nTask {i}:")
		print(f"Input: {task[:100]}{'...' if len(task) > 100 else ''}")
		
		result = parse_remember_next_time(task)
		if result:
			feature, info = result
			print(f"✓ Found pattern - Feature: '{feature}', Info: '{info[:50]}{'...' if len(info) > 50 else ''}'")
		else:
			print("✗ No pattern found")


def demo_with_mock_api():
	"""Demonstrate file creation/updating with mocked OpenAI API."""
	print("\n" + "=" * 60)
	print("DEMO: File creation and updating (with mock API)")
	print("=" * 60)
	
	with tempfile.TemporaryDirectory() as temp_dir:
		temp_context_dir = Path(temp_dir)
		print(f"Using temporary directory: {temp_context_dir}")
		
		# Mock responses for different scenarios
		mock_responses = {
			"recruiting": """# Recruiting Feature

## Overview
Handles job posting and candidate management workflows.

## Key Requirements
- To post a job you need to first ensure you possess the feature
- Job approval workflow must be completed
- Integration with HR systems required

## Testing Guidelines
- Always verify feature access before allowing job posting
- Test the complete approval process
- Validate HR system integration points""",
			
			"user-management": """# User Management Feature  

## Overview
Comprehensive user account and permission management system.

## Key Requirements
- Admin users must verify identity before accessing sensitive data
- Role-based access control (RBAC) implementation
- Audit logging for all administrative actions

## Testing Guidelines
- Test identity verification flow for admin users
- Verify role permissions work correctly
- Check audit logs are generated properly"""
		}
		
		# Mock OpenAI client
		with patch('context_updater.OpenAI') as mock_openai:
			mock_client = Mock()
			
			def mock_create_completion(*args, **kwargs):
				# Extract feature name from the prompt to return appropriate response
				prompt = kwargs['messages'][0]['content']
				if 'recruiting' in prompt.lower():
					response = Mock()
					response.choices = [Mock()]
					response.choices[0].message.content = mock_responses["recruiting"]
					return response
				elif 'user-management' in prompt.lower() or 'user management' in prompt.lower():
					response = Mock()
					response.choices = [Mock()]
					response.choices[0].message.content = mock_responses["user-management"]
					return response
				else:
					response = Mock()
					response.choices = [Mock()]
					response.choices[0].message.content = "# Generic Feature\n\nGeneric context content."
					return response
			
			mock_client.chat.completions.create.side_effect = mock_create_completion
			mock_openai.return_value = mock_client
			
			# Set fake API key
			import os
			os.environ["OPENAI_API_KEY"] = "demo-key"
			
			try:
				# Test 1: Create new file
				print("\n1. Creating new context file for 'recruiting'...")
				result1 = update_context_file(
					"recruiting", 
					"To post a job you need to first ensure you possess the feature",
					temp_context_dir
				)
				print(f"   Created: {result1}")
				
				# Show content
				with open(result1, 'r') as f:
					content = f.read()
				print("   Content preview:", content[:100] + "...")
				
				# Test 2: Update existing file
				print("\n2. Creating and then updating 'user-management'...")
				result2 = update_context_file(
					"user-management", 
					"Admin users must verify identity before accessing sensitive data",
					temp_context_dir
				)
				print(f"   Updated: {result2}")
				
				# Test 3: End-to-end processing
				print("\n3. End-to-end processing of task description...")
				task = """Test the onboarding flow thoroughly.

REMEMBER NEXT TIME FOR onboarding (The wizard has 3 main steps that must be completed in order: email verification, profile setup, and tutorial completion)

Make sure all validation works correctly."""
				
				result3 = process_task_for_context_updates(task, temp_context_dir)
				print(f"   Processed task and created: {result3}")
				
				# Show final directory contents
				print(f"\n4. Final context directory contents:")
				for file_path in temp_context_dir.glob("*.txt"):
					print(f"   - {file_path.name}")
				
			finally:
				# Clean up
				if "OPENAI_API_KEY" in os.environ:
					del os.environ["OPENAI_API_KEY"]


def demo_integration_example():
	"""Show how this integrates with the main QA agent."""
	print("\n" + "=" * 60)
	print("DEMO: Integration with QA Agent Runner")
	print("=" * 60)
	
	print("\nHow it works in run_bernard_qa_agent.py:")
	print("\n1. Agent receives task description as command line argument")
	print("2. Before starting browser automation, it calls:")
	print("   process_task_for_context_updates(task, context_dir)")
	print("3. If 'REMEMBER NEXT TIME FOR' pattern is found:")
	print("   - Extract feature name and information")
	print("   - Generate/update context file using OpenAI API")
	print("   - Save updated file to context directory")
	print("4. Agent continues with normal QA testing")
	print("5. Context files are loaded for future tests of the same feature")
	
	example_command = '''python run_bernard_qa_agent.py "Test login functionality. REMEMBER NEXT TIME FOR authentication (Users need 2FA verification)" 123 ./chrome_profile recruiting,authentication'''
	
	print(f"\nExample command line usage:")
	print(f"  {example_command}")
	
	print(f"\nThis would:")
	print(f"  - Parse the task and find 'REMEMBER NEXT TIME FOR authentication'")
	print(f"  - Create/update context/authentication.txt with 2FA information")
	print(f"  - Load context from recruiting.txt and authentication.txt")  
	print(f"  - Run QA testing with enhanced context knowledge")


if __name__ == "__main__":
	print("🤖 Context File Updater - Feature Demonstration")
	
	demo_parsing()
	demo_with_mock_api()
	demo_integration_example()
	
	print("\n" + "=" * 60)
	print("✅ Demo complete! The feature is ready for use.")
	print("Set OPENAI_API_KEY environment variable to use with real API.")
	print("=" * 60)