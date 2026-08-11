---
name: aro-hcp-int-kubectl-access
description: How to access the integration service and management clusters using kubectl.
---

You can kubectl-access int svc and mgmt clusters using like this:
```
kubectl get pods --kubeconfig int/int-uksouth-mgmt-1.kubeconfig
kubectl get pods --kubeconfig int/int-uksouth-svc-1.kubeconfig
```

Notes:
- Only read-only commands are allowed. Anything that is potentially destructive will be refused.
- Always start the invocation with a subcommand (`kubectl get …`). Any switches before the subcommand (e.g. `kubectl --kubeconfig …`) will be refused.
- If the kubeconfigs seem stale or are missing, tell the user to (re)login.
- Kubectl tells of current state, for how it go to that state you should look to kusto.

