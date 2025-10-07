
import asyncio
import re
import tempfile

from dotenv import load_dotenv

from bernard.github_interactions import comment_on_issue, get_project_issues, get_tagged_comment_after_last_test
from bernard.video import extract_video_url_from_output


def extract_final_result(output):
    # This regex matches 'Final Result:' and everything after it
    match = re.search(r'Final Result:(.*?)(?=\[?INFO\]?|\[?ERROR\]?|\[?WARNING\]?|\[?DEBUG\]?|$)', output, re.DOTALL)
    if match:
        result = match.group(1)
        # Remove ANSI color codes
        result = re.sub(r'\x1b\[[0-9;]*m', '', result)
        # Remove log lines from result (with or without brackets)
        result = re.sub(r'^(\[?\s*(INFO|WARNING|ERROR|DEBUG)\s*\]?)[^\n]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
        result = re.sub(r'^Check \.\/tmp\/recordings.*$', '', result, flags=re.MULTILINE)
        # Remove any extra blank lines
        result = re.sub(r'\n+', '\n', result)
        return result.strip()

    return "No final result found."

def make_collapsible(full_output):
    # Remove ANSI color codes
    clean = re.sub(r'\x1b\[[0-9;]*m', '', full_output)
    return f"<details><summary>Full agent output (click to expand)</summary>\n\n```\n{clean}\n```\n</details>"

# Load environment variables from .env file
load_dotenv()







async def run_agent_for_issue(description: str, issue_number: str) -> None:
	"""
	Run the Bernard QA agent for a specific issue and post results as a comment.
	
	Args:
		description: Issue description or tagged comment to process
		issue_number: GitHub issue number
	"""
	temporary_directory = tempfile.mkdtemp(prefix=f'browser_agent_{issue_number}_')
	print(f"Running agent for issue #{issue_number} with profile {temporary_directory}...")
	
	process = await asyncio.create_subprocess_exec(
		"python", "run_bernard_qa_agent.py", description, str(issue_number), temporary_directory,
		stdout=asyncio.subprocess.PIPE,
		stderr=asyncio.subprocess.STDOUT
	)
	
	stdout, _ = await process.communicate()
	output = stdout.decode()
	
	final_result = extract_final_result(output)
	collapsible_output = make_collapsible(output)
	video_url = extract_video_url_from_output(output)
	
	video_link = f"\n\n▶️ [View Test Video Here]({video_url})" if video_url else ""
	comment_message = f"✅ Test run complete!\n\n**Result:**\n{final_result}{video_link}\n\n{collapsible_output}"
	
	comment_on_issue(issue_number, comment_message)
	print(f"Commented on issue #{issue_number}.")

async def main() -> None:
	"""
	Main function to orchestrate testing of project issues.
	Fetches issues, processes them concurrently, and manages test execution.
	"""
	issues = get_project_issues()
	concurrency_semaphore = asyncio.Semaphore(5)  # Limit concurrency to 5 agents at a time

	async def run_with_concurrency_limit(description: str, issue_number: str) -> None:
		"""Run agent with concurrency limiting."""
		async with concurrency_semaphore:
			await run_agent_for_issue(description, issue_number)

	agent_tasks = []
	
	for issue in issues:
		issue_number = issue["number"]
		issue_labels = [label.lower() for label in issue.get('labels', [])]
		
		# Skip if issue has the 'ai-tested' label
		if 'ai-tested' in issue_labels:
			print(f"[SKIP] Issue #{issue_number} has 'ai-tested' label, skipping.")
			continue
		
		# Check for tagged comment after last test
		tagged_comment = get_tagged_comment_after_last_test(issue.get("comments", []))
		description = tagged_comment if tagged_comment else issue["body"]
		
		node_id = issue.get("node_id")
		if not node_id:
			print(f"[SKIP] Issue #{issue_number} missing node_id, skipping.")
			continue
		
		agent_tasks.append(run_with_concurrency_limit(description, issue_number))

	if agent_tasks:
		await asyncio.gather(*agent_tasks)
	else:
		print("No issues found to process.")



if __name__ == "__main__":
    asyncio.run(main())
