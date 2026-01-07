# GitHub App Development for Webhook-Based Automation

## 1. Creating and Configuring a GitHub App

### Registration Steps
1. Go to GitHub Settings > Developer settings > GitHub Apps > New GitHub App
2. Configure:
   - **App name**: Unique identifier
   - **Homepage URL**: Your app's homepage
   - **Webhook URL**: Endpoint to receive events (e.g., `https://your-server.com/webhook`)
   - **Webhook secret**: Random string for payload verification (high entropy recommended)
   - **Permissions**: Select minimum required permissions
   - **Events**: Subscribe to required webhook events

### Key Configuration Items
- **App ID**: Assigned by GitHub after creation
- **Private Key**: Generate and download `.pem` file for JWT signing
- **Client ID/Secret**: For OAuth flows (if needed)
- **Webhook Secret**: For payload signature verification

---

## 2. Required Permissions

| Operation | Permission | Access Level |
|-----------|------------|--------------|
| Read pull requests | `Pull requests` | Read |
| Get PR files/diff | `Pull requests` | Read |
| Create issue comments on PRs | `Issues` | Write |
| Create PR review comments | `Pull requests` | Write |
| Read repository contents | `Contents` | Read |

### Minimal Permission Set for PR Review Bot
```
Repository permissions:
  - Pull requests: Read & Write
  - Issues: Write (for timeline comments)
  - Contents: Read (for file access)
```

---

## 3. Webhook Events for Pull Requests

### Event: `pull_request`

Subscribe to the `pull_request` event and filter by action type.

#### Key Action Types
| Action | Trigger |
|--------|---------|
| `opened` | PR created |
| `synchronize` | New commits pushed to PR head branch |
| `reopened` | PR reopened |
| `closed` | PR closed or merged |
| `edited` | PR title/body edited |

#### Payload Structure
```json
{
  "action": "opened | synchronize | ...",
  "number": 123,
  "pull_request": {
    "id": 1234567890,
    "number": 123,
    "state": "open",
    "title": "PR Title",
    "body": "PR description",
    "head": {
      "ref": "feature-branch",
      "sha": "abc123..."
    },
    "base": {
      "ref": "main",
      "sha": "def456..."
    },
    "user": { "login": "author" },
    "html_url": "https://github.com/owner/repo/pull/123"
  },
  "repository": {
    "id": 12345,
    "full_name": "owner/repo",
    "clone_url": "https://github.com/owner/repo.git"
  },
  "sender": { "login": "user-who-triggered" },
  "installation": { "id": 98765 }
}
```

#### Synchronize Event Additional Fields
```json
{
  "action": "synchronize",
  "before": "previous-head-sha",
  "after": "new-head-sha",
  ...
}
```

---

## 4. Authentication: JWT vs Installation Token

### Authentication Flow
```
┌─────────────────┐    JWT Token     ┌─────────────────┐
│   GitHub App    │ ───────────────> │   GitHub API    │
│   (App-level)   │                  │   /app/*        │
└─────────────────┘                  └─────────────────┘
        │
        │ Exchange JWT for Installation Token
        ▼
┌─────────────────┐  Install Token   ┌─────────────────┐
│  Installation   │ ───────────────> │   GitHub API    │
│  (Repo-level)   │                  │   /repos/*      │
└─────────────────┘                  └─────────────────┘
```

### JWT Token (App-Level)
- **Purpose**: Authenticate as the GitHub App itself
- **Lifetime**: Maximum 10 minutes
- **Use cases**: Get installations, exchange for installation token
- **Endpoints**: Limited to `/app/*` endpoints

#### JWT Creation (Python)
```python
import jwt
import time

def create_jwt(app_id: int, private_key: str) -> str:
    """Create a JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now - 60,      # Issued 60s ago (clock drift)
        "exp": now + 600,     # Expires in 10 minutes
        "iss": app_id         # GitHub App ID
    }
    return jwt.encode(payload, private_key, algorithm="RS256")
```

### Installation Token (Repo-Level)
- **Purpose**: Act on behalf of the app in a specific installation
- **Lifetime**: 1 hour (auto-refreshable)
- **Use cases**: Read PRs, post comments, access repo contents
- **Endpoints**: Full access based on granted permissions

#### Get Installation Token
```python
import requests

def get_installation_token(jwt_token: str, installation_id: int) -> str:
    """Exchange JWT for installation access token."""
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()["token"]
```

---

## 5. Webhook Signature Verification

GitHub signs webhook payloads using HMAC-SHA256. Always verify before processing.

### Header
- `X-Hub-Signature-256`: `sha256=<hex-digest>`

### Python Implementation
```python
import hmac
import hashlib
from fastapi import HTTPException, Request

def verify_webhook_signature(
    payload_body: bytes,
    secret_token: str,
    signature_header: str | None
) -> None:
    """
    Verify GitHub webhook signature.

    Args:
        payload_body: Raw request body (bytes)
        secret_token: Webhook secret configured in GitHub App
        signature_header: Value of X-Hub-Signature-256 header

    Raises:
        HTTPException: If signature is missing or invalid
    """
    if not signature_header:
        raise HTTPException(
            status_code=403,
            detail="X-Hub-Signature-256 header is missing"
        )

    expected_signature = "sha256=" + hmac.new(
        key=secret_token.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(
            status_code=403,
            detail="Request signature verification failed"
        )
```

### FastAPI Middleware Example
```python
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
WEBHOOK_SECRET = "your-webhook-secret"

@app.post("/webhook")
async def handle_webhook(request: Request):
    # Get raw body BEFORE parsing JSON
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    verify_webhook_signature(body, WEBHOOK_SECRET, signature)

    # Now safe to parse
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "pull_request":
        action = payload["action"]
        if action in ("opened", "synchronize"):
            # Process PR
            pass

    return {"status": "ok"}
```

---

## 6. PyGithub Patterns for GitHub App Authentication

### Installation
```bash
pip install PyGithub pyjwt[crypto]
```

### Pattern 1: Using GithubIntegration (Recommended)
```python
from github import Auth, GithubIntegration, Github

# Load credentials
APP_ID = 123456
PRIVATE_KEY = open("private-key.pem").read()

# Create App authentication
auth = Auth.AppAuth(APP_ID, PRIVATE_KEY)
gi = GithubIntegration(auth=auth)

# Get installation for a specific repo
installation = gi.get_repo_installation("owner", "repo")

# Get authenticated Github instance for that installation
g = installation.get_github_for_installation()

# Now use normally
repo = g.get_repo("owner/repo")
pr = repo.get_pull(123)
pr.create_issue_comment("Hello from GitHub App!")
```

### Pattern 2: Direct Installation Auth
```python
from github import Auth, Github

APP_ID = 123456
PRIVATE_KEY = open("private-key.pem").read()
INSTALLATION_ID = 98765  # From webhook payload

# Create installation auth directly
auth = Auth.AppAuth(APP_ID, PRIVATE_KEY).get_installation_auth(INSTALLATION_ID)
g = Github(auth=auth)

# Use the authenticated client
repo = g.get_repo("owner/repo")
```

### Pattern 3: From Webhook Payload
```python
from github import Auth, GithubIntegration

def handle_pr_webhook(payload: dict):
    """Handle pull_request webhook event."""
    installation_id = payload["installation"]["id"]
    repo_full_name = payload["repository"]["full_name"]
    pr_number = payload["number"]

    # Authenticate
    auth = Auth.AppAuth(APP_ID, PRIVATE_KEY)
    gi = GithubIntegration(auth=auth)
    g = gi.get_github_for_installation(installation_id)

    # Access the PR
    repo = g.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    # Get PR diff/files
    files = pr.get_files()
    for f in files:
        print(f"File: {f.filename}, Status: {f.status}")
        print(f"Patch:\n{f.patch}")

    # Post a comment
    pr.create_issue_comment("Review completed!")

    # Or create a review with inline comments
    pr.create_review(
        body="LGTM!",
        event="APPROVE",  # or "REQUEST_CHANGES", "COMMENT"
        comments=[
            {
                "path": "src/main.py",
                "line": 10,
                "body": "Consider using a constant here"
            }
        ]
    )
```

### Complete Webhook Handler Example
```python
from fastapi import FastAPI, Request, HTTPException
from github import Auth, GithubIntegration
import hmac
import hashlib
import os

app = FastAPI()

# Configuration
APP_ID = int(os.environ["GITHUB_APP_ID"])
PRIVATE_KEY = os.environ["GITHUB_PRIVATE_KEY"]
WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]

def verify_signature(body: bytes, signature: str | None) -> None:
    if not signature:
        raise HTTPException(403, "Missing signature")
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(403, "Invalid signature")

def get_github_client(installation_id: int):
    auth = Auth.AppAuth(APP_ID, PRIVATE_KEY)
    gi = GithubIntegration(auth=auth)
    return gi.get_github_for_installation(installation_id)

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    verify_signature(body, request.headers.get("X-Hub-Signature-256"))

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event")

    if event == "pull_request":
        action = payload["action"]
        if action in ("opened", "synchronize"):
            installation_id = payload["installation"]["id"]
            repo_name = payload["repository"]["full_name"]
            pr_number = payload["number"]

            g = get_github_client(installation_id)
            repo = g.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # Your review logic here
            files = list(pr.get_files())
            pr.create_issue_comment(
                f"Received {action} event. Reviewing {len(files)} files..."
            )

    return {"status": "ok"}
```

---

## Sources

- [GitHub Docs: Building a GitHub App that responds to webhook events](https://docs.github.com/en/apps/creating-github-apps/writing-code-for-a-github-app/building-a-github-app-that-responds-to-webhook-events)
- [GitHub Docs: Using webhooks with GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/using-webhooks-with-github-apps)
- [GitHub Docs: Webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads)
- [GitHub Docs: Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
- [GitHub Docs: Permissions required for GitHub Apps](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps)
- [GitHub Docs: Choosing permissions for a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)
- [PyGithub Authentication Documentation](https://pygithub.readthedocs.io/en/stable/examples/Authentication.html)
- [PyGithub GithubIntegration Class](https://pygithub.readthedocs.io/en/stable/github_integration.html)
- [PyJWT GitHub Repository](https://github.com/jpadilla/pyjwt)
