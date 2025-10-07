"""
GitHub interactions for issue management, commenting, and labeling.
Handles all GitHub API operations related to issues and project management.
"""
import requests

from bernard.constants import COLUMN_ID, DEFAULT_BOT_USERNAME, GITHUB_GRAPHQL_URL, PROJECT_UNIQUE_ID
from bernard.github_configuration import get_github_api_headers, get_github_graphql_headers, get_repository_url


def get_latest_github_actions_comment(issue_number: str) -> str | None:
	"""
	Fetch the most recent comment by the github-actions bot for the given issue.
	
	Args:
		issue_number: GitHub issue number
		
	Returns:
		str: Comment body if found, None if no comment found
	"""
	url = get_repository_url(f"issues/{issue_number}/comments")
	headers = get_github_api_headers()
	
	try:
		response = requests.get(url, headers=headers)
		response.raise_for_status()
		comments = response.json()
		
		# Filter for github-actions bot comments
		actions_comments = [
			comment for comment in comments 
			if comment.get("user", {}).get("login") == "github-actions[bot]"
		]
		
		if not actions_comments:
			return None
		
		# Return the most recent comment body
		latest_comment = sorted(actions_comments, key=lambda c: c["created_at"], reverse=True)[0]
		return latest_comment["body"]
		
	except requests.exceptions.HTTPError as e:
		print(f"ERROR: Failed to fetch GitHub Actions comments: {e}")
		return None


def update_issue_labels(issue_number: str) -> bool:
	"""
	Update issue labels by removing 'needs-test' and adding 'ai-tested'.
	
	Args:
		issue_number: GitHub issue number
		
	Returns:
		bool: True if successful, False if failed
	"""
	url = get_repository_url(f"issues/{issue_number}")
	headers = get_github_api_headers()
	
	try:
		# Get current labels
		response = requests.get(url, headers=headers)
		response.raise_for_status()
		current_labels = [label['name'] for label in response.json().get('labels', [])]
		
		# Remove 'needs-test' if present, add 'ai-tested' if not present
		updated_labels = [label for label in current_labels if label != 'needs-test']
		
		if 'ai-tested' not in updated_labels:
			updated_labels.append('ai-tested')
		
		# Update labels
		response = requests.patch(url, headers=headers, json={"labels": updated_labels})
		response.raise_for_status()
		
		print(f"Successfully updated labels for issue #{issue_number}")
		return True
		
	except requests.exceptions.HTTPError as e:
		print(f"ERROR: Failed to update labels for issue #{issue_number}: {e}")
		return False


def comment_on_issue(issue_number: str, message: str) -> bool:
	"""
	Add a comment to a GitHub issue.
	
	Args:
		issue_number: GitHub issue number
		message: Comment message body
		
	Returns:
		bool: True if successful, False if failed
	"""
	url = get_repository_url(f"issues/{issue_number}/comments")
	headers = get_github_api_headers()
	
	try:
		response = requests.post(url, json={"body": message}, headers=headers)
		response.raise_for_status()
		print(f"Successfully commented on issue #{issue_number}")
		return True
		
	except requests.exceptions.HTTPError as e:
		print(f"ERROR: Failed to comment on issue #{issue_number}: {e}")
		return False


def get_project_issues() -> list[dict]:
	"""
	Fetch all project issues with their status and labels using GraphQL.
	Uses pagination to retrieve all issues.
	
	Returns:
		list: List of issue dictionaries with body, number, labels, and comments
	"""
	query = '''
	query($projectId: ID!, $after: String) {
		node(id: $projectId) {
			... on ProjectV2 {
				items(first: 100, after: $after) {
					nodes {
						content {
							... on Issue {
								id
								number
								state
								body
								labels(first: 20) {
									nodes { name }
								}
								comments(last: 10) {
									nodes {
										author { login }
										body
										createdAt
									}
								}
							}
						}
						fieldValues(first: 20) {
							nodes {
								... on ProjectV2ItemFieldSingleSelectValue {
									optionId
								}
							}
						}
					}
					pageInfo { hasNextPage endCursor }
				}
			}
		}
	}
	'''
	
	variables = {"projectId": PROJECT_UNIQUE_ID, "after": None}
	headers = get_github_graphql_headers()
	issues = []
	
	while True:
		try:
			response = requests.post(
				GITHUB_GRAPHQL_URL,
				headers=headers,
				json={"query": query, "variables": variables}
			)
			response.raise_for_status()
			data = response.json()
			
			items = data["data"]["node"]["items"]["nodes"]
			
			for item in items:
				content = item.get("content")
				if not content or content.get("state") != "OPEN":
					continue
				
				# Check if this item is in the desired column
				in_column = False
				for field_value in item["fieldValues"]["nodes"]:
					if field_value.get("optionId") == COLUMN_ID:
						in_column = True
						break
				
				if not in_column:
					continue
				
				labels = [label["name"] for label in content.get("labels", {}).get("nodes", [])]
				comments = [
					{
						"author": comment["author"]["login"] if comment["author"] else None,
						"body": comment["body"],
						"createdAt": comment["createdAt"]
					}
					for comment in content.get("comments", {}).get("nodes", [])
				]
				
				issues.append({
					"body": content.get("body", ""),
					"number": content.get("number"),
					"node_id": content.get("id"),
					"labels": labels,
					"comments": comments
				})
			
			page_info = data["data"]["node"]["items"]["pageInfo"]
			if page_info["hasNextPage"]:
				variables["after"] = page_info["endCursor"]
			else:
				break
				
		except requests.exceptions.HTTPError as e:
			print(f"ERROR: Failed to fetch project issues: {e}")
			break
		except KeyError as e:
			print(f"ERROR: Unexpected response structure: {e}")
			break
	
	return issues


def get_tagged_comment_after_last_test(comments: list[dict], bot_username: str = DEFAULT_BOT_USERNAME) -> str | None:
	"""
	Find the first comment mentioning the bot after the last test comment by the bot.
	
	Args:
		comments: List of comment dictionaries with author, body, and createdAt
		bot_username: Username of the bot to look for
		
	Returns:
		str: Comment body if found, None otherwise
	"""
	last_test_time = None
	
	# Find the most recent test comment by the bot
	for comment in reversed(comments):
		if comment["author"] == bot_username:
			last_test_time = comment["createdAt"]
			break
	
	# Look for a comment mentioning the bot after last_test_time
	for comment in comments:
		if f"@{bot_username}" in comment["body"]:
			if last_test_time is None or comment["createdAt"] > last_test_time:
				return comment["body"]
	
	return None


def extract_result_section_from_comment(comment_body: str) -> str | None:
	"""
	Extract the result section from a comment body.
	
	Args:
		comment_body: Full comment body text
		
	Returns:
		str: Extracted result section, None if not found
	"""
	import re
	
	# Try to extract the section after 'Result:' and before the next section
	match = re.search(
		r'Result:(.*?)(?:\n▶️|\nFull agent output|\n\s*\n|$)', 
		comment_body, 
		re.DOTALL | re.IGNORECASE
	)
	
	if match:
		return match.group(1).strip()
	
	return None


def get_issue_comments_for_change_request(issue_number: str, target_username: str = DEFAULT_BOT_USERNAME) -> str | None:
	"""
	Get the last test result for change request processing.
	
	Args:
		issue_number: GitHub issue number
		target_username: Username to look for in comments
		
	Returns:
		str: Extracted result section from the last comment, None if not found
	"""
	url = get_repository_url(f"issues/{issue_number}/comments")
	headers = get_github_api_headers()
	
	try:
		response = requests.get(url, headers=headers)
		response.raise_for_status()
		comments = response.json()
		
		# Find the most recent comment by the target username
		target_comments = [
			comment for comment in comments 
			if comment.get("user", {}).get("login") == target_username
		]
		
		if target_comments:
			latest_comment = sorted(target_comments, key=lambda c: c["created_at"], reverse=True)[0]
			return extract_result_section_from_comment(latest_comment["body"])
		
		return None
		
	except requests.exceptions.HTTPError as e:
		print(f"ERROR: Failed to fetch issue comments: {e}")
		return None