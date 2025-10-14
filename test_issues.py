
import re
import os
import asyncio
import requests
from project_issues import get_project_issues
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = "bernardhealth/bernieportal"

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

def collapse_output(full_output):
    clean = re.sub(r'\x1b\[[0-9;]*m', '', full_output)

    return (
        f"<details><summary>Full agent output (click to expand)</summary>\n\n"
        f"```\n"
        f"{clean}\n"
        f"```\n"
        f"</details>"
    )

def get_tagged_comment_after_last_test(comments, bot_username="Caleb-Hurst"):
    """
    Returns the body of the first comment mentioning the bot after the last test comment by the bot.
    """
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


def comment_on_issue(issue_number, message):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.post(url, json={"body": message}, headers=headers)
    resp.raise_for_status()


def extract_video_url(output):
    match = re.search(r'VIDEO_URL::(https?://\S+)', output)
    if match:
        return match.group(1)
    return None



async def run_agent_for_issue(desc, number, labels_arg):
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix=f'browser_agent_{number}_')
    print(f"Running agent for issue #{number} with profile {temp_dir}...")
    # labels_arg will be passed in as an argument
    process = await asyncio.create_subprocess_exec(
        "python", "run_bernard_qa_agent.py", desc, str(number), temp_dir, labels_arg,
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

async def main():
    issues = get_project_issues()
    concurrency_limiter = asyncio.Semaphore(5)  # Limit concurrency to 5 agents at a time (adjust as needed)

    async def run_with_concurrency_limit(desc, number, labels_arg):
        async with concurrency_limiter:
            await run_agent_for_issue(desc, number, labels_arg)

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
        labels_arg = ",".join(issue.get("labels", []))
        agent_tasks.append(run_with_concurrency_limit(desc, number, labels_arg))

    if agent_tasks:
        await asyncio.gather(*agent_tasks)



if __name__ == "__main__":
    asyncio.run(main())
