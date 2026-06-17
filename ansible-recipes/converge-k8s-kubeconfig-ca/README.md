# Converging Kubernetes Kubeconfig CA Data

Chinese version: `README.zh-CN.md`

This recipe rewrites selected Kubernetes kubeconfigs so their embedded `certificate-authority-data` contains only the new root CA. It is intended for the end of a root CA rotation, after kube-apiserver has already converged to new-only serving and client CA material.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane hosts, one host at a time by default.
2. Backs up selected kubeconfigs under `/etc/kubernetes/kubeconfig-backups`.
3. Replaces `certificate-authority-data` in each kubeconfig with `new_ca_file`.
4. Verifies each kubeconfig contains exactly one CA certificate and matches the new root CA.
5. Verifies every kubeconfig can access `/readyz`.
6. Optionally restarts kube-controller-manager and kube-scheduler static Pods to reload their kubeconfigs.

## Requirements

- kubeconfigs under `/etc/kubernetes`
- New root CA file, defaulting to `/etc/kubernetes/pki/ca.crt`
- `kubectl` and Python 3 on target hosts
- SSH access with privilege escalation

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `kubeconfig_ca_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `new_ca_file`: CA file to embed, defaults to `pki_dir + '/ca.crt'`
- `kubeconfig_files`: list of kubeconfig files to rewrite, defaults to admin, controller-manager, and scheduler kubeconfigs
- `restart_static_pods`: whether to touch kube-controller-manager and kube-scheduler manifests after rewriting, defaults to `false`
- `wait_static_pods`: whether to wait for restarted static Pods, defaults to `restart_static_pods`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml \
  -e restart_static_pods=true
```

## Important Warnings

- Run this only after kube-apiserver is serving with new-root-CA-signed certificates and trusts new-root-CA-signed client certificates.
- Restart kube-controller-manager and kube-scheduler after rewriting their kubeconfigs so they reload the new CA data.
