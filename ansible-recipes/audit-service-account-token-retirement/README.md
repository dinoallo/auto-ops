# Auditing ServiceAccount Token Retirement

Chinese version: `README.zh-CN.md`

This recipe checks ServiceAccount token blockers before removing the old ServiceAccount public key during Kubernetes root CA and ServiceAccount signing key rotation. It always supports legacy `kubernetes.io/service-account-token` Secret reference checks, and can also scan kubelet projected token files when `sa_key_cutover` is provided.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs API-based checks on the first master by default.
2. Reads all Secrets and Pods through `kubectl`.
3. Finds legacy `kubernetes.io/service-account-token` Secrets.
4. Fails if any Pod references one of those Secrets through a volume, `env`, or `envFrom`.
5. When `sa_key_cutover` is set, builds a live Pod UID map and scans kubelet projected token files on `masters:workers`.
6. Fails if a projected token `iat` is earlier than `sa_key_cutover`.
7. By default with projected auditing enabled, also fails if the projected `ca.crt` next to the token does not include the configured new CA file.

## Requirements

- A working kubeconfig, defaulting to `/etc/kubernetes/admin.conf`
- Inventory groups named `masters` and `workers` for projected token auditing
- `kubectl` and Python 3 on the API audit source host
- Python 3 on kubelet nodes for projected token auditing
- Permission to list Pods and Secrets across namespaces
- Root access to kubelet nodes when projected token auditing is enabled, because token files are under `/var/lib/kubelet/pods`

## Optional Variables

- `audit_source_host`: host used for API reads, defaults to the first host in `masters`
- `kubelet_target_hosts`: kubelet nodes to scan, defaults to `masters:workers`
- `kubeconfig`: kubeconfig used for the API audit, defaults to `'/etc/kubernetes/admin.conf'`
- `audit_legacy_service_account_tokens`: whether to check legacy token Secret references, defaults to `true`
- `audit_projected_service_account_tokens`: whether to check projected token files, defaults to true when `sa_key_cutover` is set
- `sa_key_cutover`: RFC3339 timestamp when kube-apiserver switched to `sa-new.key`
- `new_ca_file`: new root CA file to look for in projected `ca.crt`, defaults to `'/etc/kubernetes/pki/ca-new.crt'`
- `audit_projected_ca_bundle`: whether to check projected `ca.crt` contains `new_ca_file`, defaults to projected audit state
- `kubelet_pods_dir`: kubelet pod directory, defaults to `'/var/lib/kubelet/pods'`
- `python_interpreter`: Python interpreter used on target hosts, defaults to `'/usr/bin/python3'`
- `kubectl_command`: kubectl command path, defaults to `kubectl`

## Usage

Legacy Secret reference audit only:

```bash
ansible-playbook --syntax-check ansible-recipes/audit-service-account-token-retirement/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/audit-service-account-token-retirement/playbook.yml
```

Projected token and projected CA audit after switching the ServiceAccount signer:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/audit-service-account-token-retirement/playbook.yml \
  -e sa_key_cutover=2026-06-17T09:30:00Z \
  -e new_ca_file=/etc/kubernetes/pki/ca-new.crt
```

## Important Warnings

- If any legacy token Secret is still referenced, do not remove the old `sa.pub`.
- If projected tokens were issued before `sa_key_cutover`, restart or wait for the affected Pods before removing the old `sa.pub`.
- This playbook checks live Pods known to the API server and ignores stale kubelet pod directories whose UIDs no longer exist in the API.
