import sys
import os
import asyncio
from pathlib import Path
from browser_use import Agent, Browser, BrowserProfile, ChatOpenAI
import requests
import glob

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "bernardhealth/bernard-browser-use"
TAG_NAME = "video-uploads"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

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

def upload_asset(upload_url, file_path):
    upload_url = upload_url.split("{")[0]
    params = {"name": os.path.basename(file_path)}
    headers_asset = headers.copy()
    headers_asset["Content-Type"] = "video/mp4"
    with open(file_path, "rb") as f:
        r = requests.post(upload_url, headers=headers_asset, params=params, data=f)
    r.raise_for_status()
    return r.json()["browser_download_url"]

def comment_on_issue(issue_number, message):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
    headers_comment = headers.copy()
    resp = requests.post(url, json={"body": message}, headers=headers_comment)
    resp.raise_for_status()

def update_labels(issue_number):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}"
    headers_labels = headers.copy()
    # Get current labels
    resp = requests.get(url, headers=headers_labels)
    resp.raise_for_status()
    labels = [l['name'] for l in resp.json().get('labels', [])]
    # Remove 'needs-test' if present, add 'tested-by-bernard-agent'
    labels = [l for l in labels if l != 'needs-test']
    if 'tested-by-bernard-agent' not in labels:
        labels.append('tested-by-bernard-agent')
    # Update labels
    resp = requests.patch(url, headers=headers_labels, json={"labels": labels})
    resp.raise_for_status()

async def main():
    # Get login info and directions from environment variables (set in workflow or locally)
    login_username = 'alyssak@admin316.com'
    login_password ='Testing123!'
    directions = f"YOU ARE THE MANUAL QA TEST ENGINEER go to https://staging.bernieportal.com Log in first using username:{login_username}, and passward:{login_password} please take the following testing steps and output your results."

    # Get the task from the command line argument, or use a default
    task = sys.argv[1] if len(sys.argv) > 1 else ''

    full_task = f"{directions}\n\n{task}"

    # Accept issue number as second argument
    issue_number = sys.argv[2] if len(sys.argv) > 2 else None

    # Accept labels as third argument (comma-separated string)
    labels = sys.argv[3].split(',') if len(sys.argv) > 3 else []

    # Context variable
    context = ""
    if 'recruiting' in labels:
        recruiting_path = str(Path(__file__).parent / 'recruiting.txt')
        print(f"[DEBUG] Checking for recruiting context at: {recruiting_path}")
        if os.path.exists(recruiting_path):
            with open(recruiting_path, 'r') as f:
                context = f.read()
            print(f"[DEBUG] Loaded recruiting context (length {len(context)}):\n{context}")
        else:
            print(f"[DEBUG] recruiting.txt not found at: {recruiting_path}")

    # Set up headless browser profile with matching window, viewport, and video size
    width, height = 1920, 1280
    profile = BrowserProfile(
        headless=True,
        window_size={'width': width, 'height': height},
        viewport={'width': width, 'height': height},
        user_data_dir='./chrome_profile',
        args=[f'--window-size={width},{height}']
    )
    browser_session = Browser(
        browser_profile=profile,
        record_video_dir=Path('./tmp/recordings'),
        record_video_size={'width': width, 'height': height}
    )

    # Wait a moment to ensure browser is fully initialized and sized
    import asyncio

    agent = Agent(
        task=full_task,
        llm=ChatOpenAI(model='gpt-5-mini'),
        extend_system_message=context,
        browser_session=browser_session,
    )
    await agent.run(max_steps=100)

    # Find the latest video file in ./tmp/recordings
    video_files = glob.glob('./tmp/recordings/*.mp4')
    if video_files:
        latest_video = max(video_files, key=os.path.getmtime)
        print(f'Uploading video: {latest_video}')
        release_id, upload_url = get_or_create_release()
        video_url = upload_asset(upload_url, latest_video)
        print(f'Video uploaded! Download URL: {video_url}')
        # Do NOT comment on the issue here; let the runner handle it
        print(f'VIDEO_URL::{video_url}')
        if issue_number:
            update_labels(issue_number)
    else:
        print('No video file found to upload.')

if __name__ == '__main__':
    asyncio.run(main())
