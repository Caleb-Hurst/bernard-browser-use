# Bernard Browser Automation System

The Bernard system is an automated browser testing framework that integrates with GitHub issues to perform quality assurance testing on web applications. It uses AI-powered browser automation to execute test scenarios and provides comprehensive reporting through GitHub comments and video recordings.

## System Architecture

The refactored Bernard system follows a modular architecture with clear separation of concerns:

```
bernard/
├── __init__.py                    # Package initialization
├── constants.py                   # Centralized configuration constants
├── github_configuration.py       # GitHub API setup and authentication
├── github_interactions.py        # GitHub issue management and commenting
├── video.py                      # Video recording and upload functionality
└── project_configuration.py      # Project-specific GitHub settings

# Main execution files
├── run_bernard_qa_agent.py       # Main agent execution script
├── test_issues.py               # Issue processing orchestrator  
└── context_loader.py            # Context file loading utility
```

## Core Components

### 1. GitHub Configuration (`github_configuration.py`)
Handles GitHub API authentication and repository configuration:
- **`get_github_api_headers()`** - Returns headers for GitHub REST API requests
- **`get_github_graphql_headers()`** - Returns headers for GitHub GraphQL API requests  
- **`get_repository_url(endpoint)`** - Constructs repository-specific API URLs
- **`validate_github_configuration()`** - Validates required GitHub settings

### 2. GitHub Interactions (`github_interactions.py`)
Manages all GitHub issue operations:
- **`get_project_issues()`** - Fetches project issues via GraphQL with pagination
- **`comment_on_issue(issue_number, message)`** - Posts comments to GitHub issues
- **`update_issue_labels(issue_number)`** - Updates issue labels (removes 'needs-test', adds 'ai-tested')
- **`get_tagged_comment_after_last_test(comments)`** - Finds user comments requesting changes
- **`get_issue_comments_for_change_request(issue_number)`** - Retrieves previous test results for change requests

### 3. Video Management (`video.py`)
Handles video recording, processing, and uploads:
- **`get_or_create_github_release()`** - Creates or retrieves GitHub release for video storage
- **`upload_video_asset_to_github(upload_url, file_path)`** - Uploads video files to GitHub releases
- **`find_latest_video_file()`** - Locates the most recent video recording
- **`process_and_upload_video(browser_session, agent, issue_number)`** - Complete video processing workflow
- **`finalize_video_recording(video_recorder)`** - Safely stops and saves video recordings

### 4. Constants Management (`constants.py`)
Centralized configuration to eliminate duplication:
- GitHub authentication tokens and repository settings
- Video recording configuration (dimensions, directories)
- Browser and testing parameters
- Default credentials and model settings

### 5. Main Agent (`run_bernard_qa_agent.py`)
Primary execution script that orchestrates browser testing:
- Parses command-line arguments for task description, issue number, and browser profile
- Sets up browser configuration with video recording capabilities
- Creates and runs AI agent with appropriate context
- Processes video recordings and updates GitHub issues

### 6. Issue Orchestrator (`test_issues.py`)
Manages batch processing of GitHub project issues:
- Fetches all relevant project issues using GraphQL
- Filters issues based on labels and status
- Manages concurrent execution of multiple test agents
- Processes results and posts comments with video links

### 7. Context Loader (`context_loader.py`)
Loads contextual information from label-based text files:
- **`load_context_from_labels(labels, context_dir)`** - Loads and concatenates context files based on issue labels

## Configuration Requirements

### Environment Variables
The system requires several environment variables to be configured:

```bash
# Required: GitHub authentication
GITHUB_TOKEN=your_github_personal_access_token

# Required: GitHub project configuration  
PROJECT_UNIQUE_ID=your_github_project_unique_id
COLUMN_ID=your_github_project_column_id
```

### GitHub Personal Access Token
Create a GitHub Personal Access Token with the following permissions:
- `repo` - Full repository access
- `project` - Project access for reading project boards
- `write:discussion` - For commenting on issues

### Project Configuration
Update `bernard/project_configuration.py` with your specific GitHub project IDs:
1. Navigate to your GitHub project board
2. Use GraphQL API or browser developer tools to find `PROJECT_UNIQUE_ID`
3. Identify the `COLUMN_ID` for the column you want to process

## Usage

### Running Individual Issue Tests
Execute the main agent for a specific issue:

```bash
python run_bernard_qa_agent.py "Test description" "123" "/tmp/browser_profile" "label1,label2"
```

**Parameters:**
- `arg1` - Task description or test instructions
- `arg2` - GitHub issue number  
- `arg3` - Browser profile directory (optional)
- `arg4` - Comma-separated labels for context loading (optional)

### Processing Multiple Issues
Run the batch processor to handle multiple project issues:

```bash
python test_issues.py
```

This will:
1. Fetch all open issues from the configured project column
2. Skip issues already labeled with 'ai-tested'
3. Process issues concurrently (default: 5 concurrent agents)
4. Post results as GitHub comments with video recordings

### Context Loading
Create context files in the same directory as the scripts:
- File naming: `{label}.txt` (e.g., `onboarding.txt`, `login.txt`)
- Content: Relevant documentation, instructions, or context for that label
- The system automatically loads and includes context based on issue labels

## Video Recording

The system automatically records browser sessions and uploads them to GitHub:

1. **Recording Setup**: Videos are recorded at 1920x1280 resolution
2. **Storage**: Temporary files stored in `./tmp/recordings/`
3. **Upload**: Videos uploaded to GitHub releases under the "video-uploads" tag
4. **Integration**: Video links automatically included in issue comments

## Workflow Integration

### Typical Workflow
1. Issues are created with appropriate labels and moved to the designated project column
2. `test_issues.py` discovers new issues requiring testing
3. Individual agents are spawned for each issue using `run_bernard_qa_agent.py`
4. Browser automation executes the test scenarios
5. Results are posted as GitHub comments with video recordings
6. Issue labels are updated to reflect testing status

### Change Request Handling
When users mention `@Caleb-Hurst` in issue comments:
1. System detects tagged comments after the last test
2. Extracts previous test results for context
3. Runs agent with change request context
4. Posts updated results

## Error Handling and Monitoring

### Logging
- Console output provides real-time execution status
- Video processing errors are logged with warnings
- GitHub API errors include detailed error messages

### Failure Recovery
- Individual issue failures don't affect other concurrent tests
- Video upload failures are logged but don't prevent test completion
- Missing configuration values provide clear error messages

### Concurrency Management
- Semaphore-based concurrency limiting (default: 5 concurrent agents)
- Temporary directories prevent profile conflicts
- Isolated browser sessions for each test

## Development and Maintenance

### Code Style
- Uses tabs for indentation (following project standards)
- Full descriptive names (no abbreviations)
- Type hints for function parameters and returns
- Comprehensive docstrings for all public functions

### Testing
Before deploying changes:
1. Validate configuration with `validate_github_configuration()`
2. Test individual issue processing with known issue numbers
3. Verify video recording and upload functionality
4. Check GitHub API permissions and rate limits

### Extending the System
To add new functionality:
1. Create new modules in the `bernard/` directory
2. Update `constants.py` for any new configuration values
3. Follow the established pattern of separating concerns
4. Update this README with new functionality documentation

## Troubleshooting

### Common Issues
1. **"Missing PROJECT_UNIQUE_ID"** - Set environment variable or update `project_configuration.py`
2. **"GitHub API rate limit"** - Reduce concurrency or check token permissions
3. **"No video file found"** - Verify video recording is enabled and `./tmp/recordings/` exists
4. **"Failed to upload video"** - Check GitHub token permissions for releases

### Debug Mode Haw to enable debug mode:
1. Add verbose logging to individual modules as needed
2. Use temporary browser profiles for testing: `/tmp/debug_browser_profile`
3. Run single issues before batch processing to validate configuration

This refactored system provides a robust, maintainable foundation for automated browser testing with comprehensive GitHub integration.