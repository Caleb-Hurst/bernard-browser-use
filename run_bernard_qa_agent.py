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

import sys
import os
import asyncio
import requests
import glob
import re
from pathlib import Path
from context_loader import load_context_from_labels
from browser_use import Agent, Browser, BrowserProfile, ChatOpenAI
from browser_use.browser.profile import ViewportSize

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "bernardhealth/bernieportal"
TAG_NAME = "video-uploads"

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

"""Fetch the most recent comment by the github-actions bot for the given issue."""
def get_latest_github_actions_comment(issue_number):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    comments = resp.json()
    # github-actions bot username is 'github-actions[bot]'
    actions_comments = [c for c in comments if c.get("user", {}).get("login") == "github-actions[bot]"]
    if not actions_comments:
        return None
    # Return the body of the most recent comment
    return sorted(actions_comments, key=lambda c: c["created_at"], reverse=True)[0]["body"]

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

Removes 'needs-test' label and adds 'ai-tested' label to indicate
that automated testing has been completed for this issue.

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
    labels = [l['name'] for l in resp.json().get('labels', [])]

    # Remove 'needs-test' if present, add 'tested-by-bernard-agent'
    labels = [l for l in labels if l != 'needs-test']

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

    if any('feature-toggle' in label for label in labels):
        directions = (
            f"YOU ARE THE MANUAL QA TEST ENGINEER. "
            f"This test involves a FEATURE TOGGLE. Please ensure the feature toggle is enabled as described in the ticket or context. You may need to switch to an admin account using username to access the toggles please see the Feature Toggle Testing Instructions I have provided. Then log out and log back in as the below user type to test"
            f"You will receive details from a GitHub ticket to verify that code changes either worked or failed. DO NOT OPEN ANY NEW TABS, IF YOU NEED TO NAVIGATE TO A NEW URL USE THE ADDRESS BAR ONLY."
            f"Go to https://staging.bernieportal.com. If you are not already logged in, log in first using username: {login_username}, password: {login_password}. "
            f"Once logged in, continue to the following task. Your job is to verify that something either works or does not work and REPORT the result. "
            f"Please keep your response as short and concise as possible. Try to use bullet points if possible."
        )
    else:
        directions = (
            f"YOU ARE THE MANUAL QA TEST ENGINEER. "
            f"You will receive details from a GitHub ticket to verify that code changes either worked or failed. DO NOT OPEN ANY NEW TABS, IF YOU NEED TO NAVIGATE TO A NEW URL USE THE ADDRESS BAR ONLY."
            f"Go to https://staging.bernieportal.com. If you are not already logged in, log in first using username: {login_username}, password: {login_password}. "
            f"Once logged in, continue to the following task. Your job is to verify that something either works or does not work and REPORT the result. "
            f"Please keep your response as short and concise as possible. Try to use bullet points if possible."
        )

    # Accept issue number as second argument
    issue_number = sys.argv[2] if len(sys.argv) > 2 else None

    # Accept the task (prompt) as first argument
    task = sys.argv[1] if len(sys.argv) > 1 else ''

    # Accept user_data_dir as third argument (for unique browser profile)
    user_data_dir = sys.argv[3] if len(sys.argv) > 3 else './chrome_profile'

    # Determine if this is a change request (tagged comment)
    is_change_request = False
    if issue_number and f"@Caleb-Hurst" in task:
        is_change_request = True

    # Fetch the last test result (last comment by Caleb-Hurst) this will change later
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
        # Try to extract the section after 'Result:' and before the next section (e.g., '▶️' or 'Full agent output')
        match = re.search(r'Result:(.*?)(?:\n▶️|\nFull agent output|\n\s*\n|$)', comment_body, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    last_test_result = None

    if issue_number:
        url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        comments = resp.json()
        # Find the most recent comment by Caleb-Hurst
        caleb_comments = [c for c in comments if c.get("user", {}).get("login") == "Caleb-Hurst"]
        if caleb_comments:
            last_comment_body = sorted(caleb_comments, key=lambda c: c["created_at"], reverse=True)[0]["body"]
            last_test_result = extract_result_section(last_comment_body)

    # Build the full prompt
    if is_change_request and last_test_result:
        full_task = (
            f"{directions}\n\n"
            f"This is a CHANGE REQUEST based on the following feedback from the last test run.\n"
            f"---\nLAST TEST RESULT (Result section only):\n{last_test_result}\n---\n"
            f"Please address the following change request:\n{task}"
        )
    else:
        full_task = f"{directions}\n\n{task}"


    # Accept labels as fourth argument (comma-separated string)
    labels = sys.argv[4].split(',') if len(sys.argv) > 4 else []

    # Load context from all label-matching .txt files
    context = load_context_from_labels(labels, context_dir=Path(__file__).parent / "context")

    # Set up headless browser profile with matching window, viewport, and video size
    width, height = 1920, 1280

    profile = BrowserProfile(
        headless=True,
        window_size=ViewportSize(width=width, height=height),
        viewport=ViewportSize(width=width, height=height),
        user_data_dir=user_data_dir,
        args=[f'--window-size={width},{height}']
    )
    browser_session = Browser(
        browser_profile=profile,
        record_video_dir=Path('./tmp/recordings'),
        record_video_size={'width': width, 'height': height}
    )

    agent = Agent(
        task=full_task,
        llm=ChatOpenAI(model='gpt-4.1-mini'),
        extend_system_message=context,
        browser_session=browser_session,
    )

    await agent.run(max_steps=50)

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
