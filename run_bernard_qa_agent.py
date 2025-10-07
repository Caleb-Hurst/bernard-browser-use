import asyncio
import sys
from pathlib import Path

from bernard.constants import (
	DEFAULT_CHROME_PROFILE_DIRECTORY,
	DEFAULT_LOGIN_PASSWORD,
	DEFAULT_LOGIN_USERNAME,
	DEFAULT_MODEL,
	DEFAULT_VIDEO_HEIGHT,
	DEFAULT_VIDEO_WIDTH,
	MAX_AGENT_STEPS,
)
from bernard.github_interactions import get_issue_comments_for_change_request, update_issue_labels
from bernard.video import process_and_upload_video
from browser_use import Agent, Browser, BrowserProfile, ChatOpenAI
from browser_use.browser.profile import ViewportSize
from context_loader import load_context_from_labels


async def main() -> None:
	"""
	Main function to run the Bernard QA agent for browser-based testing.
	Handles argument parsing, browser setup, agent execution, and video processing.
	"""
	# Parse command line arguments
	task = sys.argv[1] if len(sys.argv) > 1 else ''
	issue_number = sys.argv[2] if len(sys.argv) > 2 else None
	user_data_directory = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_CHROME_PROFILE_DIRECTORY
	labels = sys.argv[4].split(',') if len(sys.argv) > 4 else []

	# Build system directions
	login_username = DEFAULT_LOGIN_USERNAME
	login_password = DEFAULT_LOGIN_PASSWORD
	system_directions = (
		f"YOU ARE THE MANUAL QA TEST ENGINEER. "
		f"You will receive details from a GitHub ticket to verify that code changes either worked or failed. "
		f"DO NOT OPEN ANY NEW TABS, IF YOU NEED TO NAVIGATE TO A NEW URL USE THE ADDRESS BAR ONLY. "
		f"Go to https://staging.bernieportal.com. If you are not already logged in, log in first using "
		f"username: {login_username}, password: {login_password}. "
		f"Once logged in, continue to the following task. Your job is to verify that something either "
		f"works or does not work and REPORT the result. "
		f"Please keep your response as short and concise as possible. Try to use bullet points if possible."
	)

	# Determine if this is a change request (tagged comment)
	is_change_request = False
	if issue_number and "@Caleb-Hurst" in task:
		is_change_request = True

	# Build the full task prompt
	if is_change_request:
		last_test_result = get_issue_comments_for_change_request(issue_number)
		if last_test_result:
			full_task = (
				f"{system_directions}\n\n"
				f"This is a CHANGE REQUEST based on the following feedback from the last test run.\n"
				f"---\nLAST TEST RESULT (Result section only):\n{last_test_result}\n---\n"
				f"Please address the following change request:\n{task}"
			)
		else:
			full_task = f"{system_directions}\n\n{task}"
	else:
		full_task = f"{system_directions}\n\n{task}"

	# Load context from label-matching .txt files
	context = load_context_from_labels(labels, context_dir=Path(__file__).parent)

	# Set up browser profile with video recording
	browser_profile = BrowserProfile(
		headless=True,
		window_size=ViewportSize(width=DEFAULT_VIDEO_WIDTH, height=DEFAULT_VIDEO_HEIGHT),
		viewport=ViewportSize(width=DEFAULT_VIDEO_WIDTH, height=DEFAULT_VIDEO_HEIGHT),
		user_data_dir=user_data_directory,
		args=[f'--window-size={DEFAULT_VIDEO_WIDTH},{DEFAULT_VIDEO_HEIGHT}']
	)

	browser_session = Browser(
		browser_profile=browser_profile,
		record_video_dir=Path('./tmp/recordings'),
		record_video_size={'width': DEFAULT_VIDEO_WIDTH, 'height': DEFAULT_VIDEO_HEIGHT}
	)

	# Create and run the agent
	agent = Agent(
		task=full_task,
		llm=ChatOpenAI(model=DEFAULT_MODEL),
		extend_system_message=context,
		browser_session=browser_session,
	)

	await agent.run(max_steps=MAX_AGENT_STEPS)

	# Process and upload video
	video_url = process_and_upload_video(browser_session, agent, issue_number)
	
	# Update issue labels if video was successfully uploaded
	if video_url and issue_number:
		update_issue_labels(issue_number)

if __name__ == '__main__':
    asyncio.run(main())
