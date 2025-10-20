"""
Bernard QA Agent Runner

This module coordinates automated QA testing using browser automation agents. It handles
the complete lifecycle of QA test execution including:
- Loading contextual information from labels
- Setting up browser automation with proper configurations
- Executing QA tests on staging environments
- Recording test sessions as videos
- Uploading test artifacts to GitHub releases
- Updating issue labels and posting results

The agent acts as a manual QA engineer, logging into staging environments and
executing test scenarios defined in GitHub issues.
"""

import asyncio
import glob
import os
import re
import sys
from pathlib import Path

import requests

from browser_use import Agent, Browser, BrowserProfile, ChatOpenAI
from browser_use.browser.profile import ViewportSize
from browser_use.llm import ChatAnthropic

from context_loader import load_context_from_labels

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "bernardhealth/bernieportal"
TAG_NAME = "video-uploads"
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Caleb-Hurst")

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

"""
Get existing GitHub release or create a new one for video uploads.

Attempts to retrieve an existing release with the configured tag name.
If no release exists, creates a new one specifically for storing
test video uploads as assets.

Returns:
    tuple: (release_id, upload_url) for the GitHub release

Raises:
    requests.exceptions.HTTPError: If GitHub API requests fail
"""
def get_or_create_release():
    url = f"https://api.github.com/repos/{REPO}/releases/tags/{TAG_NAME}"
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        return r.json()["id"], r.json()["upload_url"]

    # If not found, create it
    url = f"https://api.github.com/repos/{REPO}/releases"
    data = {
        "tag_name": TAG_NAME,
        "name": "Video Uploads",
        "body": "Automated video uploads",
        "draft": False,
        "prerelease": False
    }

    r = requests.post(url, headers=headers, json=data)
    r.raise_for_status()

    return r.json()["id"], r.json()["upload_url"]


"""
Upload a video file as a GitHub release asset.

Takes a local video file and uploads it to the specified GitHub release
as an asset that can be downloaded publicly.

Args:
    upload_url (str): GitHub release upload URL template
    file_path (str): Local path to the video file to upload

Returns:
    str: Public download URL for the uploaded asset

Raises:
    requests.exceptions.HTTPError: If the upload fails
"""
def upload_asset(upload_url, file_path):
    upload_url = upload_url.split("{")[0]
    params = {"name": os.path.basename(file_path)}
    headers_asset = headers.copy()
    headers_asset["Content-Type"] = "video/mp4"

    with open(file_path, "rb") as f:
        r = requests.post(upload_url, headers=headers_asset, params=params, data=f)
    r.raise_for_status()

    return r.json()["browser_download_url"]


"""
Update GitHub issue labels after test completion.

Removes 'testing-in-progress' and 'changes-requested' labels and adds 'ai-tested'
label to indicate that automated testing has been completed for this issue.

Args:
    issue_number (int): GitHub issue number to update

Raises:
    requests.exceptions.HTTPError: If GitHub API requests fail
"""
def update_labels(issue_number):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}"
    headers_labels = headers.copy()

    # Get current labels
    resp = requests.get(url, headers=headers_labels)
    resp.raise_for_status()
    labels = [label['name'] for label in resp.json().get('labels', [])]

    # Remove 'testing-in-progress' and 'changes-requested' if present, add 'ai-tested'
    labels = [label for label in labels if label not in ['testing-in-progress', 'changes-requested']]

    if 'ai-tested' not in labels:
        labels.append('ai-tested')

    # Update labels
    resp = requests.patch(url, headers=headers_labels, json={"labels": labels})
    resp.raise_for_status()

"""
Main entry point for QA agent execution.

Coordinates the complete QA testing workflow:
1. Parses command line arguments for task, issue number, and browser profile
2. Loads contextual information based on issue labels
3. Sets up browser automation with proper viewport and recording
4. Executes the QA agent with appropriate prompts and context
5. Handles video recording, upload, and GitHub API updates

Command line arguments:
    sys.argv[1]: Task description or test instructions
    sys.argv[2]: GitHub issue number (optional)
    sys.argv[3]: Browser profile directory (optional)
    sys.argv[4]: Comma-separated labels for context loading (optional)
"""
async def main():
    # Get login info and directions from environment variables (set in workflow or locally)

    login_username = 'alyssak@admin316.com'
    login_password = 'Testing123!'

    # Accept labels as fourth argument (comma-separated string)
    labels = sys.argv[4].split(',') if len(sys.argv) > 4 else []

    directions = (
        f"YOU ARE THE MANUAL QA TEST ENGINEER. "
        f"You will receive details from a GitHub ticket to verify that code changes either worked or failed. DO NOT OPEN ANY NEW TABS, IF YOU NEED TO NAVIGATE TO A NEW URL USE THE ADDRESS BAR ONLY."
        f"Go to https://staging.bernieportal.com/en/login. If you are not already logged in, log in first using username: {login_username}, password: {login_password}."
        f"If you receive different log in credentials below use those instead"
        f"Once logged in, continue to the following task. Your job is to verify that something either works or does not work and REPORT the result. "
        f"Please keep your response as short and concise as possible. Try to use bullet points if possible."
    )

    # Accept issue number as second argument
    issue_number = sys.argv[2] if len(sys.argv) > 2 else None

    # Accept the task (prompt) as first argument
    task = sys.argv[1] if len(sys.argv) > 1 else ''

    # Accept user_data_dir as third argument, but default to a unique directory for each run
    import uuid
    user_data_dir = sys.argv[3] if len(sys.argv) > 3 else f'./chrome_profile_{uuid.uuid4().hex}'

    # Determine if this is a change request (based on changes-requested label)
    is_change_request = False
    if issue_number and 'changes-requested' in [label.lower() for label in labels]:
        is_change_request = True

    # Fetch the last test result (last comment by BOT_USERNAME) this will change later
    """
    Extract the result section from a GitHub comment body.

    Parses a comment body to find and extract the content after 'Result:'
    and before the next section marker (like video links or full output).
    Used to get the essential test result from previous QA runs.

    Args:
        comment_body (str): The full text of a GitHub comment

    Returns:
        str or None: The extracted result text, or None if no result section found
    """
    def extract_result_section(comment_body):
        # Extract the section between '✅ Test run complete!' and 'Full agent output (click to expand)'
        match = re.search(r'✅ Test run complete!(.*?)(?:Full agent output \(click to expand\)|$)', comment_body, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    last_test_result = None
    change_request_directions = None

    def get_most_recent_tagged_comment(comments, bot_username):
        tag_pattern = re.compile(rf'(^|\s)@{re.escape(bot_username)}(\s|$)', re.IGNORECASE | re.MULTILINE)
        tagged_comments = []
        for c in comments:
            body = c.get("body", "")
            # Check if any line is exactly @bot_username (case-insensitive, stripped)
            lines = [line.strip() for line in body.splitlines()]
            direct_tag = any(line.lower() == f"@{bot_username.lower()}" for line in lines)
            regex_tag = tag_pattern.search(body.strip())
            if direct_tag or regex_tag:
                tagged_comments.append(c)
        if tagged_comments:
            # Sort by created_at descending (most recent first)
            tagged_comments_sorted = sorted(tagged_comments, key=lambda c: c["created_at"], reverse=True)
            return tagged_comments_sorted[0]["body"]
        return None

    def fetch_all_issue_comments(repo, issue_number, headers):
        comments = []
        url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments?per_page=100"
        while url:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            comments.extend(resp.json())
            # Parse Link header for pagination
            link = resp.headers.get('Link', '')
            next_url = None
            if link:
                parts = link.split(',')
                for part in parts:
                    if 'rel="next"' in part:
                        next_url = part[part.find('<')+1:part.find('>')]
                        break
            url = next_url
        return comments

    if issue_number:
        comments = fetch_all_issue_comments(REPO, issue_number, headers)
        # Find the most recent comment authored by BOT_USERNAME (for test result)
        bot_comments = [c for c in comments if c.get("user", {}).get("login") == BOT_USERNAME]
        if bot_comments:
            most_recent_bot_comment = sorted(bot_comments, key=lambda c: c["created_at"], reverse=True)[0]
            last_comment_body = most_recent_bot_comment["body"]
            last_test_result = extract_result_section(last_comment_body)
        # Use helper to get the most recent comment tagging the bot
        change_request_directions = get_most_recent_tagged_comment(comments, BOT_USERNAME)

    # Build the full prompt
    if is_change_request and last_test_result and change_request_directions:
        login_username = 'wixife7553@chansd.com'
        login_password = 'Testing123!'

        full_task = (
            f"YOU ARE THE MANUAL QA TEST ENGINEER. "
            f"You are receiving a CHANGE REQUEST based on the following feedback from the last test run.\n"
            f"DO NOT OPEN ANY NEW TABS, IF YOU NEED TO NAVIGATE TO A NEW URL USE THE ADDRESS BAR ONLY."
            f"DO NOT LOG OUT AND LOG BACK IN, STAY LOGGED IN, if you have trouble understanding what to do, consult the documentation provided"
            f"Many new pages you visit will take a second to load, if there is a loading modal, WAIT FOR IT TO DISSAPEAR and continue with your task."
            f"Please keep your response as short and concise as possible. USE BULLET POINTS IN YOUR RESPONSE. Below you will receive the results of your last test. "
            f"---\nLAST TEST RESULT (Result section only):\n{last_test_result}\n---\n"
            f"You will address these changes by going to https://staging.bernieportal.com/en/login. If you are not already logged in, log in first using username: {login_username}, password: {login_password}. If you receive different log in credentials below use those instead"
            f"Once logged in, continue to address the following change request. Your job is to verify that something either works or does not work and REPORT the result"
            f"\nCHANGE REQUEST INSTRUCTIONS:\n{change_request_directions}\n"
        )
    else:
        full_task = f"{directions}\n\n{task}"


    # Load context from all label-matching .txt files
    context = load_context_from_labels(labels, context_dir=Path(__file__).parent / "context")
    # Always include general.txt
    general_path = Path(__file__).parent / "context" / "general.txt"
    if general_path.exists():
        with open(general_path, "r") as f:
            general_context = f.read()
        context = general_context + "\n\n" + context

    # Load default config for browser profile and agent, then override as needed
    from browser_use.config import CONFIG
    width, height = 1920, 1280

    config = CONFIG.load_config()
    # Get default browser profile and agent config
    default_profile = config.get('browser_profile', {})
    default_agent = config.get('agent', {})

    # Override required fields for headless mode and window size
    default_profile['headless'] = True
    default_profile['window_size'] = {'width': width, 'height': height}
    default_profile['viewport'] = {'width': width, 'height': height}
    default_profile['user_data_dir'] = user_data_dir
    default_profile['args'] = [f'--window-size={width},{height}']

    profile = BrowserProfile(**default_profile)
    browser_session = Browser(
        browser_profile=profile,
        record_video_dir=Path('./tmp/recordings'),
        record_video_size={'width': width, 'height': height}
    )

    # Use default agent config, but override as needed
    agent_config = default_agent.copy() if default_agent else {}
    agent = Agent(
        task=full_task,
        llm=ChatAnthropic(model='claude-sonnet-4-0'),
        extend_system_message=context,
        browser_session=browser_session,
        **agent_config
    )

    await agent.run(max_steps=80)

    # Explicitly finalize the video recording if possible
    # Try both browser_session and agent.browser_session for compatibility
    video_recorder = None
    if hasattr(browser_session, "video_recorder"):
        video_recorder = getattr(browser_session, "video_recorder")
    elif hasattr(agent, "browser_session") and hasattr(agent.browser_session, "video_recorder"):
        video_recorder = getattr(agent.browser_session, "video_recorder")
    if video_recorder:
        try:
            video_recorder.stop_and_save()
        except Exception as e:
            print(f"[WARN] Failed to finalize video recording: {e}")

    # Find the latest video file in ./tmp/recordings
    video_files = glob.glob('./tmp/recordings/*.mp4')
    if video_files:
        latest_video = max(video_files, key=os.path.getmtime)
        print(f'Uploading video: {latest_video}')
        release = get_or_create_release()
        if release:
            release_id, upload_url = release
            video_url = upload_asset(upload_url, latest_video)
            print(f'Video uploaded! Download URL: {video_url}')
            print(f'VIDEO_URL::{video_url}')
            if issue_number:
                update_labels(issue_number)
        else:
            print('Failed to get or create release, skipping video upload.')
    else:
        print('No video file found to upload.')

if __name__ == '__main__':
    asyncio.run(main())
