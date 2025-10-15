"""
Tests for context_updater module - handles "REMEMBER NEXT TIME FOR" patterns.

This test suite verifies the functionality of parsing task descriptions,
generating context files using OpenAI API, and updating existing context files.
"""

import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from context_updater import (
	parse_remember_next_time,
	generate_context_content,
	update_context_file,
	process_task_for_context_updates
)


class TestParseRememberNextTime:
	"""Test parsing of REMEMBER NEXT TIME FOR patterns."""

	def test_basic_pattern(self):
		"""Test parsing basic pattern."""
		task = "Please test the login feature. REMEMBER NEXT TIME FOR recruiting (To post a job you need to first ensure you possess the feature)"
		result = parse_remember_next_time(task)
		expected = ("recruiting", "To post a job you need to first ensure you possess the feature")
		assert result == expected

	def test_pattern_with_whitespace(self):
		"""Test parsing pattern with extra whitespace."""
		task = "Test something. REMEMBER NEXT TIME FOR   user-management   (  Users must be verified before accessing admin features  )"
		result = parse_remember_next_time(task)
		expected = ("user-management", "Users must be verified before accessing admin features")
		assert result == expected

	def test_no_pattern(self):
		"""Test when no pattern is present."""
		task = "Just test the feature normally without any special instructions."
		result = parse_remember_next_time(task)
		assert result is None

	def test_case_insensitive(self):
		"""Test case insensitive matching."""
		task = "Test this. remember next time for billing-system (Payment processing requires SSL verification)"
		result = parse_remember_next_time(task)
		expected = ("billing-system", "Payment processing requires SSL verification")
		assert result == expected

	def test_multiline_information(self):
		"""Test parsing multiline information in parentheses."""
		task = """Test the feature.
		REMEMBER NEXT TIME FOR onboarding (
			The onboarding process has three steps:
			1. Email verification
			2. Profile setup  
			3. Tutorial completion
		)"""
		result = parse_remember_next_time(task)
		expected_info = """The onboarding process has three steps:
			1. Email verification
			2. Profile setup  
			3. Tutorial completion"""
		expected = ("onboarding", expected_info)
		assert result == expected

	def test_multiple_patterns_takes_first(self):
		"""Test that when multiple patterns exist, the first one is returned."""
		task = "REMEMBER NEXT TIME FOR feature1 (info1) and also REMEMBER NEXT TIME FOR feature2 (info2)"
		result = parse_remember_next_time(task)
		expected = ("feature1", "info1")
		assert result == expected


class TestGenerateContextContent:
	"""Test OpenAI API integration for generating context content."""

	def test_generate_new_content(self):
		"""Test generating content for new context file."""
		mock_response = Mock()
		mock_response.choices = [Mock()]
		mock_response.choices[0].message.content = "# Test Feature\n\nGenerated content"

		with patch('context_updater.OpenAI') as mock_openai:
			mock_client = Mock()
			mock_client.chat.completions.create.return_value = mock_response
			mock_openai.return_value = mock_client

			os.environ["OPENAI_API_KEY"] = "test-key"
			try:
				result = generate_context_content("test-feature", "Test information")
				assert result == "# Test Feature\n\nGenerated content"
				
				# Verify API was called correctly
				mock_client.chat.completions.create.assert_called_once()
				call_args = mock_client.chat.completions.create.call_args
				assert call_args[1]["model"] == "gpt-4o"
				assert "test-feature" in call_args[1]["messages"][0]["content"]
				assert "Test information" in call_args[1]["messages"][0]["content"]
			finally:
				if "OPENAI_API_KEY" in os.environ:
					del os.environ["OPENAI_API_KEY"]

	def test_generate_updated_content(self):
		"""Test generating content for updating existing file."""
		existing_content = "# Existing Feature\n\nOld information"
		mock_response = Mock()
		mock_response.choices = [Mock()]
		mock_response.choices[0].message.content = "# Existing Feature\n\nOld information\n\nNew information"

		with patch('context_updater.OpenAI') as mock_openai:
			mock_client = Mock()
			mock_client.chat.completions.create.return_value = mock_response
			mock_openai.return_value = mock_client

			os.environ["OPENAI_API_KEY"] = "test-key"
			try:
				result = generate_context_content("test-feature", "New information", existing_content)
				assert "Old information" in result
				assert "New information" in result
				
				# Verify existing content was passed to API
				call_args = mock_client.chat.completions.create.call_args
				assert existing_content in call_args[1]["messages"][0]["content"]
			finally:
				if "OPENAI_API_KEY" in os.environ:
					del os.environ["OPENAI_API_KEY"]

	def test_missing_api_key(self):
		"""Test error handling when API key is missing."""
		# Ensure API key is not set
		if "OPENAI_API_KEY" in os.environ:
			del os.environ["OPENAI_API_KEY"]
		
		try:
			generate_context_content("test-feature", "Test information")
			assert False, "Expected ValueError for missing API key"
		except ValueError as e:
			assert "OPENAI_API_KEY environment variable is not set" in str(e)

	def test_api_error_handling(self):
		"""Test handling of OpenAI API errors."""
		with patch('context_updater.OpenAI') as mock_openai:
			mock_client = Mock()
			mock_client.chat.completions.create.side_effect = Exception("API Error")
			mock_openai.return_value = mock_client

			os.environ["OPENAI_API_KEY"] = "test-key"
			try:
				try:
					generate_context_content("test-feature", "Test information")
					assert False, "Expected exception for API error"
				except Exception as e:
					assert "Failed to generate context content: API Error" in str(e)
			finally:
				if "OPENAI_API_KEY" in os.environ:
					del os.environ["OPENAI_API_KEY"]


class TestUpdateContextFile:
	"""Test context file creation and updating."""

	def test_create_new_file(self):
		"""Test creating a new context file."""
		with tempfile.TemporaryDirectory() as temp_dir:
			temp_context_dir = Path(temp_dir)
			
			mock_response = Mock()
			mock_response.choices = [Mock()]
			mock_response.choices[0].message.content = "# Authentication Feature\n\nTest content"

			with patch('context_updater.OpenAI') as mock_openai:
				mock_client = Mock()
				mock_client.chat.completions.create.return_value = mock_response
				mock_openai.return_value = mock_client

				os.environ["OPENAI_API_KEY"] = "test-key"
				try:
					result_path = update_context_file("authentication", "Test info", temp_context_dir)
					
					# Verify file was created
					assert Path(result_path).exists()
					assert Path(result_path).name == "authentication.txt"
					
					# Verify content
					with open(result_path, 'r') as f:
						content = f.read()
					assert content == "# Authentication Feature\n\nTest content"
				finally:
					if "OPENAI_API_KEY" in os.environ:
						del os.environ["OPENAI_API_KEY"]

	def test_update_existing_file(self):
		"""Test updating an existing context file."""
		with tempfile.TemporaryDirectory() as temp_dir:
			temp_context_dir = Path(temp_dir)
			
			# Create existing file
			existing_file = temp_context_dir / "test-feature.txt"
			temp_context_dir.mkdir(exist_ok=True)
			existing_content = "# Test Feature\n\nExisting content"
			
			with open(existing_file, 'w') as f:
				f.write(existing_content)
			
			mock_response = Mock()
			mock_response.choices = [Mock()]
			mock_response.choices[0].message.content = "# Test Feature\n\nExisting content\n\nNew content"

			with patch('context_updater.OpenAI') as mock_openai:
				mock_client = Mock()
				mock_client.chat.completions.create.return_value = mock_response
				mock_openai.return_value = mock_client

				os.environ["OPENAI_API_KEY"] = "test-key"
				try:
					result_path = update_context_file("test-feature", "New info", temp_context_dir)
					
					# Verify file was updated
					with open(result_path, 'r') as f:
						updated_content = f.read()
					assert "Existing content" in updated_content
					assert "New content" in updated_content
					
					# Verify existing content was passed to generate_context_content
					call_args = mock_client.chat.completions.create.call_args
					assert existing_content in call_args[1]["messages"][0]["content"]
				finally:
					if "OPENAI_API_KEY" in os.environ:
						del os.environ["OPENAI_API_KEY"]

	def test_filename_sanitization(self):
		"""Test that feature names are properly sanitized for filenames."""
		test_cases = [
			("User Management", "user-management"),
			("billing/payment", "billing-payment"),
			("API & Authentication", "api-authentication"),
			("file-upload feature!", "file-upload-feature"),
			("   spaced   ", "spaced"),
		]
		
		with tempfile.TemporaryDirectory() as temp_dir:
			temp_context_dir = Path(temp_dir)
			
			mock_response = Mock()
			mock_response.choices = [Mock()]
			mock_response.choices[0].message.content = "# Test Content"

			with patch('context_updater.OpenAI') as mock_openai:
				mock_client = Mock()
				mock_client.chat.completions.create.return_value = mock_response
				mock_openai.return_value = mock_client

				os.environ["OPENAI_API_KEY"] = "test-key"
				try:
					for feature_name, expected_filename in test_cases:
						result_path = update_context_file(feature_name, "Test info", temp_context_dir)
						assert Path(result_path).name == f"{expected_filename}.txt"
				finally:
					if "OPENAI_API_KEY" in os.environ:
						del os.environ["OPENAI_API_KEY"]


class TestProcessTaskForContextUpdates:
	"""Test end-to-end task processing."""

	def test_task_without_pattern(self):
		"""Test processing task without REMEMBER pattern."""
		with tempfile.TemporaryDirectory() as temp_dir:
			temp_context_dir = Path(temp_dir)
			task = "Just test the login feature normally"
			result = process_task_for_context_updates(task, temp_context_dir)
			assert result is None

	def test_task_with_pattern(self):
		"""Test processing task with REMEMBER pattern."""
		with tempfile.TemporaryDirectory() as temp_dir:
			temp_context_dir = Path(temp_dir)
			
			mock_response = Mock()
			mock_response.choices = [Mock()]
			mock_response.choices[0].message.content = "# Authentication Feature\n\nTest content"

			with patch('context_updater.OpenAI') as mock_openai:
				mock_client = Mock()
				mock_client.chat.completions.create.return_value = mock_response
				mock_openai.return_value = mock_client

				task = "Test login. REMEMBER NEXT TIME FOR authentication (Users need 2FA enabled)"
				
				os.environ["OPENAI_API_KEY"] = "test-key"
				try:
					result = process_task_for_context_updates(task, temp_context_dir)
					
					# Should return path to created file
					assert result is not None
					assert Path(result).exists()
					assert "authentication.txt" in result
				finally:
					if "OPENAI_API_KEY" in os.environ:
						del os.environ["OPENAI_API_KEY"]

	def test_task_with_pattern_api_error(self):
		"""Test processing task when API call fails."""
		with tempfile.TemporaryDirectory() as temp_dir:
			temp_context_dir = Path(temp_dir)
			
			# Remove API key to simulate error
			if "OPENAI_API_KEY" in os.environ:
				del os.environ["OPENAI_API_KEY"]
			
			task = "Test login. REMEMBER NEXT TIME FOR authentication (Users need 2FA enabled)"
			result = process_task_for_context_updates(task, temp_context_dir)
			
			# Should return None when API call fails
			assert result is None