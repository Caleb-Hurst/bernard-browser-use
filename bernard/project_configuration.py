"""
Project-specific configuration for GitHub project integration.
This file should be updated with actual project values from your GitHub project.
"""
import os

from bernard.github_configuration import get_github_graphql_headers

# These values need to be configured for your specific GitHub project
# You can find these in your GitHub project settings or by querying the GraphQL API

PROJECT_UNIQUE_ID = os.environ.get("PROJECT_UNIQUE_ID", "")
COLUMN_ID = os.environ.get("COLUMN_ID", "")

# Request headers for GraphQL requests (backwards compatibility)
request_headers = get_github_graphql_headers()


def validate_project_configuration() -> bool:
	"""
	Validate that required project configuration is present.
	
	Returns:
		bool: True if configuration is valid, False otherwise
	"""
	if not PROJECT_UNIQUE_ID:
		print("ERROR: PROJECT_UNIQUE_ID environment variable is not set")
		print("Please set this to your GitHub project's unique ID")
		return False
	
	if not COLUMN_ID:
		print("ERROR: COLUMN_ID environment variable is not set")  
		print("Please set this to your GitHub project column's ID")
		return False
		
	return True


def get_project_configuration() -> dict[str, str]:
	"""
	Get project configuration as a dictionary.
	
	Returns:
		dict: Project configuration values
	"""
	return {
		"project_unique_id": PROJECT_UNIQUE_ID,
		"column_id": COLUMN_ID
	}