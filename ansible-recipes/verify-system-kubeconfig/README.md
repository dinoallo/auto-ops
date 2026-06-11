# Verifying System Kubeconfigs After Certificate Rotation

Chinese version: `README.zh-CN.md`

This recipe verifies that selected Kubernetes kubeconfigs can reach the API server readiness endpoint after certificate rotation.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation.
2. Checks `/readyz` with `/etc/kubernetes/admin.conf`.
3. Checks `/readyz` with `/etc/kubernetes/controller-manager.conf`.
4. Checks `/readyz` with `/etc/kubernetes/scheduler.conf`.

## Requirements

- A Kubernetes control plane with `kubectl` available on each target host
- Inventory group named `masters`
- The target kubeconfig files present under `/etc/kubernetes`
- API server access from each target host
- SSH access with privilege escalation when kubeconfig files are root-owned

No extra variables are required for the current playbook.

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/verify-system-kubeconfig/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-system-kubeconfig/playbook.yml
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/verify-system-kubeconfig/playbook.yml
```

## Important Warnings

- This recipe is read-only from the cluster perspective, but it depends on kubeconfigs that may contain sensitive client credentials.
- A successful `/readyz` response confirms basic API reachability, not full controller or scheduler behavior.
- If any check fails after certificate rotation, inspect the kubeconfig certificate authority data, client certificate, and API server availability before continuing.
