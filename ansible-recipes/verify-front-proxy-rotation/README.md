# Verifying front-proxy Rotation

Chinese version: `README.zh-CN.md`

This recipe verifies Kubernetes aggregation API behavior after front-proxy
certificate rotation. It checks the aggregation authentication ConfigMap, lists
registered APIService objects, and queries the metrics API raw endpoint when the
metrics APIService is installed.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation.
2. Reads the `extension-apiserver-authentication` ConfigMap from the `kube-system` namespace.
3. Lists APIService objects.
4. Checks whether the metrics APIService is installed.
5. Queries `/apis/metrics.k8s.io/v1beta1` through the API server when metrics
   API is installed or `require_metrics_api=true`.
6. Prints APIService output and the metrics API response or skip reason.

## Requirements

- A Kubernetes control plane with `kubectl` available on each target host
- Inventory group named `masters`
- A working kubeconfig at `/etc/kubernetes/admin.conf`, unless `kubeconfig` is overridden
- API aggregation configured in the cluster
- Metrics API installed only when the metrics endpoint check is required
- SSH access with privilege escalation when the kubeconfig file is root-owned

No extra variables are required when the kubeadm default kubeconfig path matches your environment.

## Optional Variables

- `kubeconfig`: kubeconfig used for verification, defaults to `'/etc/kubernetes/admin.conf'`
- `metrics_apiservice_name`: APIService name to probe, defaults to `'v1beta1.metrics.k8s.io'`
- `metrics_raw_endpoint`: raw metrics API path to query, defaults to `'/apis/metrics.k8s.io/v1beta1'`
- `require_metrics_api`: fail when the metrics APIService is not installed, defaults to `false`
- `kubectl_retries`: retry count for API server checks, defaults to `12`
- `kubectl_delay`: seconds between API server check retries, defaults to `10`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/verify-front-proxy-rotation/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml
```

To use a custom kubeconfig:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml \
  -e kubeconfig=/etc/kubernetes/admin.conf
```

To require the metrics API endpoint check:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml \
  -e require_metrics_api=true
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml
```

## Important Warnings

- This recipe is read-only from the cluster perspective, but it depends on kubeconfigs that may contain sensitive client credentials.
- The playbook retries kubectl checks so static Pod restart windows do not
  produce false rotation failures.
- The metrics API raw endpoint check runs only when metrics API is installed or
  `require_metrics_api=true`.
- A successful check confirms basic aggregation API reachability, not every aggregated API implementation.
- If this fails after front-proxy rotation, inspect the front-proxy CA bundle, front-proxy client certificate, APIService conditions, and kube-apiserver logs before continuing.
