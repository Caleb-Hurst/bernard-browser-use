"""
Test project_issues module environment variable handling.

This test verifies that the project_issues module correctly reads
PROJECT_UNIQUE_ID and COLUMN_ID from environment variables.
"""
import os
import pytest
from unittest.mock import patch


def test_project_issues_reads_env_vars():
	"""Test that project_issues module reads environment variables correctly."""
	test_env = {
		'PROJECT_UNIQUE_ID': 'test_project_id_123',
		'COLUMN_ID': 'test_column_id_456',
		'GITHUB_TOKEN': 'test_token_789'
	}
	
	with patch.dict(os.environ, test_env, clear=False):
		# Import here to ensure environment variables are read after setting
		import importlib
		import project_issues
		importlib.reload(project_issues)
		
		assert project_issues.PROJECT_UNIQUE_ID == 'test_project_id_123'
		assert project_issues.COLUMN_ID == 'test_column_id_456'
		assert project_issues.GITHUB_TOKEN == 'test_token_789'


def test_project_issues_missing_env_vars():
	"""Test that project_issues module raises KeyError when env vars are missing."""
	# Remove required env vars if they exist
	env_without_required = {k: v for k, v in os.environ.items() 
							if k not in ['PROJECT_UNIQUE_ID', 'COLUMN_ID', 'GITHUB_TOKEN']}
	
	with patch.dict(os.environ, env_without_required, clear=True):
		with pytest.raises(KeyError):
			import importlib
			import project_issues
			importlib.reload(project_issues)