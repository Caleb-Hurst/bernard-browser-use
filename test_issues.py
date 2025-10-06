
import re
import os
import asyncio
import requests
from dotenv import load_dotenv
from issue_project_status import PROJECT_UNIQUE_ID, COLUMN_ID, request_headers

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

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = "bernardhealth/bernieportal"  # Change if needed



def get_project_issues():
    """Fetch all project issues, their status, and labels in one GraphQL query (with pagination)."""
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
    issues = []
    while True:
        resp = requests.post(
            "https://api.github.com/graphql",
            headers=request_headers,
            json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        data = resp.json()
        items = data["data"]["node"]["items"]["nodes"]
        for item in items:
            content = item.get("content")
            if not content or content.get("state") != "OPEN":
                continue
            # Find if this item is in the desired column
            in_column = False
            for field_value in item["fieldValues"]["nodes"]:
                if field_value.get("optionId") == COLUMN_ID:
                    in_column = True
                    break
            if not in_column:
                continue
            labels = [l["name"] for l in content.get("labels", {}).get("nodes", [])]
            comments = [
                {
                    "author": c["author"]["login"] if c["author"] else None,
                    "body": c["body"],
                    "createdAt": c["createdAt"]
                }
                for c in content.get("comments", {}).get("nodes", [])
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
    return issues
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
    collapsible = make_collapsible(output)
    video_url = extract_video_url(output)
    video_link = f"\n\n▶️ [View Test Video Here]({video_url})" if video_url else ""
    comment = f"✅ Test run complete!\n\n**Result:**\n{final_result}{video_link}\n\n{collapsible}"
    comment_on_issue(number, comment)
    print(f"Commented on issue #{number}.")

async def main():
    issues = get_project_issues()
    semaphore = asyncio.Semaphore(5)  # Limit concurrency to 5 agents at a time (adjust as needed)

    async def run_with_semaphore(desc, number):
        async with semaphore:
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
        agent_tasks.append(run_with_semaphore(desc, number))

    if agent_tasks:
        await asyncio.gather(*agent_tasks)



if __name__ == "__main__":
    asyncio.run(main())
