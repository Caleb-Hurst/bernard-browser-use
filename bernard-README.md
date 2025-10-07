# Getting Started

To set up and run this project, follow these steps:

1. **Install Python 3.11**

   Download and install Python 3.11 from [python.org](https://www.python.org/downloads/release/python-3110/).

2. **Create a virtual environment**
   ```bash
   python3.11 -m venv .venv
   ```
   This creates a local environment for dependencies.

3. **Activate the virtual environment**
   ```bash
   source .venv/bin/activate
   ```
   Ensures package installs are isolated from your global Python installation.

4. **Upgrade pip**
   ```bash
   pip install --upgrade pip
   ```

5. **Install project dependencies**
   ```bash
   pip install '.[video]'
   ```
   Installs all required dependencies, including those for video handling.

6. **Run the test script**
   ```bash
   python test_issues.py
   ```
   Run from the root of the repository, inside your virtual environment.

---

# High-Level Overview of Key Files

- **test_issues.py**
  Fetches and processes GitHub issues belonging to a specified project board column (like "AI QA"). Handles filtering, result extraction, and orchestrates which tickets are sent for testing.

- **run_bernard_qa_agent.py**
  Coordinates the automation for running QA on issues, uploading test video assets, updating labels, and posting results as comments directly on GitHub issues. It leverages the context loader for relevant background information.

- **context_loader.py**
  Supplies contextual data to the agent or test runner by loading text files based on issue labels, ensuring every test or automation run uses the correct supporting information.

---

# How They Work Together

- The **QA agent script** (`run_bernard_qa_agent.py`) is the main entry for automation: it loads context, executes tests, uploads results, and updates issue metadata.
- The **test script** (`test_issues.py`) identifies which issues are ready for testing and coordinates sending them to the QA agent.
- **context_loader.py** is a utility for loading contextual information, used by the agent to ensure each test has the right background.

---

# Automated Issue Testing Lifecycle

1. **Issue Identification:**
   When you run the test command, the script looks for tickets in a specified project board column (currently "AI QA").
2. **Batch Processing:**
   Up to 5 issues at a time are sent asynchronously to be tested in parallel.
3. **Automated Testing:**
   Each issue is processed by the QA agent, which performs the test, records the process, and generates a result video.
4. **Results and Labeling:**
   - The test output is posted as a comment directly on the GitHub issue, with a link to the video recording.
   - The issue is labeled with `ai-tested` to prevent duplicate testing.
5. **Manual Correction:**
   - If a test needs to be re-run or corrected, tagging `@Caleb-Hurst` in a comment on the issue signals the bot (currently simulated by Caleb-Hurst) to review and update the test process or result.

This workflow ensures issues in the "AI QA" column are systematically and efficiently tested, tracked, and updated, while allowing for human intervention when needed.

---

# Current Problems and Future Upgrades

- **Commenting as a User:**
  Currently, all comments on issues are made using a personal access token, so test results are posted as one of the maintainers. Ideally, this should be handled by a dedicated bot account or GitHub App for better security and auditability.

- **Prompt Clarity:**
  The full ticket contents are currently fed into the language model prompt, which can be overwhelming and confusing for the LLM. In the future, only relevant or summarized parts of the issue should be provided to improve test accuracy and efficiency.

- **Code Quality:**
  The codebase does not strictly follow any standards at the moment and is somewhat unstructured. Refactoring for consistency, maintainability, and style compliance is a recommended future step.

Improvements in these areas will enhance reliability, maintainability, and security as the project evolves.
