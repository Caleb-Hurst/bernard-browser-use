"""
GitHub API configuration and setup utilities.
Handles authentication headers and repository configuration.
"""
from bernard.constants import GITHUB_API_BASE_URL, GITHUB_TOKEN, REPOSITORY


def get_github_api_headers() -> dict[str, str]:
	"""
	Get headers for GitHub API requests.
	
	Returns:
		dict: Headers dictionary with authorization and content type
	"""
	return {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github+json"
	}


def get_github_graphql_headers() -> dict[str, str]:
	"""
	Get headers for GitHub GraphQL API requests.
	
	Returns:
		dict: Headers dictionary for GraphQL requests
	"""
	return {
		"Authorization": f"Bearer {GITHUB_TOKEN}",
		"Content-Type": "application/json"
	}


def get_repository_url(endpoint: str = "") -> str:
	"""
	Get the full URL for a GitHub API endpoint for the configured repository.
	
	Args:
		endpoint: The specific API endpoint (e.g., 'issues', 'releases')
		
	Returns:
		str: Full GitHub API URL
	"""
	base_url = f"{GITHUB_API_BASE_URL}/repos/{REPOSITORY}"
	if endpoint:
		return f"{base_url}/{endpoint}"
	return base_url


def validate_github_configuration() -> bool:
	"""
	Validate that required GitHub configuration is present.
	
	Returns:
		bool: True if configuration is valid, False otherwise
	"""
	if not GITHUB_TOKEN:
		print("ERROR: GITHUB_TOKEN environment variable is not set")
		return False
	
	if not REPOSITORY:
		print("ERROR: REPOSITORY is not configured")
		return False
		
	return True