
"""
Test Issues Module

This module orchestrates automated testing of GitHub issues using browser automation agents.
It fetches issues from a project board, runs automated QA tests on each issue, and posts
the results back to GitHub as comments. The module handles concurrent test execution,
result formatting, and GitHub API interactions.

Key responsibilities:
- Fetching issues from GitHub project boards
- Managing concurrent test execution with rate limiting
- Processing test results and extracting key information
- Posting formatted test results as GitHub comments
- Video recording management and URL extraction
"""

import re
import os
import asyncio
import requests
from project_issues import get_project_issues
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = "bernardhealth/bernieportal"

"""
Extract the final result section from agent output.

Parses the agent's output text to find and extract the "Final Result:" section,
cleaning up ANSI color codes and log lines to return just the essential result.

Args:
    output (str): Raw output text from the browser automation agent
    
Returns:
    str: Cleaned final result text, or "No final result found." if not found
"""
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

"""
Format full agent output as a collapsible markdown section.

Takes the complete agent output and wraps it in a GitHub markdown
collapsible section for clean presentation in comments.

Args:
    full_output (str): Complete agent output text
    
Returns:
    str: Formatted markdown with collapsible details section
"""
def collapse_output(full_output):
    clean = re.sub(r'\x1b\[[0-9;]*m', '', full_output)

    return (
        f"<details><summary>Full agent output (click to expand)</summary>\n\n"
        f"```\n"
        f"{clean}\n"
        f"```\n"
        f"</details>"
    )

"""
Returns the body of the first comment mentioning the bot after the last test comment by the bot.
"""
def get_tagged_comment_after_last_test(comments, bot_username="Caleb-Hurst"):
    last_test_time = None
    # Find the most recent test comment by the bot
    for c in reversed(comments):
        if c["author"] == bot_username:
            last_test_time = c["createdAt"]
            break
    # Now look for a comment mentioning the bot after last_test_time
    for c in comments:
        if f"@{bot_username}" in c["body"]:
            if last_test_time is None or c["createdAt"] > last_test_time:
                return c["body"]
    return None


"""
Post a comment to a GitHub issue.

Uses the GitHub API to add a comment to the specified issue with the provided message.

Args:
    issue_number (int): GitHub issue number to comment on
    message (str): Comment body text to post
    
Raises:
    requests.exceptions.HTTPError: If the GitHub API request fails
"""
def comment_on_issue(issue_number, message):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.post(url, json={"body": message}, headers=headers)
    resp.raise_for_status()


"""
Extract video URL from agent output.

Searches for a VIDEO_URL:: pattern in the agent output and extracts the URL.
This is used to find uploaded test recording videos.

Args:
    output (str): Agent output text to search
    
Returns:
    str or None: The extracted video URL, or None if not found
"""
def extract_video_url(output):
    match = re.search(r'VIDEO_URL::(https?://\S+)', output)
    if match:
        return match.group(1)
    return None



"""
Run the browser automation agent for a specific GitHub issue.

Executes the bernard QA agent script for the given issue, processes the output,
and posts the results back to the GitHub issue as a comment. Creates a temporary
directory for the browser profile to ensure isolation between test runs.

Args:
    desc (str): Issue description or test instructions
    number (int): GitHub issue number
    
Side Effects:
    - Creates temporary directory for browser profile
    - Executes subprocess for agent script
    - Posts comment to GitHub issue
    - Prints progress messages to stdout
"""
async def run_agent_for_issue(desc, number):
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix=f'browser_agent_{number}_')
    print(f"Running agent for issue #{number} with profile {temp_dir}...")
    process = await asyncio.create_subprocess_exec(
        "python", "run_bernard_qa_agent.py", desc, str(number), temp_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await process.communicate()
    output = stdout.decode()
    final_result = extract_final_result(output)
    collapsible = collapse_output(output)
    video_url = extract_video_url(output)
    video_link = f"\n\n▶️ [View Test Video Here]({video_url})" if video_url else ""
    comment = f"✅ Test run complete!\n\n**Result:**\n{final_result}{video_link}\n\n{collapsible}"
    comment_on_issue(number, comment)
    print(f"Commented on issue #{number}.")

"""
Main entry point for automated issue testing.

Fetches issues from the project board, filters out already tested issues,
and runs concurrent browser automation tests. Uses a semaphore to limit
concurrent execution and prevent resource exhaustion.

Flow:
    1. Fetch issues from project board
    2. Filter out issues with 'ai-tested' label
    3. Check for tagged comments for retesting
    4. Execute tests concurrently with rate limiting
    5. Handle results via individual agent runs
"""
async def main():
    issues = get_project_issues()
    concurrency_limiter = asyncio.Semaphore(5)  # Limit concurrency to 5 agents at a time (adjust as needed)

    async def run_with_concurrency_limit(desc, number):
        async with concurrency_limiter:
            await run_agent_for_issue(desc, number)

    agent_tasks = []
    for issue in issues:
        # Skip if issue has the 'ai-tested' label
        if 'ai-tested' in [l.lower() for l in issue.get('labels', [])]:
            print(f"[SKIP] Issue #{issue['number']} has 'ai-tested' label, skipping.")
            continue
        # Check for tagged comment after last test
        tagged_comment = get_tagged_comment_after_last_test(issue.get("comments", []), "Caleb-Hurst")
        desc = tagged_comment if tagged_comment else issue["body"]
        number = issue["number"]
        node_id = issue.get("node_id")
        if not node_id:
            print(f"[SKIP] Issue #{number} missing node_id, skipping.")
            continue
        agent_tasks.append(run_with_concurrency_limit(desc, number))

    if agent_tasks:
        await asyncio.gather(*agent_tasks)



if __name__ == "__main__":
    asyncio.run(main())
