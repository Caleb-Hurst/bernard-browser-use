"""
End-to-end test for context_updater module with mock OpenAI API.

This test simulates the complete functionality including file creation/updating.
"""

import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from context_updater import process_task_for_context_updates, update_context_file


def test_create_new_context_file():
	"""Test creating a new context file."""
	print("Testing creation of new context file...")
	
	with tempfile.TemporaryDirectory() as temp_dir:
		temp_context_dir = Path(temp_dir)
		
		# Mock OpenAI response
		mock_response = Mock()
		mock_response.choices = [Mock()]
		mock_response.choices[0].message.content = """# Authentication Feature

## Overview
This feature handles user authentication and login processes.

## Key Points to Remember
- Users need 2FA enabled for secure access
- Password requirements include special characters
- Session timeout is set to 30 minutes

## Testing Guidelines
- Always test with valid and invalid credentials
- Verify 2FA functionality works correctly
- Check session management and timeout behavior"""

		with patch('context_updater.OpenAI') as mock_openai:
			mock_client = Mock()
			mock_client.chat.completions.create.return_value = mock_response
			mock_openai.return_value = mock_client
			
			# Set API key
			os.environ["OPENAI_API_KEY"] = "test-key"
			
			try:
				result_path = update_context_file(
					"authentication", 
					"Users need 2FA enabled for secure access",
					temp_context_dir
				)
				
				# Verify file was created
				assert Path(result_path).exists(), f"Context file was not created: {result_path}"
				
				# Verify content
				with open(result_path, 'r') as f:
					content = f.read()
				
				assert "Authentication Feature" in content
				assert "2FA enabled" in content
				print(f"✓ New context file created successfully: {result_path}")
				
			finally:
				# Clean up environment
				if "OPENAI_API_KEY" in os.environ:
					del os.environ["OPENAI_API_KEY"]


def test_update_existing_context_file():
	"""Test updating an existing context file."""
	print("Testing update of existing context file...")
	
	with tempfile.TemporaryDirectory() as temp_dir:
		temp_context_dir = Path(temp_dir)
		
		# Create existing file
		existing_file = temp_context_dir / "user-management.txt"
		temp_context_dir.mkdir(exist_ok=True)
		
		existing_content = """# User Management

## Current Features
- User registration
- Profile management
"""
		
		with open(existing_file, 'w') as f:
			f.write(existing_content)
		
		# Mock OpenAI response for update
		mock_response = Mock()
		mock_response.choices = [Mock()]
		mock_response.choices[0].message.content = """# User Management

## Current Features
- User registration
- Profile management

## New Information
- Users must be verified before accessing admin features
- Email verification is required for new accounts

## Testing Guidelines
- Test both verified and unverified user scenarios
- Verify admin access restrictions work correctly"""

		with patch('context_updater.OpenAI') as mock_openai:
			mock_client = Mock()
			mock_client.chat.completions.create.return_value = mock_response
			mock_openai.return_value = mock_client
			
			# Set API key
			os.environ["OPENAI_API_KEY"] = "test-key"
			
			try:
				result_path = update_context_file(
					"user-management", 
					"Users must be verified before accessing admin features",
					temp_context_dir
				)
				
				# Verify file was updated
				with open(result_path, 'r') as f:
					updated_content = f.read()
				
				assert "User Management" in updated_content
				assert "verified before accessing admin" in updated_content
				assert "Profile management" in updated_content  # Original content preserved
				print(f"✓ Context file updated successfully: {result_path}")
				
			finally:
				# Clean up environment
				if "OPENAI_API_KEY" in os.environ:
					del os.environ["OPENAI_API_KEY"]


def test_end_to_end_processing():
	"""Test the complete end-to-end processing from task description."""
	print("Testing end-to-end task processing...")
	
	with tempfile.TemporaryDirectory() as temp_dir:
		temp_context_dir = Path(temp_dir)
		
		# Mock OpenAI response
		mock_response = Mock()
		mock_response.choices = [Mock()]
		mock_response.choices[0].message.content = """# Recruiting Feature

## Overview
This feature handles job posting and recruitment workflows.

## Key Requirements
- To post a job you need to first ensure you possess the feature
- Job postings require approval workflow
- Candidate management integration is required

## Testing Guidelines  
- Verify feature availability before allowing job posting
- Test the complete approval workflow
- Check candidate data integration"""

		task_description = """Please test the recruiting feature and ensure job posting works correctly.

REMEMBER NEXT TIME FOR recruiting (To post a job you need to first ensure you posses the feature)

Also check that the approval workflow functions as expected."""

		with patch('context_updater.OpenAI') as mock_openai:
			mock_client = Mock()
			mock_client.chat.completions.create.return_value = mock_response
			mock_openai.return_value = mock_client
			
			# Set API key
			os.environ["OPENAI_API_KEY"] = "test-key"
			
			try:
				result_path = process_task_for_context_updates(task_description, temp_context_dir)
				
				# Verify processing worked
				assert result_path is not None, "Expected a file path to be returned"
				assert Path(result_path).exists(), f"Context file was not created: {result_path}"
				
				# Verify content
				with open(result_path, 'r') as f:
					content = f.read()
				
				assert "Recruiting Feature" in content
				assert "posses the feature" in content or "possess the feature" in content
				print(f"✓ End-to-end processing successful: {result_path}")
				
			finally:
				# Clean up environment
				if "OPENAI_API_KEY" in os.environ:
					del os.environ["OPENAI_API_KEY"]


if __name__ == "__main__":
	print("Running context_updater end-to-end tests...\n")
	
	try:
		test_create_new_context_file()
		test_update_existing_context_file()
		test_end_to_end_processing()
		
		print("\n🎉 All end-to-end tests passed successfully!")
	except Exception as e:
		print(f"\n❌ Test failed: {str(e)}")
		import traceback
		traceback.print_exc()
		raise