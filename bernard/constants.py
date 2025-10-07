"""
Constants used across the Bernard automation system.
Centralized to avoid duplication and make configuration management easier.
"""
import os

# GitHub Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPOSITORY = "bernardhealth/bernieportal"
VIDEO_TAG_NAME = "video-uploads"

# Login Credentials
DEFAULT_LOGIN_USERNAME = 'alyssak@admin316.com'
DEFAULT_LOGIN_PASSWORD = 'Testing123!'

# Video Recording Configuration
DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1280
VIDEO_RECORDINGS_DIRECTORY = './tmp/recordings'

# Browser Configuration
DEFAULT_CHROME_PROFILE_DIRECTORY = './chrome_profile'

# Project Configuration - Import from project_configuration module
# These values need to be set as environment variables or updated in project_configuration.py
try:
	from bernard.project_configuration import COLUMN_ID, PROJECT_UNIQUE_ID
except ImportError:
	# Fallback to environment variables if project_configuration is not available
	PROJECT_UNIQUE_ID = os.environ.get("PROJECT_UNIQUE_ID", "")
	COLUMN_ID = os.environ.get("COLUMN_ID", "")

# OpenAI Configuration  
DEFAULT_MODEL = 'gpt-4.1-mini'
MAX_AGENT_STEPS = 50

# GitHub API Configuration
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Testing Configuration
DEFAULT_BOT_USERNAME = "Caleb-Hurst"