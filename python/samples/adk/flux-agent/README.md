# Flux GitOps Agent

A sample kagent agent that specializes in managing FluxCD GitOps continuous delivery pipelines.

## Overview

This agent uses the `kagent-tools-flux` package to provide expert assistance with:
- Monitoring GitOps pipeline health
- Troubleshooting failed reconciliations
- Triggering manual syncs
- Managing Flux resources (Kustomizations, GitRepositories, HelmReleases)
- Providing insights into continuous delivery workflows

## Prerequisites

- FluxCD installed in your Kubernetes cluster
- kagent installed with RBAC permissions for Flux resources
- Google Gemini API key (or configure a different model)

## Deployment

1. Build the agent:
```bash
docker build -t localhost:5001/flux-agent:latest .
docker push localhost:5001/flux-agent:latest
```

2. Deploy to kagent:
```bash
kubectl apply -f agent.yaml
```

3. Create the required secret:
```bash
kubectl create secret generic kagent-google \
  --from-literal=GOOGLE_API_KEY=your-api-key \
  -n kagent
```

## Example Interactions

**Check overall health:**
```
User: Is Flux healthy in our cluster?
Agent: [Checks Flux system status and reports controller health]
```

**Find failing resources:**
```
User: What's not syncing right now?
Agent: [Lists failed reconciliations and provides debugging info]
```

**Trigger manual sync:**
```
User: Force sync the production kustomization in flux-system namespace
Agent: [Triggers reconciliation and confirms]
```

**Investigate failures:**
```
User: Why is the my-app helm release failing?
Agent: [Gets HelmRelease details and recent events, explains the issue]
```

## RBAC

Ensure the agent's ServiceAccount has the necessary permissions. See the README in the kagent-tools-flux package for the full RBAC configuration.

## Customization

Modify `flux_agent/agent.py` to:
- Change the LLM model
- Adjust the system instruction
- Add or remove tools
- Customize behavior for your organization's GitOps workflows
