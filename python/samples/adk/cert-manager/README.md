# cert-manager Monitoring Agent

A sample kagent agent that monitors and manages TLS certificates in a Kubernetes cluster using cert-manager.

## Overview

This agent demonstrates how to use the kagent cert-manager tools to:
- Monitor certificate health across the cluster
- Identify expiring or expired certificates
- Check issuer status and troubleshoot problems
- Trigger certificate renewals
- Investigate failed certificate requests

## Prerequisites

1. **cert-manager** must be installed in your Kubernetes cluster
2. **kagent** must be deployed with appropriate RBAC permissions
3. The agent needs access to cert-manager CRDs (Certificates, Issuers, ClusterIssuers, CertificateRequests)

## Deployment

### Option 1: Deploy as a BYO (Bring Your Own) Agent

Build and push the Docker image:

```bash
cd python/samples/adk/cert-manager
docker build -t your-registry/cert-manager-agent:latest -f Dockerfile .
docker push your-registry/cert-manager-agent:latest
```

Apply the Agent resource:

```bash
kubectl apply -f agent.yaml
```

### Option 2: Run Locally

```bash
cd python/samples/adk/cert-manager
uv run python -m cert_manager.agent
```

## Example Interactions

### Check Certificate Health

**User:** "Check the health of all certificates in the default namespace"

**Agent:** The agent will:
1. List all certificates in the default namespace
2. Check expiry status for each certificate
3. Highlight any certificates that are expiring soon or have expired
4. Provide recommendations

### Troubleshoot Certificate Issues

**User:** "Why is my-app-cert not ready?"

**Agent:** The agent will:
1. Get details of the certificate
2. Check the issuer status
3. Look for failed CertificateRequests
4. Verify the TLS secret exists
5. Provide troubleshooting guidance

### Renew a Certificate

**User:** "Renew the certificate example-cert in namespace production"

**Agent:** The agent will:
1. Verify the certificate exists
2. Trigger the renewal
3. Explain that cert-manager will process the request

## Agent Capabilities

The agent has access to these cert-manager tools:

- **ListCertificates**: Overview of all certificates
- **GetCertificate**: Details of a specific certificate
- **CheckCertificateExpiry**: Expiry warnings
- **ListClusterIssuers**: View ClusterIssuers
- **ListIssuers**: View Issuers in a namespace
- **GetIssuerStatus**: Check issuer readiness
- **TriggerRenewal**: Force certificate renewal
- **ListCertificateRequests**: Find pending/failed requests
- **GetCertificateSecret**: Verify TLS secret

## RBAC Requirements

The agent needs these Kubernetes permissions:

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

## Configuration

Edit `agent.yaml` to customize:
- Model provider (Google Gemini, OpenAI, etc.)
- Model name
- System instructions
- Environment variables

## License

Apache 2.0
