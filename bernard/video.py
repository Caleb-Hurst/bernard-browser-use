"""
Video recording, processing and upload functionality for Bernard browser automation.
Handles video recording management, file processing, and GitHub release uploads.
"""
import glob
import os

import requests

from bernard.constants import VIDEO_RECORDINGS_DIRECTORY, VIDEO_TAG_NAME
from bernard.github_configuration import get_github_api_headers, get_repository_url


def get_or_create_github_release() -> tuple[str, str] | None:
	"""
	Get existing GitHub release for video uploads or create a new one.
	
	Returns:
		tuple: (release_id, upload_url) if successful, None if failed
	"""
	headers = get_github_api_headers()
	
	# Try to get existing release
	url = f"{get_repository_url('releases/tags')}/{VIDEO_TAG_NAME}"
	response = requests.get(url, headers=headers)
	
	if response.status_code == 200:
		release_data = response.json()
		return release_data["id"], release_data["upload_url"]
	
	# Create new release if not found
	url = get_repository_url('releases')
	data = {
		"tag_name": VIDEO_TAG_NAME,
		"name": "Video Uploads",
		"body": "Automated video uploads from Bernard browser testing",
		"draft": False,
		"prerelease": False
	}
	
	response = requests.post(url, headers=headers, json=data)
	
	try:
		response.raise_for_status()
		release_data = response.json()
		return release_data["id"], release_data["upload_url"]
	except requests.exceptions.HTTPError as e:
		print(f"ERROR: Failed to create GitHub release: {e}")
		return None


def upload_video_asset_to_github(upload_url: str, file_path: str) -> str | None:
	"""
	Upload a video file as an asset to a GitHub release.
	
	Args:
		upload_url: GitHub release upload URL
		file_path: Path to the video file to upload
		
	Returns:
		str: Browser download URL for the uploaded video, None if failed
	"""
	# Remove the template part from the upload URL
	upload_url = upload_url.split("{")[0]
	
	params = {"name": os.path.basename(file_path)}
	
	headers = get_github_api_headers()
	headers["Content-Type"] = "video/mp4"
	
	try:
		with open(file_path, "rb") as video_file:
			response = requests.post(upload_url, headers=headers, params=params, data=video_file)
		
		response.raise_for_status()
		return response.json()["browser_download_url"]
		
	except requests.exceptions.HTTPError as e:
		print(f"ERROR: Failed to upload video asset: {e}")
		return None
	except FileNotFoundError:
		print(f"ERROR: Video file not found: {file_path}")
		return None


def find_latest_video_file(recordings_directory: str = VIDEO_RECORDINGS_DIRECTORY) -> str | None:
	"""
	Find the most recently created video file in the recordings directory.
	
	Args:
		recordings_directory: Directory to search for video files
		
	Returns:
		str: Path to the latest video file, None if no videos found
	"""
	video_pattern = os.path.join(recordings_directory, "*.mp4")
	video_files = glob.glob(video_pattern)
	
	if not video_files:
		return None
		
	return max(video_files, key=os.path.getmtime)


def finalize_video_recording(video_recorder) -> None:
	"""
	Attempt to finalize video recording by stopping and saving.
	
	Args:
		video_recorder: Video recorder object with stop_and_save method
	"""
	if video_recorder:
		try:
			video_recorder.stop_and_save()
			print("Video recording finalized successfully")
		except Exception as e:
			print(f"WARNING: Failed to finalize video recording: {e}")


def get_video_recorder_from_session(browser_session, agent=None):
	"""
	Extract video recorder from browser session or agent for compatibility.
	
	Args:
		browser_session: Browser session object
		agent: Optional agent object to check for video recorder
		
	Returns:
		Video recorder object if found, None otherwise
	"""
	# Try browser_session first
	if hasattr(browser_session, "video_recorder"):
		return getattr(browser_session, "video_recorder")
	
	# Try agent.browser_session for compatibility
	if agent and hasattr(agent, "browser_session") and hasattr(agent.browser_session, "video_recorder"):
		return getattr(agent.browser_session, "video_recorder")
	
	return None


def extract_video_url_from_output(output: str) -> str | None:
	"""
	Extract video URL from agent output using regex pattern.
	
	Args:
		output: Agent execution output string
		
	Returns:
		str: Video URL if found, None otherwise
	"""
	import re
	match = re.search(r'VIDEO_URL::(https?://\S+)', output)
	if match:
		return match.group(1)
	return None


def process_and_upload_video(browser_session, agent=None, issue_number: str | None = None) -> str | None:
	"""
	Complete video processing workflow: finalize recording, find file, and upload.
	
	Args:
		browser_session: Browser session with video recording
		agent: Optional agent object  
		issue_number: GitHub issue number for context
		
	Returns:
		str: Video download URL if successful, None if failed
	"""
	# Finalize video recording
	video_recorder = get_video_recorder_from_session(browser_session, agent)
	finalize_video_recording(video_recorder)
	
	# Find latest video file
	latest_video = find_latest_video_file()
	if not latest_video:
		print("No video file found to upload")
		return None
	
	print(f"Uploading video: {latest_video}")
	
	# Get or create GitHub release
	release = get_or_create_github_release()
	if not release:
		print("Failed to get or create release, skipping video upload")
		return None
	
	release_id, upload_url = release
	
	# Upload video asset
	video_url = upload_video_asset_to_github(upload_url, latest_video)
	if video_url:
		print(f"Video uploaded! Download URL: {video_url}")
		print(f"VIDEO_URL::{video_url}")
		return video_url
	
	return None