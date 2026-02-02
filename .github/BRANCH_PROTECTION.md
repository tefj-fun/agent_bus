# Branch Protection Rules

## Main Branch Protection

Configure the following rules for the `main` branch in GitHub repository settings:

### Required Settings

1. **Require pull request before merging**
   - Require approvals: 1 (for team review)
   - Dismiss stale pull request approvals when new commits are pushed
   - Require review from Code Owners (if CODEOWNERS file is configured)

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging
   - Required status checks:
     - `test` (CI job that runs tests)
     - `lint` (if configured)

3. **Require conversation resolution before merging**
   - All conversations must be resolved before merging

4. **Require signed commits** (optional, but recommended)
   - Require verified signatures on commits

5. **Require linear history** (optional)
   - Prevent merge commits, force squash or rebase

6. **Include administrators**
   - Apply these rules to administrators as well (can be disabled for emergencies)

7. **Restrict who can push to matching branches**
   - Optionally restrict direct pushes to specific users/teams

8. **Allow force pushes**: Disabled
9. **Allow deletions**: Disabled

## Setup Instructions

### Via GitHub Web UI

1. Go to repository Settings → Branches
2. Add rule for branch name pattern: `main`
3. Configure the settings above

### Via GitHub API (Scripted)

```bash
#!/bin/bash
# Setup branch protection for agent_bus main branch

OWNER="your-org-or-username"
REPO="agent_bus"
BRANCH="main"
GITHUB_TOKEN="your-github-token"

curl -X PUT \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": ["test"]
    },
    "enforce_admins": false,
    "required_pull_request_reviews": {
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": false,
      "required_approving_review_count": 1
    },
    "required_conversation_resolution": true,
    "restrictions": null,
    "allow_force_pushes": false,
    "allow_deletions": false
  }'
```

### Via GitHub CLI

```bash
# Install GitHub CLI if not already installed: https://cli.github.com/

# Enable branch protection
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"dismiss_stale_reviews":true,"required_approving_review_count":1}' \
  --field required_conversation_resolution=true \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

## Verification

After setup, verify by attempting to:
1. Push directly to main (should fail)
2. Create a PR without passing CI (should be blocked)
3. Merge a PR with failing tests (should be blocked)

## Bypass Procedure (Emergency Only)

If you need to bypass branch protection in an emergency:
1. Temporarily disable "Include administrators" in settings
2. Make the required change
3. Re-enable the protection immediately after

## Notes

- Branch protection is enforced at the GitHub level, not in the repository code
- This document serves as configuration reference and team agreement
- Update this document if protection rules change
- For multi-environment repos, consider separate rules for `develop`, `staging`, `production` branches
