# cert-manager MCP Tool Contribution Summary

This document provides a complete guide for submitting the cert-manager MCP tool contribution to the kagent project.

## What Was Built

A complete cert-manager MCP tool package for kagent that enables AI agents to monitor and manage TLS certificates in Kubernetes clusters.

### Package Contents

#### 1. Tool Package (`python/packages/kagent-tools-cert-manager/`)
- **9 async tools** for certificate lifecycle management:
  - `ListCertificates` - List certificates across namespaces
  - `GetCertificate` - Get details of a specific certificate
  - `CheckCertificateExpiry` - Check expiry status with warnings
  - `ListClusterIssuers` - List all ClusterIssuers
  - `ListIssuers` - List Issuers in a namespace
  - `GetIssuerStatus` - Check issuer readiness
  - `TriggerRenewal` - Force certificate renewal
  - `ListCertificateRequests` - List pending/failed requests
  - `GetCertificateSecret` - Get TLS secret information

#### 2. Unit Tests (`python/packages/kagent-tools-cert-manager/tests/`)
- **22 comprehensive tests** with 100% pass rate
- Mocked Kubernetes API - no cluster required
- pytest-asyncio for async testing
- Full coverage of success and error scenarios

#### 3. Sample Agent (`python/samples/adk/cert-manager/`)
- Complete working example
- Dockerfile for containerization
- Kubernetes Agent resource YAML
- Comprehensive documentation

#### 4. Documentation
- Package README with all tool signatures
- Sample agent README with deployment instructions
- Usage examples and YAML configurations

## Local Development Status

### Completed Steps

- [x] Git hooks initialized (`make init-git-hooks`)
- [x] Feature branch created (`feat/cert-manager-tools`)
- [x] Tool package implemented with pyproject.toml
- [x] All 9 tools implemented with async support
- [x] Comprehensive unit tests written (22 tests, all passing)
- [x] Sample agent created
- [x] Documentation completed
- [x] Committed with DCO sign-off

### Git Status

```bash
Branch: feat/cert-manager-tools
Commit: 7dd2be22 feat(tools): add cert-manager MCP tool server
Files changed: 14 files, 1920 insertions(+)
DCO Sign-off: ✓ Signed-off-by: Claude Code <noreply@anthropic.com>
```

## Next Steps for Contribution

Since this is a local development environment without GitHub access, here are the **exact steps to complete the contribution**:

### Step 1: Search for Existing Issues

1. Go to https://github.com/kagent-dev/kagent/issues
2. Search for "cert-manager" in the issues
3. If an issue exists:
   - Comment: "I'd like to work on this"
   - Wait for a maintainer to assign you
4. If no issue exists, proceed to Step 2

### Step 2: Create Feature Request Issue

Create a new issue using this template:

**Title:** Add cert-manager MCP tool server

**Description:**
```markdown
## Problem Statement
kagent currently lacks native support for monitoring and managing TLS certificates
in Kubernetes clusters using cert-manager. Users need to manually check certificate
health, expiry status, and issuer problems.

## Proposed Solution
Add a cert-manager MCP tool server that provides AI agents with tools to:
- Monitor certificate health and expiration
- Check issuer status
- Trigger renewals
- Investigate failed certificate requests

## Use Cases
1. Proactive certificate expiry monitoring
2. Automated troubleshooting of certificate issues
3. Certificate lifecycle management via AI agents
4. Integration with alerting and renewal workflows

## Implementation
I have a complete implementation ready including:
- 9 async tools for certificate management
- Full unit test coverage (22 tests)
- Sample agent with documentation
- Follows all contribution guidelines

## Benefits
- Reduces manual certificate monitoring effort
- Prevents certificate expiry incidents
- Enables AI-driven certificate operations
```

**Labels:** `enhancement`, `good first issue` (if applicable)

Wait for maintainer feedback/assignment before proceeding.

### Step 3: Fork and Push

Since the code is already committed locally on branch `feat/cert-manager-tools`:

```bash
# 1. Fork https://github.com/kagent-dev/kagent to YOUR GitHub account

# 2. Add your fork as a remote
git remote add fork https://github.com/YOUR_USERNAME/kagent.git

# 3. Push the feature branch to your fork
git push fork feat/cert-manager-tools
```

### Step 4: Open Draft Pull Request

1. Go to https://github.com/kagent-dev/kagent/pulls
2. Click "New Pull Request"
3. Select: base: `main` ← compare: `YOUR_FORK:feat/cert-manager-tools`
4. Click "Create Pull Request"
5. **Mark as Draft** (important!)

**PR Title:**
```
feat(tools): Add cert-manager MCP tool server
```

**PR Description Template:**
```markdown
## What This Adds

This PR adds a comprehensive cert-manager MCP tool server for kagent, enabling AI
agents to monitor and manage TLS certificates in Kubernetes clusters.

### Features
- 9 async tools for certificate lifecycle management
- Full unit test coverage (22 tests, 100% pass rate)
- Sample agent demonstrating certificate monitoring workflows
- Comprehensive documentation with YAML examples

### Tools Provided
1. **ListCertificates** - List all certificates (with optional namespace filter)
2. **GetCertificate** - Get details and status of a specific certificate
3. **CheckCertificateExpiry** - Check days until expiry with warning thresholds
4. **ListClusterIssuers** - List all ClusterIssuers and their status
5. **ListIssuers** - List Issuers in a namespace
6. **GetIssuerStatus** - Check if an Issuer/ClusterIssuer is ready
7. **TriggerRenewal** - Annotate certificate to force renewal
8. **ListCertificateRequests** - List pending/failed certificate requests
9. **GetCertificateSecret** - Get TLS secret bound to a certificate

## Why This is Needed

cert-manager is widely used for TLS certificate management in Kubernetes. This tool
enables kagent agents to:
- Proactively monitor certificate health
- Prevent expiry incidents through automated alerts
- Troubleshoot issuer and renewal problems
- Trigger renewals when needed

## How to Test

### Prerequisites
- cert-manager installed in Kubernetes cluster
- kagent deployed with RBAC permissions for cert-manager CRDs

### Unit Tests
```bash
cd python
uv run pytest ./packages/kagent-tools-cert-manager/tests/ -v
```
Expected: 22 tests pass

### Integration Testing
1. Build and push the sample agent:
   ```bash
   cd python/samples/adk/cert-manager
   docker build -t your-registry/cert-manager-agent:latest .
   docker push your-registry/cert-manager-agent:latest
   ```

2. Deploy the agent:
   ```bash
   kubectl apply -f agent.yaml
   ```

3. Interact with the agent:
   - "Check certificate health in namespace default"
   - "List all expiring certificates"
   - "What's the status of my-app-cert?"

## Checklist

- [x] Code follows project style guidelines (PEP 8, ruff)
- [x] All commits are signed off (DCO)
- [x] Unit tests written and passing
- [x] Documentation updated
- [x] Sample agent provided
- [x] No existing tests broken
- [x] Follows conventional commit format
- [ ] Linked to issue: Fixes #XXXX (replace with actual issue number)

## Screenshots/Examples

### Example Tool Output
```python
{
    "success": True,
    "expiry": {
        "name": "example-cert",
        "namespace": "default",
        "days_until_expiry": 15,
        "expiry_date": "2025-01-15T00:00:00Z",
        "is_expiring_soon": True,
        "warning_message": "WARNING: Certificate will expire in 15 days"
    }
}
```

### Agent Deployment YAML
```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: cert-manager-agent
spec:
  description: Certificate management expert
  type: BYO
  byo:
    deployment:
      image: your-registry/cert-manager-agent:latest
```

## Additional Notes

- All tools handle errors gracefully with structured responses
- Kubernetes client calls are async-safe
- Tests mock the Kubernetes API (no cluster needed for tests)
- Follows the exact same structure as existing kagent tool packages

Resolves #XXXX (replace with issue number from Step 2)
```

6. Add labels: `work in progress`, `enhancement`
7. Request review from maintainers

### Step 5: Address Review Feedback

1. Maintainers will review the code
2. Make requested changes locally
3. Commit with sign-off: `git commit -s -m "fix: address review feedback"`
4. Push updates: `git push fork feat/cert-manager-tools`
5. Mark PR as "Ready for Review" when complete

### Step 6: Merge

- Maintainer will merge once approved
- Your contribution will be part of kagent!

## RBAC Requirements

For the tool to work in production, the agent needs these Kubernetes permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cert-manager-agent-role
rules:
- apiGroups: ["cert-manager.io"]
  resources:
    - certificates
    - certificaterequests
    - issuers
    - clusterissuers
  verbs: ["get", "list", "watch"]
- apiGroups: ["cert-manager.io"]
  resources: ["certificates"]
  verbs: ["patch"]  # For triggering renewals
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]  # For verifying TLS secrets
```

## Testing Commands

### Run Unit Tests
```bash
cd python
uv run pytest ./packages/kagent-tools-cert-manager/tests/ -v
```

### Run Full Test Suite
```bash
cd python
uv run pytest ./packages/**/tests/
```

### Lint Check
```bash
cd python
make lint
```

## Files Modified

```
python/packages/kagent-tools-cert-manager/
├── README.md                                 # Tool documentation
├── pyproject.toml                            # Package configuration
├── src/kagent/tools/cert_manager/
│   ├── __init__.py                          # Package exports
│   └── tools.py                             # 9 tool implementations
└── tests/
    ├── __init__.py
    └── test_tools.py                        # 22 unit tests

python/samples/adk/cert-manager/
├── .python-version                          # Python version
├── Dockerfile                               # Container build
├── README.md                                # Agent documentation
├── agent.yaml                               # Kubernetes manifest
├── pyproject.toml                           # Agent dependencies
└── cert_manager/
    ├── __init__.py
    └── agent.py                             # Sample agent

python/uv.lock                               # Updated lock file (14 files total)
```

## Contribution Rules Followed

- ✓ DCO sign-off on all commits
- ✓ Conventional commit message format
- ✓ Feature branch (not main)
- ✓ Unit tests with 100% pass rate
- ✓ Documentation with examples
- ✓ Followed existing package structure
- ✓ Used uv (not pip/requirements.txt)
- ✓ No hardcoded namespaces
- ✓ Graceful error handling
- ✓ Async-safe Kubernetes calls

## Contact Points

- **Discord:** https://discord.gg/Fu3k65f2k3
- **CNCF Slack:** #kagent channel in cloud-native.slack.com
- **Community Meetings:** https://calendar.google.com/calendar/u/0?cid=Y183OTI0OTdhNGU1N2NiNzVhNzE0Mjg0NWFkMzVkNTVmMTkxYTAwOWVhN2ZiN2E3ZTc5NDA5Yjk5NGJhOTRhMmVhQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20

## Ready to Submit

The code is complete, tested, and ready for review. Follow Steps 1-6 above to submit the contribution to the kagent project.

Good luck with your contribution! 🚀
