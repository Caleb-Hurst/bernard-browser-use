import os
import requests
from dotenv import load_dotenv

load_dotenv()
PROJECT_UNIQUE_ID = "PVT_kwDOAQ3_584AiFvQ"
COLUMN_ID = "f8088824"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

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
