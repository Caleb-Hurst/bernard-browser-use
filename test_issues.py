import re
import os
import subprocess
import requests
from dotenv import load_dotenv

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
REPO = "Caleb-Hurst/bernard-browser-use"  # Change if needed


def get_issues():
    url = f"https://api.github.com/repos/{REPO}/issues"
    params = {"labels": "needs-test", "state": "open"}
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


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


def main():
    for issue in get_issues():
        desc = issue["body"]
        number = issue["number"]
        print(f"Running agent for issue #{number}...")
        # Run your agent, passing the issue number as the second argument
        result = subprocess.run(
            ["python", "run_bernard_qa_agent.py", desc, str(number)],
            capture_output=True, text=True
        )
        final_result = extract_final_result(result.stdout)
        collapsible = make_collapsible(result.stdout)
        video_url = extract_video_url(result.stdout)
        video_link = f"\n\n▶️ [View Test Video Here]({video_url})" if video_url else ""
        comment = f"✅ Test run complete!\n\n**Result:**\n{final_result}{video_link}\n\n{collapsible}"
        comment_on_issue(number, comment)
        print(f"Commented on issue #{number}.")


if __name__ == "__main__":
    main()
