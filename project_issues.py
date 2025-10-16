"""
Project Issues Module

This module provides functionality to fetch GitHub project issues from a specific project board.
It uses the GitHub GraphQL API to retrieve issues that are in a designated column/status,
along with their metadata including labels, comments, and state information.

The module is specifically configured to work with a particular GitHub project board
and column, filtering for open issues that are ready for automated testing.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
PROJECT_UNIQUE_ID = os.environ["PROJECT_UNIQUE_ID"]
COLUMN_ID = os.environ["COLUMN_ID"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

"""
Fetch all project issues from a specific GitHub project board column.

Queries the GitHub GraphQL API to retrieve open issues that are positioned in the
configured project column. Returns detailed issue information including body text,
labels, recent comments, and metadata needed for automated testing workflows.

Returns:
    list[dict]: List of issue dictionaries containing:
        - body (str): Issue description/body text
        - number (int): GitHub issue number
        - node_id (str): GitHub GraphQL node ID
        - labels (list[str]): List of label names attached to the issue
        - comments (list[dict]): Recent comments with author, body, and timestamp

Raises:
    requests.exceptions.HTTPError: If GitHub API requests fail
    KeyError: If required environment variables are missing
"""
def get_project_issues():
    """Fetch all project issues, their status, and labels"""
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

    request_headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
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
