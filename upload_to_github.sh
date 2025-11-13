#!/usr/bin/env bash
set -euo pipefail

# === Usage ===
#   chmod +x upload_to_github.sh
#   ./upload_to_github.sh --repo my-repo-name --user your-github-username --private
# Optional flags:
#   --org your-org            # create under an org instead of your user
#   --public                  # (default is --private)
#   --email you@example.com   # git user.email if not set
#   --name "Your Name"        # git user.name if not set
#
# Auth options (one of):
#   1) Be logged in with GitHub CLI:  gh auth login
#   2) Export a PAT:  export GITHUB_TOKEN=ghp_...  (repo scope)

REPO_NAME=""
GH_USER=""
GH_ORG=""
VISIBILITY="private"
GIT_EMAIL=""
GIT_NAME=""

die(){ echo "ERROR: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_NAME="${2:-}"; shift 2;;
    --user) GH_USER="${2:-}"; shift 2;;
    --org)  GH_ORG="${2:-}"; shift 2;;
    --private) VISIBILITY="private"; shift;;
    --public)  VISIBILITY="public"; shift;;
    --email) GIT_EMAIL="${2:-}"; shift 2;;
    --name)  GIT_NAME="${2:-}"; shift 2;;
    -h|--help)
      grep '^#' "$0" | sed -e 's/^#\s\{0,1\}//'
      exit 0;;
    *) die "Unknown arg: $1";;
  esac
done

[[ -n "$REPO_NAME" ]] || die "--repo is required"
if [[ -z "$GH_ORG" && -z "$GH_USER" ]]; then
  die "Provide --user your-username or --org your-org"
fi

# Ensure git identity
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
fi

current_email="$(git config user.email || true)"
current_name="$(git config user.name || true)"

if [[ -z "$current_email" ]]; then
  [[ -n "$GIT_EMAIL" ]] || die "git user.email not set; pass --email you@example.com"
  git config user.email "$GIT_EMAIL"
fi
if [[ -z "$current_name" ]]; then
  [[ -n "$GIT_NAME" ]] || die "git user.name not set; pass --name 'Your Name'"
  git config user.name "$GIT_NAME"
fi

# Sensible .gitignore if missing
if [[ ! -f .gitignore ]]; then
  cat > .gitignore <<'EOF'
# OS / editor
.DS_Store
*.swp
*.swo
.vscode/
.idea/

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node / frontend
node_modules/

# Docker artifacts
*.log
*.tmp
.env
# Project volumes / generated rules cache (optional)
rules_cache/
EOF
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "Initial commit"
fi

# Make sure branch is main
git branch -M main

have_gh="no"
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    have_gh="yes"
  fi
fi

REPO_FULL=""
if [[ -n "$GH_ORG" ]]; then
  REPO_FULL="${GH_ORG}/${REPO_NAME}"
else
  REPO_FULL="${GH_USER}/${REPO_NAME}"
fi

create_repo_with_gh() {
  if [[ -n "$GH_ORG" ]]; then
    gh repo create "$REPO_FULL" --"$VISIBILITY" --source=. --remote=origin --push
  else
    gh repo create "$REPO_FULL" --"$VISIBILITY" --source=. --remote=origin --push
  fi
}

create_repo_with_api() {
  [[ -n "${GITHUB_TOKEN:-}" ]] || die "GITHUB_TOKEN env var not set; cannot use API fallback"

  api_url="https://api.github.com/user/repos"
  if [[ -n "$GH_ORG" ]]; then
    api_url="https://api.github.com/orgs/${GH_ORG}/repos"
  fi

  # Try to create (ignore if already exists)
  http_code=$(curl -sS -o /tmp/create_repo_resp.json -w "%{http_code}" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -d "{\"name\":\"${REPO_NAME}\",\"private\":$([[ "$VISIBILITY" == "private" ]] && echo true || echo false)}" \
    "$api_url" || true)

  if [[ "$http_code" != "201" && "$http_code" != "422" ]]; then
    echo "GitHub API response ($http_code):"; cat /tmp/create_repo_resp.json; echo
    die "Failed to create repo via API"
  fi

  # Set remote and push
  git remote remove origin 2>/dev/null || true
  git remote add origin "https://github.com/${REPO_FULL}.git"

  # Use token for push via credential helper (avoid embedding token in URL)
  git config credential.helper store
  cat > ~/.git-credentials <<EOF
https://${GITHUB_TOKEN}:x-oauth-basic@github.com
EOF

  git push -u origin main
}

# If origin already exists, just push
if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote 'origin' exists -> pushing to it"
  git push -u origin main
  echo "Done."
  exit 0
fi

echo "Creating GitHub repo: ${REPO_FULL} (${VISIBILITY})"
if [[ "$have_gh" == "yes" ]]; then
  create_repo_with_gh || {
    echo "gh create failed; falling back to API…"
    create_repo_with_api
  }
else
  echo "gh CLI not available or not logged in; using API with GITHUB_TOKEN…"
  create_repo_with_api
fi

echo "✅ Repo ready: https://github.com/${REPO_FULL}"
